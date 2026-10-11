from flask import Blueprint, g, jsonify

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, forbidden, not_found
from ..services import coupons as coupon_service
from ..services import orders as orders_service
from ..services import pricing as pricing_service
from ..services import stock as stock_service
from ..validation import (
    ORDER_STATUSES, PAY_METHODS, Errors, get_enum, get_int, get_str, parse_json_body, query_page,
    query_page_size,
)
from .cart import _cart_items

bp = Blueprint("orders", __name__, url_prefix="/api")


@bp.post("/orders")
@require_auth()
@require_role("customer")
def create_order():
    data = parse_json_body()
    errors = Errors()
    address_id = get_int(data, "address_id", errors, min_val=1)
    errors.raise_if_any()

    conn = get_db()
    address = conn.execute(
        "SELECT * FROM addresses WHERE id=? AND user_id=?", (address_id, g.user["id"])
    ).fetchone()
    if address is None:
        raise not_found()

    items = _cart_items(conn, g.user["id"])
    if not items:
        raise ApiError("CART_EMPTY")
    for it in items:
        if it["quantity"] > it["stock"]:
            raise ApiError("INSUFFICIENT_STOCK", message=f'Not enough stock for "{it["name"]}".')

    pricing_items = [{"unit_price_satang": r["price_satang"], "quantity": r["quantity"]} for r in items]
    cart_row = conn.execute("SELECT coupon_code FROM carts WHERE user_id=?", (g.user["id"],)).fetchone()
    coupon_code = cart_row["coupon_code"] if cart_row else None
    coupon_row = coupon_service.find_coupon(conn, coupon_code) if coupon_code else None

    pricing_wo_coupon, _ = pricing_service.compute(conn, pricing_items, None, g.user["id"])
    if coupon_row is not None:
        ok, reason, message = coupon_service.check_validity(
            conn, coupon_row, g.user["id"], pricing_wo_coupon["goods_total"]
        )
        if not ok:
            raise ApiError("COUPON_INVALID", message=message, reason=reason)
    pricing, _ = pricing_service.compute(conn, pricing_items, coupon_row, g.user["id"])

    conn.execute("BEGIN IMMEDIATE")
    try:
        for it in items:
            new_stock = stock_service.apply_movement(
                conn, it["product_id"], -it["quantity"], "ORDER", g.user["username"]
            )
            if new_stock is None:
                conn.execute("ROLLBACK")
                raise ApiError("INSUFFICIENT_STOCK", message=f'Not enough stock for "{it["name"]}".')
        now = tu.now_utc()
        conn.execute(
            "INSERT INTO orders (user_id, status, coupon_code, subtotal_satang, volume_discount_satang, "
            "coupon_discount_satang, goods_total_satang, vat_satang, shipping_satang, grand_total_satang, "
            "addr_label, addr_recipient_name, addr_phone, addr_line1, addr_line2, addr_province, "
            "addr_postal_code, refund_amount_satang, created_at) "
            "VALUES (?, 'PENDING_PAYMENT', ?, ?,?,?,?,?,?,?, ?,?,?,?,?,?,?, 0, ?)",
            (
                g.user["id"], coupon_row["code"] if coupon_row else None,
                pricing["subtotal"], pricing["volume_discount"], pricing["coupon_discount"],
                pricing["goods_total"], pricing["vat"], pricing["shipping"], pricing["grand_total"],
                address["label"], address["recipient_name"], address["phone"], address["line1"],
                address["line2"], address["province"], address["postal_code"], tu.to_db(now),
            ),
        )
        order_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        for it in items:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, sku, name, unit_price_satang, quantity, "
                "line_total_satang) VALUES (?,?,?,?,?,?,?)",
                (order_id, it["product_id"], it["sku"], it["name"], it["price_satang"], it["quantity"],
                 it["price_satang"] * it["quantity"]),
            )
        conn.execute("DELETE FROM cart_items WHERE user_id=?", (g.user["id"],))
        conn.execute("DELETE FROM carts WHERE user_id=?", (g.user["id"],))
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise

    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return jsonify(orders_service.serialize(conn, order)), 201


@bp.get("/orders")
@require_auth()
@require_role("customer")
def list_orders():
    errors = Errors()
    status = get_enum({"status": __import__("flask").request.args.get("status")}, "status", errors,
                       ORDER_STATUSES, required=False) if __import__("flask").request.args.get("status") else None
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    where = "user_id=?"
    params = [g.user["id"]]
    if status:
        where += " AND status=?"
        params.append(status)
    total = conn.execute(f"SELECT COUNT(*) AS n FROM orders WHERE {where}", params).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM orders WHERE {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    items = []
    for r in rows:
        count = conn.execute("SELECT COUNT(*) AS n FROM order_items WHERE order_id=?", (r["id"],)).fetchone()["n"]
        items.append(orders_service.serialize_list_item(r, count))
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({"items": items, "page": page, "page_size": page_size,
                     "total_items": total, "total_pages": total_pages})


def _load_order_for_view(conn, order_id):
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        raise not_found()
    role = g.user["role"]
    if role == "customer":
        if order["user_id"] != g.user["id"]:
            raise not_found()
    elif role in ("staff", "admin"):
        pass
    else:
        raise forbidden()
    return order


@bp.get("/orders/<int:order_id>")
@require_auth()
def get_order(order_id):
    conn = get_db()
    order = _load_order_for_view(conn, order_id)
    return jsonify(orders_service.serialize(conn, order))


@bp.post("/orders/<int:order_id>/pay")
@require_auth()
@require_role("customer")
def pay_order(order_id):
    data = parse_json_body()
    errors = Errors()
    get_enum(data, "method", errors, PAY_METHODS, msg_key="method")
    errors.raise_if_any()

    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, g.user["id"])).fetchone()
    if order is None:
        raise not_found()
    if order["status"] != "PENDING_PAYMENT":
        raise ApiError("INVALID_TRANSITION")
    now = tu.now_utc()
    conn.execute("UPDATE orders SET status='PAID', paid_at=? WHERE id=?", (tu.to_db(now), order_id))
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return jsonify(orders_service.serialize(conn, order))


@bp.post("/orders/<int:order_id>/cancel")
@require_auth()
def cancel_order_route(order_id):
    role = g.user["role"]
    if role not in ("customer", "staff", "admin"):
        raise forbidden()
    conn = get_db()
    if role == "customer":
        order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, g.user["id"])).fetchone()
    else:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        raise not_found()
    orders_service.cancel_order(conn, order_id, g.user["username"])
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return jsonify(orders_service.serialize(conn, order))


@bp.post("/orders/<int:order_id>/return")
@require_auth()
@require_role("customer")
def return_order(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, g.user["id"])).fetchone()
    if order is None:
        raise not_found()
    if order["status"] != "DELIVERED":
        raise ApiError("INVALID_TRANSITION")
    delivered_at = tu.from_db(order["delivered_at"])
    if tu.now_utc() > delivered_at + orders_service.RETURN_WINDOW:
        raise ApiError("RETURN_WINDOW_CLOSED")
    now = tu.now_utc()
    conn.execute(
        "UPDATE orders SET status='RETURNED', returned_at=?, refund_amount_satang=grand_total_satang WHERE id=?",
        (tu.to_db(now), order_id),
    )
    items = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id=?", (order_id,)
    ).fetchall()
    for it in items:
        stock_service.apply_movement(conn, it["product_id"], it["quantity"], "RETURN", g.user["username"])
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return jsonify(orders_service.serialize(conn, order))
