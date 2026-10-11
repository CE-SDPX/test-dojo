# ตารางสิทธิ์ตามบทบาท (RBAC Matrix)

## 1. คำอธิบาย

| สัญลักษณ์ | ความหมาย |
|---|---|
| ✔ | อนุญาต |
| ✔ (own) | อนุญาตเฉพาะทรัพยากรของตนเอง (ของผู้อื่นได้ 404) |
| ✖ | ไม่อนุญาต ระบบตอบ 403 `FORBIDDEN` |
| ไม่ต้องยืนยันตัวตน | เรียกได้โดยไม่มีโทเคน |

- ผู้เรียกที่ไม่มีโทเคนที่ถูกต้องต้องได้ 401 `UNAUTHENTICATED` ในทุก endpoint ยกเว้นที่ระบุว่าไม่ต้องยืนยันตัวตน
- ผู้ใช้ที่อยู่ในสถานะต้องเปลี่ยนรหัสผ่านเรียกได้เฉพาะ `GET /api/me`, `POST /api/auth/change-password` และ `POST /api/auth/logout` (ตัวอื่นได้ 403 `PASSWORD_CHANGE_REQUIRED`)
- ลำดับการตรวจเป็นไปตาม `REQ-COM-007`
- บทบาท: C = `customer`, S = `staff`, M = `manager`, A = `admin`

## 2. สิทธิ์ของ endpoint

### 2.1 ไม่ต้องยืนยันตัวตน (ผู้เยี่ยมชมเรียกได้ด้วย)

| Endpoint | หมายเหตุ |
|---|---|
| `POST /api/auth/register` | สมัครสมาชิก |
| `POST /api/auth/login` | เข้าสู่ระบบ |
| `GET /api/health`, `GET /api/version`, `POST /api/reset` | จุดเชื่อมต่อสำหรับการฝึก |
| `GET /api/products` | รายการสินค้า (REQ-CAT-001) |
| `GET /api/products/{id}` | รายละเอียดสินค้า (REQ-CAT-006) — `in_wishlist` เป็น `false` เสมอเมื่อไม่ได้เข้าสู่ระบบ |
| `GET /api/products/{id}/reviews` | รายการรีวิว (REQ-REV-004) |

สามจุดสุดท้ายยังใช้ได้ตามปกติเมื่อมีโทเคนที่ถูกต้องของบทบาทใดก็ได้ (ไม่จำกัดเฉพาะ `customer`) และ `GET /api/products/{id}` จะเติม `in_wishlist` ตามจริงเมื่อผู้เรียกเป็น `customer` ที่เข้าสู่ระบบ

### 2.2 ผู้ใช้ทุกบทบาทที่ยืนยันตัวตนแล้ว

| Endpoint | C | S | M | A |
|---|---|---|---|---|
| `POST /api/auth/logout` | ✔ | ✔ | ✔ | ✔ |
| `POST /api/auth/change-password` | ✔ | ✔ | ✔ | ✔ |
| `GET /api/me` | ✔ | ✔ | ✔ | ✔ |
| `PUT /api/me` | ✔ | ✔ | ✔ | ✔ |

### 2.3 ฟังก์ชันของลูกค้า

| Endpoint | C | S | M | A |
|---|---|---|---|---|
| `GET /api/me/addresses` | ✔ | ✖ | ✖ | ✖ |
| `POST /api/me/addresses` | ✔ | ✖ | ✖ | ✖ |
| `PUT /api/me/addresses/{id}` | ✔ (own) | ✖ | ✖ | ✖ |
| `DELETE /api/me/addresses/{id}` | ✔ (own) | ✖ | ✖ | ✖ |
| `POST /api/me/addresses/{id}/default` | ✔ (own) | ✖ | ✖ | ✖ |
| `POST /api/products/{id}/reviews` | ✔ | ✖ | ✖ | ✖ |
| `GET /api/wishlist` | ✔ | ✖ | ✖ | ✖ |
| `PUT /api/wishlist/{product_id}` | ✔ | ✖ | ✖ | ✖ |
| `DELETE /api/wishlist/{product_id}` | ✔ | ✖ | ✖ | ✖ |
| `GET /api/cart` | ✔ | ✖ | ✖ | ✖ |
| `POST /api/cart/items` | ✔ | ✖ | ✖ | ✖ |
| `PATCH /api/cart/items/{item_id}` | ✔ (own) | ✖ | ✖ | ✖ |
| `DELETE /api/cart/items/{item_id}` | ✔ (own) | ✖ | ✖ | ✖ |
| `PUT /api/cart/coupon` | ✔ | ✖ | ✖ | ✖ |
| `DELETE /api/cart/coupon` | ✔ | ✖ | ✖ | ✖ |
| `POST /api/orders` | ✔ | ✖ | ✖ | ✖ |
| `GET /api/orders` | ✔ (own) | ✖ | ✖ | ✖ |
| `POST /api/orders/{id}/pay` | ✔ (own) | ✖ | ✖ | ✖ |
| `POST /api/orders/{id}/return` | ✔ (own) | ✖ | ✖ | ✖ |

