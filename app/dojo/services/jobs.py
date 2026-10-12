"""Scheduled jobs shared by the scheduler process and the admin manual-run
endpoint — PRD-SCHEDULE, docs/design/jobs.md."""
from __future__ import annotations

import json
import sqlite3
from datetime import timedelta

from .. import time_utils as tu
from . import orders as orders_service
from . import reports as reports_service

JOB_DESCRIPTIONS = {
    "cancel-unpaid-orders": "Cancels orders that have been unpaid for 60 minutes or more.",
    "hourly-sales-report": "Creates the sales report for the previous full hour.",
    "low-stock-snapshot": "Records products with 5 or fewer items in stock.",
}
SCHEDULE_TEXT = "Every hour at minute 0 (Asia/Bangkok)"


def previous_full_hour_window(now):
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    return hour_start - timedelta(hours=1), hour_start


def next_run_at(now):
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    return hour_start + timedelta(hours=1)


def _start_run(conn, job, trigger, triggered_by):
    try:
        conn.execute(
            "INSERT INTO job_runs (job, trigger, triggered_by, status, started_at) VALUES (?,?,?, 'RUNNING', ?)",
            (job, trigger, triggered_by, tu.to_db(tu.now_utc())),
        )
    except sqlite3.IntegrityError:
        return None
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def _finish_run(conn, run_id, status, summary=None, error=None):
    conn.execute(
        "UPDATE job_runs SET status=?, finished_at=?, summary_json=?, error_message=? WHERE id=?",
        (status, tu.to_db(tu.now_utc()), json.dumps(summary) if summary is not None else None, error, run_id),
    )


def _cancel_unpaid_orders(conn):
    cutoff = tu.now_utc() - timedelta(minutes=60)
    rows = conn.execute(
        "SELECT id FROM orders WHERE status='PENDING_PAYMENT' AND created_at < ? ORDER BY id",
        (tu.to_db(cutoff),),
    ).fetchall()
    ids = []
    for r in rows:
        orders_service.cancel_order(conn, r["id"], "system")
        ids.append(r["id"])
    return {"cancelled_count": len(ids), "order_ids": ids}


def _hourly_sales_report(conn, window_start, window_end):
    if window_start is None or window_end is None:
        window_start, window_end = previous_full_hour_window(tu.now_utc())
    agg = reports_service.aggregate_range(conn, window_start, window_end)
    conn.execute(
        "INSERT INTO window_reports (window_start, window_end, order_count, gross_sales_satang, "
        "vat_total_satang, shipping_total_satang, discount_total_satang, generated_at) "
        "VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(window_start, window_end) DO UPDATE SET "
        "order_count=excluded.order_count, gross_sales_satang=excluded.gross_sales_satang, "
        "vat_total_satang=excluded.vat_total_satang, shipping_total_satang=excluded.shipping_total_satang, "
        "discount_total_satang=excluded.discount_total_satang, generated_at=excluded.generated_at",
        (tu.to_db_minute(window_start), tu.to_db_minute(window_end), agg["order_count"], agg["gross_sales"],
         agg["vat_total"], agg["shipping_total"], agg["discount_total"], tu.to_db(tu.now_utc())),
    )
    return {
        "window_start": tu.to_api_minute(window_start), "window_end": tu.to_api_minute(window_end),
        "order_count": agg["order_count"],
    }


def _low_stock_snapshot(conn):
    conn.execute("DELETE FROM low_stock_snapshot")
    rows = conn.execute(
        "SELECT id, sku, name, stock FROM products WHERE active=1 AND stock<=5 "
        "ORDER BY stock ASC, name COLLATE NOCASE ASC, id ASC"
    ).fetchall()
    for i, r in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO low_stock_snapshot (position, product_id, sku, name, stock) VALUES (?,?,?,?,?)",
            (i, r["id"], r["sku"], r["name"], r["stock"]),
        )
    conn.execute(
        "INSERT INTO system_state (key, value) VALUES ('low_stock_taken_at', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (tu.to_db(tu.now_utc()),),
    )
    return {"item_count": len(rows)}


def run_job(conn, job: str, trigger: str, triggered_by: str, window_start=None, window_end=None):
    """Returns the job_runs id, or None if the job is already running."""
    run_id = _start_run(conn, job, trigger, triggered_by)
    if run_id is None:
        return None
    try:
        conn.execute("BEGIN IMMEDIATE")
        if job == "cancel-unpaid-orders":
            summary = _cancel_unpaid_orders(conn)
        elif job == "hourly-sales-report":
            summary = _hourly_sales_report(conn, window_start, window_end)
        elif job == "low-stock-snapshot":
            summary = _low_stock_snapshot(conn)
        else:
            raise ValueError(f"unknown job {job}")
        conn.execute("COMMIT")
        _finish_run(conn, run_id, "SUCCESS", summary=summary)
    except Exception:
        conn.execute("ROLLBACK")
        _finish_run(conn, run_id, "FAILED", error="Job failed.")
        raise
    return run_id


def serialize_run(row):
    return {
        "id": row["id"], "job": row["job"], "trigger": row["trigger"], "triggered_by": row["triggered_by"],
        "status": row["status"], "started_at": tu.to_api(tu.from_db(row["started_at"])),
        "finished_at": tu.to_api(tu.from_db(row["finished_at"])) if row["finished_at"] else None,
        "summary": json.loads(row["summary_json"]) if row["summary_json"] else None,
        "error_message": row["error_message"],
    }
