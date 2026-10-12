from flask import Blueprint, g, jsonify, request

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, field_error, not_found
from ..services import stock as stock_service
from ..validation import ADJUST_REASONS, Errors, get_enum, get_int, get_str, parse_json_body, query_page, query_page_size

bp = Blueprint("inventory", __name__, url_prefix="/api/manage")


@bp.get("/inventory")
@require_auth()
@require_role("staff", "admin")
def list_inventory():
    errors = Errors()
    q = request.args.get("q")
    if q is not None:
        q = q.strip()
        if len(q) > 100:
            errors.add("q", "q")
            q = None
        elif q == "":
            q = None
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    where = "1=1"
    params = []
    if q:
        where += " AND name LIKE ?"
        params.append(f"%{q}%")
    total = conn.execute(f"SELECT COUNT(*) AS n FROM products WHERE {where}", params).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM products WHERE {where} ORDER BY name COLLATE NOCASE, id LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({
        "items": [
            {"product_id": r["id"], "sku": r["sku"], "name": r["name"], "stock": r["stock"],
             "active": bool(r["active"])}
            for r in rows
        ],
        "page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages,
    })


@bp.post("/inventory/adjustments")
@require_auth()
@require_role("staff", "admin")
def create_adjustment():
    data = parse_json_body()
    errors = Errors()
    product_id = get_int(data, "product_id", errors, min_val=1)
    delta = get_int(data, "delta", errors, min_val=-100000, max_val=99999, msg_key="delta")
    reason = get_enum(data, "reason", errors, ADJUST_REASONS, msg_key="reason")
    if delta == 0:
        errors.add("delta", "delta")
    if delta is not None and reason == "RECEIVE" and delta < 0:
        errors.add("delta", "delta_receive")
    if delta is not None and reason == "DAMAGE" and delta > 0:
        errors.add("delta", "delta_damage")
    errors.raise_if_any()

    conn = get_db()
    product = conn.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone()
    if product is None:
        raise not_found()

    new_stock = stock_service.apply_movement(conn, product_id, delta, reason, g.user["username"])
    if new_stock is None:
        raise ApiError("STOCK_NEGATIVE")
    row = conn.execute(
        "SELECT * FROM inventory_movements WHERE product_id=? ORDER BY id DESC LIMIT 1", (product_id,)
    ).fetchone()
    product_name = conn.execute("SELECT name FROM products WHERE id=?", (product_id,)).fetchone()["name"]
    return jsonify({
        "id": row["id"], "product_id": row["product_id"], "product_name": product_name,
        "delta": row["delta"], "stock_after": row["stock_after"], "reason": row["reason"],
        "actor": row["actor"], "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }), 201


@bp.get("/inventory/movements")
@require_auth()
@require_role("staff", "admin")
def list_movements():
    errors = Errors()
    product_id = None
    if request.args.get("product_id") is not None:
        raw = request.args.get("product_id")
        if not raw.isdigit():
            errors.add("product_id", "whole_number")
        else:
            product_id = int(raw)
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    where = "1=1"
    params = []
    if product_id is not None:
        where += " AND m.product_id=?"
        params.append(product_id)
    total = conn.execute(
        f"SELECT COUNT(*) AS n FROM inventory_movements m WHERE {where}", params
    ).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT m.*, p.name AS product_name FROM inventory_movements m "
        f"JOIN products p ON p.id = m.product_id WHERE {where} "
        "ORDER BY m.created_at DESC, m.id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({
        "items": [
            {
                "id": r["id"], "product_id": r["product_id"], "product_name": r["product_name"],
                "delta": r["delta"], "stock_after": r["stock_after"], "reason": r["reason"],
                "actor": r["actor"], "created_at": tu.to_api(tu.from_db(r["created_at"])),
            }
            for r in rows
        ],
        "page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages,
    })


@bp.get("/inventory/low-stock")
@require_auth()
@require_role("staff", "admin")
def low_stock():
    conn = get_db()
    state = conn.execute("SELECT value FROM system_state WHERE key='low_stock_taken_at'").fetchone()
    rows = conn.execute(
        "SELECT product_id, sku, name, stock FROM low_stock_snapshot ORDER BY position"
    ).fetchall()
    return jsonify({
        "taken_at": tu.to_api(tu.from_db(state["value"])) if state else None,
        "items": [{"product_id": r["product_id"], "sku": r["sku"], "name": r["name"], "stock": r["stock"]} for r in rows],
    })
