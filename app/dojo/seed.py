"""Seed data — docs/instructions/test-accounts-and-seed-data.md.

Loaded on first start and by POST /api/reset. Must run inside a transaction
the caller already opened (db.ensure_initialised / db.reset).
"""
from __future__ import annotations

from datetime import timedelta

from werkzeug.security import generate_password_hash

from . import time_utils as tu
from .money import parse_satang

PASSWORDS = {
    "customer": "Customer123",
    "staff": "Staff123",
    "manager": "Manager123",
    "admin": "Admin123",
}

DISPLAY_NAMES = {
    "customer1": "Somchai Jaidee",
    "customer2": "Malee Rakdee",
    "customer3": "Preecha Boonmee",
    "staff1": "Staff One",
    "staff2": "Staff Two",
    "staff3": "Staff Three",
    "manager1": "Manager One",
    "manager2": "Manager Two",
    "manager3": "Manager Three",
    "admin1": "Admin One",
    "admin2": "Admin Two",
    "admin3": "Admin Three",
}

PRODUCTS = [
    # sku, name, category, price, stock, active
    ("DM-1001", "Ceramic Coffee Mug", "Drinkware", "129.00", 40, 1),
    ("DM-1002", "Thai Tea Glass", "Drinkware", "89.00", 60, 1),
    ("DM-1003", "Stainless Tumbler 500 ml", "Drinkware", "349.00", 25, 1),
    ("DM-1004", "Glass Water Bottle", "Drinkware", "199.00", 6, 1),
    ("DM-1005", "Travel Mug", "Drinkware", "250.00", 12, 1),
    ("DM-2001", "100% Cotton T-Shirt", "Apparel", "299.00", 80, 1),
    ("DM-2002", "Canvas Tote Bag", "Apparel", "159.00", 33, 1),
    ("DM-2003", "Wool Beanie", "Apparel", "189.00", 6, 1),
    ("DM-2004", "Running Socks (3 pairs)", "Apparel", "71.50", 100, 1),
    ("DM-2005", "Rain Jacket", "Apparel", "1590.00", 8, 1),
    ("DM-3001", "Notebook, A5 (Lined)", "Stationery", "10.50", 200, 1),
    ("DM-3002", "Gel Pen Set", "Stationery", "59.00", 150, 1),
    ("DM-3003", "Limited Edition Notebook", "Stationery", "450.00", 1, 1),
    ("DM-3004", "Desk Organizer", "Stationery", "335.00", 15, 1),
    ("DM-3005", "Sticky Notes Pack", "Stationery", "25.00", 300, 1),
    ("DM-4001", "USB-C Cable 1 m", "Electronics", "100.00", 70, 1),
    ("DM-4002", "Wireless Mouse", "Electronics", "599.00", 20, 1),
    ("DM-4003", "Bluetooth Speaker", "Electronics", "999.99", 10, 1),
    ("DM-4004", "Mechanical Keyboard", "Electronics", "1000.00", 9, 1),
    ("DM-4005", "Phone Stand", "Electronics", "200.00", 45, 1),
    ("DM-5001", "Scented Candle", "Home", "149.00", 50, 1),
    ("DM-5002", "Throw Pillow", "Home", "399.00", 18, 1),
    ("DM-5003", "Vintage Poster", "Home", "350.00", 0, 1),
    ("DM-9001", "Discontinued Desk Lamp", "Home", "690.00", 4, 0),
    ("DM-9002", "Retired Wall Clock", "Home", "520.00", 0, 0),
]


def _insert_user(conn, username, role, birthdate=None, phone=None):
    conn.execute(
        "INSERT INTO users (username, password_hash, display_name, role, phone, "
        "birthdate, status, failed_login_count, locked_until, must_change_password, created_at) "
        "VALUES (?,?,?,?,?,?, 'ACTIVE', 0, NULL, 0, ?)",
        (
            username,
            generate_password_hash(PASSWORDS[role]),
            DISPLAY_NAMES[username],
            role,
            phone,
            birthdate,
            tu.to_db(tu.now_utc()),
        ),
    )
    return conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"]


