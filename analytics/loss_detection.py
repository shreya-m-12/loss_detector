"""
Rule-based loss detection engine.
Pure functions executing Section 5 rules on DataFrames with zero database dependency.
Guarded division, deterministic severity classification, and full transparency.
"""
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from config import Config
from analytics.recommendations import generate_recommendation

def evaluate_r1_loss_making(sales_df: pd.DataFrame, thresholds: dict) -> List[Dict[str, Any]]:
    """
    R1: Loss-making product
    Grain: product x month
    Condition: product_revenue - product_cost < 0
    Severity: margin <= -20% -> High; any other loss -> Medium
    """
    if sales_df is None or sales_df.empty:
        return []

    r1_th = thresholds.get("R1", Config.ANALYSIS_THRESHOLDS["R1"])
    high_margin_th = r1_th.get("high_severity_margin", -20.0)

    sdf = sales_df.copy()
    sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")

    grouped = sdf.groupby(["month", "product_name"]).agg(
        revenue=("sales_revenue", "sum"),
        cost=("product_cost", "sum"),
        quantity=("quantity_sold", "sum"),
    ).reset_index()

    alerts = []
    for _, row in grouped.iterrows():
        rev = float(row["revenue"])
        cost = float(row["cost"])
        loss = cost - rev

        if loss > 0.001:  # cost > revenue
            margin = ((rev - cost) / rev * 100.0) if rev > 0 else -100.0
            severity = "High" if margin <= high_margin_th else "Medium"

            trigger = {
                "revenue": round(rev, 2),
                "cost": round(cost, 2),
                "loss_amount": round(loss, 2),
                "margin": round(margin, 2) if rev > 0 else None,
                "quantity": round(float(row["quantity"]), 2),
            }
            expl, rec = generate_recommendation("R1", row["product_name"], row["month"], trigger, r1_th)

            alerts.append({
                "rule_code": "R1",
                "category": "Profitability",
                "subject_type": "product",
                "subject_name": row["product_name"],
                "period_month": row["month"],
                "severity": severity,
                "trigger_values": trigger,
                "threshold_json": r1_th,
                "explanation": expl,
                "recommendation": rec,
            })

    return alerts

def evaluate_r2_low_margin(sales_df: pd.DataFrame, thresholds: dict) -> List[Dict[str, Any]]:
    """
    R2: Low-margin product
    Grain: product x month
    Condition: 0 < margin < 10% (revenue > 0)
    Severity: margin < 5% -> Medium; 5% to 10% -> Low
    """
    if sales_df is None or sales_df.empty:
        return []

    r2_th = thresholds.get("R2", Config.ANALYSIS_THRESHOLDS["R2"])
    max_m = r2_th.get("max_margin", 10.0)
    med_th = r2_th.get("medium_severity_threshold", 5.0)

    sdf = sales_df.copy()
    sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")

    grouped = sdf.groupby(["month", "product_name"]).agg(
        revenue=("sales_revenue", "sum"),
        cost=("product_cost", "sum"),
        quantity=("quantity_sold", "sum"),
    ).reset_index()

    alerts = []
    for _, row in grouped.iterrows():
        rev = float(row["revenue"])
        cost = float(row["cost"])
        profit = rev - cost

        if rev > 0 and profit > 0:
            margin = (profit / rev * 100.0)
            # Boundary safeguard: exactly 10% does NOT trigger
            if 0.0 < margin < max_m:
                severity = "Medium" if margin < med_th else "Low"

                trigger = {
                    "revenue": round(rev, 2),
                    "cost": round(cost, 2),
                    "profit": round(profit, 2),
                    "margin": round(margin, 2),
                    "quantity": round(float(row["quantity"]), 2),
                }
                expl, rec = generate_recommendation("R2", row["product_name"], row["month"], trigger, r2_th)

                alerts.append({
                    "rule_code": "R2",
                    "category": "Profitability",
                    "subject_type": "product",
                    "subject_name": row["product_name"],
                    "period_month": row["month"],
                    "severity": severity,
                    "trigger_values": trigger,
                    "threshold_json": r2_th,
                    "explanation": expl,
                    "recommendation": rec,
                })

    return alerts

