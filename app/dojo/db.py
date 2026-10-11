"""SQLite connection management, schema creation and reset.

The connection is opened with isolation_level=None (autocommit) so that
callers explicitly control transactions with BEGIN IMMEDIATE / COMMIT /
ROLLBACK where atomicity across several statements matters (REQ-COM-013).
"""
from __future__ import annotations

import fcntl
import os
import sqlite3
import threading
from pathlib import Path

from flask import g

DB_PATH = os.environ.get("DOJO_DB_PATH", "/data/dojo.db")

_init_lock = threading.Lock()

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _configure(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    return _configure(conn)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def ensure_initialised() -> None:
    """Create the schema and seed data on first start.

    `api` and `scheduler` are separate processes (separate containers)
    sharing the same SQLite file, so a plain in-process lock is not enough
    to stop both from racing to create the schema on a fresh volume. An
    OS-level file lock on the shared volume makes this safe across
    processes and containers.
    """
    with _init_lock:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        lock_path = str(Path(DB_PATH).parent / ".init.lock")
        with open(lock_path, "w") as lockfile:
            fcntl.flock(lockfile, fcntl.LOCK_EX)
            try:
                conn = connect()
                try:
                    if not table_exists(conn, "users"):
                        _create_schema(conn)
                        from . import seed
                        conn.execute("BEGIN IMMEDIATE")
                        try:
                            seed.load(conn)
                            conn.execute("COMMIT")
                        except Exception:
                            conn.execute("ROLLBACK")
                            raise
                finally:
                    conn.close()
            finally:
                fcntl.flock(lockfile, fcntl.LOCK_UN)


_RESET_TABLES = [
    "order_items", "orders", "job_runs", "window_reports",
    "low_stock_snapshot", "reviews", "wishlist_items", "cart_items",
    "carts", "inventory_movements", "products", "coupons",
    "addresses", "sessions", "users", "system_state",
]


def reset(conn: sqlite3.Connection | None = None):
    """Wipe all data and reload seed data. Returns the reset instant (aware UTC)."""
    own = conn is None
    if own:
        conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        for t in _RESET_TABLES:
            conn.execute(f"DELETE FROM {t}")
        from . import seed
        reset_at = seed.load(conn)
        conn.execute("COMMIT")
        from . import images as images_service
        images_service.clear_all()
        return reset_at
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        if own:
            conn.close()


def init_app(app) -> None:
    ensure_initialised()
    app.teardown_appcontext(close_db)
