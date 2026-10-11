from flask import Blueprint, g, jsonify

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, not_found
from ..services import jobs as jobs_service
from ..validation import JOB_NAMES, Errors, get_minute_datetime, parse_json_body, query_page, query_page_size

bp = Blueprint("jobs_routes", __name__, url_prefix="/api/admin")


@bp.get("/jobs")
@require_auth()
@require_role("admin")
def list_jobs():
    conn = get_db()
    now = tu.now_utc()
    items = []
    for name in ("cancel-unpaid-orders", "hourly-sales-report", "low-stock-snapshot"):
        last = conn.execute(
            "SELECT * FROM job_runs WHERE job=? ORDER BY started_at DESC, id DESC LIMIT 1", (name,)
        ).fetchone()
        items.append({
            "name": name, "description": jobs_service.JOB_DESCRIPTIONS[name],
            "schedule": jobs_service.SCHEDULE_TEXT,
            "last_run": jobs_service.serialize_run(last) if last else None,
            "next_run_at": tu.to_api(jobs_service.next_run_at(now)),
        })
    return jsonify({"items": items})


@bp.post("/jobs/<name>/run")
@require_auth()
@require_role("admin")
def run_job(name):
    if name not in JOB_NAMES:
        raise not_found()
    window_start = window_end = None
    if name == "hourly-sales-report":
        data = parse_json_body()
        if data.get("from") is not None or data.get("to") is not None:
            errors = Errors()
            window_start = get_minute_datetime(data, "from", errors)
            window_end = get_minute_datetime(data, "to", errors)
            errors.raise_if_any()
            if window_end <= window_start or (window_end - window_start) > __import__("datetime").timedelta(hours=24):
                raise ApiError("VALIDATION_ERROR", details=[{"field": "to", "message": "The time range is not valid."}])

    conn = get_db()
    run_id = jobs_service.run_job(conn, name, "MANUAL", g.user["username"], window_start, window_end)
    if run_id is None:
        raise ApiError("JOB_ALREADY_RUNNING")
    row = conn.execute("SELECT * FROM job_runs WHERE id=?", (run_id,)).fetchone()
    return jsonify(jobs_service.serialize_run(row))


@bp.get("/jobs/<name>/runs")
@require_auth()
@require_role("admin")
def list_runs(name):
    if name not in JOB_NAMES:
        raise not_found()
    errors = Errors()
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS n FROM job_runs WHERE job=?", (name,)).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        "SELECT * FROM job_runs WHERE job=? ORDER BY started_at DESC, id DESC LIMIT ? OFFSET ?",
        (name, page_size, offset),
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({"items": [jobs_service.serialize_run(r) for r in rows], "page": page,
                     "page_size": page_size, "total_items": total, "total_pages": total_pages})
