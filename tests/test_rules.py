"""
Unit tests for loss_detection.py module.
Verifies all 6 detection rules, strict negative control boundaries, edge cases, and sample dataset parity.
"""
import json
import os
import pandas as pd
import pytest
from analytics.loss_detection import (
    evaluate_r1_loss_making, evaluate_r2_low_margin, evaluate_r3_declining_sales,
    evaluate_r4_unusual_expense, evaluate_r5_inventory_risk, evaluate_r6_discount_risk,
    run_all_detection_rules
)
from analytics.data_validation import validate_transactions_csv, validate_expenses_csv
from config import Config

def test_r1_loss_making_rule():
    # Cost (1200) > Revenue (1000) -> Loss of 200, Margin = -20% -> High severity
    df = pd.DataFrame([{
        "transaction_date": pd.to_datetime("2026-08-10"),
        "product_name": "Costly Oil",
        "sales_revenue": 1000.0,
        "product_cost": 1200.0,
        "quantity_sold": 10.0,
    }])
    alerts = evaluate_r1_loss_making(df, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts) == 1
    assert alerts[0]["rule_code"] == "R1"
    assert alerts[0]["severity"] == "High"
    assert alerts[0]["trigger_values"]["loss_amount"] == 200.0

def test_r2_boundary_negative_control():
    # Boundary test: Margin exactly 10.0% MUST NOT alert (threshold is < 10%)
    df = pd.DataFrame([{
        "transaction_date": pd.to_datetime("2026-08-10"),
        "product_name": "Mustard Oil",
        "sales_revenue": 1000.0,
        "product_cost": 900.0,  # Profit = 100, Margin = 100/1000 = 10.0%
        "quantity_sold": 10.0,
    }])
    alerts = evaluate_r2_low_margin(df, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts) == 0

def test_r3_boundary_negative_control():
    # Boundary test: decline exactly -19.0% MUST NOT alert (threshold is < -20.0%)
    df = pd.DataFrame([
        {"transaction_date": pd.to_datetime("2026-07-15"), "product_name": "Moong Dal", "quantity_sold": 100.0},
        {"transaction_date": pd.to_datetime("2026-08-15"), "product_name": "Moong Dal", "quantity_sold": 81.0},
    ])
    alerts = evaluate_r3_declining_sales(df, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts) == 0

def test_r4_boundary_negative_control():
    # Boundary test: increase exactly +29.0% MUST NOT alert (threshold is > 30.0%)
    df = pd.DataFrame([
        {"expense_date": pd.to_datetime("2026-06-15"), "expense_category": "Transport", "expense_amount": 1000.0},
        {"expense_date": pd.to_datetime("2026-07-15"), "expense_category": "Transport", "expense_amount": 1290.0},
    ])
    alerts = evaluate_r4_unusual_expense(df, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts) == 0

def test_r5_boundary_and_insufficient_history():
    # Product with only 2 months of history -> MUST NOT alert (requires >= 3 months)
    df_short = pd.DataFrame([
        {"transaction_id": 1, "transaction_date": pd.to_datetime("2026-08-15"), "product_name": "Honey", "quantity_sold": 10.0, "inventory_quantity": 100.0},
        {"transaction_id": 2, "transaction_date": pd.to_datetime("2026-09-15"), "product_name": "Honey", "quantity_sold": 10.0, "inventory_quantity": 100.0},
    ])
    alerts = evaluate_r5_inventory_risk(df_short, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts) == 0

    # Boundary test: exactly 3.0x ratio MUST NOT alert (threshold is > 3.0x)
    df_boundary = pd.DataFrame([
        {"transaction_id": 1, "transaction_date": pd.to_datetime("2026-05-15"), "product_name": "Jeera", "quantity_sold": 10.0, "inventory_quantity": 30.0},
        {"transaction_id": 2, "transaction_date": pd.to_datetime("2026-06-15"), "product_name": "Jeera", "quantity_sold": 10.0, "inventory_quantity": 30.0},
        {"transaction_id": 3, "transaction_date": pd.to_datetime("2026-07-15"), "product_name": "Jeera", "quantity_sold": 10.0, "inventory_quantity": 30.0},
    ])
    alerts_b = evaluate_r5_inventory_risk(df_boundary, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts_b) == 0

def test_r6_discount_risk_rule():
    # Selling price 100, cost 50 (margin before 50%). Discount 30, revenue 70, cost 50.
    # Margin after = (70-50)/70 = 28.57%. Drop = 50 - 28.57 = 21.43 points (> 15 points -> Medium)
    df = pd.DataFrame([{
        "transaction_date": pd.to_datetime("2026-08-10"),
        "product_name": "Discounted Biscuit",
        "quantity_sold": 10.0,
        "selling_price": 100.0,
        "discount_amount": 300.0,
        "sales_revenue": 700.0,
        "product_cost": 500.0,
    }])
    alerts = evaluate_r6_discount_risk(df, Config.ANALYSIS_THRESHOLDS)
    assert len(alerts) == 1
    assert alerts[0]["rule_code"] == "R6"
    assert alerts[0]["severity"] == "Medium"

def test_sample_dataset_matches_expected_manifest():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sales_path = os.path.join(base_dir, "datasets", "sample_transactions.csv")
    exp_path = os.path.join(base_dir, "datasets", "sample_expenses.csv")
    expected_path = os.path.join(base_dir, "datasets", "expected_alerts.json")

    with open(sales_path, "rb") as f:
        s_val = validate_transactions_csv(f.read())
    with open(exp_path, "rb") as f:
        e_val = validate_expenses_csv(f.read())

    sdf = pd.DataFrame(s_val["accepted_rows"])
    sdf["transaction_date"] = pd.to_datetime(sdf["transaction_date"])
    edf = pd.DataFrame(e_val["accepted_rows"])
    edf["expense_date"] = pd.to_datetime(edf["expense_date"])

    alerts = run_all_detection_rules(sdf, edf)

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    gen_tuples = {(a["rule_code"], a["subject_name"], a["period_month"], a["severity"]) for a in alerts}
    exp_tuples = {(e["rule_code"], e["subject_name"], e["period_month"], e["severity"]) for e in expected}

    assert gen_tuples == exp_tuples
