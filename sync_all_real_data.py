#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
ĐỒNG BỘ 100% CHỈ TỪ SHEET 'DATA ĐẶT CỌC' VÀ FILE TỒN KHO ERP WMS
=============================================================================
Quy tắc xử lý theo yêu cầu:
1. CHỈ dựa vào sheet 'Data đặt cọc' trong file Pre-Order Iphone 18 HCM&BD.xlsx
2. Lọc theo cột 'Xuất tại đâu?' (Cột N) = 'Nhận sau ở SR bán' HOẶC blank (rỗng)
3. Lấy đúng các trường:
   - Đơn hàng: Mã SO (Cột C)
   - Ngày cọc: Ngày thanh toán (Cột B)
   - Saleman: Tên nhân viên bán (Cột H) + Mã NV (Cột I)
   - SR bán: Chi nhánh bán (Cột J)
   - Số lượng đang giữ: Tổng hợp số đơn cọc theo SKU
"""

import zipfile
import xml.etree.ElementTree as ET
import re
import json
import os
import datetime
from collections import defaultdict, Counter

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(PROJECT_DIR, "Bang_ke_ton_kho_theo_serial_den_ngay_hien_tai_2026_09_20_20092026131846.xlsx")
PREORDER_FILE = os.path.join(PROJECT_DIR, "Pre-Order Iphone 18 HCM&BD.xlsx")
DATA_JS = os.path.join(PROJECT_DIR, "data.js")

COLOR_MAP = {
    "đen": {"name": "Đen", "hex": "#1f2421"},
    "đỏ burgundy": {"name": "Đỏ Burgundy", "hex": "#800020"},
    "bạc": {"name": "Bạc", "hex": "#e5e7eb"},
    "băng thanh": {"name": "Băng Thanh", "hex": "#a8c0d8"},
    "dâu tằm": {"name": "Dâu Tằm", "hex": "#722f37"},
    "nâu xám": {"name": "Nâu Xám", "hex": "#6b5b52"},
    "xanh chambray": {"name": "Xanh Chambray", "hex": "#4b6b94"},
    "xanh ô-liu": {"name": "Xanh Ô-liu", "hex": "#556b2f"},
    "trong suốt": {"name": "Trong suốt", "hex": "#e0f2fe"},
    "transparent": {"name": "Trong suốt", "hex": "#e0f2fe"}
}

SHOWROOM_NAMES = {
    "CP01": "CP01 - Kho Tổng / Showroom CMT8",
    "CP02": "CP02 - Showroom Hoàng Hoa Thám (Tân Bình)",
    "CP03": "CP03 - Showroom Cộng Hòa (Tân Bình)",
    "CP04": "CP04 - Showroom Bình Thạnh",
    "CP05": "CP05 - Showroom Quận 7",
    "CP06": "CP06 - Showroom Thủ Đức",
    "CP07": "CP07 - Showroom Cách Mạng Tháng 8 (Quận 10)",
    "CP08": "CP08 - Showroom Gò Vấp",
    "CP10": "CP10 - Showroom Thủ Dầu Một (Bình Dương)",
    "CP11": "CP11 - Showroom Dĩ An (Bình Dương)",
    "CP15": "CP15 - Showroom Biên Hòa (Đồng Nai)",
    "CP40": "CP40 - Showroom Trần Não (Quận 2)",
    "CP46": "CP46 - Showroom Hậu Giang (Quận 6)",
    "CP58": "CP58 - Showroom Nguyễn Oanh (Gò Vấp)",
    "CP64": "CP64 - Showroom Nguyễn Ảnh Thủ (Quận 12)",
    "CP67": "CP67 - Showroom Lê Văn Việt (Quận 9)",
    "CP69": "CP69 - Showroom Bình Dương",
    "CP74": "CP74 - Showroom Tân Phú (Lũy Bán Bích)",
    "CP75": "CP75 - Showroom Bình Tân (Tên Lửa)"
}

def excel_date_to_str(val):
    if not val:
        return ""
    try:
        days = float(val)
        d = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=days)
        return d.strftime("%d/%m/%Y")
    except:
        return str(val)

def load_shared_strings(zip_obj):
    shared = []
    if "xl/sharedStrings.xml" in zip_obj.namelist():
        with zip_obj.open("xl/sharedStrings.xml") as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("si"):
                    t_nodes = elem.findall(".//{*}t")
                    text = "".join([t.text for t in t_nodes if t.text])
                    shared.append(text)
                    elem.clear()
    return shared

def get_color_info(name):
    name_l = name.lower()
    for k, v in COLOR_MAP.items():
        if k in name_l:
            return v["name"], v["hex"]
    return "Tiêu chuẩn", "#64748b"

def get_capacity(name):
    m = re.search(r'(128GB|256GB|512GB|1TB|2TB)', name, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return "Tiêu chuẩn"

def get_part_number(name, raw_part):
    if raw_part and raw_part.strip():
        return raw_part.strip()
    m = re.search(r'\(([A-Z0-9\/]+)\)', name)
    if m:
        return m.group(1).strip()
    return ""

def get_model(name):
    n_l = name.lower()
    if "pro max" in n_l or "promax" in n_l:
        return "iPhone 18 Pro Max"
    elif "pro" in n_l:
        return "iPhone 18 Pro"
    elif "air" in n_l:
        return "iPhone Air"
    elif "iphone 18" in n_l:
        return "iPhone 18"
    return "Khác"

def get_category(name):
    n_l = name.lower()
    if "ốp" in n_l:
        return "case"
    elif "kính" in n_l or "hộp quà" in n_l or "cáp" in n_l:
        return "gift"
    elif "iphone" in n_l:
        return "iphone"
    return "case"

def parse_data_dat_coc_only():
    """
    Chỉ đọc sheet 'Data đặt cọc' (worksheets/sheet4.xml).
    Lọc theo: Cột N ('Xuất tại đâu?') == 'Nhận sau ở SR bán' HOẶC blank
    Lấy:
      - Đơn hàng: Mã SO (Cột C)
      - Ngày cọc: Cột B (Ngày thanh toán)
      - Saleman: Cột H (Salesman) + Cột I (Mã nhân viên)
      - SR bán: Cột J (Chi nhánh)
      - Xuất tại đâu: Cột N
      - Trạng thái: Cột G
    """
    print("➜ [1/2] Đang đọc DUY NHẤT sheet 'Data đặt cọc' từ file Pre-Order...")
    deposits_by_sku = defaultdict(list)
    deposit_sku_names = {}
    total_valid = 0
    total_matched = 0

    with zipfile.ZipFile(PREORDER_FILE, "r") as z:
        shared = load_shared_strings(z)
        sheet_path = "xl/worksheets/sheet4.xml"
        
        with z.open(sheet_path) as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("row"):
                    r_num = elem.get("r")
                    if r_num in ("1", "2"):
                        elem.clear()
                        continue
                    row_vals = {}
                    for c in elem.findall(".//{*}c"):
                        t_type = c.get("t")
                        v = c.find(".//{*}v")
                        val = ""
                        if v is not None and v.text:
                            if t_type == "s":
                                idx = int(v.text)
                                val = shared[idx] if idx < len(shared) else ""
                            else:
                                val = v.text
                        else:
                            is_node = c.find(".//{*}is/{*}t")
                            if is_node is not None and is_node.text:
                                val = is_node.text
                        col_ref = c.get("r", "")
                        m = re.match(r"([A-Z]+)", col_ref)
                        if m:
                            row_vals[m.group(1)] = val.strip()

                    sku_raw = row_vals.get("E", "")
                    so_raw = row_vals.get("C", "")
                    if not (sku_raw or so_raw):
                        elem.clear()
                        continue

                    total_valid += 1

                    # LỌC ĐIỀU KIỆN: "Xuất tại đâu?" (Cột N) = "Nhận sau ở SR bán" HOẶC blank
                    xuat_tai_dau = row_vals.get("N", "").strip()
                    if xuat_tai_dau not in ("", "Nhận sau ở SR bán"):
                        elem.clear()
                        continue

                    total_matched += 1

                    # Chuẩn hóa SKU
                    sku = ""
                    try:
                        sku = f"{int(float(sku_raw))}"
                    except:
                        sku = sku_raw

                    # Chuẩn hóa Mã SO (Đơn hàng)
                    so_code = ""
                    try:
                        so_code = f"{int(float(so_raw))}"
                    except:
                        so_code = so_raw

                    # Saleman + Mã NV
                    saleman_name = row_vals.get("H", "").strip()
                    staff_id = row_vals.get("I", "").strip().replace(".0", "")
                    saleman_display = f"{saleman_name} (Mã NV: {staff_id})" if staff_id else saleman_name
                    item_name = row_vals.get("D", "").strip()
                    if sku and item_name:
                        deposit_sku_names[sku] = item_name

                    # SR bán
                    sr_ban = row_vals.get("J", "").strip()
                    sr_name = SHOWROOM_NAMES.get(sr_ban, sr_ban or "Chưa rõ SR")

                    # Ngày cọc
                    ngay_coc = excel_date_to_str(row_vals.get("B", ""))

                    deposit_item = {
                        "don_hang": so_code,
                        "ngay_coc": ngay_coc,
                        "saleman": saleman_name,
                        "staff_id": staff_id,
                        "saleman_display": saleman_display,
                        "sr_ban": sr_ban,
                        "sr_ban_name": sr_name,
                        "xuat_tai_dau": xuat_tai_dau or "Trống (Nhận tại kho/SR)",
                        "trang_thai": row_vals.get("G", "Chờ duyệt"),
                        "phuong_thuc_gh": row_vals.get("K", "Showroom"),
                        "gan_don_dot_1": row_vals.get("M", ""),
                        "is_cp01": (sr_ban == "CP01")
                    }
                    deposits_by_sku[sku].append(deposit_item)
                    elem.clear()

        # Build complete lookup dictionary of all orders in sheet
        all_deposits_dict = {}
        with z.open(sheet_path) as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("row"):
                    r_num = elem.get("r")
                    if r_num in ("1", "2"):
                        elem.clear()
                        continue
                    row_vals = {}
                    for c in elem.findall(".//{*}c"):
                        t_type = c.get("t")
                        v = c.find(".//{*}v")
                        val = ""
                        if v is not None and v.text:
                            if t_type == "s":
                                idx = int(v.text)
                                val = shared[idx] if idx < len(shared) else ""
                            else:
                                val = v.text
                        else:
                            is_node = c.find(".//{*}is/{*}t")
                            if is_node is not None and is_node.text:
                                val = is_node.text
                        col_ref = c.get("r", "")
                        m = re.match(r"([A-Z]+)", col_ref)
                        if m:
                            row_vals[m.group(1)] = val.strip()

                    so_raw = row_vals.get("C", "")
                    if not so_raw:
                        elem.clear()
                        continue

                    so_code = ""
                    try:
                        so_code = f"{int(float(so_raw))}"
                    except:
                        so_code = so_raw

                    sku_raw = row_vals.get("E", "")
                    sku = ""
                    try:
                        sku = f"{int(float(sku_raw))}"
                    except:
                        sku = sku_raw

                    xuat_tai_dau = row_vals.get("N", "").strip()
                    is_valid_rule = (xuat_tai_dau in ("", "Nhận sau ở SR bán"))

                    saleman_name = row_vals.get("H", "").strip()
                    staff_id = row_vals.get("I", "").strip().replace(".0", "")
                    saleman_display = f"{saleman_name} (Mã NV: {staff_id})" if staff_id else saleman_name

                    sr_ban = row_vals.get("J", "").strip()
                    sr_name = SHOWROOM_NAMES.get(sr_ban, sr_ban or "Chưa rõ SR")

                    all_deposits_dict[so_code] = {
                        "don_hang": so_code,
                        "sku": sku,
                        "ngay_coc": excel_date_to_str(row_vals.get("B", "")),
                        "saleman": saleman_name,
                        "staff_id": staff_id,
                        "saleman_display": saleman_display,
                        "sr_ban": sr_ban,
                        "sr_ban_name": sr_name,
                        "xuat_tai_dau": xuat_tai_dau or "Trống (Nhận tại kho/SR)",
                        "is_valid_pickup": is_valid_rule,
                        "trang_thai": row_vals.get("G", "Chờ duyệt")
                    }
                    elem.clear()

    print(f"  ✓ Tổng số đơn trong sheet: {total_valid}")
    print(f"  ✓ Số đơn thỏa điều kiện ('Nhận sau ở SR bán' hoặc blank): {total_matched}")
    print(f"  ✓ Tổng số mã SO tra cứu được: {len(all_deposits_dict)}")
    return deposits_by_sku, all_deposits_dict, deposit_sku_names

def parse_wms_inventory():
    print("➜ [2/2] Đang đọc file tồn kho vật lý WMS ERP...")
    items = defaultdict(lambda: {
        "sku": "", "name": "", "part_number": "", "brand": "",
        "bins": defaultdict(lambda: {"bin_code": "", "bin_name": "", "zone": "", "qty": 0}),
        "serials": [], "total_qty": 0
    })

    with zipfile.ZipFile(INVENTORY_FILE, "r") as z:
        with z.open("xl/worksheets/sheet1.xml") as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("row"):
                    r_num = elem.get("r")
                    if r_num in ("1", "2", "3"):
                        elem.clear()
                        continue
                    row_vals = {}
                    for c in elem.findall(".//{*}c"):
                        v = c.find(".//{*}v")
                        t = c.find(".//{*}t")
                        val = t.text if t is not None and t.text else (v.text if v is not None and v.text else "")
                        col_ref = c.get("r", "")
                        m = re.match(r"([A-Z]+)", col_ref)
                        if m:
                            row_vals[m.group(1)] = val.strip()

                    sku = row_vals.get("B", "")
                    name = row_vals.get("C", "")
                    part_no = row_vals.get("D", "")
                    qty_str = row_vals.get("F", "1")
                    serial = row_vals.get("G", "")
                    brand = row_vals.get("J", "")
                    zone = row_vals.get("R", "")
                    bin_code = row_vals.get("S", "")
                    bin_name = row_vals.get("T", "")

                    try:
                        qty = int(float(qty_str))
                    except:
                        qty = 1

                    if sku:
                        it = items[sku]
                        it["sku"] = sku
                        it["name"] = name
                        it["part_number"] = part_no
                        it["brand"] = brand

                        bin_k = bin_code or "CHUA_CO_BIN"
                        it["bins"][bin_k]["bin_code"] = bin_code
                        it["bins"][bin_k]["bin_name"] = bin_name
                        it["bins"][bin_k]["zone"] = zone
                        it["bins"][bin_k]["qty"] += qty

                        if serial:
                            it["serials"].append(serial)
                        it["total_qty"] += qty

                    elem.clear()

    print(f"  ✓ Đã trích xuất {len(items)} SKU tồn kho thực tế từ WMS.")
    return items

def build_dataset(wms_items, deposits_by_sku, deposit_sku_names=None):
    if deposit_sku_names is None:
        deposit_sku_names = {}
    print("➜ Đang tổng hợp số lượng đang giữ và danh sách đơn cọc...")
    all_products = []

    for sku, it in wms_items.items():
        name = it["name"]
        n_l = name.lower()

        is_iphone18 = ("iphone 18" in n_l or "iphone18" in n_l)
        is_gift = ("keep moving" in n_l and "iphone" in n_l)

        if not (is_iphone18 or is_gift):
            continue

        cat = get_category(name)
        model = get_model(name)
        capacity = get_capacity(name)
        color_name, color_hex = get_color_info(name)
        part_num = get_part_number(name, it["part_number"])

        # BIN entries
        bin_entries = []
        for b_k, b_info in it["bins"].items():
            b_code = b_info["bin_code"]
            b_zone = b_info["zone"] or b_info["bin_name"]
            b_qty = b_info["qty"]
            if b_zone:
                bin_entries.append(f"[{b_zone}] {b_code} ({b_qty} cái)")
            else:
                bin_entries.append(f"{b_code} ({b_qty} cái)")

        primary_bin_code = " | ".join(bin_entries)
        primary_zone = list(it["bins"].values())[0]["zone"] or "Hàng bán mới tại kho"

        # Danh sách đơn cọc từ sheet 'Data đặt cọc' thỏa điều kiện (Xuất tại đâu = Nhận sau ở SR bán | blank)
        sku_deposits = deposits_by_sku.get(sku, [])
        cp01_deposits = [d for d in sku_deposits if d["is_cp01"]]

        # Thống kê phân bố theo từng Showroom bán (Cột J)
        sr_counts = defaultdict(int)
        for d in sku_deposits:
            sr_counts[d["sr_ban"]] += 1

        on_hand = it["total_qty"]
        # RULE CỦA USER:
        # Tồn khả dụng = Tồn khi check ERP + tồn của List đơn giữ hàng
        # (CÓ nghĩa là những đơn giữ hàng này auto khách k lấy, có thể nhả tồn để bán)
        held_orders_qty = len(sku_deposits)
        available_qty = on_hand + held_orders_qty

        # Chuẩn bị danh sách đơn giữ hiển thị trong modal
        # Bao gồm: tất cả đơn thỏa điều kiện (ưu tiên hiển thị đơn CP01 trước, sau đó là các SR khác)
        sorted_deposits = sorted(sku_deposits, key=lambda x: (not x["is_cp01"], x["sr_ban"]))

        modal_orders = []
        for d in sorted_deposits:
            modal_orders.append({
                "order_code": d["don_hang"],
                "deposit_date": d["ngay_coc"],
                "salesman": d["saleman"],
                "staff_id": d["staff_id"],
                "saleman_display": d["saleman_display"],
                "sr_ban": d["sr_ban"],
                "sr_ban_name": d["sr_ban_name"],
                "xuat_tai_dau": d["xuat_tai_dau"],
                "trang_thai": d["trang_thai"],
                "is_cp01": d["is_cp01"],
                "qty": 1,
                "status": "CAN_SELL"
            })

        # Price estimation
        price = 0
        if "256gb" in n_l:
            price = 34990000 if "pro max" in n_l else 31990000
        elif "512gb" in n_l:
            price = 40990000 if "pro max" in n_l else 37990000
        elif "1tb" in n_l:
            price = 47990000 if "pro max" in n_l else 44990000
        elif "2tb" in n_l:
            price = 54990000
        elif cat == "case":
            price = 1490000 if "apple" in it["brand"].lower() else 490000
        elif cat == "gift":
            price = 0

        clean_short = re.sub(r'\[\d+\]\s*', '', name)
        clean_short = re.sub(r'Điện thoại Apple\s*', '', clean_short)

        prod_obj = {
            "sku": sku,
            "part_number": part_num,
            "name": name,
            "short_name": clean_short,
            "category": cat,
            "model": model,
            "capacity": capacity,
            "color": color_name,
            "color_hex": color_hex,
            "retail_price": price,
            "serials": it["serials"],
            # Dữ liệu đặt cọc CHỈ từ sheet 'Data đặt cọc'
            "deposit_stats": {
                "filter_rule": "Cột 'Xuất tại đâu?' = 'Nhận sau ở SR bán' hoặc blank",
                "total_held_deposits": held_orders_qty,
                "cp01_deposits_count": len(cp01_deposits),
                "sr_distribution": dict(sr_counts),
                "orders_list": modal_orders
            },
            "inventory": {
                "warehouse_code": "11001.01",
                "warehouse_name": "CP01 - KHO TỔNG MIỀN NAM (11001.01)",
                "branch_code": "CP01",
                "bin_code": primary_bin_code,
                "bin_name": primary_zone,
                "bin_details": [dict(b) for b in it["bins"].values()],
                "on_hand_qty": on_hand, # Tồn khi check ERP
                "held_qty": held_orders_qty, # Đơn giữ hàng (auto khách k lấy, có thể nhả bán)
                "total_deposit_orders": held_orders_qty,
                "available_qty": available_qty, # Tồn khả dụng = Tồn ERP + Đơn giữ
                "held_orders": modal_orders
            }
        }
        all_products.append(prod_obj)

    # Bổ sung các SKU có đơn giữ cọc (khách không lấy, có thể nhả) nhưng tồn kho vật lý CP01 = 0
    processed_skus = set(p["sku"] for p in all_products)
    for dep_sku, dep_list in deposits_by_sku.items():
        if dep_sku not in processed_skus:
            name = deposit_sku_names.get(dep_sku, f"Điện thoại Apple iPhone 18 ({dep_sku})")
            cat = get_category(name)
            model = get_model(name)
            capacity = get_capacity(name)
            color_name, color_hex = get_color_info(name)
            part_num = get_part_number(name, "")

            modal_orders = []
            for d in dep_list:
                modal_orders.append({
                    "order_code": d["don_hang"],
                    "deposit_date": d["ngay_coc"],
                    "salesman": d["saleman"],
                    "staff_id": d["staff_id"],
                    "saleman_display": d["saleman_display"],
                    "sr_ban": d["sr_ban"],
                    "sr_ban_name": d["sr_ban_name"],
                    "xuat_tai_dau": d["xuat_tai_dau"],
                    "trang_thai": d["trang_thai"],
                    "is_cp01": d["is_cp01"],
                    "qty": 1,
                    "status": "CAN_SELL"
                })

            sr_counts = defaultdict(int)
            for d in dep_list:
                sr_counts[d["sr_ban"]] += 1

            clean_short = re.sub(r'\[\d+\]\s*', '', name)
            clean_short = re.sub(r'Điện thoại Apple\s*', '', clean_short)

            price = 0
            n_l = name.lower()
            if "256gb" in n_l: price = 34990000 if "pro max" in n_l else 31990000
            elif "512gb" in n_l: price = 40990000 if "pro max" in n_l else 37990000
            elif "1tb" in n_l: price = 47990000 if "pro max" in n_l else 44990000
            elif "2tb" in n_l: price = 54990000

            all_products.append({
                "sku": dep_sku,
                "part_number": part_num,
                "name": name,
                "short_name": clean_short,
                "category": cat,
                "model": model,
                "capacity": capacity,
                "color": color_name,
                "color_hex": color_hex,
                "retail_price": price,
                "serials": [],
                "deposit_stats": {
                    "filter_rule": "Cột 'Xuất tại đâu?' = 'Nhận sau ở SR bán' hoặc blank",
                    "total_held_deposits": len(dep_list),
                    "cp01_deposits_count": len([d for d in dep_list if d["is_cp01"]]),
                    "sr_distribution": dict(sr_counts),
                    "orders_list": modal_orders
                },
                "inventory": {
                    "warehouse_code": "11001.01",
                    "warehouse_name": "CP01 - KHO TỔNG MIỀN NAM (11001.01)",
                    "branch_code": "CP01",
                    "bin_code": "Đơn cọc giữ (Chưa có máy tại kho CP01)",
                    "bin_name": "Đơn giữ cọc có thể nhả bán",
                    "bin_details": [],
                    "on_hand_qty": 0,
                    "held_qty": len(dep_list),
                    "total_deposit_orders": len(dep_list),
                    "available_qty": len(dep_list), # 0 + len(dep_list)
                    "held_orders": modal_orders
                }
            })

    def sort_key(p):
        cat_order = {"iphone": 0, "case": 1, "gift": 2}
        model_order = {"iPhone 18 Pro Max": 0, "iPhone 18 Pro": 1, "iPhone 18": 2}
        cap_order = {"256GB": 0, "512GB": 1, "1TB": 2, "2TB": 3, "Tiêu chuẩn": 4}
        return (
            cat_order.get(p["category"], 9),
            model_order.get(p["model"], 9),
            cap_order.get(p["capacity"], 9),
            p["color"]
        )

    all_products.sort(key=sort_key)
    return all_products

def generate_data_js(products, all_deposits_dict):
    js_content = f"""/**
 * iPhone 18 Inventory & Real Deposit Data
 * Nguồn dữ liệu:
 * 1. Tồn kho ERP WMS: Bang_ke_ton_kho_theo_serial_den_ngay_hien_tai_2026_09_20_20092026131846.xlsx
 * 2. DUY NHẤT Sheet 'Data đặt cọc' trong file: Pre-Order Iphone 18 HCM&BD.xlsx
 *    (Điều kiện lọc: Cột 'Xuất tại đâu?' = 'Nhận sau ở SR bán' HOẶC blank)
 *
 * RULE TỒN KHẢ DỤNG:
 * Tồn khả dụng = Tồn khi check ERP + Tồn của list đơn giữ hàng
 * (Các đơn giữ hàng này auto khách không lấy, có thể xin nhả tồn để bán)
 *
 * Tổng sản phẩm: {len(products)} SKU | Tổng tồn CP01: {sum(p['inventory']['on_hand_qty'] for p in products)} chiếc
 * Tổng khả dụng bán: {sum(p['inventory']['available_qty'] for p in products)} chiếc
 */

