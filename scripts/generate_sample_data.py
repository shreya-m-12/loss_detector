"""
Sample data generator for Business Loss Detection System.
Produces realistic Indian grocery retail datasets across 6 consecutive months (2026-05 to 2026-10).
Deterministic generation with designed positive test cases, strict negative controls, and gap months.
Generates:
  - datasets/sample_transactions.csv
  - datasets/sample_expenses.csv
  - datasets/expected_alerts.json
  - datasets/invalid_examples/ (validation suite)
"""
import os
import json
import csv
from datetime import date
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
INVALID_DIR = os.path.join(DATASETS_DIR, "invalid_examples")
os.makedirs(DATASETS_DIR, exist_ok=True)
os.makedirs(INVALID_DIR, exist_ok=True)

MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]

# 14 realistic Indian grocery items
# Baseline healthy products:
# - Basmati Rice 5kg: List 450, Cost 360 (Margin 20%)
# - Toor Dal 1kg: List 160, Cost 120 (Margin 25%)
# - Sunflower Oil 1L: List 150, Cost 125 (Margin 16.7%)
# - Whole Wheat Atta 10kg: List 380, Cost 300 (Margin 21%)
# - Tata Salt 1kg: List 28, Cost 22 (Margin 21.4%)
# - Sugar 1kg: List 45, Cost 35 (Margin 22.2%)
# - Turmeric Powder 200g: List 65, Cost 45 (Margin 30.7%)
# - Tea Powder 500g: List 240, Cost 180 (Margin 25%)
# - Dairy Milk 1L: Healthy volume around 200 units/mo
#
# Target Rule Test Products:
# 1. R1: "Imported Olive Oil 1L" in 2026-08: List 800, Cost 950 (Cost > Revenue -> R1 Loss alert)
# 2. R2: "Refined Palm Oil 1L" across months: List 110, Cost 105 (Margin = 4.5% -> Medium R2)
#        "Gram Flour Besan 1kg" in 2026-07: List 95, Cost 88 (Margin = 7.37% -> Low R2)
# 3. R3: "Basmati Rice 1kg" in 2026-09: 2026-08 qty = 100, 2026-09 qty = 60 (-40% decline -> Medium R3)
# 4. R5: "Organic Quinoa 500g": Months 05, 06, 07 sales avg = 20 units/mo. End of 2026-07 inventory = 90 (4.5x -> Medium R5)
# 5. R6: "Premium Basmati Rice 5kg" in 2026-09: List 600, Cost 300 (List margin 50%).
#        Discount = 210 (35%), Revenue = 390. Margin after = (390-300)/390 = 23.08%. Drop = 26.92 points -> Medium R6.
#        "Instant Noodles 12-Pack" in 2026-10: List 180, Cost 120. Discount 70 (38.8%), Revenue 110. Cost > Rev (Loss + R6 drop).
#
# Negative Controls (Must NOT trigger):
# - "Moong Dal 1kg" in 2026-08: 2026-07 qty = 100, 2026-08 qty = 81 (-19.0% decline, threshold is < -20%) -> NO R3 alert!
# - "Mustard Oil 1L" in 2026-07: List 150, Cost 135 (Margin exactly (150-135)/150 = 10.0%, threshold is < 10%) -> NO R2 alert!
# - "Cumin Seeds Jeera 500g" in 2026-07: trailing 3mo avg = 20, inventory = 60 (ratio = 3.0x, threshold is > 3.0x) -> NO R5 alert!
#
# Edge Rows:
# - "Garam Masala 100g": Sales in 2026-05 and 2026-07 only (Gap month in 2026-06). R3 connects to preceding available sales month.
# - "New Honey Brand 500g": Introduced in 2026-09 (only 2 months history by 2026-10). R5 skips due to insufficient history (< 3 months).

