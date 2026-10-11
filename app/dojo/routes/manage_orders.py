from flask import Blueprint, g, jsonify, request

from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, not_found
from ..services import orders as orders_service
from ..validation import ORDER_STATUSES, Errors, get_enum, query_page, query_page_size

bp = Blueprint("manage_orders", __name__, url_prefix="/api/manage")

_ALLOWED_NEXT = {"PAID": "PACKED", "PACKED": "SHIPPED", "SHIPPED": "DELIVERED"}
_FIELD_FOR_STATUS = {"PACKED": "packed_at", "SHIPPED": "shipped_at", "DELIVERED": "delivered_at"}


@bp.get("/orders")
@require_auth()
@require_role("staff", "admin")
def list_manage_orders():
    errors = Errors()
    status = None
    if request.args.get("status"):
        status = get_enum({"status": request.args.get("status")}, "status", errors, ORDER_STATUSES)
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
    where = ["1=1"]
    params = []
    if status:
        where.append("o.status=?")
        params.append(status)
    if q:
        if q.isdigit():
            where.append("o.id = ?")
            params.append(int(q))
        else:
            where.append("lower(u.username) LIKE ?")
            params.append(f"%{q.lower()}%")
    where_sql = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*) AS n FROM orders o JOIN users u ON u.id=o.user_id WHERE {where_sql}", params
    ).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT o.* FROM orders o JOIN users u ON u.id=o.user_id WHERE {where_sql} "
        "ORDER BY o.created_at DESC, o.id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    items = []
    for r in rows:
        count = conn.execute("SELECT COUNT(*) AS n FROM order_items WHERE order_id=?", (r["id"],)).fetchone()["n"]
        item = orders_service.serialize_list_item(r, count)
        customer = conn.execute(
            "SELECT id, username, display_name FROM users WHERE id=?", (r["user_id"],)
        ).fetchone()
        item["customer"] = {"id": customer["id"], "username": customer["username"], "display_name": customer["display_name"]}
        items.append(item)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({"items": items, "page": page, "page_size": page_size,
                     "total_items": total, "total_pages": total_pages})


@bp.patch("/orders/<int:order_id>/status")
@require_auth()
@require_role("staff", "admin")
def update_order_status(order_id):
    from ..validation import parse_json_body
    data = parse_json_body()
    errors = Errors()
    new_status = get_enum(data, "status", errors, {"PACKED", "SHIPPED", "DELIVERED"}, msg_key="status")
    errors.raise_if_any()

    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        raise not_found()
    if _ALLOWED_NEXT.get(order["status"]) != new_status:
        raise ApiError("INVALID_TRANSITION")

    from .. import time_utils as tu
    now = tu.now_utc()
    field = _FIELD_FOR_STATUS[new_status]
    conn.execute(f"UPDATE orders SET status=?, {field}=? WHERE id=?", (new_status, tu.to_db(now), order_id))
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return jsonify(orders_service.serialize(conn, order))
