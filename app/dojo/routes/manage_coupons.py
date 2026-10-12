import sqlite3

from flask import Blueprint, jsonify, request

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, field_error, not_found
from ..money import to_money
from ..services import coupons as coupon_service
from ..validation import COUPON_CODE_RE, Errors, get_bool, get_int, get_money, get_str, parse_json_body, query_page, query_page_size

bp = Blueprint("manage_coupons", __name__, url_prefix="/api/manage")


def _serialize(conn, row):
    return {
        "id": row["id"], "code": row["code"], "type": row["type"],
        "percent_off": row["percent_off"],
        "amount_off": to_money(row["amount_off_satang"]) if row["amount_off_satang"] is not None else None,
        "max_discount": to_money(row["max_discount_satang"]) if row["max_discount_satang"] is not None else None,
        "min_spend": to_money(row["min_spend_satang"]),
        "starts_at": tu.to_api_minute(tu.from_db(row["starts_at"])),
        "expires_at": tu.to_api_minute(tu.from_db(row["expires_at"])),
        "per_user_limit": row["per_user_limit"], "total_limit": row["total_limit"],
        "active": bool(row["active"]), "status": coupon_service.status_of(row),
        "usage_count": coupon_service.usage_count(conn, row["code"]),
        "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }


def _validate_discount_fields(data, errors, type_, required=True):
    percent_off = None
    amount_off = None
    max_discount = None
    if type_ == "PERCENT":
        percent_off = get_int(data, "percent_off", errors, min_val=0, max_val=100, msg_key="percent_off") if required or "percent_off" in data else None
        if "max_discount" in data and data.get("max_discount") is not None:
            max_discount = get_money(data, "max_discount", errors, min_satang=1)
    elif type_ == "FIXED":
        amount_off = get_money(data, "amount_off", errors) if required or "amount_off" in data else None
    return percent_off, amount_off, max_discount


@bp.get("/coupons")
@require_auth()
@require_role("manager", "admin")
def list_coupons():
    errors = Errors()
    q = request.args.get("q")
    if q is not None:
        q = q.strip()
        if len(q) > 100:
            errors.add("q", "q")
            q = None
        elif q == "":
            q = None
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    where = "1=1"
    params = []
    if q:
        where += " AND code LIKE ?"
        params.append(f"%{q.upper()}%")
    total = conn.execute(f"SELECT COUNT(*) AS n FROM coupons WHERE {where}", params).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM coupons WHERE {where} ORDER BY code LIMIT ? OFFSET ?", params + [page_size, offset]
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({"items": [_serialize(conn, r) for r in rows], "page": page, "page_size": page_size,
                     "total_items": total, "total_pages": total_pages})


@bp.post("/coupons")
@require_auth()
@require_role("manager", "admin")
def create_coupon():
    data = parse_json_body()
    errors = Errors()
    code = get_str(data, "code", errors, min_len=4, max_len=20, pattern=COUPON_CODE_RE, msg_key="coupon_code")
    if code:
        code = code.upper()
    type_ = get_str(data, "type", errors, required=True, msg_key="type")
    if type_ is not None and type_ not in ("PERCENT", "FIXED"):
        errors.add("type", "type")
        type_ = None
    percent_off, amount_off, max_discount = (None, None, None)
    if type_:
        percent_off, amount_off, max_discount = _validate_discount_fields(data, errors, type_)
    min_spend = get_money(data, "min_spend", errors, required=False, min_satang=0) if "min_spend" in data else 0
    per_user_limit = get_int(data, "per_user_limit", errors, min_val=1, max_val=99, msg_key="per_user_limit") if "per_user_limit" in data else 1
    total_limit = None
    if "total_limit" in data and data.get("total_limit") is not None:
        total_limit = get_int(data, "total_limit", errors, min_val=1, msg_key="total_limit")
    active = get_bool(data, "active", errors, required=False) if "active" in data else True

    from ..validation import get_minute_datetime
    starts_at = get_minute_datetime(data, "starts_at", errors)
    expires_at = get_minute_datetime(data, "expires_at", errors)
    if starts_at is not None and expires_at is not None and expires_at < starts_at:
        errors.add("expires_at", "expires_before_starts")
    errors.raise_if_any()

    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        now = tu.now_utc()
        conn.execute(
            "INSERT INTO coupons (code, type, percent_off, amount_off_satang, max_discount_satang, "
            "min_spend_satang, starts_at, expires_at, per_user_limit, total_limit, active, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (code, type_, percent_off, amount_off, max_discount, min_spend or 0,
             tu.to_db_minute(starts_at), tu.to_db_minute(expires_at), per_user_limit or 1,
             total_limit, 1 if active else 0, tu.to_db(now)),
        )
        cid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
        raise ApiError("COUPON_CODE_TAKEN")

    row = conn.execute("SELECT * FROM coupons WHERE id=?", (cid,)).fetchone()
    return jsonify(_serialize(conn, row)), 201