### 2.4 คำสั่งซื้อที่ใช้ร่วมกัน

| Endpoint | C | S | M | A |
|---|---|---|---|---|
| `GET /api/orders/{id}` | ✔ (own) | ✔ | ✖ | ✔ |
| `POST /api/orders/{id}/cancel` | ✔ (own) | ✔ | ✖ | ✔ |

สถานะที่แต่ละบทบาทยกเลิกได้ กำหนดใน `REQ-ORD-004`

### 2.5 เจ้าหน้าที่คลัง (staff) และ admin

| Endpoint | C | S | M | A |
|---|---|---|---|---|
| `GET /api/manage/orders` | ✖ | ✔ | ✖ | ✔ |
| `PATCH /api/manage/orders/{id}/status` | ✖ | ✔ | ✖ | ✔ |
| `GET /api/manage/inventory` | ✖ | ✔ | ✖ | ✔ |
| `POST /api/manage/inventory/adjustments` | ✖ | ✔ | ✖ | ✔ |
| `GET /api/manage/inventory/movements` | ✖ | ✔ | ✖ | ✔ |
| `GET /api/manage/inventory/low-stock` | ✖ | ✔ | ✖ | ✔ |

### 2.6 ผู้จัดการ (manager) และ admin

| Endpoint | C | S | M | A |
|---|---|---|---|---|
| `GET /api/manage/products` | ✖ | ✖ | ✔ | ✔ |
| `POST /api/manage/products` | ✖ | ✖ | ✔ | ✔ |
| `PUT /api/manage/products/{id}` | ✖ | ✖ | ✔ | ✔ |
| `PATCH /api/manage/products/{id}/active` | ✖ | ✖ | ✔ | ✔ |
| `GET /api/manage/coupons` | ✖ | ✖ | ✔ | ✔ |
| `POST /api/manage/coupons` | ✖ | ✖ | ✔ | ✔ |
| `PUT /api/manage/coupons/{id}` | ✖ | ✖ | ✔ | ✔ |
| `PATCH /api/manage/coupons/{id}/active` | ✖ | ✖ | ✔ | ✔ |
| `GET /api/manage/reports/sales` และ `sales.csv` | ✖ | ✖ | ✔ | ✔ |
| `GET /api/manage/reports/top-products` และ `top-products.csv` | ✖ | ✖ | ✔ | ✔ |
| `GET /api/manage/reports/coupon-usage` | ✖ | ✖ | ✔ | ✔ |
| `GET /api/manage/reports/hourly` และ `hourly.csv` | ✖ | ✖ | ✔ | ✔ |

### 2.7 เฉพาะผู้ดูแลระบบ (admin)

| Endpoint | C | S | M | A |
|---|---|---|---|---|
| `GET /api/admin/users` | ✖ | ✖ | ✖ | ✔ |
| `POST /api/admin/users/{id}/lock` | ✖ | ✖ | ✖ | ✔ |
| `POST /api/admin/users/{id}/unlock` | ✖ | ✖ | ✖ | ✔ |
| `POST /api/admin/users/{id}/reset-password` | ✖ | ✖ | ✖ | ✔ |
| `PATCH /api/admin/users/{id}/role` | ✖ | ✖ | ✖ | ✔ |
| `GET /api/admin/jobs` | ✖ | ✖ | ✖ | ✔ |
| `POST /api/admin/jobs/{name}/run` | ✖ | ✖ | ✖ | ✔ |
| `GET /api/admin/jobs/{name}/runs` | ✖ | ✖ | ✖ | ✔ |

