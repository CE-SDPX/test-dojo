import math
import sqlite3
from datetime import timedelta

from flask import Blueprint, g, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from .. import time_utils as tu
from ..auth import (
    create_session, require_auth, revoke_all_sessions_except, revoke_token,
)
from ..db import get_db
from ..errors import ApiError, field_error
from ..validation import (
    Errors, PASSWORD_RE, USERNAME_RE, get_str, parse_json_body,
)

bp = Blueprint("auth", __name__, url_prefix="/api")


def _serialize_me(row):
    is_customer = row["role"] == "customer"
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "phone": row["phone"] if is_customer else None,
        "birthdate": row["birthdate"] if is_customer else None,
        "must_change_password": bool(row["must_change_password"]),
        "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }


@bp.post("/auth/register")
def register():
    data = parse_json_body()
    errors = Errors()
    username = get_str(data, "username", errors, min_len=4, max_len=20, pattern=USERNAME_RE, msg_key="username")
    password = get_str(data, "password", errors, min_len=8, max_len=20, pattern=PASSWORD_RE, msg_key="password", trim=False)
    display_name = get_str(data, "display_name", errors, min_len=2, max_len=50, msg_key="display_name")

    birthdate_raw = data.get("birthdate")
    birthdate = None
    today = tu.bkk_date_of(tu.now_utc())
    if birthdate_raw is None:
        errors.add("birthdate", "required")
    else:
        try:
            birthdate = tu.parse_date(birthdate_raw)
            if birthdate > today or birthdate.year < 1900:
                errors.add("birthdate", "birthdate_format")
                birthdate = None
        except ValueError:
            errors.add("birthdate", "birthdate_format")
    errors.raise_if_any()

    if birthdate is not None and tu.age_years(birthdate, today) < 18:
        raise ApiError("VALIDATION_ERROR", details=[field_error("birthdate", "birthdate_age")])

    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE lower(username)=lower(?)", (username,)
        ).fetchone()
        if existing is not None:
            conn.execute("ROLLBACK")
            raise ApiError("USERNAME_TAKEN")
        now = tu.now_utc()
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, role, phone, birthdate, "
            "status, failed_login_count, locked_until, must_change_password, created_at) "
            "VALUES (?,?,?, 'customer', NULL, ?, 'ACTIVE', 0, NULL, 0, ?)",
            (username, generate_password_hash(password), display_name, birthdate.isoformat(), tu.to_db(now)),
        )
        uid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
        raise ApiError("USERNAME_TAKEN")
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return jsonify({
        "id": row["id"], "username": row["username"], "display_name": row["display_name"],
        "role": row["role"], "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }), 201


@bp.post("/auth/login")
def login():
    data = parse_json_body()
    errors = Errors()
    username = get_str(data, "username", errors, min_len=1, max_len=200, msg_key="invalid")
    password = get_str(data, "password", errors, min_len=1, max_len=200, msg_key="invalid", trim=False)
    errors.raise_if_any()

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE lower(username)=lower(?)", (username,)).fetchone()
    if user is None:
        raise ApiError("INVALID_CREDENTIALS")

    now = tu.now_utc()
    if user["locked_until"] and tu.from_db(user["locked_until"]) > now:
        remaining = tu.from_db(user["locked_until"]) - now
        minutes = max(1, math.ceil(remaining.total_seconds() / 60))
        raise ApiError("ACCOUNT_LOCKED", fmt={"n": minutes})

    if not check_password_hash(user["password_hash"], password):
        new_count = user["failed_login_count"] + 1
        locked_until = tu.to_db(now + timedelta(minutes=3)) if new_count >= 5 else None
        conn.execute(
            "UPDATE users SET failed_login_count=?, locked_until=? WHERE id=?",
            (new_count, locked_until, user["id"]),
        )
        raise ApiError("INVALID_CREDENTIALS")

    if user["status"] == "LOCKED":
        raise ApiError("ACCOUNT_DISABLED")

    conn.execute("UPDATE users SET failed_login_count=0, locked_until=NULL WHERE id=?", (user["id"],))
    token, expires = create_session(conn, user["id"])
    return jsonify({
        "token": token, "token_type": "Bearer", "expires_in": 600,
        "must_change_password": bool(user["must_change_password"]),
        "user": {
            "id": user["id"], "username": user["username"],
            "display_name": user["display_name"], "role": user["role"],
        },
    })


@bp.post("/auth/logout")
@require_auth(exempt_name="logout")
def logout():
    revoke_token(get_db(), g.token)
    return "", 204


@bp.post("/auth/change-password")
@require_auth(exempt_name="change_password")
def change_password():
    data = parse_json_body()
    errors = Errors()
    current = get_str(data, "current_password", errors, min_len=1, msg_key="invalid", trim=False)
    new_password = get_str(data, "new_password", errors, min_len=8, max_len=20, pattern=PASSWORD_RE, msg_key="password", trim=False)
    errors.raise_if_any()

    user = g.user
    if not check_password_hash(user["password_hash"], current):
        raise ApiError("INVALID_CURRENT_PASSWORD")
    if check_password_hash(user["password_hash"], new_password):
        raise ApiError("VALIDATION_ERROR", details=[field_error("new_password", "new_password_same")])

    conn = get_db()
    conn.execute(
        "UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?",
        (generate_password_hash(new_password), user["id"]),
    )
    revoke_all_sessions_except(conn, user["id"], g.token)
    return "", 204


@bp.get("/me")
@require_auth(exempt_name="me")
def get_me():
    return jsonify(_serialize_me(g.user))


@bp.put("/me")
@require_auth()
def update_me():
    data = parse_json_body()
    errors = Errors()
    user = g.user

    new_display_name = user["display_name"]
    if "display_name" in data:
        v = get_str(data, "display_name", errors, min_len=2, max_len=50, msg_key="display_name")
        if v is not None:
            new_display_name = v

    new_phone = user["phone"]
    if user["role"] == "customer" and "phone" in data:
        raw = data.get("phone")
        if raw is None or raw == "":
            new_phone = None
        elif isinstance(raw, str) and __import__("re").match(r"^0\d{9}$", raw.strip()):
            new_phone = raw.strip()
        else:
            errors.add("phone", "phone")

    errors.raise_if_any()
    conn = get_db()
    conn.execute(
        "UPDATE users SET display_name=?, phone=? WHERE id=?",
        (new_display_name, new_phone, user["id"]),
    )
    row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return jsonify(_serialize_me(row))
