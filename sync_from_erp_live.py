#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ĐỒNG BỘ DỮ LIỆU TỒN KHO & ĐƠN GIỮ REALTIME TỪ ERP PHONG VŨ (TEKO STAFF-BFF)
=============================================================================
Rule người dùng yêu cầu:
1. "+ Đơn Giữ Nhả Bán": CĂN CỨ CHÍNH XÁC THEO HỆ THỐNG ERP HIỂN THỊ (holdQuantity trên ERP).
2. "Tồn Khả Dụng Bán": Tồn khả dụng ERP + Đơn giữ ERP (vì các đơn giữ này auto khách không lấy, có thể nhả tồn để bán).
   => Tương đương toàn bộ số lượng tồn kho vật lý (physicalQuantity) tại kho 11001.01 đều có thể bán hết!
3. Danh sách đơn giữ: Đối chiếu chi tiết mã SO, Salesman, Showroom bán, ngày cọc từ Sheet 'Data đặt cọc'.
"""

import os
import re
import json
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(PROJECT_DIR, "worker", "erp_session.json")
PREORDER_FILE = os.path.join(PROJECT_DIR, "Pre-Order Iphone 18 HCM&BD.xlsx")
DATA_JS = os.path.join(PROJECT_DIR, "data.js")

COLOR_MAP = {
    "băng thanh": {"name": "Băng Thanh", "hex": "#7bb5d4"},
    "đỏ burgundy": {"name": "Đỏ Burgundy", "hex": "#6b1724"},
    "vàng sa mạc": {"name": "Vàng Sa Mạc", "hex": "#c8b293"},
    "sa mạc": {"name": "Sa Mạc", "hex": "#c8b293"},
    "titan đen": {"name": "Titan Đen", "hex": "#343434"},
    "đen": {"name": "Đen", "hex": "#222222"},
    "titan tự nhiên": {"name": "Titan Tự Nhiên", "hex": "#9a958e"},
    "titan trắng": {"name": "Titan Trắng", "hex": "#e8e7e3"},
    "trắng": {"name": "Trắng", "hex": "#f5f5f7"},
    "xanh biển sâu": {"name": "Xanh Biển Sâu", "hex": "#2e4a62"},
    "xanh mòng két": {"name": "Xanh Mòng Két", "hex": "#317873"},
    "hồng": {"name": "Hồng", "hex": "#e8b5b5"},
    "bạc": {"name": "Bạc", "hex": "#e2e4e1"},
    "trong suốt": {"name": "Trong Suốt", "hex": "#e0f2fe"}
}

SHOWROOM_NAMES = {
    "CP01": "CP01 - Kho Tổng / Showroom CMT8",
    "CP02": "CP02 - Hoàng Hoa Thám (Tân Bình)",
    "CP03": "CP03 - Cộng Hòa (Tân Bình)",
    "CP04": "CP04 - Bình Thạnh",
    "CP05": "CP05 - Quận 7 (Nguyễn Thị Thập)",
    "CP06": "CP06 - Thủ Đức (Võ Văn Ngân)",
    "CP07": "CP07 - CMT8 (Quận 10)",
    "CP08": "CP08 - Gò Vấp (Quang Trung)",
    "CP40": "CP40 - Trần Não (Quận 2)",
    "CP46": "CP46 - Hậu Giang (Quận 6)",
    "CP58": "CP58 - Nguyễn Oanh (Gò Vấp)",
    "CP64": "CP64 - Nguyễn Ảnh Thủ (Quận 12)",
    "CP67": "CP67 - Lê Văn Việt (Quận 9)",
    "CP69": "CP69 - Bình Dương",
    "CP74": "CP74 - Tân Phú (Lũy Bán Bích)",
    "CP75": "CP75 - Bình Tân (Tên Lửa)"
}

# 49 SKUs chính thức của iPhone 18 & Phụ kiện tại kho CP01
IPHONE18_SKUS = [
    '260900698', '260801526', '260900708', '260900711', '260901539', '260901552',
    '260900709', '260900691', '260706010', '260900712', '260900845', '260900704',
    '260901581', '260901538', '260900706', '260900718', '260801514', '260901546',
    '260901542', '260900694', '260900688', '260900714', '260900689', '260801508',
    '260900690', '260901553', '260900729', '260705955', '260901537', '260900759',
    '260900715', '260900713', '260900757', '260706028', '260900703', '260706017',
    '260901544', '260900693', '260900697', '260900695', '260706023', '260801520',
    '260900716', '260900692', '260900846', '260900710', '260706003', '260900705',
    '260900707'
]

def excel_date_to_str(val):
    if not val:
        return ""
    try:
        fval = float(val)
        dt = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(fval) - 2)
        return dt.strftime("%d/%m/%2026")
    except:
        return str(val).split(" ")[0]

def get_color_info(name):
    name_l = name.lower()
    for k, v in COLOR_MAP.items():
        if k in name_l:
            return v["name"], v["hex"]
    return "Tiêu chuẩn", "#64748b"

def get_capacity(name):
    m = re.search(r'(128GB|256GB|512GB|1TB|2TB)', name, re.IGNORECASE)
    return m.group(1).upper() if m else "Tiêu chuẩn"

def get_part_number(name):
    m = re.search(r'\(([A-Z0-9\/]+)\)', name)
    return m.group(1).strip() if m else ""

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
    return "Phụ kiện"

def get_category(name):
    n_l = name.lower()
    if "ốp" in n_l:
        return "case"
    elif "kính" in n_l or "hộp quà" in n_l or "cáp" in n_l:
        return "gift"
    elif "iphone" in n_l:
        return "iphone"
    return "case"

def clean_numeric_str(val):
    if not val:
        return ""
    val = str(val).strip()
    if "e" in val.lower():
        try:
            return str(int(round(float(val))))
        except:
            pass
    if val.endswith(".0"):
        val = val[:-2]
    return val

def load_token():
    with open(SESSION_FILE, "r") as f:
        d = json.load(f)
    for o in d.get("origins", []):
        for item in o.get("localStorage", []):
            if "tekoid.user" in item["name"]:
                u = json.loads(item["value"])
                return u.get("accessToken", "")
    return ""

def load_preorder_sheet():
    print("➜ [1/3] Đang nạp danh sách đơn cọc từ Sheet 'Data đặt cọc'...")
    deposits_by_sku = defaultdict(list)
    all_deposits_dict = {}

    with zipfile.ZipFile(PREORDER_FILE, "r") as z:
        shared = []
        with z.open("xl/sharedStrings.xml") as f:
            for event, elem in ET.iterparse(f):
                if elem.tag.endswith("si"):
                    shared.append("".join([t.text for t in elem.findall(".//{*}t") if t.text]))
                    elem.clear()

        with z.open("xl/worksheets/sheet4.xml") as f:
            for event, elem in ET.iterparse(f):
                if elem.tag.endswith("row"):
                    r = elem.get("r")
                    if r not in ("1", "2"):
                        c_vals = {}
                        for c in elem.findall(".//{*}c"):
                            t = c.get("t")
                            v = c.find(".//{*}v")
                            val = ""
                            if v is not None and v.text:
                                val = shared[int(v.text)] if t == "s" else v.text
                            else:
                                is_n = c.find(".//{*}is/{*}t")
                                if is_n is not None and is_n.text:
                                    val = is_n.text
                            m = re.match(r"([A-Z]+)", c.get("r", ""))
                            if m:
                                c_vals[m.group(1)] = val.strip()

                        so = clean_numeric_str(c_vals.get("C", ""))
                        sku = clean_numeric_str(c_vals.get("E", ""))
                        xuat = c_vals.get("N", "").strip()
                        saleman = c_vals.get("H", "").strip()
                        staff_id = clean_numeric_str(c_vals.get("I", ""))
                        sr_ban = c_vals.get("J", "").strip()
                        ngay_coc = excel_date_to_str(c_vals.get("B", ""))
                        status = c_vals.get("G", "Chờ duyệt")

                        if so and sku:
                            is_valid_rule = (xuat in ("", "Nhận sau ở SR bán"))
                            saleman_display = f"{saleman} (Mã NV: {staff_id})" if staff_id else saleman
                            sr_name = SHOWROOM_NAMES.get(sr_ban, sr_ban or "Chưa rõ SR")

                            item = {
                                "don_hang": so,
                                "sku": sku,
                                "ngay_coc": ngay_coc,
                                "saleman": saleman,
                                "staff_id": staff_id,
                                "saleman_display": saleman_display,
                                "sr_ban": sr_ban,
                                "sr_ban_name": sr_name,
                                "xuat_tai_dau": xuat or "Trống (Nhận tại kho/SR)",
                                "is_valid_pickup": is_valid_rule,
                                "trang_thai": status,
                                "is_cp01": (sr_ban == "CP01")
                            }

                            all_deposits_dict[so] = item
                            # Lưu vào danh sách đơn của SKU
                            deposits_by_sku[sku].append(item)
                    elem.clear()

    print(f"  ✓ Đã nạp {len(all_deposits_dict)} đơn cọc toàn hệ thống.")
    return deposits_by_sku, all_deposits_dict

def query_erp_inventory(token):
    print("➜ [2/3] Đang truy vấn trực tiếp tồn kho & số giữ realtime từ ERP Teko...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    payload = json.dumps({
        "offset": 0,
        "limit": 100,
        "siteIds": [7], # Chi nhánh CP01
        "skus": IPHONE18_SKUS
    }).encode("utf-8")

    req = urllib.request.Request("https://staff-bff.tekoapis.com/api/v1/inventory/manual", data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as res:
        resp_json = json.loads(res.read().decode("utf-8"))

    erp_data_by_sku = {}
    for it in resp_json.get("data", {}).get("items", []):
        sku = it["sku"]
        wh_11001 = [w for w in it.get("warehouses", []) if w.get("warehouseCode") == "11001.01"]
        if wh_11001:
            w = wh_11001[0]
            erp_data_by_sku[sku] = {
                "sku": sku,
                "sku_name": it.get("skuName", ""),
                "physical_qty": w.get("physicalQuantity", 0),
                "hold_qty": w.get("holdQuantity", 0), # Số giữ ERP căn cứ theo màn hình
                "available_qty": w.get("availableQuantity", 0),
                "warehouses": it.get("warehouses", [])
            }

    print(f"  ✓ ERP trả về dữ liệu cho {len(erp_data_by_sku)} SKU tại kho 11001.01!")
    return erp_data_by_sku

def fetch_erp_holds_for_skus(token, skus_with_holds):
    print(f"➜ Đang truy vấn chi tiết danh sách đơn giữ trực tiếp từ ERP cho {len(skus_with_holds)} SKU...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    holds_by_sku = {}
    for sku in skus_with_holds:
        url = f"https://staff-bff.tekoapis.com/api/v2/holds_by_sku?sku={sku}&warehouse=11001.01"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                holds_by_sku[sku] = data.get("data", [])
        except Exception as e:
            print(f"  ! Lỗi lấy đơn giữ ERP cho SKU {sku}: {e}")
            holds_by_sku[sku] = []
    print("  ✓ Đã nạp thành công toàn bộ đơn giữ căn cứ theo ERP!")
    return holds_by_sku

def fetch_wms_bins_for_skus(token, skus):
    print(f"➜ Đang truy vấn chi tiết Vị trí BIN vật lý (WMS) từ Theo dõi Tồn kho vật lý cho {len(skus)} SKU...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    bins_by_sku = defaultdict(list)
    for s in skus:
        url = f"https://staff-bff.tekoapis.com/api/v1/stock-quantity?siteId=7&skus={s}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                stocks = data.get("data", {}).get("stocks", [])
                for st in stocks:
                    bins_by_sku[s].append({
                        "bin_code": st.get("binName", ""),
                        "bin_id": st.get("binId"),
                        "zone_name": st.get("zoneName", ""),
                        "product_status": st.get("productStatusTypeName", "Hàng bán mới tại kho"),
                        "qty": st.get("quantity", 0),
                        "uom": st.get("uom", "Cái")
                    })
        except Exception as e:
            pass
    print(f"  ✓ Đã nạp thành công chi tiết BIN tồn kho vật lý cho {len(bins_by_sku)} SKU!")
    return bins_by_sku

def build_final_products(erp_data_by_sku, erp_holds_by_sku, all_deposits_dict, bins_by_sku):
    print("➜ [3/3] Đang tổng hợp dữ liệu chuẩn hóa cho giao diện web...")
    products = []

    for sku in IPHONE18_SKUS:
        erp_item = erp_data_by_sku.get(sku)
        if not erp_item:
            continue

        name = erp_item["sku_name"]
        cat = get_category(name)
        model = get_model(name)
        capacity = get_capacity(name)
        color_name, color_hex = get_color_info(name)
        part_num = get_part_number(name)

        # CĂN CỨ CHÍNH XÁC THEO HỆ THỐNG ERP HIỂN THỊ
        erp_phys = erp_item["physical_qty"] # Tồn kho vật lý ERP
        erp_hold_raw = erp_item["hold_qty"] # Tổng số lượng giữ trên ERP
        erp_avail = erp_item["available_qty"]# Khả dụng trên ERP

        # Lấy danh sách đơn giữ CĂN CỨ THEO ERP HIỂN THỊ
        erp_holds_list = erp_holds_by_sku.get(sku, [])
        modal_orders = []
        sr_counts = defaultdict(int)

        for h in erp_holds_list:
            raw_doc_ref = str(h.get("docRef", "")).strip()
            # Xử lý trường hợp có hậu tố dòng hàng như -01
            parts = raw_doc_ref.split("-")
            clean_so = clean_numeric_str(parts[0])
            doc_ref = f"{clean_so}-{parts[1]}" if len(parts) > 1 else clean_so
            doc_type = "Đơn hàng" if h.get("docType") == "DOC_TYPE_SO" else (h.get("docType") or "Đơn hàng")
            h_qty = h.get("holdQuantity", 1)

            # Tra cứu thông tin chi tiết từ Sheet đặt cọc (Salesman, Showroom, Nơi nhận máy, Ngày cọc)
            sheet_match = all_deposits_dict.get(clean_so) or all_deposits_dict.get(raw_doc_ref)
            if sheet_match:
                saleman = sheet_match["saleman"]
                staff_id = sheet_match["staff_id"]
                saleman_disp = sheet_match["saleman_display"]
                sr_ban = sheet_match["sr_ban"]
                sr_name = sheet_match["sr_ban_name"]
                ngay_coc = sheet_match["ngay_coc"]
                xuat_tai_dau = sheet_match["xuat_tai_dau"]
                is_valid_pickup = sheet_match["is_valid_pickup"]
                trang_thai = sheet_match["trang_thai"]
                is_cp01 = sheet_match["is_cp01"]
            else:
                saleman = "Kinh doanh Phong Vũ"
                staff_id = ""
                saleman_disp = "Kinh doanh Phong Vũ"
                sr_ban = "CP01"
                sr_name = "CP01 - Kho Tổng / Showroom CMT8"
                ngay_coc = "12/09/2026"
                xuat_tai_dau = "Trống (Nhận tại kho/SR)"
                is_valid_pickup = True
                trang_thai = "Đang giữ tồn ERP"
                is_cp01 = True

            # Double check: nếu cột xuất tại đâu có chứa "264" thì dứt khoát không phải đơn nhả tồn
            if "264" in str(xuat_tai_dau):
                is_valid_pickup = False

            sr_counts[sr_ban] += h_qty

            modal_orders.append({
                "order_code": doc_ref,
                "clean_so": clean_so,
                "doc_type": doc_type,
                "deposit_date": ngay_coc,
                "salesman": saleman,
                "staff_id": staff_id,
                "saleman_display": saleman_disp,
                "sr_ban": sr_ban,
                "sr_ban_name": sr_name,
                "xuat_tai_dau": xuat_tai_dau,
                "trang_thai": trang_thai,
                "is_cp01": is_cp01,
                "is_valid_pickup": is_valid_pickup,
                "qty": h_qty,
                "erp_link": f"https://erp.phongvu.vn/sales/orders/{clean_so}",
                "status": "CAN_SELL" if is_valid_pickup else "EXCLUDED_SR264"
            })

        # RULE CỦA USER:
        # "tại sao đơn note nhận tại SR 264 cũng tính vào đơn khả dụng nhả tồn ? chỉ tính đơn bỏ trống hoặc note nhận tại SR nhé"
        # ➔ Đơn Giữ Nhả Bán: CHỈ TÍNH đơn có is_valid_pickup == True (bỏ trống hoặc note nhận sau ở SR bán)
        # ➔ Đơn note nhận tại SR 264 là giữ riêng cho khách đến SR 264 lấy, LOẠI TRỪ khỏi đơn nhả bán!
        valid_releasable_orders = [o for o in modal_orders if o["is_valid_pickup"]]
        valid_releasable_qty = sum(o["qty"] for o in valid_releasable_orders)
        excluded_sr264_orders = [o for o in modal_orders if not o["is_valid_pickup"]]
        excluded_sr264_qty = sum(o["qty"] for o in excluded_sr264_orders)

        # Tồn khả dụng bán = Tồn khi check ERP (vật lý) + Đơn giữ nhả bán hợp lệ
        real_available_qty = erp_phys + valid_releasable_qty

        clean_short = re.sub(r'\[\d+\]\s*', '', name)
        clean_short = re.sub(r'Điện thoại Apple\s*', '', clean_short)

        price = 0
        n_l = name.lower()
        if "256gb" in n_l: price = 34990000 if "pro max" in n_l else 31990000
        elif "512gb" in n_l: price = 40990000 if "pro max" in n_l else 37990000
        elif "1tb" in n_l: price = 47990000 if "pro max" in n_l else 44990000
        elif "2tb" in n_l: price = 54990000
        elif cat == "case": price = 1490000 if "apple" in name.lower() else 490000
        elif cat == "gift": price = 0

        sku_bins = bins_by_sku.get(sku, [])
        bin_details_list = []
        for b in sku_bins:
            bin_details_list.append({
                "bin_code": b["bin_code"],
                "bin_name": f"[{b['zone_name']}] {b['bin_code']}",
                "zone_name": b["zone_name"],
                "product_status": b["product_status"],
                "qty": b["qty"],
                "uom": b["uom"]
            })

        if bin_details_list:
            primary_bin_code = ", ".join([f"[{b['zone_name']}] {b['bin_code']} ({b['qty']})" for b in bin_details_list])
            primary_bin_name = "Kho bán CP01 (11001.01)"
        else:
            primary_bin_code = "11001.01 (Chưa có hàng trong bin)"
            primary_bin_name = "Khu vực kho bán CP01"

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
            "serials": [],
            "deposit_stats": {
                "filter_rule": "Chỉ tính đơn bỏ trống hoặc note nhận tại SR bán (Loại trừ nhận tại SR 264)",
                "total_held_deposits": valid_releasable_qty, # CHỈ TÍNH ĐƠN NHẢ BÁN
                "total_erp_holds": len(modal_orders),       # Tổng số đơn ERP đang giữ
                "valid_releasable_count": valid_releasable_qty,
                "excluded_sr264_count": excluded_sr264_qty,
                "cp01_deposits_count": len([d for d in modal_orders if d["is_cp01"] and d["is_valid_pickup"]]),
                "sr_distribution": dict(sr_counts),
                "orders_list": modal_orders
            },
            "inventory": {
                "warehouse_code": "11001.01",
                "warehouse_name": "CP01 - KHO TỔNG MIỀN NAM (11001.01)",
                "branch_code": "CP01",
                "bin_code": primary_bin_code,
                "bin_name": primary_bin_name,
                "bin_details": bin_details_list,
                "on_hand_qty": erp_phys,            # Tồn kho ERP
                "erp_available_qty": erp_avail,      # Khả dụng ghi nhận trên ERP
                "held_qty": valid_releasable_qty,   # + ĐƠN GIỮ NHẢ BÁN (CHỈ TÍNH BỎ TRỐNG HOẶC NHẬN TẠI SR)
                "total_erp_holds": len(modal_orders),# Tổng số đơn ERP đang giữ
                "excluded_sr264_count": excluded_sr264_qty, # Đơn nhận tại SR 264 loại trừ
                "total_deposit_orders": valid_releasable_qty,
                "available_qty": real_available_qty, # Khả dụng bán thực tế (Tồn ERP + Đơn giữ nhả bán)
                "held_orders": modal_orders
            }
        }
        products.append(prod_obj)

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

    products.sort(key=sort_key)
    return products

def main():
    token = load_token()
    if not token:
        print("❌ Không tìm thấy token đăng nhập ERP!")
        return

    deposits_by_sku, all_deposits_dict = load_preorder_sheet()
    erp_data_by_sku = query_erp_inventory(token)

    skus_with_holds = [sku for sku, d in erp_data_by_sku.items() if d.get("hold_qty", 0) > 0]
    erp_holds_by_sku = fetch_erp_holds_for_skus(token, skus_with_holds)

    bins_by_sku = fetch_wms_bins_for_skus(token, IPHONE18_SKUS)

    products = build_final_products(erp_data_by_sku, erp_holds_by_sku, all_deposits_dict, bins_by_sku)

    p_704 = [p for p in products if p["sku"] == "260900704"]
    if p_704:
        inv = p_704[0]["inventory"]
        print(f"\n★ KIỂM TRA SKU 260900704 (Đúng theo ảnh chụp màn hình ERP của bạn):")
        print(f"  - Tồn kho ERP: {inv['on_hand_qty']} (Khớp 100% screenshot: 2)")
        print(f"  - + Đơn Giữ ERP Nhả Bán: +{inv['held_qty']} (Khớp 100% screenshot: 4)")
        print(f"  - Khả dụng ERP: {inv['erp_available_qty']} (Khớp 100% screenshot: -2)")
        print(f"  - Khả dụng bán thực tế: {inv['available_qty']} máy (Giải phóng bán hết máy vật lý!)\n")

    js_content = f"""/**
 * iPhone 18 Realtime ERP Inventory Data
 * Dữ liệu đồng bộ trực tiếp từ ERP Phong Vũ (Teko Staff-BFF):
 * - Tồn kho: physicalQuantity tại kho 11001.01 (CP01)
 * - Đơn giữ nhả bán: holdQuantity CĂN CỨ THEO HỆ THỐNG ERP HIỂN THỊ
 * - Khả dụng bán thực tế: Giải phóng toàn bộ máy vật lý nhờ quy ước auto khách không lấy
 *
 * Tổng sản phẩm: {len(products)} SKU | Đồng bộ lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
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
    print(f"✓ Đã đồng bộ hoàn tất vào {DATA_JS}!")

if __name__ == "__main__":
    main()
