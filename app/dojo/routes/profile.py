from flask import Blueprint, g, jsonify

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, not_found
from ..validation import PHONE_RE, POSTAL_RE, Errors, get_str, parse_json_body

bp = Blueprint("profile", __name__, url_prefix="/api")

MAX_ADDRESSES = 5


def _serialize(row):
    return {
        "id": row["id"], "label": row["label"], "recipient_name": row["recipient_name"],
        "phone": row["phone"], "line1": row["line1"], "line2": row["line2"],
        "province": row["province"], "postal_code": row["postal_code"],
        "is_default": bool(row["is_default"]), "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }


def _validate_address(data):
    errors = Errors()
    label = get_str(data, "label", errors, min_len=1, max_len=30, msg_key="label")
    recipient_name = get_str(data, "recipient_name", errors, min_len=2, max_len=50, msg_key="recipient_name")
    phone = get_str(data, "phone", errors, min_len=1, max_len=20, pattern=PHONE_RE, msg_key="phone")
    line1 = get_str(data, "line1", errors, min_len=5, max_len=100, msg_key="line1")
    line2 = get_str(data, "line2", errors, required=False, max_len=100, msg_key="line2")
    province = get_str(data, "province", errors, min_len=2, max_len=50, msg_key="province")
    postal_code = get_str(data, "postal_code", errors, min_len=1, max_len=10, pattern=POSTAL_RE, msg_key="postal_code")
    errors.raise_if_any()
    return {
        "label": label, "recipient_name": recipient_name, "phone": phone,
        "line1": line1, "line2": line2 or None, "province": province, "postal_code": postal_code,
    }


@bp.get("/me/addresses")
@require_auth()
@require_role("customer")
def list_addresses():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM addresses WHERE user_id=? ORDER BY created_at, id", (g.user["id"],)
    ).fetchall()
    return jsonify({"items": [_serialize(r) for r in rows]})


@bp.post("/me/addresses")
@require_auth()
@require_role("customer")
def create_address():
    data = parse_json_body()
    fields = _validate_address(data)
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM addresses WHERE user_id=?", (g.user["id"],)
        ).fetchone()["n"]
        if count >= MAX_ADDRESSES:
            conn.execute("ROLLBACK")
            raise ApiError("ADDRESS_LIMIT")
        is_default = 1 if count == 0 else 0
        conn.execute(
            "INSERT INTO addresses (user_id, label, recipient_name, phone, line1, line2, province, "
            "postal_code, is_default, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (g.user["id"], fields["label"], fields["recipient_name"], fields["phone"], fields["line1"],
             fields["line2"], fields["province"], fields["postal_code"], is_default, tu.to_db(tu.now_utc())),
        )
        new_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    row = conn.execute("SELECT * FROM addresses WHERE id=?", (new_id,)).fetchone()
    return jsonify(_serialize(row)), 201


def _own_address(conn, address_id):
    row = conn.execute(
        "SELECT * FROM addresses WHERE id=? AND user_id=?", (address_id, g.user["id"])
    ).fetchone()
    if row is None:
        raise not_found()
    return row


@bp.put("/me/addresses/<int:address_id>")
@require_auth()
@require_role("customer")
def update_address(address_id):
    conn = get_db()
    _own_address(conn, address_id)
    data = parse_json_body()
    fields = _validate_address(data)
    conn.execute(
        "UPDATE addresses SET label=?, recipient_name=?, phone=?, line1=?, line2=?, province=?, postal_code=? "
        "WHERE id=?",
        (fields["label"], fields["recipient_name"], fields["phone"], fields["line1"], fields["line2"],
         fields["province"], fields["postal_code"], address_id),
    )
    row = conn.execute("SELECT * FROM addresses WHERE id=?", (address_id,)).fetchone()
    return jsonify(_serialize(row))


@bp.delete("/me/addresses/<int:address_id>")
@require_auth()
@require_role("customer")
def delete_address(address_id):
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        addr = conn.execute(
            "SELECT * FROM addresses WHERE id=? AND user_id=?", (address_id, g.user["id"])
        ).fetchone()
        if addr is None:
            conn.execute("ROLLBACK")
            raise not_found()
        was_default = bool(addr["is_default"])
        conn.execute("DELETE FROM addresses WHERE id=?", (address_id,))
        if was_default:
            nxt = conn.execute(
                "SELECT id FROM addresses WHERE user_id=? ORDER BY created_at DESC, id LIMIT 1",
                (g.user["id"],),
            ).fetchone()
            if nxt is not None:
                conn.execute("UPDATE addresses SET is_default=1 WHERE id=?", (nxt["id"],))
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return "", 204


@bp.post("/me/addresses/<int:address_id>/default")
@require_auth()
@require_role("customer")
def set_default_address(address_id):
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        addr = conn.execute(
            "SELECT * FROM addresses WHERE id=? AND user_id=?", (address_id, g.user["id"])
        ).fetchone()
        if addr is None:
            conn.execute("ROLLBACK")
            raise not_found()
        conn.execute("UPDATE addresses SET is_default=0 WHERE user_id=? AND is_default=1", (g.user["id"],))
        conn.execute("UPDATE addresses SET is_default=1 WHERE id=?", (address_id,))
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    row = conn.execute("SELECT * FROM addresses WHERE id=?", (address_id,)).fetchone()
    return jsonify(_serialize(row))
