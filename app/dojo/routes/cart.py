from flask import Blueprint, g, jsonify

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, not_found
from ..money import to_money
from ..services import coupons as coupon_service
from ..services import pricing as pricing_service
from ..validation import Errors, get_int, get_str, parse_json_body
from .catalog import stock_status

bp = Blueprint("cart", __name__, url_prefix="/api")

MAX_QTY_PER_LINE = 10
MAX_LINES = 20


def _cart_items(conn, user_id):
    return conn.execute(
        "SELECT ci.id, ci.product_id, ci.quantity, p.sku, p.name, p.price_satang, p.stock "
        "FROM cart_items ci JOIN products p ON p.id = ci.product_id "
        "WHERE ci.user_id=? ORDER BY ci.id", (user_id,)
    ).fetchall()


def serialize_cart(conn, user_id):
    items = _cart_items(conn, user_id)
    cart_row = conn.execute("SELECT coupon_code FROM carts WHERE user_id=?", (user_id,)).fetchone()
    coupon_code = cart_row["coupon_code"] if cart_row else None
    coupon_row = coupon_service.find_coupon(conn, coupon_code) if coupon_code else None

    pricing_items = [{"unit_price_satang": r["price_satang"], "quantity": r["quantity"]} for r in items]
    pricing, coupon_info = pricing_service.compute(conn, pricing_items, coupon_row, user_id)

    return {
        "items": [
            {
                "id": r["id"], "product_id": r["product_id"], "sku": r["sku"], "name": r["name"],
                "unit_price": to_money(r["price_satang"]), "quantity": r["quantity"],
                "line_total": to_money(r["price_satang"] * r["quantity"]),
                "stock_status": stock_status(r["stock"]),
            }
            for r in items
        ],
        "coupon": coupon_info,
        "pricing": {k: to_money(v) for k, v in pricing.items()},
    }, pricing, items


@bp.get("/cart")
@require_auth()
@require_role("customer")
def get_cart():
    body, _, _ = serialize_cart(get_db(), g.user["id"])
    return jsonify(body)


@bp.post("/cart/items")
@require_auth()
@require_role("customer")
def add_cart_item():
    data = parse_json_body()
    errors = Errors()
    product_id = get_int(data, "product_id", errors, min_val=1)
    quantity = get_int(data, "quantity", errors, min_val=1, max_val=MAX_QTY_PER_LINE, msg_key="quantity")
    errors.raise_if_any()

    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if product is None:
        raise not_found()

    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            "SELECT * FROM cart_items WHERE user_id=? AND product_id=?", (g.user["id"], product_id)
        ).fetchone()
        new_qty = quantity + (existing["quantity"] if existing else 0)
        if new_qty > MAX_QTY_PER_LINE:
            conn.execute("ROLLBACK")
            raise ApiError("QUANTITY_LIMIT")
        if new_qty > product["stock"]:
            conn.execute("ROLLBACK")
            msg = "This product is out of stock." if product["stock"] == 0 else f"Only {product['stock']} left in stock."
            raise ApiError("INSUFFICIENT_STOCK", message=msg)
        if existing is None:
            line_count = conn.execute(
                "SELECT COUNT(*) AS n FROM cart_items WHERE user_id=?", (g.user["id"],)
            ).fetchone()["n"]
            if line_count >= MAX_LINES:
                conn.execute("ROLLBACK")
                raise ApiError("CART_LINE_LIMIT")
            conn.execute(
                "INSERT INTO cart_items (user_id, product_id, quantity, created_at) VALUES (?,?,?,?)",
                (g.user["id"], product_id, new_qty, tu.to_db(tu.now_utc())),
            )
        else:
            conn.execute("UPDATE cart_items SET quantity=? WHERE id=?", (new_qty, existing["id"]))
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    body, _, _ = serialize_cart(conn, g.user["id"])
    return jsonify(body)


@bp.patch("/cart/items/<int:item_id>")
@require_auth()
@require_role("customer")
def update_cart_item(item_id):
    data = parse_json_body()
    errors = Errors()
    quantity = get_int(data, "quantity", errors, min_val=1, max_val=MAX_QTY_PER_LINE, msg_key="quantity")
    errors.raise_if_any()

    conn = get_db()
    item = conn.execute(
        "SELECT ci.*, p.stock FROM cart_items ci JOIN products p ON p.id = ci.product_id "
        "WHERE ci.id=? AND ci.user_id=?", (item_id, g.user["id"])
    ).fetchone()
    if item is None:
        raise not_found()
    if quantity > item["stock"]:
        msg = "This product is out of stock." if item["stock"] == 0 else f"Only {item['stock']} left in stock."
        raise ApiError("INSUFFICIENT_STOCK", message=msg)
    conn.execute("UPDATE cart_items SET quantity=? WHERE id=?", (quantity, item_id))
    body, _, _ = serialize_cart(conn, g.user["id"])
    return jsonify(body)


@bp.delete("/cart/items/<int:item_id>")
@require_auth()
@require_role("customer")
def delete_cart_item(item_id):
    conn = get_db()
    cur = conn.execute("DELETE FROM cart_items WHERE id=? AND user_id=?", (item_id, g.user["id"]))
    if cur.rowcount == 0:
        raise not_found()
    body, _, _ = serialize_cart(conn, g.user["id"])
    return jsonify(body)


@bp.put("/cart/coupon")
@require_auth()
@require_role("customer")
def apply_coupon():
    data = parse_json_body()
    errors = Errors()
    code = get_str(data, "code", errors, min_len=1, max_len=50, msg_key="invalid")
    errors.raise_if_any()

    conn = get_db()
    items = _cart_items(conn, g.user["id"])
    if not items:
        raise ApiError("CART_EMPTY")

    pricing_items = [{"unit_price_satang": r["price_satang"], "quantity": r["quantity"]} for r in items]
    pricing_no_coupon, _ = pricing_service.compute(conn, pricing_items, None, g.user["id"])
    after_volume = pricing_no_coupon["goods_total"]

    coupon_row = coupon_service.find_coupon(conn, code)
    ok, reason, message = coupon_service.check_validity(conn, coupon_row, g.user["id"], after_volume)
    if not ok:
        raise ApiError("COUPON_INVALID", message=message, reason=reason)

    conn.execute(
        "INSERT INTO carts (user_id, coupon_code, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET coupon_code=excluded.coupon_code, updated_at=excluded.updated_at",
        (g.user["id"], coupon_row["code"], tu.to_db(tu.now_utc())),
    )
    body, _, _ = serialize_cart(conn, g.user["id"])
    return jsonify(body)


@bp.delete("/cart/coupon")
@require_auth()
@require_role("customer")
def remove_coupon():
    conn = get_db()
    conn.execute("DELETE FROM carts WHERE user_id=?", (g.user["id"],))
    body, _, _ = serialize_cart(conn, g.user["id"])
    return jsonify(body)
