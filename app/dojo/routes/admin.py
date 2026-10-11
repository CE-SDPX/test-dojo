import secrets
import string

from flask import Blueprint, g, jsonify, request
from werkzeug.security import generate_password_hash

from .. import time_utils as tu
from ..auth import require_auth, require_role, revoke_all_sessions
from ..db import get_db
from ..errors import ApiError, not_found
from ..validation import ROLES, Errors, get_enum, parse_json_body, query_page, query_page_size

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _serialize(row):
    temp_locked = bool(row["locked_until"] and tu.from_db(row["locked_until"]) > tu.now_utc())
    return {
        "id": row["id"], "username": row["username"], "display_name": row["display_name"],
        "role": row["role"], "status": row["status"], "temporarily_locked": temp_locked,
        "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }


def _unlocked_admin_count(conn, exclude_id=None):
    if exclude_id is None:
        row = conn.execute("SELECT COUNT(*) AS n FROM users WHERE role='admin' AND status='ACTIVE'").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role='admin' AND status='ACTIVE' AND id<>?", (exclude_id,)
        ).fetchone()
    return row["n"]


@bp.get("/users")
@require_auth()
@require_role("admin")
def list_users():
    errors = Errors()
    q = request.args.get("q")
    if q is not None:
        q = q.strip()
        if len(q) > 100:
            errors.add("q", "q")
            q = None
        elif q == "":
            q = None
    role = None
    if request.args.get("role"):
        role = get_enum({"role": request.args.get("role")}, "role", errors, ROLES, msg_key="role")
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    where = ["1=1"]
    params = []
    if q:
        where.append("(lower(username) LIKE ? OR lower(display_name) LIKE ?)")
        params += [f"%{q.lower()}%", f"%{q.lower()}%"]
    if role:
        where.append("role=?")
        params.append(role)
    where_sql = " AND ".join(where)

    total = conn.execute(f"SELECT COUNT(*) AS n FROM users WHERE {where_sql}", params).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM users WHERE {where_sql} ORDER BY username COLLATE NOCASE, id LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({"items": [_serialize(r) for r in rows], "page": page, "page_size": page_size,
                     "total_items": total, "total_pages": total_pages})


@bp.post("/users/<int:user_id>/lock")
@require_auth()
@require_role("admin")
def lock_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        raise not_found()
    if user_id == g.user["id"]:
        raise ApiError("SELF_LOCK_FORBIDDEN")
    if user["status"] == "LOCKED":
        raise ApiError("ACCOUNT_ALREADY_LOCKED")
    if user["role"] == "admin" and _unlocked_admin_count(conn, exclude_id=user_id) == 0:
        raise ApiError("LAST_ADMIN")
    conn.execute("UPDATE users SET status='LOCKED' WHERE id=?", (user_id,))
    revoke_all_sessions(conn, user_id)
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return jsonify(_serialize(row))


@bp.post("/users/<int:user_id>/unlock")
@require_auth()
@require_role("admin")
def unlock_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        raise not_found()
    temp_locked = bool(user["locked_until"] and tu.from_db(user["locked_until"]) > tu.now_utc())
    if user["status"] != "LOCKED" and not temp_locked:
        raise ApiError("ACCOUNT_NOT_LOCKED")
    conn.execute(
        "UPDATE users SET status='ACTIVE', failed_login_count=0, locked_until=NULL WHERE id=?", (user_id,)
    )
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return jsonify(_serialize(row))


@bp.post("/users/<int:user_id>/reset-password")
@require_auth()
@require_role("admin")
def reset_password(user_id):
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        raise not_found()
    letters = string.ascii_letters
    digits = string.digits
    temp_password = "".join(secrets.choice(letters) for _ in range(8)) + "".join(secrets.choice(digits) for _ in range(4))
    conn.execute(
        "UPDATE users SET password_hash=?, must_change_password=1, failed_login_count=0, locked_until=NULL WHERE id=?",
        (generate_password_hash(temp_password), user_id),
    )
    revoke_all_sessions(conn, user_id)
    return jsonify({"temporary_password": temp_password})


@bp.patch("/users/<int:user_id>/role")
@require_auth()
@require_role("admin")
def change_role(user_id):
    data = parse_json_body()
    errors = Errors()
    new_role = get_enum(data, "role", errors, ROLES, msg_key="role")
    errors.raise_if_any()

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        raise not_found()
    if user["role"] == "admin" and new_role != "admin" and user["status"] == "ACTIVE":
        if _unlocked_admin_count(conn, exclude_id=user_id) == 0:
            raise ApiError("LAST_ADMIN")
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return jsonify(_serialize(row))
