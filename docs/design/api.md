# เอกสารอ้างอิง API

เอกสารฉบับนี้สรุปจุดเชื่อมต่อ (endpoint) ทั้งหมดของ DojoMart รูปแบบข้อมูลที่ส่งและรับ และรหัสข้อผิดพลาด ไฟล์ `openapi.yaml` ในโฟลเดอร์เดียวกันมีเนื้อหาเดียวกันในรูปแบบที่นำเข้า Postman ได้ ข้อกำหนดเชิงพฤติกรรมอยู่ใน PRD ที่อ้างอิงในแต่ละส่วน

## 1. ข้อตกลงทั่วไป

| เรื่อง | ข้อตกลง |
|---|---|
| ที่อยู่หลัก (base URL) | `http://localhost:8001` (ปรับได้ด้วย `API_PORT`) เส้นทางทั้งหมดขึ้นต้นด้วย `/api` |
| รูปแบบข้อมูล | JSON (`Content-Type: application/json; charset=utf-8`) ยกเว้นไฟล์ CSV |
| การยืนยันตัวตน | ส่วนหัว `Authorization: Bearer <token>` โทเคนได้จาก `POST /api/auth/login` |
| จำนวนเงิน | สตริงทศนิยม 2 ตำแหน่ง เช่น `"1234.50"` |
| เวลา | ISO 8601 พร้อมส่วนต่างเวลา `+07:00` เช่น `"2026-10-10T14:30:05+07:00"` เวลาของคูปองไม่มีวินาที เช่น `"2026-10-10T14:30+07:00"` |
| วันที่ล้วน | `YYYY-MM-DD` |
| ฟิลด์ที่ไม่รู้จักในคำขอ | ถูกละเว้น |
| การแบ่งหน้า | พารามิเตอร์ `page`, `page_size` การตอบกลับ `{ items, page, page_size, total_items, total_pages }` ตาม `REQ-COM-011` |
| CORS | อนุญาตทุก origin (อยู่นอกขอบเขตการทดสอบ) |

