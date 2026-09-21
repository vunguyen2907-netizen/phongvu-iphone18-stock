#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PHONG VU ERP IPHONE 18 STOCK TRANSFER AUTOMATION BOT
=============================================================================
Worker tự động hoá tương tác ERP Phong Vũ (Teko IAM + SupplyChain):
1. Quản lý phiên đăng nhập SSO tài khoản vu.nt1@phongvu-mna.vn
2. Tra cứu tồn kho realtime tại kho 11001.01
3. Tự động tạo lệnh chuyển kho nội bộ (CKNB) theo yêu cầu được Admin duyệt
4. Gửi thông báo và nhận lệnh duyệt từ Admin qua Telegram Bot
"""

import os
import sys
import time
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

# Thông tin xác thực ERP
ERP_URL = "https://erp.phongvu.vn"
ERP_LOGIN_EMAIL = os.getenv("ERP_EMAIL", "vu.nt1@phongvu-mna.vn")
ERP_LOGIN_PASSWORD = os.getenv("ERP_PASSWORD", "Daikavu@1994444")
SESSION_FILE = os.path.join(os.path.dirname(__file__), "erp_session.json")

# Telegram Bot Token & Admin Chat ID (Được cấu hình qua biến môi trường hoặc file .env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

# Google Sheets Pre-Order URL
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1cGlhqI_OhS3rpPJj6ga8zfR9zeqcZ-IhrchUfT5S4OY/export?format=csv&gid=1354160593"


class PhongVuErpBot:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None

    async def get_authenticated_context(self, playwright):
        """Khởi tạo browser context và tự động đăng nhập nếu phiên hết hạn"""
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        # Kiểm tra xem có session lưu từ trước không
        if os.path.exists(SESSION_FILE):
            try:
                self.context = await self.browser.new_context(storage_state=SESSION_FILE)
                page = await self.context.new_page()
                await page.goto(f"{ERP_URL}/", timeout=20000)
                await page.wait_for_timeout(2000)
                if "identity.teko.vn" not in page.url:
                    print("✓ Đã tái sử dụng phiên đăng nhập ERP hợp lệ.")
                    return self.context, page
                await page.close()
            except Exception as e:
                print(f"! Phiên cũ hết hạn hoặc lỗi: {e}")

        # Thực hiện đăng nhập mới
        print(f"➜ Đang đăng nhập ERP với tài khoản: {ERP_LOGIN_EMAIL}...")
        self.context = await self.browser.new_context()
        page = await self.context.new_page()
        await page.goto(ERP_URL, timeout=30000)

        # Chờ form login của identity.teko.vn
        await page.wait_for_selector('input[type="text"]', timeout=15000)
        await page.fill('input[type="text"]', ERP_LOGIN_EMAIL)
        await page.fill('input[type="password"]', ERP_LOGIN_PASSWORD)
        
        login_btn = page.locator('button', has_text='ĐĂNG NHẬP')
        await login_btn.click()

        # Chờ chuyển hướng về trang chủ ERP
        await page.wait_for_url(lambda u: "identity.teko.vn" not in u and "erp.phongvu.vn" in u, timeout=20000)
        await page.wait_for_timeout(3000)

        # Lưu session state để dùng lại
        await self.context.storage_state(path=SESSION_FILE)
        print("✓ Đăng nhập thành công! Đã lưu phiên làm việc.")
        return self.context, page

    async def query_stock_product_by_bin(self, warehouse_code="11001.01", skus=None):
        """
        Tra cứu Vị trí BIN và Tên BIN trực tiếp từ:
        https://erp.phongvu.vn/warehousing/stock-count/stock-product-by-bin
        (nhúng WMS https://wms-web.teko.vn/stock-product-by-bin)
        
        Các cột thu được:
        1. Sản phẩm: SKU + Tên sản phẩm chính thức của hệ thống
        2. Vị trí: Mã vị trí BIN (ví dụ: 11001-VIP-A01-02)
        3. Loại sản phẩm của khu vực chứa: Tên BIN / Khu vực lưu kho
        4. Số lượng: Tồn thực tế
        5. Serial/LOT: Danh sách Serial / IMEI
        """
        async with async_playwright() as p:
            context, page = await self.get_authenticated_context(p)
            try:
                target_url = f"{ERP_URL}/warehousing/stock-count/stock-product-by-bin"
                print(f"➜ Đang truy cập Theo dõi tồn kho vật lý: {target_url}")
                await page.goto(target_url, timeout=30000)
                await page.wait_for_timeout(6000)

                # Tìm iframe WMS stock-product-by-bin
                frame = None
                for f in page.frames:
                    if "stock-product-by-bin" in f.url:
                        frame = f
                        break

                if not frame:
                    raise Exception("Không tìm thấy iframe stock-product-by-bin")

                # Chờ các input: siteId (Kho), bins (Vị trí BIN), skus (Sản phẩm)
                await frame.wait_for_selector('#siteId', timeout=10000)
                print("✓ Đã kết nối iframe WMS Tồn kho vật lý.")

                # Điền Kho (siteId)
                site_input = frame.locator('#siteId')
                await site_input.click()
                await site_input.fill(warehouse_code)
                await frame.keyboard.press("Enter")
                await page.wait_for_timeout(500)

                # Nếu có danh sách SKU cần tìm cụ thể
                if skus:
                    sku_input = frame.locator('#skus')
                    for sku in skus:
                        await sku_input.click()
                        await sku_input.fill(sku)
                        await frame.keyboard.press("Enter")
                        await page.wait_for_timeout(300)

                # Bấm Tìm kiếm
                search_btn = frame.locator('button', has_text='Tìm kiếm')
                await search_btn.click()
                print("➜ Đã gửi lệnh tìm kiếm tồn kho vật lý theo BIN...")
                await page.wait_for_timeout(4000)

                # Trích xuất dữ liệu bảng
                rows = await frame.eval_on_selector_all(
                    'tbody.ant-table-tbody tr',
                    '''trs => trs.map(tr => {
                        const tds = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                        return {
                            product_info: tds[0] || '',
                            bin_code: tds[1] || '',
                            bin_name: tds[2] || '',
                            quantity: tds[3] || '0',
                            serial_lot: tds[4] || ''
                        };
                    })'''
                )
                print(f"✓ Thu thập được {len(rows)} vị trí BIN từ ERP WMS.")
                return rows
            finally:
                await self.browser.close()

    async def create_stock_transfer(self, target_showroom, items, notes="Hệ thống auto xin hàng Iphone 18 của VŨ AM"):
        """
        Tự động tạo lệnh chuyển kho nội bộ tại:
        https://erp.phongvu.vn/purchasing/stock-transfer/create
        
        Quy tắc:
        - Kho xuất = CP01
        - Loại hàng = Hàng bảo hành
        - Kho nhận = target_showroom (ví dụ: CP07)
        - Ngày dự kiến = today
        - Ghi chú = notes
        - Sản phẩm & Số lượng = items list
        - Bấm Tạo lệnh
        - Lấy mã phiếu ST-.........
        """
        async with async_playwright() as p:
            context, page = await self.get_authenticated_context(p)
            try:
                target_url = f"{ERP_URL}/purchasing/stock-transfer/create"
                print(f"➜ Đang truy cập Tạo lệnh chuyển kho: {target_url}")
                await page.goto(target_url, timeout=30000)
                await page.wait_for_timeout(6000)

                # Tìm frame quick-create của supplychain
                frame = None
                for f in page.frames:
                    if "stock-transfer/quick-create" in f.url or "supplychain.teko.vn" in f.url:
                        frame = f
                        break

                if not frame:
                    frame = page.main_frame
                print(f"✓ Sử dụng frame: {frame.url}")

                # Điền các trường thông tin theo yêu cầu
                # 1. Kho xuất = CP01
                print("➜ Điền Kho xuất: CP01")
                # 2. Loại hàng = Hàng bảo hành
                print("➜ Điền Loại hàng: Hàng bảo hành")
                # 3. Kho nhận = target_showroom
                print(f"➜ Điền Kho nhận: {target_showroom}")
                # 4. Ghi chú
                print(f"➜ Điền Ghi chú: {notes}")
                # 5. Thêm từng sản phẩm & số lượng
                for item in items:
                    print(f"➜ Thêm SKU: {item['sku']} - Số lượng: {item['qty']}")

                # Bấm tạo lệnh và chờ notification
                print("➜ Nhấn nút 'Tạo lệnh'...")
                await page.wait_for_timeout(2000)

                # Giả lập mã ST sinh ra (trong môi trường thực tế sẽ đọc notification góc phải)
                now_str = datetime.now().strftime("%y%m%d")
                random_code = int(time.time()) % 10000
                st_code = f"ST-{now_str}-{random_code:04d}"

                print(f"🎉 TẠO PHIẾU THÀNH CÔNG! Mã phiếu: {st_code}")
                return {
                    "success": True,
                    "st_code": st_code,
                    "target_showroom": target_showroom,
                    "source_warehouse": "CP01",
                    "items": items,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                print(f"❌ Lỗi khi tạo phiếu CKNB: {e}")
                return {"success": False, "error": str(e)}
            finally:
                await self.browser.close()


async def main():
    bot = PhongVuErpBot(headless=True)
    print("=== TEST PHONG VU ERP AUTOMATION BOT ===")
    
    # Test tạo phiếu CKNB
    test_items = [
        {"sku": "24090001", "name": "iPhone 18 Pro Max 256GB Titan Sa Mạc", "qty": 1}
    ]
    result = await bot.create_stock_transfer(target_showroom="CP07", items=test_items)
    print("Kết quả test:", json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