## 3. สิทธิ์ของหน้าจอ

| หน้า | Route | ผู้เยี่ยมชม | C | S | M | A |
|---|---|---|---|---|---|---|
| Sign in | `/login` | ✔ | ไม่ต้องยืนยันตัวตน | | | |
| Register | `/register` | ✔ | ไม่ต้องยืนยันตัวตน | | | |
| Profile | `/profile` | ✖ | ✔ | ✔ | ✔ | ✔ |
| Change password | `/change-password` | ✖ | ✔ | ✔ | ✔ | ✔ |
| Products (หน้าแรกของผู้เยี่ยมชม) | `/products` | ✔ | ✔ | ✖ | ✖ | ✖ |
| Product detail | `/products/{id}` | ✔ | ✔ | ✖ | ✖ | ✖ |
| Wishlist | `/wishlist` | ✖ | ✔ | ✖ | ✖ | ✖ |
| Cart | `/cart` | ✖ | ✔ | ✖ | ✖ | ✖ |
| Checkout | `/checkout` | ✖ | ✔ | ✖ | ✖ | ✖ |
| Order confirmation | `/orders/{id}/confirmation` | ✖ | ✔ (own) | ✖ | ✖ | ✖ |
| My orders | `/orders` | ✖ | ✔ | ✖ | ✖ | ✖ |
| Order detail | `/orders/{id}` | ✖ | ✔ (own) | ✖ | ✖ | ✖ |
| Order queue | `/staff/orders` | ✖ | ✖ | ✔ | ✖ | ✔ |
| Inventory | `/staff/inventory` | ✖ | ✖ | ✔ | ✖ | ✔ |
| Low stock | `/staff/low-stock` | ✖ | ✖ | ✔ | ✖ | ✔ |
| Product management | `/manager/products` | ✖ | ✖ | ✖ | ✔ | ✔ |
| Coupon management | `/manager/coupons` | ✖ | ✖ | ✖ | ✔ | ✔ |
| Reports | `/manager/reports` | ✖ | ✖ | ✖ | ✔ | ✔ |
| User management | `/admin/users` | ✖ | ✖ | ✖ | ✖ | ✔ |
| Jobs | `/admin/jobs` | ✖ | ✖ | ✖ | ✖ | ✔ |

- หน้าที่ ✖ สำหรับบทบาทที่เข้าสู่ระบบแล้วต้องแสดงหน้า 403 เมื่อเปิดโดยตรงผ่าน URL
- หน้าที่ ✖ สำหรับผู้เยี่ยมชม (ยังไม่เข้าสู่ระบบ) ต้องนำไปหน้า `/login` ยกเว้น Products และ Product detail ซึ่งเปิดได้โดยตรง
- ผู้ดูแลระบบดูคำสั่งซื้อของลูกค้าผ่านหน้า Order queue (ไม่มีหน้า `/orders/{id}` สำหรับ admin)
- หน้าแรก (`/`) นำผู้เยี่ยมชมและ `customer` ไปหน้า Products เสมอ ส่วน `staff`, `manager`, `admin` ไปหน้าแรกของบทบาทตนเอง (`REQ-AUTH-011`)

## 4. เมนูของแต่ละบทบาท

| บทบาท | รายการเมนู (ตามลำดับ) |
|---|---|
| ผู้เยี่ยมชม | Products (พร้อมลิงก์ Sign in และ Create an account แทนเมนูผู้ใช้) |
| `customer` | Products, Wishlist, Cart, My orders, Profile, Sign out |
| `staff` | Orders, Inventory, Low stock, Profile, Sign out |
| `manager` | Reports, Products, Coupons, Profile, Sign out |
| `admin` | Users, Jobs, Orders, Inventory, Low stock, Products, Coupons, Reports, Profile, Sign out |

ข้อความของเมนูเป็นไปตาม `docs/design/ui/copy-deck.md`
