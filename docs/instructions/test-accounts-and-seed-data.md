# บัญชีทดสอบและข้อมูลเริ่มต้น

เอกสารนี้ระบุบัญชีทดสอบ รหัสผ่าน และข้อมูลเริ่มต้นที่ระบบสร้างเมื่อเริ่มครั้งแรกและเมื่อล้างข้อมูล (reset) ตามขั้นตอนใน `getting-started.md` หัวข้อ 5

ให้ **T0** แทนเวลาของการเริ่มระบบครั้งแรกหรือการ reset ล่าสุด (เห็นได้จาก `reset_at` ที่ `POST /api/reset` ตอบกลับ) ข้อมูลบางรายการระบุเวลาเทียบกับ T0

## 1. บัญชีทดสอบ

รหัสผ่านของบัญชีที่ระบบจัดเตรียมไว้เป็นรหัสเดียวกันทั้งบทบาท

| บทบาท | Username | รหัสผ่าน | ชื่อแสดงผล |
|---|---|---|---|
| customer | `customer1` | `Customer123` | Somchai Jaidee |
| customer | `customer2` | `Customer123` | Malee Rakdee |
| customer | `customer3` | `Customer123` | Preecha Boonmee |
| staff | `staff1` | `Staff123` | Staff One |
| staff | `staff2` | `Staff123` | Staff Two |
| staff | `staff3` | `Staff123` | Staff Three |
| manager | `manager1` | `Manager123` | Manager One |
| manager | `manager2` | `Manager123` | Manager Two |
| manager | `manager3` | `Manager123` | Manager Three |
| admin | `admin1` | `Admin123` | Admin One |
| admin | `admin2` | `Admin123` | Admin Two |
| admin | `admin3` | `Admin123` | Admin Three |

บัญชีทุกบัญชีมีสถานะ `ACTIVE` ไม่ถูกล็อก และมีตัวนับการเข้าสู่ระบบผิดเป็น 0 บัญชีที่สมัครเองผ่านหน้า Create an account เป็นบทบาท `customer` เสมอ และหายไปเมื่อ reset

## 2. ข้อมูลเริ่มต้นของลูกค้า

### customer1 (บัญชีใหม่)

| รายการ | ข้อมูล |
|---|---|
| เบอร์โทร / วันเกิด | `0812345678` / `1995-03-14` |
| ที่อยู่ | 1 รายการ: Home (ที่อยู่หลัก) ผู้รับ Somchai Jaidee `0812345678` 55/1 Phahonyothin Rd, Bangkok, 10400 |
| ตะกร้า / รายการโปรด / รีวิว / คำสั่งซื้อ | ไม่มี |

### customer2 (มีประวัติคำสั่งซื้อ)

| รายการ | ข้อมูล |
|---|---|
| เบอร์โทร / วันเกิด | `0898765432` / `1990-07-21` |
| ที่อยู่ | 2 รายการ: Home (ที่อยู่หลัก) 99/9 Sukhumvit Rd, Bangkok, 10110 และ Office 12 Silom Rd, Bangkok, 10500 (ผู้รับ Malee Rakdee `0898765432`) |
| ตะกร้า / รายการโปรด | ไม่มี |
| รีวิว | Ceramic Coffee Mug คะแนน 4 ("Sturdy and keeps coffee warm.") |
| คำสั่งซื้อ | 8 รายการ ตามตารางด้านล่าง ใช้ที่อยู่ Home |

| รหัส | สถานะ | เวลาที่เกี่ยวข้อง | รายการสินค้า | คูปอง | ยอดชำระสุทธิ |
|---|---|---|---|---|---|
| 1 | `DELIVERED` | ส่งมอบเมื่อ T0 − 8 วัน (เลยกำหนดคืนสินค้า) | Rain Jacket ×1, Gel Pen Set ×2 | `SAVE10` | ฿1,480.32 |
| 2 | `DELIVERED` | ส่งมอบเมื่อ T0 − 6 วัน (ยังคืนสินค้าได้) | Ceramic Coffee Mug ×2, Canvas Tote Bag ×1 | ไม่มี | ฿496.19 |
| 3 | `SHIPPED` | จัดส่งเมื่อ T0 − 1 วัน | USB-C Cable 1 m ×1 | ไม่มี | ฿157.00 |
| 4 | `PACKED` | แพ็กเมื่อ T0 − 3 ชั่วโมง | Wireless Mouse ×1 | ไม่มี | ฿640.93 |
| 5 | `PAID` | สร้าง T0 − 95 นาที ชำระ T0 − 90 นาที | Scented Candle ×2 | ไม่มี | ฿368.86 |
| 6 | `PENDING_PAYMENT` | สร้างเมื่อ T0 − 61 นาที | Throw Pillow ×1 | ไม่มี | ฿476.93 |
| 7 | `PENDING_PAYMENT` | สร้างเมื่อ T0 − 59 นาที | Sticky Notes Pack ×4 | ไม่มี | ฿157.00 |
| 8 | `CANCELLED` | ยกเลิกเมื่อ T0 − 2 วัน (ยกเลิกตอนรอชำระ) | Gel Pen Set ×2 | ไม่มี | ฿176.26 |

