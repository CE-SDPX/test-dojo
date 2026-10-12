import sqlite3

from flask import Blueprint, g, jsonify, request

from .. import images as images_service
from .. import time_utils as tu
from ..auth import require_auth, require_role
from ..db import get_db
from ..errors import ApiError, field_error, not_found
from ..money import to_money
from ..validation import CATEGORIES, Errors, SKU_RE, get_bool, get_int, get_money, get_str, parse_json_body, query_page, query_page_size

bp = Blueprint("manage_products", __name__, url_prefix="/api/manage")


def _serialize(row):
    return {
        "id": row["id"], "sku": row["sku"], "name": row["name"], "description": row["description"],
        "category": row["category"], "price": to_money(row["price_satang"]), "stock": row["stock"],
        "active": bool(row["active"]), "created_at": tu.to_api(tu.from_db(row["created_at"])),
        "image_url": f"/api/products/{row['id']}/image",
        "has_image": images_service.has_custom_image(row["id"]),
    }


@bp.get("/products")
@require_auth()
@require_role("manager", "admin")
def list_manage_products():
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
        where += " AND (name LIKE ? OR sku LIKE ?)"
        params += [f"%{q}%", f"%{q.upper()}%"]
    total = conn.execute(f"SELECT COUNT(*) AS n FROM products WHERE {where}", params).fetchone()["n"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM products WHERE {where} ORDER BY name COLLATE NOCASE, id LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return jsonify({"items": [_serialize(r) for r in rows], "page": page, "page_size": page_size,
                     "total_items": total, "total_pages": total_pages})


@bp.post("/products")
@require_auth()
@require_role("manager", "admin")
def create_product():
    data = parse_json_body()
    errors = Errors()
    sku = get_str(data, "sku", errors, min_len=3, max_len=20, pattern=SKU_RE, msg_key="sku")
    name = get_str(data, "name", errors, min_len=2, max_len=100, msg_key="name")
    description = get_str(data, "description", errors, required=False, max_len=1000, msg_key="description")
    category = get_str(data, "category", errors, required=True, msg_key="category")
    if category is not None and category not in CATEGORIES:
        errors.add("category", "category")
    price = get_money(data, "price", errors)
    stock = 0
    if "stock" in data:
        stock = get_int(data, "stock", errors, min_val=0, max_val=100000, msg_key="whole_number")
    errors.raise_if_any()

    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        now = tu.now_utc()
        conn.execute(
            "INSERT INTO products (sku, name, description, category, price_satang, stock, active, created_at) "
            "VALUES (?,?,?,?,?,?,1,?)",
            (sku, name, description, category, price, stock, tu.to_db(now)),
        )
        pid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
        raise ApiError("SKU_TAKEN")

    if stock and stock > 0:
        from ..services import stock as stock_service
        stock_service.apply_movement(conn, pid, stock, "RECEIVE", g.user["username"])
        conn.execute("UPDATE products SET stock=? WHERE id=?", (stock, pid))

    row = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    return jsonify(_serialize(row)), 201


@bp.put("/products/<int:product_id>")
@require_auth()
@require_role("manager", "admin")
def update_product(product_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if existing is None:
        raise not_found()

    data = parse_json_body()
    errors = Errors()
    name = get_str(data, "name", errors, required=False, min_len=2, max_len=100, msg_key="name") if "name" in data else existing["name"]
    description = existing["description"]
    if "description" in data:
        description = get_str(data, "description", errors, required=False, max_len=1000, msg_key="description", allow_none_clears=True)
    category = existing["category"]
    if "category" in data:
        category = get_str(data, "category", errors, required=True, msg_key="category")
        if category is not None and category not in CATEGORIES:
            errors.add("category", "category")
    price = existing["price_satang"]
    if "price" in data:
        price = get_money(data, "price", errors)
    errors.raise_if_any()

    conn.execute(
        "UPDATE products SET name=?, description=?, category=?, price_satang=? WHERE id=?",
        (name, description, category, price, product_id),
    )
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    return jsonify(_serialize(row))


@bp.post("/products/<int:product_id>/image")
@require_auth()
@require_role("manager", "admin")
def upload_product_image(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if row is None:
        raise not_found()

    file = request.files.get("image")
    if file is None or file.filename == "":
        raise ApiError("VALIDATION_ERROR", details=[field_error("image", "required")])
    data = file.read()
    images_service.validate_and_save(product_id, data)

    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    return jsonify(_serialize(row))


@bp.patch("/products/<int:product_id>/active")
@require_auth()
@require_role("manager", "admin")
def set_product_active(product_id):
    data = parse_json_body()
    errors = Errors()
    active = get_bool(data, "active", errors)
    errors.raise_if_any()

    conn = get_db()
    row = conn.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone()
    if row is None:
        raise not_found()
    conn.execute("UPDATE products SET active=? WHERE id=?", (1 if active else 0, product_id))
    if not active:
        conn.execute("DELETE FROM cart_items WHERE product_id=?", (product_id,))
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    return jsonify(_serialize(row))
