"""Entrypoint: `python -m dojo.scheduler`. Runs the three hourly jobs at
every top of the hour (Asia/Bangkok). Does not catch up on missed hours."""
import time

from . import db
from . import time_utils as tu
from .services import jobs as jobs_service

JOB_ORDER = ("cancel-unpaid-orders", "hourly-sales-report", "low-stock-snapshot")


def run_once(conn):
    for job in JOB_ORDER:
        try:
            jobs_service.run_job(conn, job, "SCHEDULED", "system")
        except Exception:
            # The failure is already recorded in job_runs; move on to the
            # next job so one failing job does not block the others.
            pass


def main():
    db.ensure_initialised()
    while True:
        now = tu.now_utc()
        next_run = jobs_service.next_run_at(now)
        time.sleep(max(1.0, (next_run - now).total_seconds()))
        conn = db.connect()
        try:
            run_once(conn)
        finally:
            conn.close()


if __name__ == "__main__":
    main()