const INITIAL_PRODUCTS = {json.dumps(products, ensure_ascii=False, indent=2)};

// Tra cứu nhanh đơn đặt cọc từ Sheet Data đặt cọc (Rule đối chiếu đơn ERP)
const ALL_DEPOSITS_LOOKUP = {json.dumps(all_deposits_dict, ensure_ascii=False, indent=2)};

// Danh sách Showroom Phong Vũ
const PHONGVU_SHOWROOMS = [
  {{ code: "CP01", name: "Phong Vũ KHO TỔNG / CMT8 (11001.01)" }},
  {{ code: "CP07", name: "Phong Vũ Cách Mạng Tháng 8 (Quận 10)" }},
  {{ code: "CP02", name: "Phong Vũ Hoàng Hoa Thám (Tân Bình)" }},
  {{ code: "CP03", name: "Phong Vũ Cộng Hòa (Tân Bình)" }},
  {{ code: "CP04", name: "Phong Vũ Bình Thạnh" }},
  {{ code: "CP05", name: "Phong Vũ Quận 7 (Nguyễn Thị Thập)" }},
  {{ code: "CP06", name: "Phong Vũ Thủ Đức (Võ Văn Ngân)" }},
  {{ code: "CP08", name: "Phong Vũ Gò Vấp (Quang Trung)" }},
  {{ code: "CP40", name: "Phong Vũ Trần Não (Quận 2)" }},
  {{ code: "CP46", name: "Phong Vũ Hậu Giang (Quận 6)" }},
  {{ code: "CP58", name: "Phong Vũ Nguyễn Oanh (Gò Vấp)" }},
  {{ code: "CP64", name: "Phong Vũ Nguyễn Ảnh Thủ (Quận 12)" }},
  {{ code: "CP67", name: "Phong Vũ Lê Văn Việt (Quận 9)" }},
  {{ code: "CP69", name: "Phong Vũ Bình Dương" }},
  {{ code: "CP74", name: "Phong Vũ Tân Phú (Lũy Bán Bích)" }},
  {{ code: "CP75", name: "Phong Vũ Bình Tân (Tên Lửa)" }}
];
"""
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"✓ Đã ghi thành công vào {DATA_JS}!")

if __name__ == "__main__":
    deposits_by_sku, all_deposits_dict, deposit_sku_names = parse_data_dat_coc_only()
    wms_items = parse_wms_inventory()
    products = build_dataset(wms_items, deposits_by_sku, deposit_sku_names)
    generate_data_js(products, all_deposits_dict)