def evaluate_r3_declining_sales(sales_df: pd.DataFrame, thresholds: dict) -> List[Dict[str, Any]]:
    """
    R3: Declining sales
    Grain: product x month
    Condition: % change in quantity vs product's preceding month that HAS sales < -20%
    Safeguards: previous quantity >= MIN_PREV_QTY (default 10); no previous month -> no alert
    Severity: decline > 50% -> High; > 35% -> Medium; else Low
    """
    if sales_df is None or sales_df.empty:
        return []

    r3_th = thresholds.get("R3", Config.ANALYSIS_THRESHOLDS["R3"])
    th_pct = r3_th.get("threshold_pct", -20.0)
    min_prev_q = r3_th.get("min_prev_qty", 10.0)
    high_dec = r3_th.get("high_severity_decline", -50.0)
    med_dec = r3_th.get("medium_severity_decline", -35.0)

    sdf = sales_df.copy()
    sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")

    grouped = sdf.groupby(["product_name", "month"]).agg(
        quantity=("quantity_sold", "sum")
    ).reset_index()

    alerts = []
    # For each product, order by month and look at preceding available sales month
    for pname, pgroup in grouped.groupby("product_name"):
        pgroup_sorted = pgroup.sort_values(by="month").reset_index(drop=True)
        for i in range(1, len(pgroup_sorted)):
            prev_row = pgroup_sorted.iloc[i - 1]
            curr_row = pgroup_sorted.iloc[i]

            prev_q = float(prev_row["quantity"])
            curr_q = float(curr_row["quantity"])

            if prev_q >= min_prev_q and prev_q > 0:
                pct_change = ((curr_q - prev_q) / prev_q * 100.0)
                # Boundary safeguard: exactly -20.0% does NOT trigger
                if pct_change < th_pct:
                    # Severity: decline > 50% (pct_change < -50) -> High; > 35% -> Medium; else Low
                    if pct_change < high_dec:
                        severity = "High"
                    elif pct_change < med_dec:
                        severity = "Medium"
                    else:
                        severity = "Low"

                    trigger = {
                        "prev_month": prev_row["month"],
                        "prev_quantity": round(prev_q, 2),
                        "curr_quantity": round(curr_q, 2),
                        "pct_change": round(pct_change, 2),
                    }
                    expl, rec = generate_recommendation("R3", pname, curr_row["month"], trigger, r3_th)

                    alerts.append({
                        "rule_code": "R3",
                        "category": "Sales Volume",
                        "subject_type": "product",
                        "subject_name": pname,
                        "period_month": curr_row["month"],
                        "severity": severity,
                        "trigger_values": trigger,
                        "threshold_json": r3_th,
                        "explanation": expl,
                        "recommendation": rec,
                    })

    return alerts

def evaluate_r4_unusual_expense(expenses_df: pd.DataFrame, thresholds: dict) -> List[Dict[str, Any]]:
    """
    R4: Unusual expense increase
    Grain: category x month
    Condition: % increase vs preceding month with an expense in that category > 30%
    Safeguards: previous amount >= MIN_PREV_EXPENSE (default 1000) and > 0; no previous month -> no alert
    Severity: increase > 100% -> High; > 50% -> Medium; else Low
    """
    if expenses_df is None or expenses_df.empty:
        return []

    r4_th = thresholds.get("R4", Config.ANALYSIS_THRESHOLDS["R4"])
    th_pct = r4_th.get("threshold_pct", 30.0)
    min_prev_exp = r4_th.get("min_prev_expense", 1000.0)
    high_inc = r4_th.get("high_severity_increase", 100.0)
    med_inc = r4_th.get("medium_severity_increase", 50.0)

    edf = expenses_df.copy()
    edf["month"] = edf["expense_date"].dt.strftime("%Y-%m")

    grouped = edf.groupby(["expense_category", "month"]).agg(
        amount=("expense_amount", "sum")
    ).reset_index()

    alerts = []
    for cat, cgroup in grouped.groupby("expense_category"):
        cgroup_sorted = cgroup.sort_values(by="month").reset_index(drop=True)
        for i in range(1, len(cgroup_sorted)):
            prev_row = cgroup_sorted.iloc[i - 1]
            curr_row = cgroup_sorted.iloc[i]

            prev_amt = float(prev_row["amount"])
            curr_amt = float(curr_row["amount"])

            if prev_amt >= min_prev_exp and prev_amt > 0:
                pct_change = ((curr_amt - prev_amt) / prev_amt * 100.0)
                # Boundary safeguard: exactly +30.0% does NOT trigger
                if pct_change > th_pct:
                    if pct_change > high_inc:
                        severity = "High"
                    elif pct_change > med_inc:
                        severity = "Medium"
                    else:
                        severity = "Low"

                    trigger = {
                        "prev_month": prev_row["month"],
                        "prev_amount": round(prev_amt, 2),
                        "curr_amount": round(curr_amt, 2),
                        "pct_change": round(pct_change, 2),
                    }
                    expl, rec = generate_recommendation("R4", cat, curr_row["month"], trigger, r4_th)

                    alerts.append({
                        "rule_code": "R4",
                        "category": "Operating Expenses",
                        "subject_type": "expense_category",
                        "subject_name": cat,
                        "period_month": curr_row["month"],
                        "severity": severity,
                        "trigger_values": trigger,
                        "threshold_json": r4_th,
                        "explanation": expl,
                        "recommendation": rec,
                    })

    return alerts

