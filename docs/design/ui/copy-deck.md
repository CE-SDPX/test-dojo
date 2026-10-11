# ชุดข้อความบนหน้าจอ (Copy Deck)

เอกสารนี้กำหนดข้อความทุกจุดบนหน้าจอของ DojoMart ซึ่งเป็นภาษาอังกฤษ ข้อความ การสะกด ตัวพิมพ์ใหญ่-เล็ก และเครื่องหมายวรรคตอน ต้องตรงกับเอกสารนี้ทุกตัวอักษร ข้อความที่เป็นผลตอบกลับของ API (ตาม `docs/design/api.md` หัวข้อ 3 และ 4) ต้องแสดงตามที่ API ส่งมาโดยไม่ดัดแปลง

## 1. ข้อตกลงทั่วไป

| เรื่อง | ข้อตกลง |
|---|---|
| ชื่อระบบ | `DojoMart` |
| ชื่อแท็บของเบราว์เซอร์ (`<title>`) | `DojoMart – {ชื่อหน้า}` ใช้เครื่องหมายขีดกลางยาว `–` คั่น ชื่อหน้าตามตารางด้านล่าง |
| ปุ่มและหัวข้อ | ขึ้นต้นด้วยตัวพิมพ์ใหญ่ตัวแรกเท่านั้น (sentence case) เว้นแต่เป็นชื่อเฉพาะ |
| จำนวนเงิน | `฿1,234.50` ส่วนลดที่มากกว่า 0 แสดงนำหน้าด้วยเครื่องหมายลบ เช่น `-฿170.80` ส่วนลดที่เป็น 0 แสดง `฿0.00` ค่าจัดส่ง 0 แสดง `Free` |
| วันที่และเวลา | `dd/MM/yyyy HH:mm` (เวลาไทย) และ `dd/MM/yyyy` สำหรับวันที่ล้วน |
| ส่วนท้ายของทุกหน้า | `DojoMart v{version} ({source_hash 8 ตัวแรก})` |
| ข้อความระหว่างโหลด | `Loading…` |
| ข้อผิดพลาดการเชื่อมต่อหรือข้อผิดพลาดภายใน | `Something went wrong. Please try again.` |
| เซสชันหมดอายุ | `Your session has expired. Please sign in again.` |
| ฟิลด์ที่จำเป็น | ทำเครื่องหมาย `*` ต่อท้ายชื่อฟิลด์ และมีข้อความอธิบาย `* Required` ที่ท้ายฟอร์ม |
| ศัพท์ | ใช้ตามตารางศัพท์ใน `docs/requirements/glossary.md` หัวข้อ 7 |

## 2. ชื่อหน้า (ใช้ใน `<title>`)

| หน้า | ชื่อหน้า |
|---|---|
| `/login` | `Sign in` |
| `/register` | `Create an account` |
| `/profile` | `Profile` |
| `/change-password` | `Change password` |
| `/products` | `Products` |
| `/products/{id}` | ชื่อสินค้า |
| `/wishlist` | `Wishlist` |
| `/cart` | `Cart` |
| `/checkout` | `Checkout` |
| `/orders/{id}/confirmation` | `Order confirmation` |
| `/orders` | `My orders` |
| `/orders/{id}` | `Order #{id}` |
| `/staff/orders` | `Orders` |
| `/staff/inventory` | `Inventory` |
| `/staff/low-stock` | `Low stock` |
| `/manager/products` | `Manage products` |
| `/manager/coupons` | `Coupons` |
| `/manager/reports` | `Reports` |
| `/admin/users` | `Users` |
| `/admin/jobs` | `Jobs` |
| 403 | `Access denied` |
| 404 | `Page not found` |

## 3. เมนูและส่วนหัว

