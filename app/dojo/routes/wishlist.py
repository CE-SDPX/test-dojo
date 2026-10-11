from flask import Blueprint, g, jsonify

from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, not_found
from ..money import to_money
from .catalog import stock_status

bp = Blueprint("wishlist", __name__, url_prefix="/api")

MAX_WISHLIST = 50


@bp.get("/wishlist")
@require_auth()
@require_role("customer")
def list_wishlist():
    conn = get_db()
    rows = conn.execute(
        "SELECT w.product_id, w.added_at, p.sku, p.name, p.price_satang, p.stock "
        "FROM wishlist_items w JOIN products p ON p.id = w.product_id "
        "WHERE w.user_id=? ORDER BY w.added_at DESC, w.product_id DESC",
        (g.user["id"],),
    ).fetchall()
    return jsonify({"items": [
        {
            "product_id": r["product_id"], "sku": r["sku"], "name": r["name"],
            "price": to_money(r["price_satang"]), "stock_status": stock_status(r["stock"]),
            "image_url": f"/api/products/{r['product_id']}/image",
            "added_at": tu.to_api(tu.from_db(r["added_at"])),
        }
        for r in rows
    ]})


@bp.put("/wishlist/<int:product_id>")
@require_auth()
@require_role("customer")
def add_wishlist(product_id):
    conn = get_db()
    product = conn.execute("SELECT id FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if product is None:
        raise not_found()
    conn.execute("BEGIN IMMEDIATE")
    try:
        exists = conn.execute(
            "SELECT 1 FROM wishlist_items WHERE user_id=? AND product_id=?", (g.user["id"], product_id)
        ).fetchone()
        if exists is not None:
            conn.execute("ROLLBACK")
            raise ApiError("ALREADY_IN_WISHLIST")
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM wishlist_items WHERE user_id=?", (g.user["id"],)
        ).fetchone()["n"]
        if count >= MAX_WISHLIST:
            conn.execute("ROLLBACK")
            raise ApiError("WISHLIST_LIMIT")
        now = tu.now_utc()
        conn.execute(
            "INSERT INTO wishlist_items (user_id, product_id, added_at) VALUES (?,?,?)",
            (g.user["id"], product_id, tu.to_db(now)),
        )
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return jsonify({"product_id": product_id, "added_at": tu.to_api(now)}), 201


@bp.delete("/wishlist/<int:product_id>")
@require_auth()
@require_role("customer")
def remove_wishlist(product_id):
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM wishlist_items WHERE user_id=? AND product_id=?", (g.user["id"], product_id)
    )
    if cur.rowcount == 0:
        raise not_found()
    return "", 204