@bp.put("/coupons/<int:coupon_id>")
@require_auth()
@require_role("manager", "admin")
def update_coupon(coupon_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM coupons WHERE id=?", (coupon_id,)).fetchone()
    if existing is None:
        raise not_found()

    data = parse_json_body()
    errors = Errors()
    percent_off = existing["percent_off"]
    amount_off = existing["amount_off_satang"]
    max_discount = existing["max_discount_satang"]
    if existing["type"] == "PERCENT":
        if "percent_off" in data:
            percent_off = get_int(data, "percent_off", errors, min_val=1, max_val=100, msg_key="percent_off")
        if "max_discount" in data:
            max_discount = get_money(data, "max_discount", errors, min_satang=1) if data.get("max_discount") is not None else None
    else:
        if "amount_off" in data:
            amount_off = get_money(data, "amount_off", errors)

    min_spend = existing["min_spend_satang"]
    if "min_spend" in data:
        min_spend = get_money(data, "min_spend", errors, min_satang=0)
    per_user_limit = existing["per_user_limit"]
    if "per_user_limit" in data:
        per_user_limit = get_int(data, "per_user_limit", errors, min_val=1, max_val=99, msg_key="per_user_limit")
    total_limit = existing["total_limit"]
    if "total_limit" in data:
        total_limit = get_int(data, "total_limit", errors, min_val=1, msg_key="total_limit") if data.get("total_limit") is not None else None

    from ..validation import get_minute_datetime
    starts_at = tu.from_db(existing["starts_at"])
    if "starts_at" in data:
        starts_at = get_minute_datetime(data, "starts_at", errors)
    expires_at = tu.from_db(existing["expires_at"])
    if "expires_at" in data:
        expires_at = get_minute_datetime(data, "expires_at", errors)
    if starts_at is not None and expires_at is not None and expires_at < starts_at:
        errors.add("expires_at", "expires_before_starts")
    errors.raise_if_any()

    conn.execute(
        "UPDATE coupons SET percent_off=?, amount_off_satang=?, max_discount_satang=?, min_spend_satang=?, "
        "starts_at=?, expires_at=?, per_user_limit=?, total_limit=? WHERE id=?",
        (percent_off, amount_off, max_discount, min_spend, tu.to_db_minute(starts_at), tu.to_db_minute(expires_at),
         per_user_limit, total_limit, coupon_id),
    )
    row = conn.execute("SELECT * FROM coupons WHERE id=?", (coupon_id,)).fetchone()
    return jsonify(_serialize(conn, row))


@bp.patch("/coupons/<int:coupon_id>/active")
@require_auth()
@require_role("manager", "admin")
def set_coupon_active(coupon_id):
    data = parse_json_body()
    errors = Errors()
    active = get_bool(data, "active", errors)
    errors.raise_if_any()

    conn = get_db()
    row = conn.execute("SELECT id FROM coupons WHERE id=?", (coupon_id,)).fetchone()
    if row is None:
        raise not_found()
    conn.execute("UPDATE coupons SET active=? WHERE id=?", (1 if active else 0, coupon_id))
    row = conn.execute("SELECT * FROM coupons WHERE id=?", (coupon_id,)).fetchone()
    return jsonify(_serialize(conn, row))