def _insert_address(conn, user_id, label, recipient, phone, line1, line2, province, postal, is_default, created_at):
    conn.execute(
        "INSERT INTO addresses (user_id, label, recipient_name, phone, line1, line2, "
        "province, postal_code, is_default, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user_id, label, recipient, phone, line1, line2, province, postal, is_default, tu.to_db(created_at)),
    )
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def _insert_product(conn, sku, name, category, price, stock, active):
    conn.execute(
        "INSERT INTO products (sku, name, category, price_satang, stock, active, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (sku, name, category, parse_satang(price), stock, active, tu.to_db(tu.now_utc())),
    )
    return conn.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone()["id"]


def _insert_coupon(conn, code, type_, starts_at, expires_at, min_spend="0.00", per_user_limit=1,
                    total_limit=None, percent_off=None, amount_off=None, max_discount=None, active=1):
    conn.execute(
        "INSERT INTO coupons (code, type, percent_off, amount_off_satang, max_discount_satang, "
        "min_spend_satang, starts_at, expires_at, per_user_limit, total_limit, active, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            code, type_, percent_off,
            parse_satang(amount_off) if amount_off else None,
            parse_satang(max_discount) if max_discount else None,
            parse_satang(min_spend), tu.to_db_minute(starts_at), tu.to_db_minute(expires_at),
            per_user_limit, total_limit, active, tu.to_db(tu.now_utc()),
        ),
    )


def _far_future():
    from datetime import datetime
    return datetime(2099, 12, 31, 16, 59, tzinfo=tu.UTC)  # 2099-12-31T23:59+07:00


def _far_past_start():
    from datetime import datetime
    return datetime(2019, 12, 31, 17, 0, tzinfo=tu.UTC)  # 2020-01-01T00:00+07:00


def _insert_movement(conn, product_id, delta, stock_after, reason, actor, created_at):
    conn.execute(
        "INSERT INTO inventory_movements (product_id, delta, stock_after, reason, actor, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (product_id, delta, stock_after, reason, actor, tu.to_db(created_at)),
    )


def _insert_order(conn, user_id, status, address, items, pricing, coupon_code,
                   created_at, paid_at=None, packed_at=None, shipped_at=None,
                   delivered_at=None, cancelled_at=None, returned_at=None, refund="0.00"):
    conn.execute(
        "INSERT INTO orders (user_id, status, coupon_code, subtotal_satang, volume_discount_satang, "
        "coupon_discount_satang, goods_total_satang, vat_satang, shipping_satang, grand_total_satang, "
        "addr_label, addr_recipient_name, addr_phone, addr_line1, addr_line2, addr_province, addr_postal_code, "
        "refund_amount_satang, created_at, paid_at, packed_at, shipped_at, delivered_at, cancelled_at, returned_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            user_id, status, coupon_code,
            parse_satang(pricing["subtotal"]), parse_satang(pricing["volume_discount"]),
            parse_satang(pricing["coupon_discount"]), parse_satang(pricing["goods_total"]),
            parse_satang(pricing["vat"]), parse_satang(pricing["shipping"]), parse_satang(pricing["grand_total"]),
            address["label"], address["recipient_name"], address["phone"], address["line1"],
            address.get("line2"), address["province"], address["postal_code"],
            parse_satang(refund), tu.to_db(created_at),
            tu.to_db(paid_at) if paid_at else None, tu.to_db(packed_at) if packed_at else None,
            tu.to_db(shipped_at) if shipped_at else None, tu.to_db(delivered_at) if delivered_at else None,
            tu.to_db(cancelled_at) if cancelled_at else None, tu.to_db(returned_at) if returned_at else None,
        ),
    )
    order_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    for sku, name, unit_price, qty in items:
        unit_satang = parse_satang(unit_price)
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, sku, name, unit_price_satang, quantity, line_total_satang) "
            "VALUES (?, (SELECT id FROM products WHERE sku=?), ?, ?, ?, ?, ?)",
            (order_id, sku, sku, name, unit_satang, qty, unit_satang * qty),
        )
    return order_id