| องค์ประกอบ | ข้อความ |
|---|---|
| เมนูของผู้เยี่ยมชม (ยังไม่เข้าสู่ระบบ) | `Products` ส่วนช่องผู้ใช้แสดง `Sign in` และ `Create an account` แทนชื่อผู้ใช้และ `Sign out` |
| เมนูของ `customer` | `Products`, `Wishlist`, `Cart`, `My orders`, `Profile`, `Sign out` |
| เมนูของ `staff` | `Orders`, `Inventory`, `Low stock`, `Profile`, `Sign out` |
| เมนูของ `manager` | `Reports`, `Products`, `Coupons`, `Profile`, `Sign out` |
| เมนูของ `admin` | `Users`, `Jobs`, `Orders`, `Inventory`, `Low stock`, `Products`, `Coupons`, `Reports`, `Profile`, `Sign out` |
| รายการ Cart | แสดง `Cart ({n})` เมื่อ n คือจำนวนสินค้าต่างชนิดในตะกร้าและ n มากกว่า 0 มิฉะนั้นแสดง `Cart` |
| ปุ่มเปิดเมนูบนจอแคบ (กว้างน้อยกว่า 768 px) | `Menu` |
| ชื่อผู้ใช้ที่ส่วนหัว | `Signed in as {display_name}` |
| ช่องค้นหา (ลูกค้า) | placeholder `Search products` ป้ายกำกับที่อ่านด้วยโปรแกรมอ่านหน้าจอ `Search products` ปุ่ม `Search` |
| ข้อความเกิน 100 อักขระในช่องค้นหา | `Search text must be at most 100 characters.` |

## 4. หน้า Sign in และ Create an account

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ Sign in | `Sign in` |
| ป้ายกำกับ | `Username`, `Password` |
| ปุ่ม | `Sign in` |
| ลิงก์ | `Create an account` |
| ข้อความหลังสมัครสำเร็จ | `Account created. Please sign in.` |
| หัวข้อ Register | `Create an account` |
| ป้ายกำกับ | `Username`, `Password`, `Confirm password`, `Display name`, `Date of birth` |
| คำอธิบายใต้ช่อง Username | `4 to 20 letters, digits or underscores.` |
| คำอธิบายใต้ช่อง Password | `8 to 20 characters with at least one letter and one digit.` |
| ปุ่ม | `Create account` |
| ลิงก์ | `Already have an account? Sign in` |
| รหัสผ่านไม่ตรงกัน | `Passwords do not match.` |

## 5. หน้า Profile และ Change password

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ | `Profile` |
| ป้ายกำกับ | `Username`, `Display name`, `Phone`, `Date of birth` |
| ปุ่ม | `Save changes` |
| ข้อความสำเร็จ | `Profile updated.` |
| ลิงก์ | `Change password` |
| หัวข้อส่วนที่อยู่ | `Addresses` |
| ปุ่ม | `Add address`, `Edit`, `Delete`, `Set as default` |
| ป้ายที่อยู่หลัก | `Default` |
| ไม่มีที่อยู่ | `You have no saved addresses.` |
| ข้อความเตือนจำนวนที่อยู่ | `You can save up to 5 addresses.` |
| ป้ายกำกับในฟอร์มที่อยู่ | `Label`, `Recipient name`, `Phone`, `Address line 1`, `Address line 2 (optional)`, `Province`, `Postal code` |
| ปุ่มในฟอร์มที่อยู่ | `Save address`, `Cancel` |
| ข้อความสำเร็จ | `Address saved.`, `Address deleted.`, `Default address updated.` |
| หน้าต่างยืนยันการลบ | หัวข้อ `Delete address` ข้อความ `Delete this address?` ปุ่ม `Delete` และ `Cancel` |
| หัวข้อ Change password | `Change password` |
| ป้ายกำกับ | `Current password`, `New password`, `Confirm new password` |
| ปุ่ม | `Change password` |
| ข้อความสำเร็จ | `Password changed successfully.` |
| ข้อความเมื่อถูกบังคับเปลี่ยน | `You must change your password before continuing.` |
| รหัสผ่านไม่ตรงกัน | `Passwords do not match.` |

## 6. หน้า Products และรายละเอียดสินค้า

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ | `Products` |
| ตัวกรอง | `Category` (ตัวเลือกแรก `All categories`), `Min price`, `Max price`, `Sort by` |
| ตัวเลือกการเรียง | `Name (A–Z)`, `Name (Z–A)`, `Price (low to high)`, `Price (high to low)` |
| ปุ่ม/ลิงก์ | `Apply filters`, `Clear filters` |
| จำนวนผลลัพธ์ | `{n} products` และ `1 product` เมื่อมีหนึ่งรายการ |
| การแบ่งหน้า | `Previous`, `Next`, `Page {n} of {total}` |
| คะแนน | `{avg} ({count} reviews)`, `{avg} (1 review)`, `No reviews yet` |
| สถานะสต็อก | `In stock`, `Only {n} left`, `Out of stock` |
| ปุ่มบนการ์ด | `Add to cart` |
| ข้อความสำเร็จ | `Added to cart.` |
| ไม่พบสินค้า (ไม่มีคำค้น) | `No products found.` |
| ไม่พบสินค้า (มีคำค้น) | `No products found for "{q}".` |
| ลิงก์กลับ | `Back to products` |
| ป้ายกำกับในหน้ารายละเอียด | `Quantity`, `Description`, `Reviews` |
| ปุ่มรายการโปรด | `Add to wishlist`, `Remove from wishlist` |
| ข้อความรายการโปรด | `Added to wishlist.`, `Removed from wishlist.` |
| ฟอร์มรีวิว | หัวข้อ `Write a review` ป้ายกำกับ `Rating`, `Comment (optional)` ตัวนับ `{n}/500` ปุ่ม `Submit review` |
| ข้อความสำเร็จของรีวิว | `Thank you for your review.` |
| รายการรีวิว | `{display_name}`, `Rating: {n}/5`, วันที่ `dd/MM/yyyy` |
| ไม่มีรีวิว | `No reviews yet.` |

