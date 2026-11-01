"""
Dashboard routes and interactive JSON filter endpoints for Business Loss Detection System.
Serves 6 KPI cards, 6 Chart.js data streams, product rankings, and alert summaries.
"""
from flask import Blueprint, render_template, request, jsonify
import pandas as pd
from database.operations import (
    get_active_dataset, load_sales_dataframe, load_expenses_dataframe,
    get_alerts_for_dataset
)
from analytics.financial_analysis import (
    compute_overall_kpis, compute_monthly_trends, compute_product_performance,
    compute_expense_distribution
)
from analytics.filters import apply_dataframe_filters, filter_alerts

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def index():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return render_template("dashboard.html", active_dataset=None)

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)
    alerts_list = get_alerts_for_dataset(dataset_id)

    # Compute baseline metrics
    kpis = compute_overall_kpis(sales_df, expenses_df)
    monthly_trends = compute_monthly_trends(sales_df, expenses_df)
    products_perf = compute_product_performance(sales_df, alerts_list)
    expense_dist = compute_expense_distribution(expenses_df)

    # Available filter dropdown options
    products_list = sorted(list(set(sales_df["product_name"].tolist()))) if not sales_df.empty else []
    categories_list = sorted(list(set(expenses_df["expense_category"].tolist()))) if not expenses_df.empty else []
    months_list = [m["month"] for m in monthly_trends]

    # Alert severity counts
    alert_counts = {
        "High": sum(1 for a in alerts_list if a["severity"] == "High"),
        "Medium": sum(1 for a in alerts_list if a["severity"] == "Medium"),
        "Low": sum(1 for a in alerts_list if a["severity"] == "Low"),
        "Total": len(alerts_list),
    }

    return render_template(
        "dashboard.html",
        active_dataset=active_dataset,
        kpis=kpis,
        monthly_trends=monthly_trends,
        products_perf=products_perf,
        expense_dist=expense_dist,
        alerts_list=alerts_list[:5],  # Top 5 priority alerts on dashboard
        alert_counts=alert_counts,
        products_list=products_list,
        categories_list=categories_list,
        months_list=months_list,
    )

@dashboard_bp.route("/api/dashboard-data")
def api_dashboard_data():
    """
    Server-side JSON filtering endpoint.
    Recalculates KPIs, charts, and product table dynamically based on user filters.
    """
    active_dataset = get_active_dataset()
    if not active_dataset:
        return jsonify({"error": "No active dataset"}), 404

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)
    alerts_list = get_alerts_for_dataset(dataset_id)

    # Extract query params
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    product_name = request.args.get("product_name")

    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "product_name": product_name,
    }

    # Apply filters with strict product-level semantics
    f_sales, f_expenses, is_product_filtered = apply_dataframe_filters(sales_df, expenses_df, filters)

    kpis = compute_overall_kpis(f_sales, f_expenses, is_product_filtered=is_product_filtered)
    monthly_trends = compute_monthly_trends(f_sales, f_expenses)
    products_perf = compute_product_performance(f_sales, alerts_list)
    expense_dist = compute_expense_distribution(f_expenses)

    # Filter alerts list for display
    alert_filters = {}
    if product_name and product_name != "All":
        alert_filters["product"] = product_name
    filtered_alerts = filter_alerts(alerts_list, alert_filters)

    alert_counts = {
        "High": sum(1 for a in filtered_alerts if a["severity"] == "High"),
        "Medium": sum(1 for a in filtered_alerts if a["severity"] == "Medium"),
        "Low": sum(1 for a in filtered_alerts if a["severity"] == "Low"),
        "Total": len(filtered_alerts),
    }

    # Chart 1: Monthly Revenue vs Expenses
    chart_rev_vs_exp = {
        "labels": [m["month"] for m in monthly_trends],
        "revenue": [m["revenue"] for m in monthly_trends],
        "costs_expenses": [
            round(m["product_cost"] + (m["operating_expenses"] if not is_product_filtered else 0.0), 2)
            for m in monthly_trends
        ],
    }

    # Chart 2: Monthly Profit Trend
    chart_profit_trend = {
        "labels": [m["month"] for m in monthly_trends],
        "gross_profit": [m["gross_profit"] for m in monthly_trends],
        "net_profit": [m["net_profit"] if not is_product_filtered else None for m in monthly_trends],
    }

    # Chart 3: Product Profitability (Top 8 items)
    top_prods = products_perf[:8]
    chart_prod_profit = {
        "labels": [p["product_name"] for p in top_prods],
        "gross_profit": [p["gross_profit"] for p in top_prods],
        "revenue": [p["sales_revenue"] for p in top_prods],
    }

    # Chart 4: Expense Distribution
    chart_expense_pie = {
        "labels": [e["category"] for e in expense_dist],
        "amounts": [e["amount"] for e in expense_dist],
    }

    # Chart 5: Monthly Sales Quantity
    chart_qty_trend = {
        "labels": [m["month"] for m in monthly_trends],
        "quantity": [m["quantity_sold"] for m in monthly_trends],
    }

    # Chart 6: Discount Impact
    chart_discount_impact = {
        "labels": [m["month"] for m in monthly_trends],
        "discount_amount": [m["discount_amount"] for m in monthly_trends],
        "revenue": [m["revenue"] for m in monthly_trends],
    }

    return jsonify({
        "success": True,
        "kpis": kpis,
        "is_product_filtered": is_product_filtered,
        "charts": {
            "rev_vs_exp": chart_rev_vs_exp,
            "profit_trend": chart_profit_trend,
            "product_profit": chart_prod_profit,
            "expense_pie": chart_expense_pie,
            "qty_trend": chart_qty_trend,
            "discount_impact": chart_discount_impact,
        },
        "products_perf": products_perf,
        "alerts": filtered_alerts[:5],
        "alert_counts": alert_counts,
    })
