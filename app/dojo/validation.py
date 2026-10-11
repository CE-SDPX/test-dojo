"""Reusable request validation helpers. Field messages come from errors.py
section matching docs/design/api.md section 4."""
from __future__ import annotations

import re

from flask import request

from . import time_utils as tu
from .errors import ApiError, field_error, validation_error
from .money import parse_satang

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")
PHONE_RE = re.compile(r"^0\d{9}$")
POSTAL_RE = re.compile(r"^\d{5}$")
SKU_RE = re.compile(r"^[A-Z0-9-]{3,20}$")
COUPON_CODE_RE = re.compile(r"^[A-Z0-9]{4,20}$")
# password: 8-20 chars, no whitespace, at least one letter and one digit
PASSWORD_RE = re.compile(r"^(?=\S{8,20}$)(?=.*[A-Za-z])(?=.*\d)\S+$")

CATEGORIES = {"Drinkware", "Apparel", "Stationery", "Electronics", "Home"}
SORTS = {"name_asc", "name_desc", "price_asc", "price_desc"}
ORDER_STATUSES = {"PENDING_PAYMENT", "PAID", "PACKED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}
ROLES = {"customer", "staff", "manager", "admin"}
ADJUST_REASONS = {"RECEIVE", "DAMAGE", "CORRECTION"}
PAY_METHODS = {"CARD", "PROMPTPAY"}
JOB_NAMES = {"cancel-unpaid-orders", "hourly-sales-report", "low-stock-snapshot"}


class Errors:
    def __init__(self):
        self.items = []

    def add(self, field, key):
        self.items.append(field_error(field, key))

    def raise_if_any(self):
        if self.items:
            raise validation_error(self.items)


def parse_json_body() -> dict:
    raw = request.get_data(cache=True, as_text=False)
    if raw and raw.strip():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ApiError("INVALID_JSON")
        return data
    return {}


def get_str(data, field, errors, required=True, min_len=None, max_len=None,
            pattern=None, msg_key="invalid", trim=True, allow_none_clears=False):
    val = data.get(field, None)
    if val is None:
        if allow_none_clears:
            return ""
        if required:
            errors.add(field, "required")
        return None
    if not isinstance(val, str):
        errors.add(field, msg_key)
        return None
    v = val.strip() if trim else val
    if v == "":
        if allow_none_clears:
            return ""
        if required:
            errors.add(field, "required")
            return None
    if min_len is not None and len(v) < min_len:
        errors.add(field, msg_key)
        return None
    if max_len is not None and len(v) > max_len:
        errors.add(field, msg_key)
        return None
    if pattern is not None and not pattern.match(v):
        errors.add(field, msg_key)
        return None
    return v


def get_int(data, field, errors, required=True, min_val=None, max_val=None, msg_key="whole_number"):
    val = data.get(field, None)
    if val is None:
        if required:
            errors.add(field, "required")
        return None
    if isinstance(val, bool) or not isinstance(val, int):
        errors.add(field, msg_key)
        return None
    if min_val is not None and val < min_val:
        errors.add(field, msg_key)
        return None
    if max_val is not None and val > max_val:
        errors.add(field, msg_key)
        return None
    return val


def get_bool(data, field, errors, required=True):
    val = data.get(field, None)
    if val is None:
        if required:
            errors.add(field, "required")
        return None
    if not isinstance(val, bool):
        errors.add(field, "active")
        return None
    return val


def get_money(data, field, errors, required=True, min_satang=1, max_satang=9999999, msg_key="amount_default"):
    val = data.get(field, None)
    if val is None:
        if required:
            errors.add(field, "required")
        return None
    try:
        satang = parse_satang(val)
    except ValueError:
        errors.add(field, msg_key)
        return None
    if satang < min_satang or satang > max_satang:
        errors.add(field, msg_key)
        return None
    return satang


def get_enum(data, field, errors, choices, required=True, msg_key="invalid"):
    val = data.get(field, None)
    if val is None:
        if required:
            errors.add(field, "required")
        return None
    if val not in choices:
        errors.add(field, msg_key)
        return None
    return val


def get_minute_datetime(data, field, errors):
    val = data.get(field, None)
    if val is None:
        errors.add(field, "required")
        return None
    try:
        return tu.parse_minute_precision(val)
    except ValueError:
        errors.add(field, "datetime_minute")
        return None


def query_q(errors):
    q = request.args.get("q")
    if q is None:
        return None
    q = q.strip()
    if len(q) > 100:
        errors.add("q", "q")
        return None
    return q or None


def query_page(errors):
    raw = request.args.get("page")
    if raw is None:
        return 1
    if not raw.isdigit() or int(raw) < 1:
        errors.add("page", "page")
        return 1
    return int(raw)


def query_page_size(errors):
    raw = request.args.get("page_size")
    if raw is None:
        return 10
    if not raw.isdigit() or not (1 <= int(raw) <= 50):
        errors.add("page_size", "page_size")
        return 10
    return int(raw)


def query_money(field, errors, msg_key="price_format"):
    raw = request.args.get(field)
    if raw is None:
        return None
    try:
        return parse_satang(raw)
    except ValueError:
        errors.add(field, msg_key)
        return None


def query_date(field, errors, required=True):
    raw = request.args.get(field)
    if raw is None:
        if required:
            errors.add(field, "required")
        return None
    try:
        return tu.parse_date(raw)
    except ValueError:
        errors.add(field, "date_format")
        return None


def query_minute_datetime(field, errors, required=True):
    raw = request.args.get(field)
    if raw is None:
        if required:
            errors.add(field, "required")
        return None
    try:
        return tu.parse_minute_precision(raw)
    except ValueError:
        errors.add(field, "datetime_minute")
        return None
