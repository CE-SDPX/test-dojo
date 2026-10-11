"""Order lifecycle helpers shared by the API and the scheduler — PRD-ORDER."""
from __future__ import annotations

from datetime import timedelta

from .. import time_utils as tu
from ..errors import ApiError
from ..money import to_money
from . import stock as stock_service

CANCELLABLE_STATUSES = ("PENDING_PAYMENT", "PAID", "PACKED")
RETURN_WINDOW = timedelta(days=7)


def cancel_order(conn, order_id: int, actor: str) -> bool:
    """REQ-ORD-005. Returns True if cancelled, raises ApiError(INVALID_TRANSITION)
    if the order is not in a cancellable status."""
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        return False
    if order["status"] not in CANCELLABLE_STATUSES:
        raise ApiError("INVALID_TRANSITION")
    now = tu.now_utc()
    refund = order["grand_total_satang"] if order["status"] in ("PAID", "PACKED") else 0
    conn.execute(
        "UPDATE orders SET status='CANCELLED', cancelled_at=?, refund_amount_satang=? WHERE id=?",
        (tu.to_db(now), refund, order_id),
    )
    items = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id=?", (order_id,)
    ).fetchall()
    for it in items:
        stock_service.apply_movement(conn, it["product_id"], it["quantity"], "CANCEL", actor)
    return True


def serialize(conn, order) -> dict:
    items = conn.execute(
        "SELECT product_id, sku, name, unit_price_satang, quantity, line_total_satang "
        "FROM order_items WHERE order_id=? ORDER BY id", (order["id"],)
    ).fetchall()
    customer = conn.execute(
        "SELECT id, username, display_name FROM users WHERE id=?", (order["user_id"],)
    ).fetchone()
    delivered_at = tu.from_db(order["delivered_at"]) if order["delivered_at"] else None
    return_deadline = tu.to_api(delivered_at + RETURN_WINDOW) if order["status"] == "DELIVERED" and delivered_at else None
    return {
        "id": order["id"],
        "status": order["status"],
        "customer": {"id": customer["id"], "username": customer["username"], "display_name": customer["display_name"]},
        "items": [
            {
                "product_id": it["product_id"], "sku": it["sku"], "name": it["name"],
                "unit_price": to_money(it["unit_price_satang"]), "quantity": it["quantity"],
                "line_total": to_money(it["line_total_satang"]),
            }
            for it in items
        ],
        "coupon_code": order["coupon_code"],
        "pricing": {
            "subtotal": to_money(order["subtotal_satang"]),
            "volume_discount": to_money(order["volume_discount_satang"]),
            "coupon_discount": to_money(order["coupon_discount_satang"]),
            "goods_total": to_money(order["goods_total_satang"]),
            "vat": to_money(order["vat_satang"]),
            "shipping": to_money(order["shipping_satang"]),
            "grand_total": to_money(order["grand_total_satang"]),
        },
        "address": {
            "label": order["addr_label"], "recipient_name": order["addr_recipient_name"],
            "phone": order["addr_phone"], "line1": order["addr_line1"],
            "line2": order["addr_line2"], "province": order["addr_province"],
            "postal_code": order["addr_postal_code"],
        },
        "refund_amount": to_money(order["refund_amount_satang"]),
        "created_at": tu.to_api(tu.from_db(order["created_at"])),
        "paid_at": tu.to_api(tu.from_db(order["paid_at"])) if order["paid_at"] else None,
        "packed_at": tu.to_api(tu.from_db(order["packed_at"])) if order["packed_at"] else None,
        "shipped_at": tu.to_api(tu.from_db(order["shipped_at"])) if order["shipped_at"] else None,
        "delivered_at": tu.to_api(tu.from_db(order["delivered_at"])) if order["delivered_at"] else None,
        "cancelled_at": tu.to_api(tu.from_db(order["cancelled_at"])) if order["cancelled_at"] else None,
        "returned_at": tu.to_api(tu.from_db(order["returned_at"])) if order["returned_at"] else None,
        "return_deadline": return_deadline,
    }


def serialize_list_item(order, item_count) -> dict:
    return {
        "id": order["id"], "status": order["status"],
        "grand_total": to_money(order["grand_total_satang"]),
        "item_count": item_count,
        "created_at": tu.to_api(tu.from_db(order["created_at"])),
    }