## 2. รูปแบบข้อผิดพลาด

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "details": [ { "field": "quantity", "message": "Quantity must be a whole number from 1 to 10." } ]
  }
}
```

- `details` ปรากฏเฉพาะ `VALIDATION_ERROR`
- `reason` (ข้อความสั้นรหัสตัวพิมพ์ใหญ่) ปรากฏเพิ่มในออบเจ็กต์ `error` เฉพาะ `COUPON_INVALID`

## 3. รหัสข้อผิดพลาด

| `code` | HTTP | `message` | กรณี |
|---|---|---|---|
| `VALIDATION_ERROR` | 400 | `One or more fields are invalid.` | ข้อมูลในคำขอ พารามิเตอร์ หรือ query ไม่ถูกต้อง |
| `INVALID_JSON` | 400 | `Request body must be valid JSON.` | เนื้อหาคำขอไม่ใช่ JSON ที่ถูกต้อง |
| `INVALID_CURRENT_PASSWORD` | 400 | `Current password is incorrect.` | รหัสผ่านปัจจุบันไม่ถูกต้องตอนเปลี่ยนรหัสผ่าน |
| `UNAUTHENTICATED` | 401 | `Authentication is required.` | ไม่มีโทเคน โทเคนไม่ถูกต้อง หมดอายุ หรือถูกยกเลิก |
| `INVALID_CREDENTIALS` | 401 | `Invalid username or password.` | ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง |
| `FORBIDDEN` | 403 | `You do not have permission to perform this action.` | บทบาทไม่มีสิทธิ์ |
| `ACCOUNT_DISABLED` | 403 | `Your account has been locked by an administrator.` | บัญชีถูกล็อกโดยผู้ดูแลระบบ |
| `PASSWORD_CHANGE_REQUIRED` | 403 | `You must change your password before continuing.` | ต้องเปลี่ยนรหัสผ่านก่อน |
| `REVIEW_NOT_ALLOWED` | 403 | `You can review a product only after receiving it.` | ลูกค้ายังไม่เคยได้รับสินค้านั้น |
| `NOT_FOUND` | 404 | `The requested resource was not found.` | ไม่พบทรัพยากร หรือเป็นของผู้อื่น (สำหรับ `customer`) หรือเส้นทางไม่มีอยู่ |
| `METHOD_NOT_ALLOWED` | 405 | `Method not allowed.` | วิธี HTTP ไม่รองรับ |
| `USERNAME_TAKEN` | 409 | `This username is already taken.` | ชื่อผู้ใช้ซ้ำ |
| `QUANTITY_LIMIT` | 409 | `You can add at most 10 of each product.` | จำนวนต่อสินค้าในตะกร้าเกิน 10 |
| `CART_LINE_LIMIT` | 409 | `Your cart can hold at most 20 different products.` | รายการในตะกร้าเกิน 20 |
| `INSUFFICIENT_STOCK` | 409 | `This product is out of stock.` (สต็อก 0) / `Only {n} left in stock.` (เมื่อเพิ่มหรือแก้ตะกร้า) / `Not enough stock for "{name}".` (เมื่อสั่งซื้อ) | สต็อกไม่พอ |
| `CART_EMPTY` | 409 | `Your cart is empty.` | ตะกร้าว่าง |
| `COUPON_INVALID` | 409 | ข้อความตามเหตุผลใน `REQ-COUP-002` | คูปองใช้ไม่ได้ (`reason`: `NOT_FOUND`, `NOT_STARTED`, `EXPIRED`, `MIN_SPEND`, `USER_LIMIT`, `TOTAL_LIMIT`) |
| `INVALID_TRANSITION` | 409 | `This order cannot be changed from its current status.` | เปลี่ยนสถานะคำสั่งซื้อไม่ได้ |
| `RETURN_WINDOW_CLOSED` | 409 | `The 7-day return period has ended.` | เลยกำหนดคืนสินค้า |
| `ADDRESS_LIMIT` | 409 | `You can save at most 5 addresses.` | ที่อยู่ครบ 5 รายการ |
| `ALREADY_IN_WISHLIST` | 409 | `This product is already in your wishlist.` | สินค้าอยู่ในรายการโปรดแล้ว |
| `WISHLIST_LIMIT` | 409 | `Your wishlist can hold at most 50 products.` | รายการโปรดครบ 50 |
| `REVIEW_EXISTS` | 409 | `You have already reviewed this product.` | รีวิวสินค้านี้แล้ว |
| `STOCK_NEGATIVE` | 409 | `Stock cannot be negative.` | การปรับสต็อกทำให้ติดลบ |
| `SKU_TAKEN` | 409 | `This SKU is already in use.` | รหัสสินค้าซ้ำ |
| `COUPON_CODE_TAKEN` | 409 | `This coupon code is already in use.` | รหัสคูปองซ้ำ |
| `ACCOUNT_ALREADY_LOCKED` | 409 | `This account is already locked.` | ล็อกบัญชีที่ถูกล็อกแล้ว |
| `ACCOUNT_NOT_LOCKED` | 409 | `This account is not locked.` | ปลดล็อกบัญชีที่ไม่ได้ถูกล็อก |
| `SELF_LOCK_FORBIDDEN` | 409 | `You cannot lock your own account.` | ผู้ดูแลระบบล็อกตนเอง |
| `LAST_ADMIN` | 409 | `At least one unlocked administrator must remain.` | ล็อกหรือลดบทบาทผู้ดูแลระบบคนสุดท้าย |
| `JOB_ALREADY_RUNNING` | 409 | `This job is already running.` | สั่งรันงานที่กำลังทำงานอยู่ |
| `ACCOUNT_LOCKED` | 423 | `Your account is temporarily locked. Please try again in {n} minute(s).` | ล็อกชั่วคราวจากการเข้าสู่ระบบผิดซ้ำ |
| `INTERNAL_ERROR` | 500 | `An unexpected error occurred.` | ข้อผิดพลาดภายใน |

## 4. ข้อความข้อผิดพลาดรายฟิลด์ (`details[].message`)

| ฟิลด์ | เงื่อนไขที่ไม่ผ่าน | ข้อความ |
|---|---|---|
| (ทุกฟิลด์) | ขาดหรือว่าง | `This field is required.` |
| `username` | รูปแบบหรือความยาวไม่ถูกต้อง | `Username must be 4 to 20 characters and contain only letters, digits and underscores.` |
| `password`, `new_password` | ไม่ตรงกฎรหัสผ่าน | `Password must be 8 to 20 characters with at least one letter and one digit, and no spaces.` |
| `new_password` | ซ้ำกับรหัสผ่านปัจจุบัน | `New password must be different from the current password.` |
| `display_name` | ความยาวไม่ถูกต้อง | `Display name must be 2 to 50 characters.` |
| `birthdate` | ไม่ใช่วันที่ที่ถูกต้อง | `Enter a valid date in the format YYYY-MM-DD.` |
| `birthdate` | อายุไม่ถึง 18 ปี | `You must be at least 18 years old to register.` |
| `phone` | รูปแบบไม่ถูกต้อง | `Phone number must be 10 digits starting with 0.` |
| `label` | ความยาวไม่ถูกต้อง | `Label must be 1 to 30 characters.` |
| `recipient_name` | ความยาวไม่ถูกต้อง | `Recipient name must be 2 to 50 characters.` |
| `line1` | ความยาวไม่ถูกต้อง | `Address line 1 must be 5 to 100 characters.` |
| `line2` | ความยาวเกิน | `Address line 2 must be at most 100 characters.` |
| `province` | ความยาวไม่ถูกต้อง | `Province must be 2 to 50 characters.` |
| `postal_code` | ไม่ใช่ตัวเลข 5 หลัก | `Postal code must be 5 digits.` |
| `address_id`, `product_id` | ไม่ใช่จำนวนเต็ม | `This field must be a whole number.` |
| `quantity` | ไม่ใช่จำนวนเต็ม 1 ถึง 10 | `Quantity must be a whole number from 1 to 10.` |
| `rating` | ไม่ใช่จำนวนเต็ม 1 ถึง 5 | `Rating must be a whole number from 1 to 5.` |
| `comment` | ยาวเกิน 500 | `Comment must be at most 500 characters.` |
| `q` | ยาวเกิน 100 | `Search text must be at most 100 characters.` |
| `category` | ไม่อยู่ในรายการ | `Category must be one of: Drinkware, Apparel, Stationery, Electronics, Home.` |
| `min_price`, `max_price` | ไม่ใช่จำนวนเงินที่ถูกต้อง | `Price must be a number with at most 2 decimal places.` |
| `min_price` | มากกว่า `max_price` | `Minimum price must not be greater than maximum price.` |
| `sort` | ไม่อยู่ในรายการ | `Sort must be one of: name_asc, name_desc, price_asc, price_desc.` |
| `page` | ไม่ใช่จำนวนเต็ม 1 ขึ้นไป | `Page must be a whole number of 1 or more.` |
| `page_size` | ไม่ใช่จำนวนเต็ม 1 ถึง 50 | `Page size must be a whole number from 1 to 50.` |
| `limit` (รายงานสินค้าขายดี) | ไม่ใช่จำนวนเต็ม 1 ถึง 20 | `Limit must be a whole number from 1 to 20.` |
| `status` | ไม่ใช่ค่าที่กำหนด | `Status is not valid.` |
| `code` (คูปอง) | รูปแบบไม่ถูกต้อง | `Coupon code must be 4 to 20 letters or digits.` |
| `sku` | รูปแบบไม่ถูกต้อง | `SKU must be 3 to 20 characters using A-Z, 0-9 and hyphens.` |
| `name` (สินค้า) | ความยาวไม่ถูกต้อง | `Name must be 2 to 100 characters.` |
| `description` | ยาวเกิน | `Description must be at most 1000 characters.` |
| `price`, `amount_off`, `max_discount`, `min_spend` | ช่วงหรือรูปแบบไม่ถูกต้อง | `Amount must be between 0.01 and 99999.99.` (`min_spend` ใช้ `Amount must be between 0.00 and 99999.99.`) |
| `percent_off` | ไม่ใช่จำนวนเต็ม 1 ถึง 100 | `Percent must be a whole number from 1 to 100.` |
| `per_user_limit` | ไม่ใช่จำนวนเต็ม 1 ถึง 99 | `Limit per user must be a whole number from 1 to 99.` |
| `total_limit` | ไม่ใช่จำนวนเต็ม 1 ขึ้นไป หรือ `null` | `Total limit must be a whole number of 1 or more.` |
| `type` | ไม่ใช่ `PERCENT` หรือ `FIXED` | `Type must be PERCENT or FIXED.` |
| `starts_at`, `expires_at`, `from`, `to` (แบบวันและเวลา) | รูปแบบไม่ถูกต้องหรือมีวินาที | `Enter a date and time in the format YYYY-MM-DDTHH:mm+07:00.` |
| `expires_at` | ก่อน `starts_at` | `Expiry must not be before the start.` |
| `to` (แบบวันและเวลา) | ไม่หลัง `from` หรือเกินช่วงที่กำหนด | `The time range is not valid.` |
| `from`, `to` (แบบวันที่) | ไม่ใช่วันที่ที่ถูกต้อง | `Enter a valid date in the format YYYY-MM-DD.` |
| `from` | หลัง `to` | `Start date must not be after end date.` |
| `to` | ช่วงเกิน 366 วัน | `The date range must not exceed 366 days.` |
| `delta` | เป็น 0 ไม่ใช่จำนวนเต็ม หรือเกินช่วง | `Quantity change must be a non-zero whole number up to 100000.` |
| `delta` | ไม่สอดคล้องกับ `reason` | `Received stock must be a positive number.` / `Damaged stock must be a negative number.` |
| `reason` | ไม่อยู่ในรายการ | `Reason must be one of: RECEIVE, DAMAGE, CORRECTION.` |
| `role` | ไม่อยู่ในรายการ | `Role must be one of: customer, staff, manager, admin.` |
| `method` | ไม่ใช่ `CARD` หรือ `PROMPTPAY` | `Payment method must be CARD or PROMPTPAY.` |
| `active` | ไม่ใช่ค่า true/false | `Active must be true or false.` |
| (ฟิลด์อื่น) | ไม่ถูกต้องทั่วไป | `This field is invalid.` |

## 5. โครงสร้างข้อมูลหลัก

| ชื่อ | ฟิลด์ |
|---|---|
| **User (`/api/me`)** | `id`, `username`, `display_name`, `role`, `phone`, `birthdate`, `must_change_password`, `created_at` |
| **Address** | `id`, `label`, `recipient_name`, `phone`, `line1`, `line2`, `province`, `postal_code`, `is_default`, `created_at` |
| **Product (รายการ)** | `id`, `sku`, `name`, `category`, `price`, `stock_status`, `average_rating`, `review_count` |
| **Product (รายละเอียด)** | ฟิลด์ของรายการ และ `description`, `stock`, `in_wishlist` |
| **Review** | `id`, `rating`, `comment`, `display_name`, `created_at` |
| **Cart** | `items[]` (`id`, `product_id`, `sku`, `name`, `unit_price`, `quantity`, `line_total`, `stock_status`), `coupon`, `pricing` (`subtotal`, `volume_discount`, `coupon_discount`, `goods_total`, `vat`, `shipping`, `grand_total`) |
| **Order** | ดูตัวอย่างใน `PRD-ORDER` |
| **Order (รายการ)** | `id`, `status`, `grand_total`, `item_count`, `created_at` และสำหรับ `/api/manage/orders` เพิ่ม `customer` (`id`, `username`, `display_name`) |
| **Coupon (จัดการ)** | `id`, `code`, `type`, `percent_off`, `amount_off`, `max_discount`, `min_spend`, `starts_at`, `expires_at`, `per_user_limit`, `total_limit`, `active`, `status`, `usage_count`, `created_at` |
| **Product (จัดการ)** | `id`, `sku`, `name`, `description`, `category`, `price`, `stock`, `active`, `created_at` |
| **Inventory item** | `product_id`, `sku`, `name`, `stock`, `active` |
| **Movement** | `id`, `product_id`, `product_name`, `delta`, `stock_after`, `reason`, `actor`, `created_at` |
| **User (ผู้ดูแล)** | `id`, `username`, `display_name`, `role`, `status`, `temporarily_locked`, `created_at` |
| **Job** | `name`, `description`, `schedule`, `last_run`, `next_run_at` |
| **Job run** | `id`, `job`, `trigger`, `triggered_by`, `status`, `started_at`, `finished_at`, `summary`, `error_message` |

## 6. รายการ endpoint

คอลัมน์ "สำเร็จ" คือรหัสสถานะเมื่อสำเร็จ ส่วนข้อผิดพลาดทั่วไปของทุก endpoint (401, 403, 404 ตามข้อกำหนดการตรวจสอบ, 405, 500) ไม่ระบุซ้ำ

### 6.1 การยืนยันตัวตนและโปรไฟล์ (`PRD-AUTH`, `PRD-PROFILE`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| POST | `/api/auth/register` | ไม่ต้องยืนยันตัวตน | 201 | 400, 409 `USERNAME_TAKEN` |
| POST | `/api/auth/login` | ไม่ต้องยืนยันตัวตน | 200 | 400, 401 `INVALID_CREDENTIALS`, 403 `ACCOUNT_DISABLED`, 423 `ACCOUNT_LOCKED` |
| POST | `/api/auth/logout` | ทุกบทบาท | 204 | |
| POST | `/api/auth/change-password` | ทุกบทบาท | 204 | 400 `INVALID_CURRENT_PASSWORD` |
| GET | `/api/me` | ทุกบทบาท | 200 | |
| PUT | `/api/me` | ทุกบทบาท | 200 | 400 |
| GET | `/api/me/addresses` | customer | 200 | |
| POST | `/api/me/addresses` | customer | 201 | 400, 409 `ADDRESS_LIMIT` |
| PUT | `/api/me/addresses/{id}` | customer | 200 | 400, 404 |
| DELETE | `/api/me/addresses/{id}` | customer | 204 | 404 |
| POST | `/api/me/addresses/{id}/default` | customer | 200 | 404 |

### 6.2 สินค้า รีวิว และรายการโปรด (`PRD-CATALOG`, `PRD-REVIEW`, `PRD-WISHLIST`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| GET | `/api/products` | customer | 200 | 400 (พารามิเตอร์ `q`, `category`, `min_price`, `max_price`, `sort`, `page`, `page_size`) |
| GET | `/api/products/{id}` | customer | 200 | 404 |
| GET | `/api/products/{id}/reviews` | customer | 200 | 400, 404 |
| POST | `/api/products/{id}/reviews` | customer | 201 | 400, 403 `REVIEW_NOT_ALLOWED`, 404, 409 `REVIEW_EXISTS` |
| GET | `/api/wishlist` | customer | 200 | |
| PUT | `/api/wishlist/{product_id}` | customer | 201 | 404, 409 `ALREADY_IN_WISHLIST`, 409 `WISHLIST_LIMIT` |
| DELETE | `/api/wishlist/{product_id}` | customer | 204 | 404 |

### 6.3 ตะกร้าและคูปอง (`PRD-CART`, `PRD-COUPON`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| GET | `/api/cart` | customer | 200 | |
| POST | `/api/cart/items` | customer | 200 | 400, 404, 409 `QUANTITY_LIMIT`, `INSUFFICIENT_STOCK`, `CART_LINE_LIMIT` |
| PATCH | `/api/cart/items/{item_id}` | customer | 200 | 400, 404, 409 `INSUFFICIENT_STOCK` |
| DELETE | `/api/cart/items/{item_id}` | customer | 200 | 404 |
| PUT | `/api/cart/coupon` | customer | 200 | 400, 409 `COUPON_INVALID`, 409 `CART_EMPTY` |
| DELETE | `/api/cart/coupon` | customer | 200 | |

### 6.4 คำสั่งซื้อ (`PRD-ORDER`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| POST | `/api/orders` | customer | 201 | 400, 404 (ที่อยู่), 409 `CART_EMPTY`, `INSUFFICIENT_STOCK`, `COUPON_INVALID` |
| GET | `/api/orders` | customer | 200 | 400 |
| GET | `/api/orders/{id}` | customer (own), staff, admin | 200 | 404 |
| POST | `/api/orders/{id}/pay` | customer (own) | 200 | 400, 404, 409 `INVALID_TRANSITION` |
| POST | `/api/orders/{id}/cancel` | customer (own), staff, admin | 200 | 404, 409 `INVALID_TRANSITION` |
| POST | `/api/orders/{id}/return` | customer (own) | 200 | 404, 409 `INVALID_TRANSITION`, `RETURN_WINDOW_CLOSED` |
| GET | `/api/manage/orders` | staff, admin | 200 | 400 |
| PATCH | `/api/manage/orders/{id}/status` | staff, admin | 200 | 400, 404, 409 `INVALID_TRANSITION` |

### 6.5 สต็อก (`PRD-INVENTORY`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| GET | `/api/manage/inventory` | staff, admin | 200 | 400 |
| POST | `/api/manage/inventory/adjustments` | staff, admin | 201 | 400, 404, 409 `STOCK_NEGATIVE` |
| GET | `/api/manage/inventory/movements` | staff, admin | 200 | 400 |
| GET | `/api/manage/inventory/low-stock` | staff, admin | 200 | |

### 6.6 การจัดการสินค้าและคูปอง (`PRD-CATALOG`, `PRD-COUPON`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| GET | `/api/manage/products` | manager, admin | 200 | 400 |
| POST | `/api/manage/products` | manager, admin | 201 | 400, 409 `SKU_TAKEN` |
| PUT | `/api/manage/products/{id}` | manager, admin | 200 | 400, 404 |
| PATCH | `/api/manage/products/{id}/active` | manager, admin | 200 | 400, 404 |
| GET | `/api/manage/coupons` | manager, admin | 200 | 400 |
| POST | `/api/manage/coupons` | manager, admin | 201 | 400, 409 `COUPON_CODE_TAKEN` |
| PUT | `/api/manage/coupons/{id}` | manager, admin | 200 | 400, 404 |
| PATCH | `/api/manage/coupons/{id}/active` | manager, admin | 200 | 400, 404 |

### 6.7 รายงาน (`PRD-REPORT`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| GET | `/api/manage/reports/sales` | manager, admin | 200 | 400 |
| GET | `/api/manage/reports/sales.csv` | manager, admin | 200 (CSV) | 400 |
| GET | `/api/manage/reports/top-products` | manager, admin | 200 | 400 |
| GET | `/api/manage/reports/top-products.csv` | manager, admin | 200 (CSV) | 400 |
| GET | `/api/manage/reports/coupon-usage` | manager, admin | 200 | 400 |
| GET | `/api/manage/reports/hourly` | manager, admin | 200 | 400 |
| GET | `/api/manage/reports/hourly.csv` | manager, admin | 200 (CSV) | 400 |

### 6.8 การจัดการผู้ใช้และงานตั้งเวลา (`PRD-ADMIN`, `PRD-SCHEDULE`)

| Method | Path | บทบาท | สำเร็จ | ข้อผิดพลาดเฉพาะ |
|---|---|---|---|---|
| GET | `/api/admin/users` | admin | 200 | 400 |
| POST | `/api/admin/users/{id}/lock` | admin | 200 | 404, 409 `SELF_LOCK_FORBIDDEN`, `ACCOUNT_ALREADY_LOCKED`, `LAST_ADMIN` |
| POST | `/api/admin/users/{id}/unlock` | admin | 200 | 404, 409 `ACCOUNT_NOT_LOCKED` |
| POST | `/api/admin/users/{id}/reset-password` | admin | 200 | 404 |
| PATCH | `/api/admin/users/{id}/role` | admin | 200 | 400, 404, 409 `LAST_ADMIN` |
| GET | `/api/admin/jobs` | admin | 200 | |
| POST | `/api/admin/jobs/{name}/run` | admin | 200 | 400, 404, 409 `JOB_ALREADY_RUNNING` |
| GET | `/api/admin/jobs/{name}/runs` | admin | 200 | 400, 404 |

### 6.9 จุดเชื่อมต่อสำหรับการฝึก (อยู่นอกขอบเขตการทดสอบ)

| Method | Path | ผลลัพธ์ |
|---|---|---|
| GET | `/api/health` | `{ "status": "ok" }` |
| GET | `/api/version` | `{ "version": "1.0.0", "source_hash": "<hex>", "started_at": "<เวลา>" }` |
| POST | `/api/reset` | `{ "status": "reset", "reset_at": "<เวลา>" }` ล้างข้อมูลและโหลดข้อมูลเริ่มต้นใหม่ |

## 7. ตัวอย่างการเรียกใช้

```bash
# เข้าสู่ระบบ
curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"customer1","password":"Customer123"}'

# ใช้โทเคนที่ได้ (แทนที่ <token>)
curl -s http://localhost:8001/api/me -H "Authorization: Bearer <token>"
```

ตัวอย่างเพิ่มเติม รวมถึงการใช้ Postman อยู่ใน `docs/instructions/tools-and-tips.md`