## 7. หน้า Wishlist และ Cart

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ Wishlist | `Wishlist` |
| รายการโปรดว่าง | `Your wishlist is empty.` |
| ปุ่ม | `Remove`, `Add to cart` |
| หัวข้อ Cart | `Cart` |
| หัวตาราง | `Product`, `Unit price`, `Quantity`, `Total` |
| ปุ่ม | `Remove` |
| ช่องคูปอง | ป้ายกำกับ `Coupon code` ปุ่ม `Apply`, `Remove coupon` |
| ข้อความคูปองที่ใช้ได้ | `Coupon {code} applied.` |
| ข้อความคูปองที่ใช้ไม่ได้แล้ว | `Coupon {code} is not applicable. {message}` โดย `{message}` คือข้อความที่ API ส่ง |
| ป้ายกำกับในกล่องสรุป | `Subtotal`, `Volume discount`, `Coupon discount`, `VAT (7%)`, `Shipping`, `Total` |
| ปุ่ม/ลิงก์ | `Checkout`, `Continue shopping` |
| ตะกร้าว่าง | `Your cart is empty.` |

## 8. หน้า Checkout, Order confirmation, My orders และ Order detail

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ Checkout | `Checkout` |
| หัวข้อส่วน | `Delivery address`, `Order summary` |
| ปุ่ม | `Place order` (ระหว่างส่งคำขอ `Placing order…`) |
| ไม่มีที่อยู่ | `Add a delivery address before placing an order.` พร้อมลิงก์ `Go to profile` |
| หัวข้อ Order confirmation | `Thank you for your order` |
| ข้อความ | `Your order #{id} has been placed.` |
| ยอดที่ต้องชำระ | `Total to pay: {amount}` |
| คำเตือน | `Your order will be cancelled automatically if it is not paid within 60 minutes.` |
| วิธีชำระเงิน | ป้ายกำกับ `Payment method` ตัวเลือก `Credit/debit card` และ `PromptPay` |
| ปุ่ม | `Pay now` |
| ข้อความสำเร็จ | `Payment received.` |
| หัวข้อ My orders | `My orders` |
| หัวตาราง | `Order`, `Date`, `Status`, `Items`, `Total` |
| ตัวกรอง | `Status` (ตัวเลือกแรก `All statuses`) |
| ลิงก์ | `View` |
| ไม่มีคำสั่งซื้อ | `You have not placed any orders yet.` |
| หัวข้อ Order detail | `Order #{id}` |
| หัวข้อส่วน | `Items`, `Delivery address`, `Payment summary`, `Timeline` |
| ป้ายเวลา | `Placed`, `Paid`, `Packed`, `Shipped`, `Delivered`, `Cancelled`, `Returned` |
| ป้ายอื่น | `Refund amount`, `Return by {dd/MM/yyyy HH:mm}` |
| ปุ่ม | `Pay now`, `Cancel order`, `Return order` |
| หน้าต่างยืนยันการยกเลิก | หัวข้อ `Cancel order` ข้อความ `Cancel this order?` ปุ่ม `Yes, cancel` และ `Keep order` |
| หน้าต่างยืนยันการคืนสินค้า | หัวข้อ `Return order` ข้อความ `Return this order? The full amount will be refunded.` ปุ่ม `Yes, return` และ `Keep order` |
| ข้อความสำเร็จ | `Order cancelled.`, `Order returned.` |

**ป้ายสถานะคำสั่งซื้อ**

| ค่าสถานะ | ป้าย |
|---|---|
| `PENDING_PAYMENT` | `Pending payment` |
| `PAID` | `Paid` |
| `PACKED` | `Packed` |
| `SHIPPED` | `Shipped` |
| `DELIVERED` | `Delivered` |
| `CANCELLED` | `Cancelled` |
| `RETURNED` | `Returned` |