หมายเหตุ
- เวลาของสถานะก่อนหน้าในแต่ละคำสั่งซื้อ (เช่น เวลาชำระของคำสั่งซื้อที่ 1 ถึง 4) เกิดก่อนเวลาที่ระบุเสมอ
- คำสั่งซื้อที่ 1 ใช้คูปอง `SAVE10` และไม่ถูกยกเลิก ดังนั้น `customer2` ใช้ `SAVE10` ได้อีกไม่ได้
- ประวัติการเคลื่อนไหวของสต็อก (inventory movements) เริ่มต้นว่าง จำนวนสต็อกในตารางสินค้าเป็นจำนวนปัจจุบัน

### customer3 (ตะกร้ามีของ และที่อยู่ครบ 5 รายการ)

| รายการ | ข้อมูล |
|---|---|
| เบอร์โทร / วันเกิด | ไม่มี / `2000-01-01` |
| ที่อยู่ | 5 รายการ: Home (ที่อยู่หลัก) Chiang Mai 50000, Office Phuket 83000, Parents Khon Kaen 40000, Condo Chonburi 20000, Shop Songkhla 90000 (ผู้รับ Preecha Boonmee `0855555555`) |
| ตะกร้า | Limited Edition Notebook ×1, Ceramic Coffee Mug ×2, Wool Beanie ×1 (ไม่ใช้คูปอง) |
| รายการโปรด | Scented Candle, Throw Pillow |
| รีวิว | Ceramic Coffee Mug คะแนน 5 ("Perfect size for my morning coffee.") |
| คำสั่งซื้อ | ไม่มี |

รีวิวของ `customer3` เป็นข้อมูลเริ่มต้นที่ระบบสร้างให้โดยตรง (ไม่ผ่านเงื่อนไขการรีวิวตามปกติ) ดังนั้น Ceramic Coffee Mug มีรีวิวเริ่มต้น 2 รายการ คะแนนเฉลี่ย 4.5

## 3. สินค้า

สินค้า 25 รายการ (ใช้งานอยู่ 23 รายการ) ราคาเป็นราคาต่อหน่วยไม่รวม VAT ทุกรายการมีคำอธิบายสั้น ๆ

| SKU | ชื่อสินค้า | หมวดหมู่ | ราคา | สต็อก | สถานะ |
|---|---|---|---|---|---|
| DM-1001 | Ceramic Coffee Mug | Drinkware | 129.00 | 40 | active |
| DM-1002 | Thai Tea Glass (แก้วชาไทย) | Drinkware | 89.00 | 60 | active |
| DM-1003 | Stainless Tumbler 500 ml | Drinkware | 349.00 | 25 | active |
| DM-1004 | Glass Water Bottle | Drinkware | 199.00 | 5 | active |
| DM-1005 | Travel Mug | Drinkware | 250.00 | 12 | active |
| DM-2001 | 100% Cotton T-Shirt | Apparel | 299.00 | 80 | active |
| DM-2002 | Canvas Tote Bag | Apparel | 159.00 | 33 | active |
| DM-2003 | Wool Beanie | Apparel | 189.00 | 6 | active |
| DM-2004 | Running Socks (3 pairs) | Apparel | 71.50 | 100 | active |
| DM-2005 | Rain Jacket | Apparel | 1590.00 | 8 | active |
| DM-3001 | Notebook, A5 (Lined) | Stationery | 10.50 | 200 | active |
| DM-3002 | Gel Pen Set | Stationery | 59.00 | 150 | active |
| DM-3003 | Limited Edition Notebook | Stationery | 450.00 | 1 | active |
| DM-3004 | Desk Organizer | Stationery | 333.33 | 15 | active |
| DM-3005 | Sticky Notes Pack | Stationery | 25.00 | 300 | active |
| DM-4001 | USB-C Cable 1 m | Electronics | 100.00 | 70 | active |
| DM-4002 | Wireless Mouse | Electronics | 599.00 | 20 | active |
| DM-4003 | Bluetooth Speaker | Electronics | 999.99 | 10 | active |
| DM-4004 | Mechanical Keyboard | Electronics | 1000.00 | 9 | active |
| DM-4005 | Phone Stand | Electronics | 200.00 | 45 | active |
| DM-5001 | Scented Candle | Home | 149.00 | 50 | active |
| DM-5002 | Throw Pillow | Home | 399.00 | 18 | active |
| DM-5003 | Vintage Poster | Home | 350.00 | 0 | active |
| DM-9001 | Discontinued Desk Lamp | Home | 690.00 | 4 | inactive |
| DM-9002 | Retired Wall Clock | Home | 520.00 | 0 | inactive |

