"""Time helpers. The system clock is Asia/Bangkok (UTC+07:00), no DST.

Storage: all timestamps are kept in the database as UTC, second precision,
e.g. ``2026-10-10T07:30:05Z``. Coupon/report window timestamps carry only
minute precision, e.g. ``2026-10-10T07:30Z``.

API output converts to ``+07:00`` before serialising.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

BKK = timezone(timedelta(hours=7))
UTC = timezone.utc

_SECOND_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})$"
)
_MINUTE_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})$"
)
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_bkk() -> datetime:
    return now_utc().astimezone(BKK)


def now_minute_utc() -> datetime:
    """Current time truncated to the minute (for coupon/window comparisons)."""
    n = now_utc()
    return n.replace(second=0, microsecond=0)


def to_db(dt: datetime) -> str:
    """Store as UTC, second precision, e.g. 2026-10-10T07:30:05Z."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_db_minute(dt: datetime) -> str:
    """Store as UTC, minute precision, e.g. 2026-10-10T07:30Z."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def from_db(s: str) -> datetime:
    """Parse a value stored by to_db()/to_db_minute() back into aware UTC."""
    if s is None:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if len(s) == 16:  # YYYY-MM-DDTHH:MM+00:00 missing seconds already appended
        pass
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_api(dt: datetime) -> str:
    """Serialise for the API, second precision, +07:00."""
    if dt is None:
        return None
    return dt.astimezone(BKK).strftime("%Y-%m-%dT%H:%M:%S+07:00")


def to_api_minute(dt: datetime) -> str:
    """Serialise for the API, minute precision, +07:00 (coupons, windows)."""
    if dt is None:
        return None
    return dt.astimezone(BKK).strftime("%Y-%m-%dT%H:%M+07:00")


def to_api_date(d: date) -> str:
    if d is None:
        return None
    return d.strftime("%Y-%m-%d")


def parse_minute_precision(s: str) -> datetime:
    """Parse a coupon/window timestamp. Must be minute precision, no seconds.

    Raises ValueError if the format is wrong (including when seconds are
    present, which REQ-COUP-001 / REQ-SCH-005 forbid).
    """
    if not isinstance(s, str):
        raise ValueError("not a string")
    m = _MINUTE_RE.match(s.strip())
    if not m:
        raise ValueError("bad minute-precision datetime")
    year, month, day, hour, minute, offset = m.groups()
    naive = f"{year}-{month}-{day}T{hour}:{minute}:00"
    off = "+00:00" if offset == "Z" else offset
    dt = datetime.fromisoformat(naive + off)
    return dt.astimezone(UTC)


def parse_second_precision(s: str) -> datetime:
    if not isinstance(s, str):
        raise ValueError("not a string")
    m = _SECOND_RE.match(s.strip())
    if not m:
        raise ValueError("bad second-precision datetime")
    off = "+00:00" if m.group(7) == "Z" else m.group(7)
    naive = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}"
    dt = datetime.fromisoformat(naive + off)
    return dt.astimezone(UTC)


def parse_date(s: str) -> date:
    if not isinstance(s, str):
        raise ValueError("not a string")
    m = _DATE_RE.match(s.strip())
    if not m:
        raise ValueError("bad date")
    y, mo, d = (int(x) for x in m.groups())
    return date(y, mo, d)


def bkk_date_of(dt: datetime) -> date:
    """The Asia/Bangkok calendar date of an aware UTC datetime."""
    return dt.astimezone(BKK).date()


def start_of_bkk_date(d: date) -> datetime:
    """UTC instant of 00:00 Asia/Bangkok on date d."""
    local_midnight = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=BKK)
    return local_midnight.astimezone(UTC)


def age_years(birthdate: date, as_of: date) -> int:
    """Age in whole years on `as_of`, treating Feb-29 birthdays as Mar-1
    in non-leap years (per REQ-AUTH-001)."""
    try:
        anniversary = birthdate.replace(year=as_of.year)
    except ValueError:
        # Feb 29 birthday, as_of.year is not a leap year -> use Mar 1
        anniversary = date(as_of.year, 3, 1)
    years = as_of.year - birthdate.year
    if as_of <= anniversary:
        years -= 1
    return years