def evaluate_r5_inventory_risk(sales_df: pd.DataFrame, thresholds: dict) -> List[Dict[str, Any]]:
    """
    R5: Inventory risk
    Grain: product, as of each month-end
    Condition: latest inventory snapshot at or before month-end > 3 x average monthly quantity sold
    Safeguards:
      - Require at least 3 months of sales history up to that month (MIN_HISTORY_MONTHS = 3)
      - Average = mean quantity over trailing 3 months that have sales (including current month)
      - Avg must be > 0.
      - Otherwise insufficient data, no alert.
    Severity: inventory >= 6x average -> High; >= 4x -> Medium; else Low
    """
    if sales_df is None or sales_df.empty:
        return []

    r5_th = thresholds.get("R5", Config.ANALYSIS_THRESHOLDS["R5"])
    mult_th = r5_th.get("multiple_threshold", 3.0)
    min_hist = r5_th.get("min_history_months", 3)
    high_mult = r5_th.get("high_severity_multiple", 6.0)
    med_mult = r5_th.get("medium_severity_multiple", 4.0)

    sdf = sales_df.copy()
    sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")

    # Group monthly quantities
    monthly_qty = sdf.groupby(["product_name", "month"]).agg(
        quantity=("quantity_sold", "sum")
    ).reset_index()

    # Sort sales transactions to get latest inventory snapshot up to each month
    sort_cols = ["transaction_date"]
    if "transaction_id" in sdf.columns:
        sort_cols.append("transaction_id")
    elif "line_number" in sdf.columns:
        sort_cols.append("line_number")
    sdf_sorted = sdf.sort_values(by=sort_cols, ascending=True)

    alerts = []
    for pname, pgroup in monthly_qty.groupby("product_name"):
        pgroup_sorted = pgroup.sort_values(by="month").reset_index(drop=True)
        # We need at least min_hist months of sales history
        for i in range(len(pgroup_sorted)):
            curr_month = pgroup_sorted.iloc[i]["month"]
            # Available history up to and including current month
            history_slice = pgroup_sorted.iloc[:i + 1]

            if len(history_slice) < min_hist:
                # Insufficient history -> no alert
                continue

            # Trailing 3 months of sales
            trailing_3 = history_slice.iloc[-3:]
            avg_qty = float(trailing_3["quantity"].mean())

            if avg_qty <= 0:
                continue

            # Find latest inventory snapshot for product on or before the end of curr_month
            month_txs = sdf_sorted[
                (sdf_sorted["product_name"] == pname) &
                (sdf_sorted["month"] <= curr_month)
            ]
            if month_txs.empty:
                continue

            latest_snapshot = float(month_txs.iloc[-1]["inventory_quantity"])
            ratio = latest_snapshot / avg_qty

            # Boundary safeguard: exactly 3.0x does NOT trigger
            if ratio > mult_th:
                if ratio >= high_mult:
                    severity = "High"
                elif ratio >= med_mult:
                    severity = "Medium"
                else:
                    severity = "Low"

                trigger = {
                    "inventory_snapshot": round(latest_snapshot, 2),
                    "avg_monthly_sales": round(avg_qty, 2),
                    "ratio": round(ratio, 2),
                    "history_months_used": len(trailing_3),
                }
                expl, rec = generate_recommendation("R5", pname, curr_month, trigger, r5_th)

                alerts.append({
                    "rule_code": "R5",
                    "category": "Inventory Management",
                    "subject_type": "product",
                    "subject_name": pname,
                    "period_month": curr_month,
                    "severity": severity,
                    "trigger_values": trigger,
                    "threshold_json": r5_th,
                    "explanation": expl,
                    "recommendation": rec,
                })

    return alerts