## 9. หน้าของ staff

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ Orders | `Orders` |
| ช่องค้นหา | placeholder `Search by order number or username` |
| ตัวกรอง | `Status` (ตัวเลือกแรก `All statuses`) |
| หัวตาราง | `Order`, `Customer`, `Date`, `Status`, `Total`, `Actions` |
| ปุ่ม | `Mark as packed`, `Mark as shipped`, `Mark as delivered`, `Cancel order` |
| ข้อความสำเร็จ | `Order updated.` |
| ไม่พบ | `No orders found.` |
| หัวข้อ Inventory | `Inventory` |
| ช่องค้นหา | placeholder `Search by product name` |
| หัวตาราง | `SKU`, `Product`, `Stock`, `Status`, `Actions` |
| ค่าสถานะสินค้า | `Active`, `Inactive` |
| ปุ่ม | `Adjust stock`, `History` |
| หน้าต่างปรับสต็อก | หัวข้อ `Adjust stock` ป้ายกำกับ `Quantity change`, `Reason` ตัวเลือก `Received`, `Damaged`, `Correction` คำอธิบาย `Use a positive number to add stock and a negative number to remove it.` ปุ่ม `Save` และ `Cancel` |
| ข้อความสำเร็จ | `Stock updated.` |
| ประวัติสต็อก | หัวข้อ `Stock history` หัวตาราง `Date`, `Change`, `Stock after`, `Reason`, `By` |
| เหตุผลในประวัติ | `RECEIVE` = `Received`, `DAMAGE` = `Damaged`, `CORRECTION` = `Correction`, `ORDER` = `Order`, `CANCEL` = `Cancelled order`, `RETURN` = `Returned order` |
| หัวข้อ Low stock | `Low stock` |
| ข้อความเวลา | `Snapshot taken at {dd/MM/yyyy HH:mm}` |
| ยังไม่มี snapshot | `No snapshot has been taken yet.` |
| ไม่มีสินค้าใกล้หมด | `No products are low on stock.` |
| หัวตาราง | `SKU`, `Product`, `Stock` |

## 10. หน้าของ manager

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ | `Manage products` |
| ช่องค้นหา | placeholder `Search by name or SKU` |
| หัวตาราง | `SKU`, `Name`, `Category`, `Price`, `Stock`, `Status`, `Actions` |
| ปุ่ม | `Add product`, `Edit`, `Deactivate`, `Activate`, `Save product`, `Cancel` |
| ป้ายกำกับในฟอร์ม | `SKU`, `Name`, `Description`, `Category`, `Price`, `Initial stock` (เฉพาะตอนสร้าง) |
| ข้อความสำเร็จ | `Product saved.` |
| หน้าต่างยืนยันการปิดการใช้งาน | หัวข้อ `Deactivate product` ข้อความ `Deactivate this product? It will be removed from all carts and wishlists.` ปุ่ม `Deactivate` และ `Cancel` |
| หัวข้อ Coupons | `Coupons` |
| ช่องค้นหา | placeholder `Search by code` |
| หัวตาราง | `Code`, `Type`, `Discount`, `Min. spend`, `Starts`, `Expires`, `Used`, `Status`, `Actions` |
| ค่าในคอลัมน์ Discount | `{n}%` หรือ `{n}% (max {amount})` สำหรับแบบเปอร์เซ็นต์ และ `{amount}` สำหรับแบบคงที่ |
| ป้ายสถานะ | `Active`, `Scheduled`, `Expired`, `Disabled` |
| ปุ่ม | `Add coupon`, `Edit`, `Disable`, `Enable`, `Save coupon`, `Cancel` |
| ป้ายกำกับในฟอร์ม | `Code`, `Type`, `Percent off`, `Amount off`, `Maximum discount (optional)`, `Minimum spend`, `Starts at`, `Expires at`, `Limit per user`, `Total limit (optional)` |
| ตัวเลือก Type | `Percentage`, `Fixed amount` |
| หมายเหตุเขตเวลา | `Times are in Asia/Bangkok (UTC+07:00).` |
| ข้อความสำเร็จ | `Coupon saved.` |
| หัวข้อ Reports | `Reports` |
| แท็บ | `Sales`, `Top products`, `Coupons`, `Window reports` |
| ป้ายกำกับ | `From`, `To` (แท็บ Window reports ใช้ `From (date and time)`, `To (date and time)`) |
| ปุ่ม | `Show report`, `Export CSV` |
| ป้ายสรุปยอดขาย | `Orders`, `Gross sales`, `VAT`, `Shipping`, `Discounts`, `Average order value` |
| หัวตารางยอดขายรายวัน | `Date`, `Orders`, `Gross sales`, `VAT`, `Shipping`, `Discounts` |
| หัวตารางสินค้าขายดี | `Rank`, `Product`, `Quantity`, `Revenue` |
| หัวตารางคูปอง | `Code`, `Orders`, `Discount total` |
| หัวตารางรายงานรายช่วงเวลา | `Window`, `Orders`, `Gross sales`, `VAT`, `Shipping`, `Discounts`, `Generated` |
| ไม่มีข้อมูล | `No data for the selected period.` |

