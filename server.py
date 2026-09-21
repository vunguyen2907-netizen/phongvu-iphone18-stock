#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REALTIME ERP SYNC & WEB SERVER FOR PHONG VU IPHONE 18 STOCK
============================================================
1. Serves static web frontend (index.html, app.js, style.css, data.js).
2. Provides realtime API /api/live-stock and /api/sync to query Teko ERP live.
3. Runs background auto-refresh worker every 60s to ensure data is always fresh.
"""

import os
import sys
import json
import time
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from sync_from_erp_live import (
    load_token, load_preorder_sheet, query_erp_inventory,
    IPHONE18_SKUS, build_final_products, clean_numeric_str, DATA_JS
)

PORT = 3108
CACHE_LOCK = threading.Lock()
CACHED_DATA = {
    "products": [],
    "last_sync": 0,
    "last_sync_str": "",
    "is_syncing": False
}

# Pre-load Excel preorder reference into memory
print("➜ [SERVER] Đang nạp dữ liệu đặt cọc đối chiếu từ file Excel...")
DEPOSITS_BY_SKU, ALL_DEPOSITS_DICT = load_preorder_sheet()
print(f"  ✓ Đã nạp {len(ALL_DEPOSITS_DICT)} đơn đặt cọc đối chiếu vào bộ nhớ máy chủ.")


def perform_erp_live_sync(force=False):
    """Truy vấn realtime trực tiếp từ ERP Phong Vũ (Teko IAM + Staff-BFF)"""
    global CACHED_DATA
    with CACHE_LOCK:
        now = time.time()
        # Nếu vừa sync trong vòng 20s và không bắt buộc force, trả về cache ngay (<5ms)
        if not force and CACHED_DATA["products"] and (now - CACHED_DATA["last_sync"] < 20):
            return CACHED_DATA

        if CACHED_DATA["is_syncing"]:
            return CACHED_DATA
        CACHED_DATA["is_syncing"] = True

    try:
        t0 = time.time()
        token = load_token()
        if not token:
            print("! [SERVER] Không tìm thấy ERP token!")
            with CACHE_LOCK:
                CACHED_DATA["is_syncing"] = False
            return CACHED_DATA

        # 1. Tra cứu tồn kho & số giữ manual inventory
        erp_data = query_erp_inventory(token)

        # 2. Tra cứu chi tiết đơn giữ ERP song song
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        skus_with_holds = [sku for sku, d in erp_data.items() if d.get("hold_qty", 0) > 0]

        def fetch_hold(sku):
            url = f"https://staff-bff.tekoapis.com/api/v2/holds_by_sku?sku={sku}&warehouse=11001.01"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as res:
                    return sku, json.loads(res.read().decode("utf-8")).get("data", [])
            except:
                return sku, []

        def fetch_bin(sku):
            url = f"https://staff-bff.tekoapis.com/api/v1/stock-quantity?siteId=7&skus={sku}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as res:
                    return sku, json.loads(res.read().decode("utf-8")).get("data", {}).get("stocks", [])
            except:
                return sku, []

        with ThreadPoolExecutor(max_workers=15) as executor:
            hold_results = list(executor.map(fetch_hold, skus_with_holds))
            bin_results = list(executor.map(fetch_bin, IPHONE18_SKUS))

        erp_holds_by_sku = dict(hold_results)

        bins_by_sku = defaultdict(list)
        for sku, stocks in bin_results:
            for st in stocks:
                bins_by_sku[sku].append({
                    "bin_code": st.get("binName", ""),
                    "bin_id": st.get("binId"),
                    "zone_name": st.get("zoneName", ""),
                    "product_status": st.get("productStatusTypeName", "Hàng bán mới tại kho"),
                    "qty": st.get("quantity", 0),
                    "uom": st.get("uom", "Cái")
                })

        products = build_final_products(erp_data, erp_holds_by_sku, ALL_DEPOSITS_DICT, bins_by_sku)

        sync_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        elapsed = time.time() - t0

        with CACHE_LOCK:
            CACHED_DATA["products"] = products
            CACHED_DATA["last_sync"] = time.time()
            CACHED_DATA["last_sync_str"] = sync_str
            CACHED_DATA["is_syncing"] = False

        print(f"✓ [REALTIME ERP] Đã cập nhật xong {len(products)} SKU từ ERP Phong Vũ trong {elapsed:.2f}s! ({sync_str})")

        # Cập nhật song song file data.js để dự phòng
        js_content = f"""/**
 * iPhone 18 Realtime ERP Inventory Data (Auto-synced)
 * Cập nhật lúc: {sync_str}
 */
const INITIAL_PRODUCTS = {json.dumps(products, ensure_ascii=False, indent=2)};
const ALL_DEPOSITS_LOOKUP = {json.dumps(ALL_DEPOSITS_DICT, ensure_ascii=False, indent=2)};
"""
        with open(DATA_JS, "w", encoding="utf-8") as f:
            f.write(js_content)

    except Exception as e:
        print(f"! [SERVER] Lỗi đồng bộ ERP: {e}")
        with CACHE_LOCK:
            CACHED_DATA["is_syncing"] = False

    return CACHED_DATA


def background_sync_worker():
    """Tự động đồng bộ ngầm định kỳ mỗi 60 giây"""
    while True:
        time.sleep(60)
        try:
            perform_erp_live_sync(force=True)
        except Exception as e:
            print(f"! [WORKER] Lỗi worker ngầm: {e}")


class RealtimeInventoryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/api/live-stock", "/api/sync", "/api/refresh"):
            params = parse_qs(parsed.query)
            force = (params.get("force", ["false"])[0].lower() in ("true", "1", "yes"))

            data = perform_erp_live_sync(force=force)

            response_payload = {
                "success": True,
                "is_realtime": True,
                "timestamp": data.get("last_sync_str", datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
                "total_products": len(data.get("products", [])),
                "products": data.get("products", [])
            }

            resp_bytes = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        # Phục vụ các file tĩnh bình thường (index.html, app.js, style.css...)
        super().do_GET()


def main():
    # Khởi động lần đầu
    perform_erp_live_sync(force=True)

    # Chạy thread đồng bộ ngầm
    worker_thread = threading.Thread(target=background_sync_worker, daemon=True)
    worker_thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), RealtimeInventoryHandler)
    print(f"🚀 [SERVER] Máy chủ Realtime ERP đang chạy tại http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
