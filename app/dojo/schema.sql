-- Schema per docs/design/data-model.md

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('customer','staff','manager','admin')),
    phone TEXT,
    birthdate TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','LOCKED')),
    failed_login_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until TEXT,
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0,1)),
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX ux_users_username_ci ON users (lower(username));

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX ix_sessions_user ON sessions (user_id);

CREATE TABLE addresses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    recipient_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    line1 TEXT NOT NULL,
    line2 TEXT,
    province TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1)),
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX ux_addresses_default ON addresses (user_id) WHERE is_default = 1;

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('Drinkware','Apparel','Stationery','Electronics','Home')),
    price_satang INTEGER NOT NULL CHECK (price_satang > 0 AND price_satang <= 9999999),
    stock INTEGER NOT NULL CHECK (stock >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE inventory_movements (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    delta INTEGER NOT NULL CHECK (delta <> 0),
    stock_after INTEGER NOT NULL CHECK (stock_after >= 0),
    reason TEXT NOT NULL CHECK (reason IN ('RECEIVE','DAMAGE','CORRECTION','ORDER','CANCEL','RETURN')),
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX ix_movements_product ON inventory_movements (product_id);

CREATE TABLE carts (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    coupon_code TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE cart_items (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
    created_at TEXT NOT NULL,
    UNIQUE (user_id, product_id)
);

CREATE TABLE wishlist_items (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    added_at TEXT NOT NULL,
    PRIMARY KEY (user_id, product_id)
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT CHECK (comment IS NULL OR length(comment) <= 500),
    created_at TEXT NOT NULL,
    UNIQUE (product_id, user_id)
);

CREATE TABLE coupons (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('PERCENT','FIXED')),
    percent_off INTEGER CHECK (percent_off BETWEEN 1 AND 100),
    amount_off_satang INTEGER CHECK (amount_off_satang > 0),
    max_discount_satang INTEGER CHECK (max_discount_satang > 0),
    min_spend_satang INTEGER NOT NULL DEFAULT 0 CHECK (min_spend_satang >= 0),
    starts_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    per_user_limit INTEGER NOT NULL DEFAULT 1 CHECK (per_user_limit BETWEEN 1 AND 99),
    total_limit INTEGER CHECK (total_limit >= 1),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL,
    CHECK (starts_at <= expires_at),
    CHECK (
        (type = 'PERCENT' AND percent_off IS NOT NULL AND amount_off_satang IS NULL) OR
        (type = 'FIXED' AND amount_off_satang IS NOT NULL AND percent_off IS NULL)
    )
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL CHECK (status IN ('PENDING_PAYMENT','PAID','PACKED','SHIPPED','DELIVERED','CANCELLED','RETURNED')),
    coupon_code TEXT,
    subtotal_satang INTEGER NOT NULL CHECK (subtotal_satang >= 0),
    volume_discount_satang INTEGER NOT NULL CHECK (volume_discount_satang >= 0),
    coupon_discount_satang INTEGER NOT NULL CHECK (coupon_discount_satang >= 0),
    goods_total_satang INTEGER NOT NULL CHECK (goods_total_satang >= 0),
    vat_satang INTEGER NOT NULL CHECK (vat_satang >= 0),
    shipping_satang INTEGER NOT NULL CHECK (shipping_satang >= 0),
    grand_total_satang INTEGER NOT NULL CHECK (grand_total_satang >= 0),
    addr_label TEXT NOT NULL,
    addr_recipient_name TEXT NOT NULL,
    addr_phone TEXT NOT NULL,
    addr_line1 TEXT NOT NULL,
    addr_line2 TEXT,
    addr_province TEXT NOT NULL,
    addr_postal_code TEXT NOT NULL,
    refund_amount_satang INTEGER NOT NULL DEFAULT 0 CHECK (refund_amount_satang >= 0),
    created_at TEXT NOT NULL,
    paid_at TEXT,
    packed_at TEXT,
    shipped_at TEXT,
    delivered_at TEXT,
    cancelled_at TEXT,
    returned_at TEXT,
    CHECK (goods_total_satang = subtotal_satang - volume_discount_satang - coupon_discount_satang),
    CHECK (grand_total_satang = goods_total_satang + vat_satang + shipping_satang)
);
CREATE INDEX ix_orders_user ON orders (user_id);
CREATE INDEX ix_orders_status ON orders (status);
CREATE INDEX ix_orders_coupon ON orders (coupon_code);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    unit_price_satang INTEGER NOT NULL CHECK (unit_price_satang > 0),
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
    line_total_satang INTEGER NOT NULL CHECK (line_total_satang = unit_price_satang * quantity)
);
CREATE INDEX ix_order_items_order ON order_items (order_id);

CREATE TABLE job_runs (
    id INTEGER PRIMARY KEY,
    job TEXT NOT NULL CHECK (job IN ('cancel-unpaid-orders','hourly-sales-report','low-stock-snapshot')),
    trigger TEXT NOT NULL CHECK (trigger IN ('SCHEDULED','MANUAL')),
    triggered_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('RUNNING','SUCCESS','FAILED')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    summary_json TEXT,
    error_message TEXT
);
CREATE UNIQUE INDEX ux_job_runs_running ON job_runs (job) WHERE status = 'RUNNING';

CREATE TABLE window_reports (
    id INTEGER PRIMARY KEY,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    order_count INTEGER NOT NULL CHECK (order_count >= 0),
    gross_sales_satang INTEGER NOT NULL CHECK (gross_sales_satang >= 0),
    vat_total_satang INTEGER NOT NULL CHECK (vat_total_satang >= 0),
    shipping_total_satang INTEGER NOT NULL CHECK (shipping_total_satang >= 0),
    discount_total_satang INTEGER NOT NULL CHECK (discount_total_satang >= 0),
    generated_at TEXT NOT NULL,
    UNIQUE (window_start, window_end),
    CHECK (window_start < window_end)
);

CREATE TABLE low_stock_snapshot (
    position INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    stock INTEGER NOT NULL CHECK (stock >= 0)
);

CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
