from flask import Blueprint, g, jsonify

from .. import time_utils as tu
from ..auth import optional_auth, require_auth, require_role
from ..db import get_db
from ..errors import ApiError, not_found
from ..validation import Errors, get_int, get_str, parse_json_body, query_page, query_page_size

bp = Blueprint("reviews", __name__, url_prefix="/api")


def _serialize(row):
    return {
        "id": row["id"], "rating": row["rating"], "comment": row["comment"],
        "display_name": row["display_name"], "created_at": tu.to_api(tu.from_db(row["created_at"])),
    }


@bp.get("/products/<int:product_id>/reviews")
@optional_auth
def list_reviews(product_id):
    conn = get_db()
    product = conn.execute("SELECT id FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if product is None:
        raise not_found()
    errors = Errors()
    page = query_page(errors)
    page_size = query_page_size(errors)
    errors.raise_if_any()

    total = conn.execute("SELECT COUNT(*) AS n FROM reviews WHERE product_id=?", (product_id,)).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        "SELECT r.id, r.rating, r.comment, r.created_at, u.display_name "
        "FROM reviews r JOIN users u ON u.id = r.user_id WHERE r.product_id=? "
        "ORDER BY r.created_at DESC, r.id DESC LIMIT ? OFFSET ?",
        (product_id, page_size, offset),
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({
        "items": [_serialize(r) for r in rows],
        "page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages,
    })


@bp.post("/products/<int:product_id>/reviews")
@require_auth()
@require_role("customer")
def create_review(product_id):
    conn = get_db()
    product = conn.execute("SELECT id FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if product is None:
        raise not_found()

    data = parse_json_body()
    errors = Errors()
    rating = get_int(data, "rating", errors, min_val=1, max_val=5, msg_key="rating")
    comment = get_str(data, "comment", errors, required=False, max_len=500, msg_key="comment")
    errors.raise_if_any()

    delivered = conn.execute(
        "SELECT 1 FROM orders o JOIN order_items oi ON oi.order_id = o.id "
        "WHERE o.user_id=? AND oi.product_id=? AND o.status='DELIVERED' LIMIT 1",
        (g.user["id"], product_id),
    ).fetchone()
    if delivered is None:
        raise ApiError("REVIEW_NOT_ALLOWED")

    conn.execute("BEGIN IMMEDIATE")
    try:
        exists = conn.execute(
            "SELECT 1 FROM reviews WHERE product_id=? AND user_id=?", (product_id, g.user["id"])
        ).fetchone()
        if exists is not None:
            conn.execute("ROLLBACK")
            raise ApiError("REVIEW_EXISTS")
        now = tu.now_utc()
        conn.execute(
            "INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
            (product_id, g.user["id"], rating, comment, tu.to_db(now)),
        )
        review_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute("COMMIT")
    except ApiError:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return jsonify({
        "id": review_id, "rating": rating, "comment": comment,
        "display_name": g.user["display_name"], "created_at": tu.to_api(now),
    }), 201