def generate_sample_data():
    transactions = []
    
    # Helper to add transaction lines
    def add_tx(tx_date, prod, qty, price, disc, cost, inv, ref=""):
        rev_before = (Decimal(str(qty)) * Decimal(str(price))).quantize(Decimal("0.01"))
        disc_dec = Decimal(str(disc)).quantize(Decimal("0.01"))
        rev_after = rev_before - disc_dec
        cost_dec = Decimal(str(cost)).quantize(Decimal("0.01"))
        
        transactions.append({
            "transaction_date": tx_date,
            "product_name": prod,
            "quantity_sold": f"{float(qty):.3f}",
            "selling_price": f"{float(price):.2f}",
            "discount_amount": f"{float(disc_dec):.2f}",
            "sales_revenue": f"{float(rev_after):.2f}",
            "product_cost": f"{float(cost_dec):.2f}",
            "inventory_quantity": f"{float(inv):.3f}",
            "transaction_ref": ref
        })

    # 1. Healthy baseline products across 6 months
    baseline_catalog = [
        ("Toor Dal 1kg", 160.00, 120.00, 50.0, 40.0),
        ("Sunflower Oil 1L", 150.00, 125.00, 60.0, 50.0),
        ("Whole Wheat Atta 10kg", 380.00, 300.00, 40.0, 35.0),
        ("Tata Salt 1kg", 28.00, 22.00, 100.0, 60.0),
        ("Sugar 1kg", 45.00, 35.00, 80.0, 50.0),
        ("Tea Powder 500g", 240.00, 180.00, 40.0, 30.0),
    ]

    for month_idx, m in enumerate(MONTHS):
        day_str = f"{m}-15"
        for prod, price, cost_unit, qty, inv in baseline_catalog:
            cost_total = cost_unit * qty
            add_tx(day_str, prod, qty, price, 0.0, cost_total, inv, f"TX-BASE-{prod[:3]}-{m}")

    # 2. Designed positive cases:
    # R1: "Imported Olive Oil 1L"
    # Months 05, 06, 07: Healthy
    for m in ["2026-05", "2026-06", "2026-07"]:
        add_tx(f"{m}-10", "Imported Olive Oil 1L", 10.0, 800.00, 0.0, 6800.00, 25.0, f"TX-OIL-{m}")
    # Month 08: Wholesale supplier price spiked to 950/bottle, selling at 800 -> Loss of ₹1,500 (margin -18.75% -> Medium R1)
    add_tx("2026-08-10", "Imported Olive Oil 1L", 10.0, 800.00, 0.0, 9500.00, 15.0, "TX-OIL-2026-08")
    # Months 09, 10: Repriced to 1050
    for m in ["2026-09", "2026-10"]:
        add_tx(f"{m}-10", "Imported Olive Oil 1L", 8.0, 1050.00, 0.0, 7200.00, 12.0, f"TX-OIL-{m}")

    # R2: "Refined Palm Oil 1L"
    # 2026-06: Revenue 11,000, Cost 10,500 -> Profit 500, Margin = 4.55% (< 5% -> Medium R2)
    add_tx("2026-06-12", "Refined Palm Oil 1L", 100.0, 110.00, 0.0, 10500.00, 40.0, "TX-PALM-2026-06")
    # "Gram Flour Besan 1kg"
    # 2026-07: Revenue 4,750, Cost 4,400 -> Profit 350, Margin = 7.37% (5% to 10% -> Low R2)
    add_tx("2026-07-14", "Gram Flour Besan 1kg", 50.0, 95.00, 0.0, 4400.00, 30.0, "TX-BESAN-2026-07")

    # R3: "Basmati Rice 1kg"
    # 2026-08: 100 units sold
    add_tx("2026-08-10", "Basmati Rice 1kg", 100.0, 120.00, 0.0, 9500.00, 80.0, "TX-RICE-2026-08")
    # 2026-09: 60 units sold (-40% decline, prev_qty >= 10 -> Medium R3)
    add_tx("2026-09-10", "Basmati Rice 1kg", 60.0, 120.00, 0.0, 5700.00, 60.0, "TX-RICE-2026-09")

    # R5: "Organic Quinoa 500g"
    # Months 05, 06, 07: 20 units sold each month -> trailing 3-month avg = 20 units/mo
    add_tx("2026-05-20", "Organic Quinoa 500g", 20.0, 220.00, 0.0, 3200.00, 40.0, "TX-QN-05")
    add_tx("2026-06-20", "Organic Quinoa 500g", 20.0, 220.00, 0.0, 3200.00, 50.0, "TX-QN-06")
    # End of 2026-07 snapshot = 90.0 units -> 90 / 20 = 4.5x (> 4x and < 6x -> Medium R5)
    add_tx("2026-07-20", "Organic Quinoa 500g", 20.0, 220.00, 0.0, 3200.00, 90.0, "TX-QN-07")
    add_tx("2026-08-20", "Organic Quinoa 500g", 20.0, 220.00, 0.0, 3200.00, 30.0, "TX-QN-08")

    # R6: "Premium Basmati Rice 5kg"
    # 2026-09: Qty 50, Price 600 -> Rev before = 30,000, Cost = 15,000 (Margin before = 50.0%)
    # Discount = 10,500 (35%), Rev after = 19,500. Margin after = (19,500-15,000)/19,500 = 23.08%
    # Drop = 50.0 - 23.08 = 26.92 points (> 20 and <= 30 -> Medium R6)
    add_tx("2026-09-18", "Premium Basmati Rice 5kg", 50.0, 600.00, 10500.00, 15000.00, 40.0, "TX-PRMRICE-2026-09")

    # Negative Controls (Strict boundary testing - must NOT alert):
    # Neg Control 1 for R3: "Moong Dal 1kg"
    # 2026-07: 100 units
    add_tx("2026-07-08", "Moong Dal 1kg", 100.0, 140.00, 0.0, 11000.00, 50.0, "TX-MOONG-07")
    # 2026-08: 81 units -> change = (81-100)/100 = -19.0% (threshold is < -20.0%, so exactly -19% must NOT alert)
    add_tx("2026-08-08", "Moong Dal 1kg", 81.0, 140.00, 0.0, 8910.00, 45.0, "TX-MOONG-08")

    # Neg Control 2 for R2: "Mustard Oil 1L"
    # 2026-07: Qty 100, Price 150 -> Rev = 15,000, Cost = 13,500. Margin = 1,500/15,000 = 10.0% (threshold is < 10.0%, so exactly 10.0% must NOT alert)
    add_tx("2026-07-16", "Mustard Oil 1L", 100.0, 150.00, 0.0, 13500.00, 30.0, "TX-MUSTARD-07")

    # Neg Control 3 for R5: "Cumin Seeds Jeera 500g"
    # Months 05, 06, 07: 20 units each -> 3-mo avg = 20. End of 07 inventory = 60.0 units -> ratio = 60/20 = 3.0x (threshold is > 3.0x, so exactly 3.0x must NOT alert)
    add_tx("2026-05-22", "Cumin Seeds Jeera 500g", 20.0, 180.00, 0.0, 2600.00, 20.0, "TX-JEERA-05")
    add_tx("2026-06-22", "Cumin Seeds Jeera 500g", 20.0, 180.00, 0.0, 2600.00, 20.0, "TX-JEERA-06")
    add_tx("2026-07-22", "Cumin Seeds Jeera 500g", 20.0, 180.00, 0.0, 2600.00, 60.0, "TX-JEERA-07")

    # Edge Rows:
    # Gap month product: "Garam Masala 100g" in 2026-05 (40 units) and 2026-07 (35 units). No records in 2026-06.
    add_tx("2026-05-18", "Garam Masala 100g", 40.0, 75.00, 0.0, 2000.00, 25.0, "TX-GM-05")
    add_tx("2026-07-18", "Garam Masala 100g", 35.0, 75.00, 0.0, 1750.00, 20.0, "TX-GM-07")

    # Short history product: "New Honey Brand 500g" in 2026-09 and 2026-10 only (only 2 months -> R5 skips)
    add_tx("2026-09-05", "New Honey Brand 500g", 15.0, 280.00, 0.0, 3150.00, 80.0, "TX-HONEY-09")
    add_tx("2026-10-05", "New Honey Brand 500g", 15.0, 280.00, 0.0, 3150.00, 80.0, "TX-HONEY-10")

    # Write sample_transactions.csv
    sales_file = os.path.join(DATASETS_DIR, "sample_transactions.csv")
    fieldnames = [
        "transaction_date", "product_name", "quantity_sold", "selling_price",
        "discount_amount", "sales_revenue", "product_cost", "inventory_quantity", "transaction_ref"
    ]
    with open(sales_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    # 3. Operating Expenses:
    # Baseline categories: Rent (15,000), Salaries (25,000), Electricity (4,000), Transport (2,500), Marketing (2,000), Maintenance (1,500)
    expenses = []
    for m in MONTHS:
        # Standard baseline
        expenses.append({"expense_date": f"{m}-01", "expense_category": "Rent", "expense_amount": "15000.00"})
        expenses.append({"expense_date": f"{m}-05", "expense_category": "Salaries", "expense_amount": "25000.00"})
        expenses.append({"expense_date": f"{m}-10", "expense_category": "Electricity", "expense_amount": "4000.00"})
        expenses.append({"expense_date": f"{m}-15", "expense_category": "Transport", "expense_amount": "2500.00"})
        expenses.append({"expense_date": f"{m}-20", "expense_category": "Marketing", "expense_amount": "2000.00"})
        expenses.append({"expense_date": f"{m}-25", "expense_category": "Maintenance", "expense_amount": "1500.00"})

    # Positive R4 Case: "Electricity" surge in 2026-08
    # 2026-07 was 4,000. In 2026-08: extra AC usage & commercial surcharge -> 6,400 (+60.0% increase > 50% -> Medium R4)
    # Remove standard 4,000 for Electricity in 2026-08 and replace with 6,400
    for exp in expenses:
        if exp["expense_category"] == "Electricity" and exp["expense_date"].startswith("2026-08"):
            exp["expense_amount"] = "6400.00"

    # Negative Control for R4: "Transport" in 2026-07
    # 2026-06 was 2,500. In 2026-07: 3,225 (+29.0% increase, threshold is > 30.0%) -> Must NOT alert!
    for exp in expenses:
        if exp["expense_category"] == "Transport" and exp["expense_date"].startswith("2026-07"):
            exp["expense_amount"] = "3225.00"

    # Write sample_expenses.csv
    exp_file = os.path.join(DATASETS_DIR, "sample_expenses.csv")
    with open(exp_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["expense_date", "expense_category", "expense_amount"])
        writer.writeheader()
        writer.writerows(expenses)

    # 4. Create expected_alerts.json manifest
    expected_alerts = [
        {
            "rule_code": "R1",
            "subject_name": "Imported Olive Oil 1L",
            "period_month": "2026-08",
            "severity": "Medium",
            "note": "Revenue 8000 < Cost 9500, loss 1500, margin -18.75%"
        },
        {
            "rule_code": "R2",
            "subject_name": "Refined Palm Oil 1L",
            "period_month": "2026-06",
            "severity": "Medium",
            "note": "Margin 4.55% (< 5% -> Medium)"
        },
        {
            "rule_code": "R2",
            "subject_name": "Gram Flour Besan 1kg",
            "period_month": "2026-07",
            "severity": "Low",
            "note": "Margin 7.37% (5% to 10% -> Low)"
        },
        {
            "rule_code": "R3",
            "subject_name": "Basmati Rice 1kg",
            "period_month": "2026-09",
            "severity": "Medium",
            "note": "Sales fell from 100 to 60 (-40.0%)"
        },
        {
            "rule_code": "R4",
            "subject_name": "Electricity",
            "period_month": "2026-08",
            "severity": "Medium",
            "note": "Expense rose from 4000 to 6400 (+60.0%)"
        },
        {
            "rule_code": "R5",
            "subject_name": "Organic Quinoa 500g",
            "period_month": "2026-07",
            "severity": "Medium",
            "note": "Inventory 90 vs 3-mo avg 20 (ratio 4.5x)"
        },
        {
            "rule_code": "R6",
            "subject_name": "Premium Basmati Rice 5kg",
            "period_month": "2026-09",
            "severity": "Medium",
            "note": "Margin drop from 50.0% to 23.08% = 26.92 points drop"
        }
    ]

    manifest_file = os.path.join(DATASETS_DIR, "expected_alerts.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(expected_alerts, f, indent=2)

    # 5. Generate invalid_examples for validation tests (Section 9)
    # 5.1 missing_column.csv
    with open(os.path.join(INVALID_DIR, "missing_column.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_date", "product_name", "quantity_sold", "selling_price"]) # missing sales_revenue, cost, inventory
        writer.writerow(["2026-08-10", "Rice 1kg", "10", "100.00"])

    # 5.2 bad_dates.csv (DD/MM/YYYY non-ISO)
    with open(os.path.join(INVALID_DIR, "bad_dates.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerow(["15/08/2026", "Rice 1kg", "10", "100.00", "0.00", "1000.00", "800.00", "50", "TX-BAD-DATE"])

    # 5.3 negative_values.csv
    with open(os.path.join(INVALID_DIR, "negative_values.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerow(["2026-08-10", "Rice 1kg", "-5.000", "100.00", "0.00", "-500.00", "400.00", "20", "TX-NEG"])

    # 5.4 non_numeric.csv
    with open(os.path.join(INVALID_DIR, "non_numeric.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerow(["2026-08-10", "Rice 1kg", "ten", "100.00", "0.00", "1000.00", "800.00", "50", "TX-NON-NUM"])

    # 5.5 duplicates.csv
    with open(os.path.join(INVALID_DIR, "duplicates.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerow(["2026-08-10", "Rice 1kg", "10", "100.00", "0.00", "1000.00", "800.00", "50", ""])
        writer.writerow(["2026-08-10", "Rice 1kg", "10", "100.00", "0.00", "1000.00", "800.00", "50", ""]) # exact duplicate

    # 5.6 revenue_mismatch.csv (qty * price - discount != sales_revenue)
    with open(os.path.join(INVALID_DIR, "revenue_mismatch.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerow(["2026-08-10", "Rice 1kg", "10", "100.00", "0.00", "750.00", "800.00", "50", "TX-REV-MISMATCH"])

    # 5.7 semicolon_bom.csv (Excel Windows delimiter & BOM)
    with open(os.path.join(INVALID_DIR, "semicolon_bom.csv"), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(fieldnames)
        writer.writerow(["2026-08-10", "Rice 1kg", "10", "100.00", "0.00", "1000.00", "800.00", "50", "TX-SEMI"])

    # 5.8 empty_file.csv
    with open(os.path.join(INVALID_DIR, "empty_file.csv"), "w", newline="", encoding="utf-8") as f:
        pass

    print("[generate_sample_data] Generated sample_transactions.csv, sample_expenses.csv, expected_alerts.json, and invalid_examples.")

if __name__ == "__main__":
    generate_sample_data()
