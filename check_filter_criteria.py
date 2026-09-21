#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import zipfile
import xml.etree.ElementTree as ET
import re
from collections import defaultdict, Counter

EXCEL_FILE = "Pre-Order Iphone 18 HCM&BD.xlsx"

shared = []
with zipfile.ZipFile(EXCEL_FILE, "r") as z:
    with z.open("xl/sharedStrings.xml") as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag.endswith("si"):
                t_nodes = elem.findall(".//{*}t")
                shared.append("".join([t.text for t in t_nodes if t.text]))
                elem.clear()

    filtered_orders = []
    with z.open("xl/worksheets/sheet4.xml") as f:
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
                    col_ref = c.get("r", "")
                    m = re.match(r"([A-Z]+)", col_ref)
                    if m:
                        row_vals[m.group(1)] = val.strip()

                so = row_vals.get("C", "")
                sku_raw = row_vals.get("E", "")
                xuat_tai_dau = row_vals.get("N", "").strip()

                # Filter condition: "Xuất tại đâu?" = Nhận sau ở SR bán hoặc blank
                if (so or sku_raw) and (xuat_tai_dau == "" or xuat_tai_dau == "Nhận sau ở SR bán"):
                    filtered_orders.append(row_vals)
                elem.clear()

    print(f"Tổng số đơn thỏa điều kiện ('Nhận sau ở SR bán' hoặc blank): {len(filtered_orders)}")
    
    sr_counter = Counter(r.get("J", "") for r in filtered_orders)
    print("\n--- SỐ ĐƠN THEO SR BÁN (Chi nhánh Cột J) ---")
    for sr, count in sr_counter.most_common():
        print(f"  Chi nhánh {sr or '(Trống)'}: {count} đơn")

    sku_counter = Counter(r.get("E", "") for r in filtered_orders)
    print("\n--- SỐ ĐƠN CỌC THEO SKU ---")
    for sku, count in sku_counter.most_common():
        sample_name = next(r.get("D", "") for r in filtered_orders if r.get("E", "") == sku)
        print(f"  [{sku}] {sample_name[:50]}: {count} đơn")

    # In mẫu vài đơn để xem
    print("\n--- MẪU 5 ĐƠN THỎA ĐIỀU KIỆN ---")
    for r in filtered_orders[:5]:
        print(f"  SO: {r.get('C')} | Ngày: {r.get('B')} | Salesman: {r.get('H')} | SR bán: {r.get('J')} | Xuất tại đâu: {repr(r.get('N'))} | SKU: {r.get('E')}")