สต็อกในตารางเป็นจำนวนปัจจุบัน ซึ่งรวมผลของคำสั่งซื้อเริ่มต้นของ `customer2` ไว้แล้ว (ไม่ต้องนำจำนวนในคำสั่งซื้อมาหักซ้ำ)

## 4. คูปอง

ให้ **T0m** แทน T0 ที่ตัดวินาทีทิ้ง (ละเอียดระดับนาที)

| รหัส | ประเภท | ส่วนลด | ขั้นต่ำ | จำกัดต่อผู้ใช้ | จำกัดรวม | ใช้ได้ตั้งแต่ | ใช้ได้ถึง | active |
|---|---|---|---|---|---|---|---|---|
| `SAVE10` | PERCENT | 10% (สูงสุด 200.00) | 0.00 | 1 | ไม่จำกัด | 2020-01-01T00:00+07:00 | 2099-12-31T23:59+07:00 | ใช่ |
| `FLAT100` | FIXED | 100.00 | 500.00 | 5 | ไม่จำกัด | 2020-01-01T00:00+07:00 | 2099-12-31T23:59+07:00 | ใช่ |
| `BIGFLAT` | FIXED | 5000.00 | 0.00 | 5 | ไม่จำกัด | 2020-01-01T00:00+07:00 | 2099-12-31T23:59+07:00 | ใช่ |
| `LASTONE` | PERCENT | 15% (ไม่จำกัดเพดาน) | 0.00 | 1 | 1 | 2020-01-01T00:00+07:00 | 2099-12-31T23:59+07:00 | ใช่ |
| `SOON3` | PERCENT | 5% (ไม่จำกัดเพดาน) | 0.00 | 5 | ไม่จำกัด | T0m | T0m + 3 นาที | ใช่ |
| `LATER10` | FIXED | 50.00 | 0.00 | 5 | ไม่จำกัด | T0m + 10 นาที | 2099-12-31T23:59+07:00 | ใช่ |
| `OLD2025` | PERCENT | 20% (ไม่จำกัดเพดาน) | 0.00 | 1 | ไม่จำกัด | 2025-01-01T00:00+07:00 | 2025-12-31T23:59+07:00 | ใช่ |
| `OFF5` | PERCENT | 5% (ไม่จำกัดเพดาน) | 0.00 | 1 | ไม่จำกัด | 2020-01-01T00:00+07:00 | 2099-12-31T23:59+07:00 | **ไม่** |

- `SOON3` ใช้ได้ตั้งแต่ต้นนาทีของ T0m ถึงสิ้นนาที T0m + 3 นาที (รวมนาทีสุดท้าย) หลังจากนั้นหมดอายุ
- `LATER10` เริ่มใช้ได้ตั้งแต่ต้นนาที T0m + 10 นาที
- ผู้จัดการสร้างคูปองใหม่ที่หมดอายุในอีกไม่กี่นาทีได้ เพื่อทดสอบเรื่องเวลา

## 5. งานตั้งเวลาและรายงาน

| รายการ | สถานะเริ่มต้น |
|---|---|
| ประวัติการรันงาน | ว่าง |
| รายงานรายช่วงเวลา | ว่าง |
| snapshot สินค้าใกล้หมด | บันทึกที่ T0 ประกอบด้วย Vintage Poster (0), Limited Edition Notebook (1), Glass Water Bottle (5) ตามลำดับนี้ |
| งานตั้งเวลา | ทำงานทุกต้นชั่วโมงเวลาไทย (ดู `PRD-SCHEDULE`) |

คำสั่งซื้อเริ่มต้นหมายเลข 5, 6 และ 7 ออกแบบไว้สำหรับทดสอบงาน `cancel-unpaid-orders` และคำสั่งซื้อหมายเลข 1 ถึง 5 มีเวลาชำระเงินในอดีต ซึ่งใช้ทดสอบรายงานได้โดยเลือกช่วงวันที่ให้ครอบคลุม

## 6. ข้อควรระวังเมื่อใช้ข้อมูลเริ่มต้น

1. ข้อมูลเริ่มต้นเปลี่ยนไปทันทีที่มีการทดสอบ เช่น สั่งซื้อแล้วสต็อกลดลง ควร reset ก่อนเริ่มเรื่องใหม่
2. ข้อมูลที่อ้างอิง T0 เปลี่ยนตามเวลา reset ครั้งล่าสุด
3. ตัวเลขในตัวอย่างของ `PRD-CROSS` อ้างอิงราคาและคูปองในเอกสารนี้
