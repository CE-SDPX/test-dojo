from flask import Blueprint, g, jsonify, send_file

from .. import images as images_service
from ..auth import optional_auth
from ..db import get_db
from ..errors import not_found
from ..money import to_money
from ..validation import (
    CATEGORIES, SORTS, Errors, query_money, query_page, query_page_size, query_q,
)

bp = Blueprint("catalog", __name__, url_prefix="/api")


def stock_status(stock: int) -> str:
    if stock <= 0:
        return "OUT_OF_STOCK"
    if stock <= 5:
        return "LOW_STOCK"
    return "IN_STOCK"


def _rating_row(conn, product_id):
    return conn.execute(
        "SELECT COUNT(*) AS n, AVG(rating) AS avg FROM reviews WHERE product_id=?", (product_id,)
    ).fetchone()


def _avg_rating_str(avg, n):
    if n == 0:
        return None
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(avg).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _serialize_list_item(conn, row):
    r = _rating_row(conn, row["id"])
    return {
        "id": row["id"], "sku": row["sku"], "name": row["name"], "category": row["category"],
        "price": to_money(row["price_satang"]), "stock_status": stock_status(row["stock"]),
        "average_rating": _avg_rating_str(r["avg"], r["n"]), "review_count": r["n"],
        "image_url": f"/api/products/{row['id']}/image",
    }


def _serialize_detail(conn, row, user_id):
    base = _serialize_list_item(conn, row)
    in_wishlist = user_id is not None and conn.execute(
        "SELECT 1 FROM wishlist_items WHERE user_id=? AND product_id=?", (user_id, row["id"])
    ).fetchone() is not None
    base.update({
        "description": row["description"], "stock": row["stock"], "in_wishlist": in_wishlist,
    })
    return base


_SORT_SQL = {
    "name_asc": "ORDER BY name COLLATE NOCASE ASC, id ASC",
    "name_desc": "ORDER BY name COLLATE NOCASE DESC, id ASC",
    "price_asc": "ORDER BY price_satang ASC, name COLLATE NOCASE ASC, id ASC",
    "price_desc": "ORDER BY price_satang DESC, name COLLATE NOCASE ASC, id ASC",
}


@bp.get("/products")
@optional_auth
def list_products():
    errors = Errors()
    q = query_q(errors)
    category = __import__("flask").request.args.get("category")
    if category is not None and category not in CATEGORIES:
        errors.add("category", "category")
    min_price = query_money("min_price", errors)
    max_price = query_money("max_price", errors)
    if min_price is not None and max_price is not None and min_price > max_price:
        errors.add("min_price", "price_range")
    sort = __import__("flask").request.args.get("sort", "name_asc")
    if sort not in SORTS:
        errors.add("sort", "sort")
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    conn = get_db()
    where = ["active = 1"]
    params = []
    if q:
        where.append("name LIKE ? ESCAPE '\\'")
        params.append(_like_escape(q))
    if category is not None:
        where.append("category = ?")
        params.append(category)
    if min_price is not None:
        where.append("price_satang > ?")
        params.append(min_price)
    if max_price is not None:
        where.append("price_satang <= ?")
        params.append(max_price)
    where_sql = " AND ".join(where)

    total = conn.execute(f"SELECT COUNT(*) AS n FROM products WHERE {where_sql}", params).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM products WHERE {where_sql} {_SORT_SQL[sort]} LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()

    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({
        "items": [_serialize_list_item(conn, r) for r in rows],
        "page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages,
    })


def _like_escape(s: str) -> str:
    return "%" + s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@bp.get("/products/<int:product_id>")
@optional_auth
def get_product(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if row is None:
        raise not_found()
    user_id = g.user["id"] if g.user else None
    return jsonify(_serialize_detail(conn, row, user_id))


@bp.get("/products/<int:product_id>/image")
@optional_auth
def get_product_image(product_id):
    conn = get_db()
    privileged = g.user is not None and g.user["role"] in ("manager", "admin")
    if privileged:
        row = conn.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone()
    else:
        row = conn.execute("SELECT id FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if row is None:
        raise not_found()
    resp = send_file(images_service.resolve_image_path(product_id), mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "no-store"
    return resp