## 11. หน้าของ admin

| องค์ประกอบ | ข้อความ |
|---|---|
| หัวข้อ Users | `Users` |
| ช่องค้นหา | placeholder `Search by username or name` |
| ตัวกรอง | `Role` (ตัวเลือกแรก `All roles`) |
| ค่า Role ที่แสดง | `customer`, `staff`, `manager`, `admin` |
| หัวตาราง | `Username`, `Name`, `Role`, `Status`, `Created`, `Actions` |
| ป้ายสถานะ | `Active`, `Locked`, `Temporarily locked` |
| ปุ่ม | `Lock`, `Unlock`, `Reset password`, `Change role` |
| ยืนยันการล็อก | หัวข้อ `Lock account` ข้อความ `Lock this account? The user will be signed out immediately.` ปุ่ม `Lock` และ `Cancel` |
| ยืนยันการปลดล็อก | หัวข้อ `Unlock account` ข้อความ `Unlock this account?` ปุ่ม `Unlock` และ `Cancel` |
| ยืนยันการรีเซ็ตรหัสผ่าน | หัวข้อ `Reset password` ข้อความ `Reset the password for {username}? A temporary password will be generated.` ปุ่ม `Reset password` และ `Cancel` |
| ผลการรีเซ็ต | หัวข้อ `Temporary password` ข้อความ `Share this password with the user. It will not be shown again.` ปุ่ม `Close` |
| หน้าต่างเปลี่ยนบทบาท | หัวข้อ `Change role` ป้ายกำกับ `Role` ปุ่ม `Save` และ `Cancel` |
| ข้อความสำเร็จ | `Account locked.`, `Account unlocked.`, `Role updated.` |
| หัวข้อ Jobs | `Jobs` |
| หัวตาราง | `Job`, `Description`, `Schedule`, `Last run`, `Next run`, `Actions` |
| คำอธิบายงาน `cancel-unpaid-orders` | `Cancels orders that have been unpaid for 60 minutes or more.` |
| คำอธิบายงาน `hourly-sales-report` | `Creates the sales report for the previous full hour.` |
| คำอธิบายงาน `low-stock-snapshot` | `Records products with 5 or fewer items in stock.` |
| ตารางเวลา | `Every hour at minute 0 (Asia/Bangkok)` |
| ยังไม่เคยรัน | `Never` |
| ปุ่ม | `Run now`, `View history` |
| ยืนยันการรัน | ข้อความ `Run this job now?` ปุ่ม `Run now` และ `Cancel` |
| หน้าต่างรันรายงาน | หัวข้อ `Run report` ป้ายกำกับ `From (optional)`, `To (optional)` คำอธิบาย `Leave empty to use the previous full hour.` ปุ่ม `Run report` และ `Cancel` |
| ผลการรัน | `Job finished: {summary}` |
| ป้ายสถานะการรัน | `Success`, `Failed`, `Running` |
| ประวัติการรัน | หัวข้อ `Run history` หัวตาราง `Started`, `Finished`, `Trigger`, `By`, `Status`, `Result` |
| ค่า Trigger | `Scheduled`, `Manual` |

## 12. หน้า 403 และ 404

| หน้า | หัวข้อ | ข้อความ | ลิงก์ |
|---|---|---|---|
| 403 | `Access denied` | `You do not have permission to view this page.` | `Go to my home page` |
| 404 | `Page not found` | `The page you are looking for does not exist.` | `Go to my home page` |

## 13. ข้อความจากข้อมูลตรวจสอบ

ข้อความที่แสดงข้างฟิลด์ที่ไม่ผ่านการตรวจสอบใช้ถ้อยคำเดียวกับ `docs/design/api.md` หัวข้อ 4 ทั้งกรณีที่หน้าจอตรวจเองก่อนส่ง และกรณีที่ API ตอบกลับ
