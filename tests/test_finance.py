"""
Unit tests for financial_analysis.py.
Verifies hand-calculated indicators, zero-revenue margin guards, and inventory snapshot logic.
"""
import pandas as pd
import pytest
from analytics.financial_analysis import (
    compute_overall_kpis, compute_monthly_trends, compute_product_performance
)

def test_hand_calculated_financial_kpis():
    # Tiny dataset with known numbers
    # Sale 1: Revenue 1,000, Cost 600
    # Sale 2: Revenue 2,000, Cost 1,400
    # Total Revenue = 3,000
    # Total Cost = 2,000
    # Gross Profit = 1,000, Gross Margin = 33.33%
    # Operating Expenses: Rent 500, Electricity 200 = 700
    # Net Profit = 1,000 - 700 = 300, Net Margin = 300 / 3,000 * 100 = 10.0%
    sales_data = [
        {"sales_revenue": 1000.0, "product_cost": 600.0, "quantity_sold": 10.0},
        {"sales_revenue": 2000.0, "product_cost": 1400.0, "quantity_sold": 20.0},
    ]
    sales_df = pd.DataFrame(sales_data)

    exp_data = [
        {"expense_amount": 500.0, "expense_category": "Rent"},
        {"expense_amount": 200.0, "expense_category": "Electricity"},
    ]
    exp_df = pd.DataFrame(exp_data)

    kpis = compute_overall_kpis(sales_df, exp_df)

    assert kpis["total_revenue"] == 3000.0
    assert kpis["total_product_cost"] == 2000.0
    assert kpis["gross_profit"] == 1000.0
    assert round(kpis["gross_margin"], 2) == 33.33
    assert kpis["operating_expenses"] == 700.0
    assert kpis["net_profit"] == 300.0
    assert round(kpis["net_margin"], 2) == 10.0

def test_zero_revenue_margin_is_none():
    # If revenue is 0, margin MUST be None (rendered as N/A, never 0.0 or ZeroDivisionError)
    sales_df = pd.DataFrame([{"sales_revenue": 0.0, "product_cost": 100.0, "quantity_sold": 5.0}])
    exp_df = pd.DataFrame([{"expense_amount": 50.0}])

    kpis = compute_overall_kpis(sales_df, exp_df)
    assert kpis["total_revenue"] == 0.0
    assert kpis["gross_margin"] is None
    assert kpis["net_margin"] is None

def test_inventory_snapshot_never_summed():
    # Product 'Rice' has 3 sales on different dates:
    # Day 1: inventory 50
    # Day 2: inventory 45
    # Day 3: inventory 30
    # The product's inventory MUST be 30 (the latest snapshot), NEVER 50+45+30=125!
    sales_data = [
        {"transaction_id": 1, "transaction_date": "2026-08-01", "product_name": "Rice", "quantity_sold": 5, "sales_revenue": 250, "product_cost": 200, "discount_amount": 0, "inventory_quantity": 50},
        {"transaction_id": 2, "transaction_date": "2026-08-05", "product_name": "Rice", "quantity_sold": 5, "sales_revenue": 250, "product_cost": 200, "discount_amount": 0, "inventory_quantity": 45},
        {"transaction_id": 3, "transaction_date": "2026-08-10", "product_name": "Rice", "quantity_sold": 15, "sales_revenue": 750, "product_cost": 600, "discount_amount": 0, "inventory_quantity": 30},
    ]
    df = pd.DataFrame(sales_data)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    perf = compute_product_performance(df)
    assert len(perf) == 1
    assert perf[0]["product_name"] == "Rice"
    assert perf[0]["latest_inventory"] == 30.0  # NOT 125!
    assert perf[0]["quantity_sold"] == 25.0
