"""Stock adjustment with a conditional UPDATE so it is safe under
concurrent requests (REQ-COM-013, REQ-ORD-009)."""
from __future__ import annotations

from .. import time_utils as tu


def apply_movement(conn, product_id: int, delta: int, reason: str, actor: str):
    """Apply delta to products.stock and record the movement. Returns the
    new stock, or None if this would have made stock negative (nothing is
    changed in that case)."""
    cur = conn.execute(
        "UPDATE products SET stock = stock + ? WHERE id=? AND stock + ? >= 0",
        (delta, product_id, delta),
    )
    if cur.rowcount == 0:
        return None
    row = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
    conn.execute(
        "INSERT INTO inventory_movements (product_id, delta, stock_after, reason, actor, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (product_id, delta, row["stock"], reason, actor, tu.to_db(tu.now_utc())),
    )
    return row["stock"]
