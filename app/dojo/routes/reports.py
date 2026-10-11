import csv
import io

from flask import Blueprint, Response, jsonify, request

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..money import to_money
from ..services import reports as reports_service
from ..validation import Errors, query_date, query_minute_datetime

bp = Blueprint("reports", __name__, url_prefix="/api/manage/reports")

MAX_DAYS = 366
MAX_WINDOW_HOURS = 24


def _date_range_params(errors):
    from_date = query_date("from", errors)
    to_date = query_date("to", errors)
    if from_date and to_date:
        if from_date > to_date:
            errors.add("from", "date_range_order")
        elif (to_date - from_date).days + 1 > MAX_DAYS:
            errors.add("to", "date_range_too_long")
    return from_date, to_date


def _window_params(errors):
    from_dt = query_minute_datetime("from", errors)
    to_dt = query_minute_datetime("to", errors)
    if from_dt and to_dt:
        if to_dt <= from_dt or (to_dt - from_dt) > __import__("datetime").timedelta(hours=MAX_WINDOW_HOURS):
            errors.add("to", "range_invalid")
    return from_dt, to_dt


def _sales_payload(conn, from_date, to_date):
    totals, avg, daily = reports_service.sales_summary(conn, from_date, to_date)
    return {
        "from": tu.to_api_date(from_date), "to": tu.to_api_date(to_date),
        "order_count": totals["order_count"], "gross_sales": to_money(totals["gross_sales"]),
        "vat_total": to_money(totals["vat_total"]), "shipping_total": to_money(totals["shipping_total"]),
        "discount_total": to_money(totals["discount_total"]), "average_order_value": to_money(avg),
        "daily": [
            {
                "date": tu.to_api_date(d), "order_count": agg["order_count"],
                "gross_sales": to_money(agg["gross_sales"]), "vat_total": to_money(agg["vat_total"]),
                "shipping_total": to_money(agg["shipping_total"]), "discount_total": to_money(agg["discount_total"]),
            }
            for d, agg in daily
        ],
    }


@bp.get("/sales")
@require_auth()
@require_role("manager", "admin")
def sales():
    errors = Errors()
    from_date, to_date = _date_range_params(errors)
    errors.raise_if_any()
    return jsonify(_sales_payload(get_db(), from_date, to_date))


def _csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    resp = Response(buf.getvalue(), mimetype="text/csv")
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@bp.get("/sales.csv")
@require_auth()
@require_role("manager", "admin")
def sales_csv():
    errors = Errors()
    from_date, to_date = _date_range_params(errors)
    errors.raise_if_any()
    payload = _sales_payload(get_db(), from_date, to_date)
    rows = [
        [d["date"], d["order_count"], d["gross_sales"], d["vat_total"], d["shipping_total"], d["discount_total"]]
        for d in payload["daily"]
    ]
    filename = f"sales-report_{from_date.isoformat()}_{to_date.isoformat()}.csv"
    return _csv_response(filename, ["date", "order_count", "gross_sales", "vat_total", "shipping_total", "discount_total"], rows)


@bp.get("/top-products")
@require_auth()
@require_role("manager", "admin")
def top_products_route():
    errors = Errors()
    from_date, to_date = _date_range_params(errors)
    limit_raw = request.args.get("limit", "5")
    limit = 5
    if not limit_raw.isdigit() or not (1 <= int(limit_raw) <= 20):
        errors.add("limit", "limit")
    else:
        limit = int(limit_raw)
    errors.raise_if_any()
    rows = reports_service.top_products(get_db(), from_date, to_date, limit)
    return jsonify({"items": [
        {"product_id": r["product_id"], "sku": r["sku"], "name": r["name"],
         "quantity": r["quantity"], "revenue": to_money(r["revenue"])}
        for r in rows
    ]})


@bp.get("/top-products.csv")
@require_auth()
@require_role("manager", "admin")
def top_products_csv():
    errors = Errors()
    from_date, to_date = _date_range_params(errors)
    limit_raw = request.args.get("limit", "5")
    limit = 5
    if not limit_raw.isdigit() or not (1 <= int(limit_raw) <= 20):
        errors.add("limit", "limit")
    else:
        limit = int(limit_raw)
    errors.raise_if_any()
    rows = reports_service.top_products(get_db(), from_date, to_date, limit)
    csv_rows = [
        [i + 1, r["product_id"], r["sku"], r["name"], r["quantity"], to_money(r["revenue"])]
        for i, r in enumerate(rows)
    ]
    filename = f"top-products_{from_date.isoformat()}_{to_date.isoformat()}.csv"
    return _csv_response(filename, ["rank", "product_id", "sku", "name", "quantity", "revenue"], csv_rows)


@bp.get("/coupon-usage")
@require_auth()
@require_role("manager", "admin")
def coupon_usage_route():
    errors = Errors()
    from_date, to_date = _date_range_params(errors)
    errors.raise_if_any()
    rows = reports_service.coupon_usage(get_db(), from_date, to_date)
    return jsonify({"items": [
        {"code": r["code"], "order_count": r["order_count"], "discount_total": to_money(r["discount_total"])}
        for r in rows
    ]})


@bp.get("/hourly")
@require_auth()
@require_role("manager", "admin")
def hourly():
    errors = Errors()
    from_dt, to_dt = _window_params(errors)
    errors.raise_if_any()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM window_reports WHERE window_start >= ? AND window_start <= ? ORDER BY window_start ASC",
        (tu.to_db_minute(from_dt), tu.to_db_minute(to_dt)),
    ).fetchall()
    return jsonify({"items": [_serialize_window(r) for r in rows]})


def _serialize_window(r):
    return {
        "window_start": tu.to_api_minute(tu.from_db(r["window_start"])),
        "window_end": tu.to_api_minute(tu.from_db(r["window_end"])),
        "order_count": r["order_count"], "gross_sales": to_money(r["gross_sales_satang"]),
        "vat_total": to_money(r["vat_total_satang"]), "shipping_total": to_money(r["shipping_total_satang"]),
        "discount_total": to_money(r["discount_total_satang"]),
        "generated_at": tu.to_api(tu.from_db(r["generated_at"])),
    }


@bp.get("/hourly.csv")
@require_auth()
@require_role("manager", "admin")
def hourly_csv():
    errors = Errors()
    from_dt, to_dt = _window_params(errors)
    errors.raise_if_any()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM window_reports WHERE window_start >= ? AND window_start <= ? ORDER BY window_start ASC",
        (tu.to_db_minute(from_dt), tu.to_db_minute(to_dt)),
    ).fetchall()
    csv_rows = [
        [
            tu.to_api_minute(tu.from_db(r["window_start"])), tu.to_api_minute(tu.from_db(r["window_end"])),
            r["order_count"], to_money(r["gross_sales_satang"]), to_money(r["vat_total_satang"]),
            to_money(r["shipping_total_satang"]), to_money(r["discount_total_satang"]),
        ]
        for r in rows
    ]
    filename = f"window-report_{from_dt.strftime('%Y%m%dT%H%M')}_{to_dt.strftime('%Y%m%dT%H%M')}.csv"
    return _csv_response(
        filename,
        ["window_start", "window_end", "order_count", "gross_sales", "vat_total", "shipping_total", "discount_total"],
        csv_rows,
    )
