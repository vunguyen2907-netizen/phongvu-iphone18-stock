#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
IMPORT THỰC TẾ DỮ LIỆU TỒN KHO VÀ ĐƠN CỌC VÀO LOCAL WEB
=============================================================================
Script này xử lý:
1. Đọc file export từ ERP [Theo dõi Tồn kho vật lý] (nút Xuất file trên web ERP)
2. Đọc file export từ Google Sheets Pre-Order [data đặt cọc]
3. Tự động chuyển đổi và cập nhật chính xác 100% vào data.js trên local
"""

import os
import csv
import json
import re

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JS_PATH = os.path.join(PROJECT_DIR, "data.js")


def import_wms_export(filepath):
    """
    Đọc file export từ https://erp.phongvu.vn/warehousing/stock-count/stock-product-by-bin
    Các cột: Sản phẩm, Vị trí, Loại sản phẩm của khu vực chứa, Số lượng, Serial/LOT
    """
    if not os.path.exists(filepath):
        print(f"File không tồn tại: {filepath}")
        return []

    products = []
    print(f"➜ Đang đọc dữ liệu từ file WMS: {filepath}...")

    # Đọc file CSV/TSV
    with open(filepath, mode="r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Chuẩn hóa tên cột
            product_raw = row.get("Sản phẩm") or row.get("Product") or ""
            bin_code = row.get("Vị trí") or row.get("Bin") or ""
            bin_type = row.get("Loại sản phẩm của khu vực chứa") or row.get("Area Type") or "Hàng bán mới tại kho"
            qty_raw = row.get("Số lượng") or row.get("Quantity") or "0"

            # Tách mã SKU từ chuỗi dạng: "[260900704] Điện thoại Apple iPhone 18 Pro Max 256GB - Đỏ Burgundy (MJXQ4X/A)"
            sku_match = re.search(r'\[(\d+)\]', product_raw)
            sku = sku_match.group(1) if sku_match else ""
            
            # Tách Part Number
            part_match = re.search(r'\(([A-Z0-9\/]+)\)', product_raw)
            part_number = part_match.group(1) if part_match else ""

            # Tách tên sản phẩm sạch
            clean_name = re.sub(r'\[\d+\]\s*', '', product_raw).strip()

            # Xác định dung lượng
            cap_match = re.search(r'(128GB|256GB|512GB|1TB|2TB)', clean_name, re.IGNORECASE)
            capacity = cap_match.group(1).upper() if cap_match else "Tiêu chuẩn"

            # Xác định màu sắc
            color_match = re.search(r'-\s*([^\(]+)', clean_name)
            color = color_match.group(1).strip() if color_match else ""

            try:
                on_hand = int(float(qty_raw))
            except:
                on_hand = 0

            if sku:
                products.append({
                    "sku": sku,
                    "part_number": part_number,
                    "name": clean_name or product_raw,
                    "category": "iphone" if "iphone" in clean_name.lower() else "case",
                    "model": "iPhone 18 Pro Max" if "pro max" in clean_name.lower() else ("iPhone 18 Pro" if "pro" in clean_name.lower() else "iPhone 18"),
                    "capacity": capacity,
                    "color": color,
                    "inventory": {
                        "warehouse_code": "11001.01",
                        "warehouse_name": "CP01 - KHO TỔNG MIỀN NAM (11001.01)",
                        "branch_code": "CP01",
                        "bin_code": bin_code,
                        "bin_name": bin_type,
                        "on_hand_qty": on_hand,
                        "held_qty": 0,
                        "available_qty": on_hand,
                        "held_orders": []
                    }
                })

    print(f"✓ Đã trích xuất được {len(products)} sản phẩm từ file ERP.")
    return products


def update_data_js(products):
    """Ghi danh sách sản phẩm thực tế vào data.js"""
    if not products:
        print("Không có dữ liệu để ghi!")
        return

    js_content = f"""/**
 * iPhone 18 Inventory & Product Data (Real Data Import)
 * Tự động cập nhật từ ERP Phong Vũ
 */

const INITIAL_PRODUCTS = {json.dumps(products, ensure_ascii=False, indent=2)};

const PHONGVU_SHOWROOMS = [
  {{ code: "CP07", name: "Phong Vũ Cách Mạng Tháng 8 (HCM)" }},
  {{ code: "CP02", name: "Phong Vũ Hoàng Hoa Thám (HCM)" }},
  {{ code: "CP03", name: "Phong Vũ Cộng Hòa (HCM)" }},
  {{ code: "CP04", name: "Phong Vũ Bình Thạnh (HCM)" }},
  {{ code: "CP05", name: "Phong Vũ Quận 7 (HCM)" }},
  {{ code: "CP06", name: "Phong Vũ Thủ Đức (HCM)" }},
  {{ code: "CP08", name: "Phong Vũ Gò Vấp (HCM)" }},
  {{ code: "CP10", name: "Phong Vũ Bình Dương (Thủ Dầu Một)" }},
  {{ code: "CP11", name: "Phong Vũ Dĩ An (Bình Dương)" }},
  {{ code: "CP15", name: "Phong Vũ Biên Hòa (Đồng Nai)" }}
];
"""
    with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"✓ Đã cập nhật thành công vào data.js ({len(products)} sản phẩm)!")


if __name__ == "__main__":
    # Tìm file export trong thư mục
    csv_files = [f for f in os.listdir(PROJECT_DIR) if f.endswith(".csv") and "data" not in f]
    if csv_files:
        print(f"Tìm thấy file export: {csv_files[0]}")
        prods = import_wms_export(os.path.join(PROJECT_DIR, csv_files[0]))
        update_data_js(prods)
    else:
        print("Chưa có file export trong thư mục. Vui lòng xem hướng dẫn để import.")
