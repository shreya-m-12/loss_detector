"""
Filtering module for sales, expenses, and alerts.
Maintains financial consistency and applies store-level vs product-level constraints.
"""
import pandas as pd
from datetime import datetime

def apply_dataframe_filters(sales_df: pd.DataFrame, expenses_df: pd.DataFrame, filters: dict):
    """
    Applies start_date, end_date, and product_name filters to sales and expenses DataFrames.
    Returns (filtered_sales_df, filtered_expenses_df, is_product_filtered).
    """
    filtered_sales = sales_df.copy() if sales_df is not None and not sales_df.empty else pd.DataFrame()
    filtered_expenses = expenses_df.copy() if expenses_df is not None and not expenses_df.empty else pd.DataFrame()
    is_product_filtered = False

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    product_name = filters.get("product_name")

    # Date range filters apply strictly to both
    if start_date:
        start_dt = pd.to_datetime(start_date)
        if not filtered_sales.empty:
            filtered_sales = filtered_sales[filtered_sales["transaction_date"] >= start_dt]
        if not filtered_expenses.empty:
            filtered_expenses = filtered_expenses[filtered_expenses["expense_date"] >= start_dt]

    if end_date:
        end_dt = pd.to_datetime(end_date)
        if not filtered_sales.empty:
            filtered_sales = filtered_sales[filtered_sales["transaction_date"] <= end_dt]
        if not filtered_expenses.empty:
            filtered_expenses = filtered_expenses[filtered_expenses["expense_date"] <= end_dt]

    # Product filter applies only to sales
    if product_name and product_name.strip() and product_name.lower() != "all":
        is_product_filtered = True
        if not filtered_sales.empty:
            filtered_sales = filtered_sales[filtered_sales["product_name"] == product_name.strip()]

    return filtered_sales, filtered_expenses, is_product_filtered

def filter_alerts(alerts_list: list, filters: dict) -> list:
    """
    Filters pre-computed alerts by severity, rule_code, month, product, and category.
    """
    if not alerts_list:
        return []

    result = alerts_list
    severity = filters.get("severity")
    rule_code = filters.get("rule_code")
    month = filters.get("month")
    product = filters.get("product")
    category = filters.get("category")

    if severity and severity != "All":
        result = [a for a in result if a.get("severity") == severity]

    if rule_code and rule_code != "All":
        result = [a for a in result if a.get("rule_code") == rule_code]

    if month and month != "All":
        result = [a for a in result if a.get("period_month") == month]

    if product and product != "All":
        result = [a for a in result if a.get("subject_type") == "product" and a.get("subject_name") == product]

    if category and category != "All":
        result = [a for a in result if a.get("category") == category]

    return result