def evaluate_r6_discount_risk(sales_df: pd.DataFrame, thresholds: dict) -> List[Dict[str, Any]]:
    """
    R6: Discount margin risk
    Grain: product x month
    Condition: margin_before - margin_after > 15 percentage points
    Definitions:
      - revenue_before = sum(quantity_sold * selling_price)
      - margin_before = ((revenue_before - product_cost) / revenue_before) * 100
      - revenue_after = sum(sales_revenue)
      - margin_after = ((revenue_after - product_cost) / revenue_after) * 100
    Safeguards:
      - skip if revenue_before = 0 or total discount = 0
      - if revenue_after = 0 with discount > 0, raise HIGH alert with margin_after shown as None / N/A
    Severity: impact > 30 points -> High; > 20 -> Medium; else Low
    """
    if sales_df is None or sales_df.empty:
        return []

    r6_th = thresholds.get("R6", Config.ANALYSIS_THRESHOLDS["R6"])
    th_drop = r6_th.get("drop_threshold_points", 15.0)
    high_drop = r6_th.get("high_severity_drop", 30.0)
    med_drop = r6_th.get("medium_severity_drop", 20.0)

    sdf = sales_df.copy()
    sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")
    sdf["rev_before"] = sdf["quantity_sold"] * sdf["selling_price"]

    grouped = sdf.groupby(["month", "product_name"]).agg(
        rev_before=("rev_before", "sum"),
        rev_after=("sales_revenue", "sum"),
        cost=("product_cost", "sum"),
        discount=("discount_amount", "sum"),
    ).reset_index()

    alerts = []
    for _, row in grouped.iterrows():
        rev_b = float(row["rev_before"])
        rev_a = float(row["rev_after"])
        cost = float(row["cost"])
        disc = float(row["discount"])

        # Skip if revenue_before = 0 or total discount = 0
        if rev_b <= 0 or disc <= 0.001:
            continue

        margin_b = ((rev_b - cost) / rev_b * 100.0)

        if rev_a <= 0 and disc > 0:
            # 100% discount / free items
            trigger = {
                "margin_before": round(margin_b, 2),
                "margin_after": None,
                "drop_points": 100.0,
                "discount_amount": round(disc, 2),
                "revenue_before": round(rev_b, 2),
                "revenue_after": round(rev_a, 2),
                "product_cost": round(cost, 2),
            }
            expl, rec = generate_recommendation("R6", row["product_name"], row["month"], trigger, r6_th)
            alerts.append({
                "rule_code": "R6",
                "category": "Pricing & Discounts",
                "subject_type": "product",
                "subject_name": row["product_name"],
                "period_month": row["month"],
                "severity": "High",
                "trigger_values": trigger,
                "threshold_json": r6_th,
                "explanation": expl,
                "recommendation": rec,
            })
            continue

        margin_a = ((rev_a - cost) / rev_a * 100.0)
        drop = margin_b - margin_a

        # Boundary safeguard: exactly 15.0 points does NOT trigger
        if drop > th_drop:
            if drop > high_drop:
                severity = "High"
            elif drop > med_drop:
                severity = "Medium"
            else:
                severity = "Low"

            trigger = {
                "margin_before": round(margin_b, 2),
                "margin_after": round(margin_a, 2),
                "drop_points": round(drop, 2),
                "discount_amount": round(disc, 2),
                "revenue_before": round(rev_b, 2),
                "revenue_after": round(rev_a, 2),
                "product_cost": round(cost, 2),
            }
            expl, rec = generate_recommendation("R6", row["product_name"], row["month"], trigger, r6_th)

            alerts.append({
                "rule_code": "R6",
                "category": "Pricing & Discounts",
                "subject_type": "product",
                "subject_name": row["product_name"],
                "period_month": row["month"],
                "severity": severity,
                "trigger_values": trigger,
                "threshold_json": r6_th,
                "explanation": expl,
                "recommendation": rec,
            })

    return alerts

def run_all_detection_rules(sales_df: pd.DataFrame, expenses_df: pd.DataFrame, thresholds: dict = None) -> List[Dict[str, Any]]:
    """
    Executes all six detection rules and returns deduplicated alerts list.
    Deduplication key: (rule_code, subject_name, period_month)
    """
    th = thresholds or Config.ANALYSIS_THRESHOLDS
    all_alerts = []

    all_alerts.extend(evaluate_r1_loss_making(sales_df, th))
    all_alerts.extend(evaluate_r2_low_margin(sales_df, th))
    all_alerts.extend(evaluate_r3_declining_sales(sales_df, th))
    all_alerts.extend(evaluate_r4_unusual_expense(expenses_df, th))
    all_alerts.extend(evaluate_r5_inventory_risk(sales_df, th))
    all_alerts.extend(evaluate_r6_discount_risk(sales_df, th))

    # Deduplicate deterministically
    seen = set()
    deduped = []
    for alert in all_alerts:
        key = (alert["rule_code"], alert["subject_name"], alert["period_month"])
        if key not in seen:
            seen.add(key)
            deduped.append(alert)

    # Sort: High -> Medium -> Low, then period_month desc, then rule_code asc
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    deduped.sort(key=lambda a: (severity_order.get(a["severity"], 3), a["period_month"], a["rule_code"]), reverse=False)

    return deduped
