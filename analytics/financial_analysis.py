"""
Financial analysis engine computing retail KPIs, monthly trends, product performance,
and expense distribution. Strictly implements Section 2.3 financial definitions.
"""
from decimal import Decimal
import pandas as pd
import numpy as np

def compute_overall_kpis(sales_df: pd.DataFrame, expenses_df: pd.DataFrame, is_product_filtered: bool = False) -> dict:
    """
    Computes business-level financial indicators:
    - Revenue = sum(sales_revenue)
    - Product Cost = sum(product_cost)
    - Gross Profit = Revenue - Product Cost
    - Operating Expenses = sum(expense_amount)
    - Net Profit = Gross Profit - Operating Expenses
    - Margins: profit / revenue * 100 (or None if revenue <= 0)
    """
    if sales_df is None or sales_df.empty:
        total_revenue = 0.0
        total_product_cost = 0.0
        total_qty = 0.0
    else:
        total_revenue = float(sales_df["sales_revenue"].sum())
        total_product_cost = float(sales_df["product_cost"].sum())
        total_qty = float(sales_df["quantity_sold"].sum())

    gross_profit = total_revenue - total_product_cost
    gross_margin = (gross_profit / total_revenue * 100.0) if total_revenue > 0 else None

    if is_product_filtered:
        # Expenses are store-wide, not allocated to individual products
        return {
            "total_revenue": total_revenue,
            "total_product_cost": total_product_cost,
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
            "operating_expenses": None,
            "net_profit": None,
            "net_margin": None,
            "total_quantity": total_qty,
            "is_product_filtered": True,
            "note": "Expenses and Net Profit are business-level and not allocated to individual products."
        }

    if expenses_df is None or expenses_df.empty:
        total_expenses = 0.0
    else:
        total_expenses = float(expenses_df["expense_amount"].sum())

    net_profit = gross_profit - total_expenses
    net_margin = (net_profit / total_revenue * 100.0) if total_revenue > 0 else None

    return {
        "total_revenue": total_revenue,
        "total_product_cost": total_product_cost,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        "operating_expenses": total_expenses,
        "net_profit": net_profit,
        "net_margin": net_margin,
        "total_quantity": total_qty,
        "is_product_filtered": False,
    }

def compute_monthly_trends(sales_df: pd.DataFrame, expenses_df: pd.DataFrame) -> list:
    """
    Aggregates financial indicators by calendar month (YYYY-MM).
    Calculates revenue, product cost, gross profit, operating expenses, net profit, and net margin.
    """
    all_months = set()

    sales_m = pd.DataFrame()
    if sales_df is not None and not sales_df.empty:
        sdf = sales_df.copy()
        sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")
        sales_m = sdf.groupby("month").agg(
            revenue=("sales_revenue", "sum"),
            product_cost=("product_cost", "sum"),
            quantity=("quantity_sold", "sum"),
            discount=("discount_amount", "sum"),
        ).reset_index()
        all_months.update(sales_m["month"].tolist())

    exp_m = pd.DataFrame()
    if expenses_df is not None and not expenses_df.empty:
        edf = expenses_df.copy()
        edf["month"] = edf["expense_date"].dt.strftime("%Y-%m")
        exp_m = edf.groupby("month").agg(
            operating_expenses=("expense_amount", "sum")
        ).reset_index()
        all_months.update(exp_m["month"].tolist())

    if not all_months:
        return []

    sorted_months = sorted(list(all_months))
    records = []

    s_lookup = {row["month"]: row for _, row in sales_m.iterrows()} if not sales_m.empty else {}
    e_lookup = {row["month"]: row for _, row in exp_m.iterrows()} if not exp_m.empty else {}

    for m in sorted_months:
        s_row = s_lookup.get(m, {})
        e_row = e_lookup.get(m, {})

        rev = float(s_row.get("revenue", 0.0))
        pcost = float(s_row.get("product_cost", 0.0))
        qty = float(s_row.get("quantity", 0.0))
        disc = float(s_row.get("discount", 0.0))
        exp = float(e_row.get("operating_expenses", 0.0))

        gross = rev - pcost
        net = gross - exp
        net_m = (net / rev * 100.0) if rev > 0 else None
        gross_m = (gross / rev * 100.0) if rev > 0 else None

        records.append({
            "month": m,
            "revenue": round(rev, 2),
            "product_cost": round(pcost, 2),
            "gross_profit": round(gross, 2),
            "gross_margin": round(gross_m, 2) if gross_m is not None else None,
            "operating_expenses": round(exp, 2),
            "net_profit": round(net, 2),
            "net_margin": round(net_m, 2) if net_m is not None else None,
            "quantity_sold": round(qty, 2),
            "discount_amount": round(disc, 2),
        })

    return records

