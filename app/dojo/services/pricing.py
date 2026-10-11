"""Cart/order pricing — REQ-CROSS-001, REQ-CART-005 to REQ-CART-009."""
from __future__ import annotations

from ..money import percent_of
from . import coupons as coupon_service

VOLUME_THRESHOLD_SATANG = 100000  # 1,000.00
VOLUME_PERCENT = 10
VAT_PERCENT = 7
SHIPPING_THRESHOLD_SATANG = 50000  # 500.00
SHIPPING_FEE_SATANG = 5000  # 50.00


def compute(conn, items, coupon_row, user_id):
    """items: iterable of rows/dicts with unit_price_satang and quantity.

    Returns (pricing: dict of satang ints, coupon_info: dict|None).
    """
    subtotal = sum(it["unit_price_satang"] * it["quantity"] for it in items)
    volume_discount = percent_of(subtotal, VOLUME_PERCENT) if subtotal >= VOLUME_THRESHOLD_SATANG else 0
    after_volume = subtotal - volume_discount

    coupon_discount = 0
    coupon_info = None
    if coupon_row is not None:
        ok, reason, message = coupon_service.check_validity(conn, coupon_row, user_id, after_volume)
        coupon_info = {"code": coupon_row["code"], "valid": ok, "message": message}
        if ok:
            coupon_discount = coupon_service.compute_discount(coupon_row, after_volume)

    goods_total = after_volume - coupon_discount
    vat = percent_of(goods_total, VAT_PERCENT)
    if not items:
        shipping = 0
    else:
        shipping = 0 if goods_total >= SHIPPING_THRESHOLD_SATANG else SHIPPING_FEE_SATANG
    grand_total = goods_total + vat + shipping

    pricing = {
        "subtotal": subtotal,
        "volume_discount": volume_discount,
        "coupon_discount": coupon_discount,
        "goods_total": goods_total,
        "vat": vat,
        "shipping": shipping,
        "grand_total": grand_total,
    }
    return pricing, coupon_info
