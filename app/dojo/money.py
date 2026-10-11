"""Money helpers. Amounts are stored and computed as integer satang
(1 baht = 100 satang) and serialised to the API as 2-decimal strings.
"""
from __future__ import annotations

import re

_MONEY_RE = re.compile(r"^(\d{1,7})\.(\d{2})$")


def parse_satang(s: str) -> int:
    """Parse a "1234.50"-style string into integer satang. Raises ValueError
    on anything that is not exactly 2 decimal digits."""
    if not isinstance(s, str):
        raise ValueError("not a string")
    m = _MONEY_RE.match(s.strip())
    if not m:
        raise ValueError("bad money format")
    baht, cents = m.groups()
    return int(baht) * 100 + int(cents)


def to_money(satang: int) -> str:
    """Render integer satang as a 2-decimal baht string."""
    if satang is None:
        return None
    sign = "-" if satang < 0 else ""
    satang = abs(satang)
    return f"{sign}{satang // 100}.{satang % 100:02d}"


def round_half_up_ratio(numerator: int, denominator: int) -> int:
    """round(numerator / denominator) using half-up rounding, for
    non-negative integers. Used for percentage discounts, VAT and other
    values that must be rounded to the nearest satang."""
    if denominator == 0:
        return 0
    q, r = divmod(numerator, denominator)
    if 2 * r >= denominator:
        q += 1
    return q


def percent_of(amount_satang: int, percent: int) -> int:
    """amount * percent / 100, rounded half-up to the nearest satang."""
    return round_half_up_ratio(amount_satang * percent, 100)