def compute_product_performance(sales_df: pd.DataFrame, alerts_list: list = None) -> list:
    """
    Computes performance summary per product:
    - Quantity sold
    - Sales revenue
    - Product cost
    - Gross profit & margin
    - Latest inventory snapshot (latest transaction date, break ties by transaction_id)
    - Associated active alert tags
    """
    if sales_df is None or sales_df.empty:
        return []

    # Map alerts by product name
    prod_alerts = {}
    if alerts_list:
        for a in alerts_list:
            if a.get("subject_type") == "product":
                pname = a.get("subject_name")
                prod_alerts.setdefault(pname, []).append(a)

    # Calculate latest inventory snapshot per product (NEVER sum inventory)
    sort_cols = ["transaction_date"]
    if "transaction_id" in sales_df.columns:
        sort_cols.append("transaction_id")
    elif "line_number" in sales_df.columns:
        sort_cols.append("line_number")
    sorted_df = sales_df.sort_values(by=sort_cols, ascending=True)
    latest_inv = sorted_df.groupby("product_name").last()[["inventory_quantity"]].to_dict()["inventory_quantity"]

    grouped = sales_df.groupby("product_name").agg(
        quantity_sold=("quantity_sold", "sum"),
        sales_revenue=("sales_revenue", "sum"),
        product_cost=("product_cost", "sum"),
        discount_amount=("discount_amount", "sum"),
        tx_count=("transaction_id", "count"),
    ).reset_index()

    products_out = []
    for _, row in grouped.iterrows():
        pname = row["product_name"]
        qty = float(row["quantity_sold"])
        rev = float(row["sales_revenue"])
        cost = float(row["product_cost"])
        disc = float(row["discount_amount"])
        gross = rev - cost
        margin = (gross / rev * 100.0) if rev > 0 else None
        avg_price = (rev / qty) if qty > 0 else 0.0
        inv_qty = float(latest_inv.get(pname, 0.0))

        # Risk status determination
        alerts = prod_alerts.get(pname, [])
        severities = [a["severity"] for a in alerts]
        if "High" in severities:
            risk_status = "High Risk"
        elif "Medium" in severities:
            risk_status = "Medium Risk"
        elif "Low" in severities:
            risk_status = "Low Risk"
        else:
            risk_status = "Healthy"

        products_out.append({
            "product_name": pname,
            "quantity_sold": round(qty, 2),
            "average_selling_price": round(avg_price, 2),
            "sales_revenue": round(rev, 2),
            "product_cost": round(cost, 2),
            "discount_amount": round(disc, 2),
            "gross_profit": round(gross, 2),
            "gross_margin": round(margin, 2) if margin is not None else None,
            "latest_inventory": round(inv_qty, 2),
            "risk_status": risk_status,
            "alert_count": len(alerts),
            "alerts": alerts,
        })

    # Sort descending by revenue
    products_out.sort(key=lambda x: x["sales_revenue"], reverse=True)
    return products_out

def compute_expense_distribution(expenses_df: pd.DataFrame) -> list:
    """
    Computes breakdown of operating expenses by category:
    Total amount and percentage of total expenses.
    """
    if expenses_df is None or expenses_df.empty:
        return []

    total_exp = float(expenses_df["expense_amount"].sum())
    grouped = expenses_df.groupby("expense_category")["expense_amount"].sum().reset_index()

    records = []
    for _, row in grouped.iterrows():
        cat = row["expense_category"]
        amt = float(row["expense_amount"])
        pct = (amt / total_exp * 100.0) if total_exp > 0 else 0.0
        records.append({
            "category": cat,
            "amount": round(amt, 2),
            "percentage": round(pct, 2)
        })

    records.sort(key=lambda x: x["amount"], reverse=True)
    return records
