#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script đọc toàn bộ sheet 'Data đặt cọc' từ Pre-Order Iphone 18 HCM&BD.xlsx
"""

import zipfile
import xml.etree.ElementTree as ET
import re
from collections import defaultdict

EXCEL_FILE = "Pre-Order Iphone 18 HCM&BD.xlsx"

shared_strings = []
with zipfile.ZipFile(EXCEL_FILE, "r") as z:
    if "xl/sharedStrings.xml" in z.namelist():
        print("Đang đọc sharedStrings.xml...")
        with z.open("xl/sharedStrings.xml") as f:
            for event, elem in ET.iterparse(f, events=("end",)):
                if elem.tag.endswith("si"):
                    t_nodes = elem.findall(".//{*}t")
                    text = "".join([t.text for t in t_nodes if t.text])
                    shared_strings.append(text)
                    elem.clear()
        print(f"Đã nạp {len(shared_strings)} shared strings.")

    # Tìm sheet có tên 'Data đặt cọc'
    sheet_rel = "worksheets/sheet4.xml"
    print(f"Đang đọc {sheet_rel} (Data đặt cọc)...")
    
    rows = []
    with z.open(f"xl/{sheet_rel}") as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag.endswith("row"):
                r_num = elem.get("r")
                if r_num == "1":
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
                            val = shared_strings[idx] if idx < len(shared_strings) else ""
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

                if r_num == "2":
                    headers = row_vals
                    print("Headers (Row 2):", headers)
                else:
                    sku = row_vals.get("E", "")
                    so_raw = row_vals.get("C", "")
                    # Format SO number
                    so_code = ""
                    if so_raw:
                        try:
                            so_code = f"{int(float(so_raw))}"
                        except:
                            so_code = so_raw

                    if sku or so_code:
                        rows.append({
                            "row": r_num,
                            "date": row_vals.get("B", ""),
                            "so_code": so_code,
                            "sku_name": row_vals.get("D", ""),
                            "sku": sku,
                            "warehouse": row_vals.get("F", ""),
                            "order_status": row_vals.get("G", ""),
                            "salesman": row_vals.get("H", ""),
                            "staff_id": row_vals.get("I", ""),
                            "branch": row_vals.get("J", ""),
                            "delivery_method": row_vals.get("K", ""),
                            "phase_1": row_vals.get("M", ""),
                            "export_loc": row_vals.get("N", ""),
                            "sr_feedback": row_vals.get("O", "")
                        })
                elem.clear()

print(f"\n✓ Đã đọc tổng cộng {len(rows)} đơn đặt cọc từ sheet 'Data đặt cọc'!")

# Thống kê theo chi nhánh
branches = defaultdict(int)
for r in rows:
    branches[r["branch"]] += 1

print("\n--- SỐ ĐƠN CỌC THEO CHI NHÁNH ---")
for b, c in sorted(branches.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"  Chi nhánh {b}: {c} đơn")

# Thống kê theo SKU
skus = defaultdict(int)
for r in rows:
    skus[r["sku"]] += 1

print("\n--- TOP SKU ĐẶT CỌC ---")
for s, c in sorted(skus.items(), key=lambda x: x[1], reverse=True)[:15]:
    # tìm tên
    sample = next((r["sku_name"] for r in rows if r["sku"] == s), "")
    print(f"  [{s}] {sample[:50]}: {c} đơn cọc")

# Thống kê đơn cọc riêng cho kho CP01 hoặc chi nhánh CP01
cp01_orders = [r for r in rows if r["branch"] == "CP01" or r["warehouse"] == "CP01" or "11001" in r["warehouse"]]
print(f"\n--- SỐ ĐƠN CỌC LIÊN QUAN ĐẾN CP01 (Kho 11001.01): {len(cp01_orders)} đơn ---")
for o in cp01_orders[:10]:
    print(f"  SO: {o['so_code']} | SKU: {o['sku']} | Sales: {o['salesman']} | Status: {o['order_status']} | Branch: {o['branch']}")