def _price(items, volume_pct_threshold="1000.00"):
    """Compute pricing for a seed order with no coupon (helper only)."""
    sub = sum(parse_satang(p) * q for _, _, p, q in items)
    from .money import percent_of
    vd = percent_of(sub, 10) if sub >= parse_satang(volume_pct_threshold) else 0
    goods = sub - vd
    vat = percent_of(goods, 7)
    ship = 0 if goods >= parse_satang("500.00") else 5000
    from .money import to_money
    return {
        "subtotal": to_money(sub), "volume_discount": to_money(vd), "coupon_discount": "0.00",
        "goods_total": to_money(goods), "vat": to_money(vat), "shipping": to_money(ship),
        "grand_total": to_money(goods + vat + ship),
    }


def load(conn):
    """Delete-then-seed is already done by the caller for reset(); this
    function only inserts. Returns the reset instant (aware UTC)."""
    reset_at = tu.now_utc()
    conn.execute(
        "INSERT INTO system_state (key, value) VALUES ('last_reset_at', ?)",
        (tu.to_db(reset_at),),
    )

    uid = {}
    for n in range(1, 4):
        uid[f"customer{n}"] = _insert_user(conn, f"customer{n}", "customer")
    for n in range(1, 4):
        uid[f"staff{n}"] = _insert_user(conn, f"staff{n}", "staff")
    for n in range(1, 4):
        uid[f"manager{n}"] = _insert_user(conn, f"manager{n}", "manager")
    for n in range(1, 4):
        uid[f"admin{n}"] = _insert_user(conn, f"admin{n}", "admin")

    conn.execute("UPDATE users SET phone=?, birthdate=? WHERE id=?",
                 ("0812345678", "1995-03-14", uid["customer1"]))
    conn.execute("UPDATE users SET phone=?, birthdate=? WHERE id=?",
                 ("0898765432", "1990-07-21", uid["customer2"]))
    conn.execute("UPDATE users SET birthdate=? WHERE id=?",
                 ("2000-01-01", uid["customer3"]))

    now = reset_at
    _insert_address(conn, uid["customer1"], "Home", "Somchai Jaidee", "0812345678",
                     "55/1 Phahonyothin Rd", None, "Bangkok", "10400", 1, now)

    c2_home = _insert_address(conn, uid["customer2"], "Home", "Malee Rakdee", "0898765432",
                               "99/9 Sukhumvit Rd", None, "Bangkok", "10110", 1, now)
    _insert_address(conn, uid["customer2"], "Office", "Malee Rakdee", "0898765432",
                    "12 Silom Rd", None, "Bangkok", "10500", 0, now)

    _insert_address(conn, uid["customer3"], "Home", "Preecha Boonmee", "0855555555",
                     "99 Nimmanhaemin Rd", None, "Chiang Mai", "50000", 1, now)
    _insert_address(conn, uid["customer3"], "Office", "Preecha Boonmee", "0855555555",
                     "15 Patong Beach Rd", None, "Phuket", "83000", 0, now)
    _insert_address(conn, uid["customer3"], "Parents", "Preecha Boonmee", "0855555555",
                     "22 Mittraphap Rd", None, "Khon Kaen", "40000", 0, now)
    _insert_address(conn, uid["customer3"], "Condo", "Preecha Boonmee", "0855555555",
                     "8 Sukhumvit Pattaya Rd", None, "Chonburi", "20000", 0, now)
    _insert_address(conn, uid["customer3"], "Shop", "Preecha Boonmee", "0855555555",
                     "3 Niphat Uthit 1 Rd", None, "Songkhla", "90000", 0, now)

    pid = {}
    for sku, name, cat, price, stock, active in PRODUCTS:
        pid[sku] = _insert_product(conn, sku, name, cat, price, stock, active)

    far_future = _far_future()
    far_past = _far_past_start()
    t0m = reset_at.replace(second=0, microsecond=0)
    _insert_coupon(conn, "SAVE10", "PERCENT", far_past, far_future,
                    percent_off=10, max_discount="200.00", per_user_limit=1)
    _insert_coupon(conn, "FLAT100", "FIXED", far_past, far_future,
                    amount_off="100.00", min_spend="500.00", per_user_limit=5)
    _insert_coupon(conn, "BIGFLAT", "FIXED", far_past, far_future,
                    amount_off="5000.00", per_user_limit=5)
    _insert_coupon(conn, "LASTONE", "PERCENT", far_past, far_future,
                    percent_off=15, per_user_limit=1, total_limit=2)
    _insert_coupon(conn, "SOON3", "PERCENT", t0m, t0m + timedelta(minutes=3),
                    percent_off=5, per_user_limit=5)
    _insert_coupon(conn, "LATER10", "FIXED", t0m + timedelta(minutes=10), far_future,
                    amount_off="50.00", per_user_limit=5)
    from datetime import datetime
    _insert_coupon(conn, "OLD2025", "PERCENT",
                    datetime(2024, 12, 31, 17, 0, tzinfo=tu.UTC),
                    datetime(2025, 12, 31, 16, 59, tzinfo=tu.UTC),
                    percent_off=20, per_user_limit=1)
    _insert_coupon(conn, "OFF5", "PERCENT", far_past, far_future,
                    percent_off=10, per_user_limit=1, active=0)

    c2 = uid["customer2"]
    addr2 = {"label": "Home", "recipient_name": "Malee Rakdee", "phone": "0898765432",
             "line1": "99/9 Sukhumvit Rd", "line2": None, "province": "Bangkok", "postal_code": "10110"}

    # Order 1: DELIVERED, uses SAVE10, delivered T0-8d (return window closed)
    created = now - timedelta(days=9)
    paid = now - timedelta(days=8, hours=12)
    packed = now - timedelta(days=8, hours=10)
    shipped = now - timedelta(days=8, hours=6)
    delivered = now - timedelta(days=8)
    items1 = [("DM-2005", "Rain Jacket", "1590.00", 1), ("DM-3002", "Gel Pen Set", "59.00", 2)]
    pricing1 = {"subtotal": "1708.00", "volume_discount": "170.80", "coupon_discount": "153.72",
                "goods_total": "1383.48", "vat": "96.84", "shipping": "0.00", "grand_total": "1480.32"}
    _insert_order(conn, c2, "DELIVERED", addr2, items1, pricing1, "SAVE10",
                  created, paid, packed, shipped, delivered)
    _insert_movement(conn, pid["DM-2005"], -1, 8, "ORDER", "customer2", created)
    _insert_movement(conn, pid["DM-3002"], -2, 150, "ORDER", "customer2", created)

    # Order 2: DELIVERED, no coupon, delivered T0-6d (return window open)
    created = now - timedelta(days=7)
    paid = now - timedelta(days=6, hours=20)
    packed = now - timedelta(days=6, hours=18)
    shipped = now - timedelta(days=6, hours=12)
    delivered = now - timedelta(days=6)
    items2 = [("DM-1001", "Ceramic Coffee Mug", "129.00", 2), ("DM-2002", "Canvas Tote Bag", "159.00", 1)]
    pricing2 = _price(items2)
    _insert_order(conn, c2, "DELIVERED", addr2, items2, pricing2, None,
                  created, paid, packed, shipped, delivered)
    _insert_movement(conn, pid["DM-1001"], -2, 40, "ORDER", "customer2", created)
    _insert_movement(conn, pid["DM-2002"], -1, 33, "ORDER", "customer2", created)

    # Order 3: SHIPPED, shipped T0-1d
    created = now - timedelta(days=2)
    paid = now - timedelta(days=1, hours=20)
    packed = now - timedelta(days=1, hours=12)
    shipped = now - timedelta(days=1)
    items3 = [("DM-4001", "USB-C Cable 1 m", "100.00", 1)]
    pricing3 = _price(items3)
    _insert_order(conn, c2, "SHIPPED", addr2, items3, pricing3, None, created, paid, packed, shipped)
    _insert_movement(conn, pid["DM-4001"], -1, 70, "ORDER", "customer2", created)

    # Order 4: PACKED, packed T0-3h
    created = now - timedelta(hours=4)
    paid = now - timedelta(hours=3, minutes=30)
    packed = now - timedelta(hours=3)
    items4 = [("DM-4002", "Wireless Mouse", "599.00", 1)]
    pricing4 = _price(items4)
    _insert_order(conn, c2, "PACKED", addr2, items4, pricing4, None, created, paid, packed)
    _insert_movement(conn, pid["DM-4002"], -1, 20, "ORDER", "customer2", created)

    # Order 5: PAID, created T0-95min, paid T0-90min
    created = now - timedelta(minutes=95)
    paid = now - timedelta(minutes=90)
    items5 = [("DM-5001", "Scented Candle", "149.00", 2)]
    pricing5 = _price(items5)
    _insert_order(conn, c2, "PAID", addr2, items5, pricing5, None, created, paid)
    _insert_movement(conn, pid["DM-5001"], -2, 50, "ORDER", "customer2", created)

    # Order 6: PENDING_PAYMENT, created T0-61min
    created = now - timedelta(minutes=61)
    items6 = [("DM-5002", "Throw Pillow", "399.00", 1)]
    pricing6 = _price(items6)
    _insert_order(conn, c2, "PENDING_PAYMENT", addr2, items6, pricing6, None, created)
    _insert_movement(conn, pid["DM-5002"], -1, 18, "ORDER", "customer2", created)

    # Order 7: PENDING_PAYMENT, created T0-59min
    created = now - timedelta(minutes=59)
    items7 = [("DM-3005", "Sticky Notes Pack", "25.00", 4)]
    pricing7 = _price(items7)
    _insert_order(conn, c2, "PENDING_PAYMENT", addr2, items7, pricing7, None, created)
    _insert_movement(conn, pid["DM-3005"], -4, 300, "ORDER", "customer2", created)

    # Order 8: CANCELLED while PENDING_PAYMENT, cancelled T0-2d
    created = now - timedelta(days=2, hours=1)
    cancelled = now - timedelta(days=2)
    items8 = [("DM-3002", "Gel Pen Set", "59.00", 2)]
    pricing8 = _price(items8)
    _insert_order(conn, c2, "CANCELLED", addr2, items8, pricing8, None, created,
                  cancelled_at=cancelled, refund="0.00")
    _insert_movement(conn, pid["DM-3002"], -2, 148, "ORDER", "customer2", created)
    _insert_movement(conn, pid["DM-3002"], 2, 150, "CANCEL", "customer2", cancelled)

    # customer2 review
    conn.execute(
        "INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
        (pid["DM-1001"], c2, 4, "Sturdy and keeps coffee warm.", tu.to_db(now - timedelta(days=5))),
    )
    # customer3 review (seeded directly, bypassing the purchase check)
    conn.execute(
        "INSERT INTO reviews (product_id, user_id, rating, comment, created_at) VALUES (?,?,?,?,?)",
        (pid["DM-1001"], uid["customer3"], 5, "Perfect size for my morning coffee.",
         tu.to_db(now - timedelta(days=4))),
    )

    # customer3 cart
    c3 = uid["customer3"]
    conn.execute("INSERT INTO carts (user_id, coupon_code, updated_at) VALUES (?, NULL, ?)",
                 (c3, tu.to_db(now)))
    for sku, qty, offset in [("DM-3003", 1, 3), ("DM-1001", 2, 2), ("DM-2003", 1, 1)]:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity, created_at) VALUES (?,?,?,?)",
            (c3, pid[sku], qty, tu.to_db(now - timedelta(minutes=offset))),
        )

    # customer3 wishlist
    conn.execute("INSERT INTO wishlist_items (user_id, product_id, added_at) VALUES (?,?,?)",
                 (c3, pid["DM-5001"], tu.to_db(now - timedelta(days=1))))
    conn.execute("INSERT INTO wishlist_items (user_id, product_id, added_at) VALUES (?,?,?)",
                 (c3, pid["DM-5002"], tu.to_db(now - timedelta(hours=12))))

    # low-stock snapshot (initial, matches REQ-INV-004 ordering)
    rows = [
        (1, pid["DM-5003"], "DM-5003", "Vintage Poster", 0),
        (2, pid["DM-3003"], "DM-3003", "Limited Edition Notebook", 1),
        (3, pid["DM-1004"], "DM-1004", "Glass Water Bottle", 5),
    ]
    for position, product_id, sku, name, stock in rows:
        conn.execute(
            "INSERT INTO low_stock_snapshot (position, product_id, sku, name, stock) VALUES (?,?,?,?,?)",
            (position, product_id, sku, name, stock),
        )
    conn.execute("INSERT INTO system_state (key, value) VALUES ('low_stock_taken_at', ?)",
                 (tu.to_db(now),))

    return reset_at
