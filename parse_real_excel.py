#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import zipfile
import xml.etree.ElementTree as ET
import re
import json
from collections import defaultdict

xlsx_path = "Bang_ke_ton_kho_theo_serial_den_ngay_hien_tai_2026_09_20_20092026131846.xlsx"

items = defaultdict(lambda: {
    "sku": "",
    "name": "",
    "part_number": "",
    "brand": "",
    "branch_code": "",
    "branch_name": "",
    "category_name": "",
    "group_name": "",
    "bins": defaultdict(lambda: {"bin_code": "", "bin_name": "", "qty": 0}),
    "serials": [],
    "total_qty": 0
})

with zipfile.ZipFile(xlsx_path, "r") as z:
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
                cat_name = row_vals.get("L", "")
                grp_name = row_vals.get("N", "")
                branch_code = row_vals.get("P", "")
                branch_name = row_vals.get("Q", "")
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
                    it["category_name"] = cat_name
                    it["group_name"] = grp_name
                    it["branch_code"] = branch_code
                    it["branch_name"] = branch_name
                    
                    bin_key = bin_code or "CHUA_CO_BIN"
                    it["bins"][bin_key]["bin_code"] = bin_code
                    it["bins"][bin_key]["bin_name"] = bin_name
                    it["bins"][bin_key]["qty"] += qty
                    
                    if serial:
                        it["serials"].append(serial)
                    it["total_qty"] += qty
                
                elem.clear()

print(f"Tổng số SKU trong toàn bộ file Excel: {len(items)}")

# Check brands and categories
brands = defaultdict(int)
for sku, it in items.items():
    brands[it["brand"]] += it["total_qty"]

print("\n--- TOP BRANDS BY QTY ---")
for b, q in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f"{b or '(Trống)'}: {q}")

# Filter iPhone 18 products and cases
target_items = []
for sku, it in items.items():
    n_low = it["name"].lower()
    if "iphone 18" in n_low or "iphone18" in n_low:
        target_items.append(it)

print(f"\n--- TÌM THẤY {len(target_items)} SẢN PHẨM IPHONE 18 VÀ PHỤ KIỆN IPHONE 18 ---")
for it in sorted(target_items, key=lambda x: x["name"]):
    bin_summary = ", ".join([f"{b['bin_code']} ({b['qty']})" for b in it["bins"].values()])
    print("=" * 60)
    print("SKU:", it["sku"], "| Tồn:", it["total_qty"])
    print("Tên:", it["name"])
    print("Part Number:", it["part_number"])
    print("Bins:", bin_summary)
    print("Chi tiết Bins:", [dict(b) for b in it["bins"].values()])
    print("Serials mẫu:", it["serials"][:5])


