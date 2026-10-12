"""Sales report aggregation — PRD-REPORT, REQ-CROSS-006."""
from __future__ import annotations

from datetime import timedelta

from .. import time_utils as tu
from ..money import round_half_up_ratio

COUNTED_STATUSES = ("PAID", "PACKED", "SHIPPED", "DELIVERED")


def aggregate_range(conn, start_dt, end_dt) -> dict:
    """Aggregate counted orders whose paid_at is in [start_dt, end_dt)."""
    row = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(grand_total_satang),0) AS gross, "
        "COALESCE(SUM(vat_satang),0) AS vat, COALESCE(SUM(shipping_satang),0) AS ship, "
        "COALESCE(SUM(volume_discount_satang+coupon_discount_satang),0) AS disc "
        "FROM orders WHERE status IN ('PAID','PACKED','SHIPPED') "
        "AND paid_at >= ? AND paid_at < ?",
        (tu.to_db(start_dt), tu.to_db(end_dt)),
    ).fetchone()
    return {
        "order_count": row["n"], "gross_sales": row["gross"], "vat_total": row["vat"],
        "shipping_total": row["ship"], "discount_total": row["disc"],
    }


def sales_summary(conn, from_date, to_date):
    """Returns (totals dict, average_order_value int, daily list of (date, dict))."""
    cur = from_date
    daily = []
    totals = {"order_count": 0, "gross_sales": 0, "vat_total": 0, "shipping_total": 0, "discount_total": 0}
    while cur <= to_date:
        start = tu.start_of_bkk_date(cur)
        end = tu.start_of_bkk_date(cur + timedelta(days=1))
        agg = aggregate_range(conn, start, end)
        daily.append((cur, agg))
        for k in totals:
            totals[k] += agg[k]
        cur += timedelta(days=1)
    avg = round_half_up_ratio(totals["gross_sales"], totals["order_count"]) if totals["order_count"] else 0
    return totals, avg, daily


def top_products(conn, from_date, to_date, limit):
    start = tu.start_of_bkk_date(from_date)
    end = tu.start_of_bkk_date(to_date + timedelta(days=1))
    rows = conn.execute(
        "SELECT oi.product_id AS product_id, oi.sku AS sku, p.name AS name, "
        "SUM(oi.quantity) AS quantity, SUM(oi.line_total_satang) AS revenue "
        "FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id "
        "WHERE o.status IN ('PAID','PACKED','SHIPPED','DELIVERED') AND o.paid_at >= ? AND o.paid_at < ? "
        "GROUP BY oi.product_id "
        "ORDER BY quantity DESC, p.name COLLATE NOCASE ASC, oi.product_id ASC LIMIT ?",
        (tu.to_db(start), tu.to_db(end), limit),
    ).fetchall()
    return rows


def coupon_usage(conn, from_date, to_date):
    start = tu.start_of_bkk_date(from_date)
    end = tu.start_of_bkk_date(to_date + timedelta(days=1))
    rows = conn.execute(
        "SELECT coupon_code AS code, COUNT(*) AS order_count, SUM(coupon_discount_satang) AS discount_total "
        "FROM orders WHERE status IN ('PAID','PACKED','SHIPPED','DELIVERED') AND paid_at >= ? AND paid_at < ? "
        "AND coupon_code IS NOT NULL "
        "GROUP BY coupon_code ORDER BY discount_total DESC, coupon_code ASC",
        (tu.to_db(start), tu.to_db(end)),
    ).fetchall()
    return rows
