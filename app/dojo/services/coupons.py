"""Coupon validity, discount calculation, usage counting — PRD-COUPON."""
from __future__ import annotations

from .. import time_utils as tu
from ..money import percent_of

# reason -> message template (uses {min_spend} placeholder for MIN_SPEND)
REASON_MESSAGES = {
    "NOT_FOUND": "This coupon code is not valid.",
    "NOT_STARTED": "This coupon is not active yet.",
    "EXPIRED": "This coupon has expired.",
    "MIN_SPEND": "Spend at least ฿{min_spend} to use this coupon.",
    "USER_LIMIT": "You have already used this coupon.",
    "TOTAL_LIMIT": "This coupon is no longer available.",
}


def find_coupon(conn, code: str):
    code = (code or "").strip().upper()
    return conn.execute("SELECT * FROM coupons WHERE code=?", (code,)).fetchone()


def usage_count(conn, code: str, user_id: int | None = None) -> int:
    if user_id is None:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE coupon_code=? AND status<>'CANCELLED'",
            (code,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE coupon_code=? AND user_id=? AND status<>'CANCELLED'",
            (code, user_id),
        ).fetchone()
    return row["n"]


def money_display(satang: int) -> str:
    sign = "-" if satang < 0 else ""
    satang = abs(satang)
    return f"{sign}{satang // 100:,}.{satang % 100:02d}"


def check_validity(conn, coupon, user_id: int, goods_after_volume_satang: int):
    """Evaluate REQ-COUP-002 in order. Returns (ok: bool, reason: str|None,
    message: str|None)."""
    if coupon is None or not coupon["active"]:
        return False, "NOT_FOUND", REASON_MESSAGES["NOT_FOUND"]
    now = tu.now_minute_utc()
    starts = tu.from_db(coupon["starts_at"])
    expires = tu.from_db(coupon["expires_at"])
    if now < starts:
        return False, "NOT_STARTED", REASON_MESSAGES["NOT_STARTED"]
    if now > expires:
        return False, "EXPIRED", REASON_MESSAGES["EXPIRED"]
    if goods_after_volume_satang < coupon["min_spend_satang"]:
        msg = REASON_MESSAGES["MIN_SPEND"].format(min_spend=money_display(coupon["min_spend_satang"]))
        return False, "MIN_SPEND", msg
    if usage_count(conn, coupon["code"], user_id) >= coupon["per_user_limit"]:
        return False, "USER_LIMIT", REASON_MESSAGES["USER_LIMIT"]
    if coupon["total_limit"] is not None and usage_count(conn, coupon["code"]) > coupon["total_limit"]:
        return False, "TOTAL_LIMIT", REASON_MESSAGES["TOTAL_LIMIT"]
    return True, None, None


def compute_discount(coupon, goods_after_volume_satang: int) -> int:
    """REQ-COUP-003."""
    if coupon["type"] == "PERCENT":
        discount = percent_of(goods_after_volume_satang, coupon["percent_off"])
        if coupon["max_discount_satang"] is not None:
            discount = min(discount, coupon["max_discount_satang"])
    else:
        discount = coupon["amount_off_satang"]
    return min(discount, goods_after_volume_satang)


def status_of(coupon) -> str:
    """REQ-COUP-009."""
    if not coupon["active"]:
        return "DISABLED"
    now = tu.now_minute_utc()
    starts = tu.from_db(coupon["starts_at"])
    expires = tu.from_db(coupon["expires_at"])
    if now < starts:
        return "SCHEDULED"
    if now > expires:
        return "EXPIRED"
    return "ACTIVE"
