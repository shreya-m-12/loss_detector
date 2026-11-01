"""
Financial Analysis and Product Analysis routes for Business Loss Detection System.
Provides deep-dive analytical tables, monthly breakdowns, margins, and SKU inventory audits.
"""
from flask import Blueprint, render_template, request
from database.operations import (
    get_active_dataset, load_sales_dataframe, load_expenses_dataframe, get_alerts_for_dataset
)
from analytics.financial_analysis import (
    compute_overall_kpis, compute_monthly_trends, compute_product_performance,
    compute_expense_distribution
)
from analytics.filters import apply_dataframe_filters

analysis_bp = Blueprint("analysis", __name__)

@analysis_bp.route("/financial-analysis")
def financial_analysis():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return render_template("financial_analysis.html", active_dataset=None)

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    filters = {"start_date": start_date, "end_date": end_date}

    f_sales, f_expenses, _ = apply_dataframe_filters(sales_df, expenses_df, filters)

    kpis = compute_overall_kpis(f_sales, f_expenses)
    monthly_trends = compute_monthly_trends(f_sales, f_expenses)
    expense_dist = compute_expense_distribution(f_expenses)

    return render_template(
        "financial_analysis.html",
        active_dataset=active_dataset,
        kpis=kpis,
        monthly_trends=monthly_trends,
        expense_dist=expense_dist,
        start_date=start_date or "",
        end_date=end_date or "",
    )

@analysis_bp.route("/product-analysis")
def product_analysis():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return render_template("product_analysis.html", active_dataset=None)

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)
    alerts_list = get_alerts_for_dataset(dataset_id)

    selected_product = request.args.get("product_name", "").strip()
    filters = {"product_name": selected_product} if selected_product and selected_product != "All" else {}

    f_sales, _, is_filtered = apply_dataframe_filters(sales_df, expenses_df, filters)
    products_perf = compute_product_performance(f_sales, alerts_list)
    all_products = sorted(list(set(sales_df["product_name"].tolist()))) if not sales_df.empty else []

    # Single product historical drilldown if filtered
    prod_history = []
    if is_filtered and not f_sales.empty:
        sdf = f_sales.copy()
        sdf["month"] = sdf["transaction_date"].dt.strftime("%Y-%m")
        grouped = sdf.groupby("month").agg(
            quantity=("quantity_sold", "sum"),
            revenue=("sales_revenue", "sum"),
            cost=("product_cost", "sum"),
            discount=("discount_amount", "sum"),
        ).reset_index()
        for _, row in grouped.iterrows():
            rev = float(row["revenue"])
            cost = float(row["cost"])
            profit = rev - cost
            m = (profit / rev * 100.0) if rev > 0 else None
            prod_history.append({
                "month": row["month"],
                "quantity": float(row["quantity"]),
                "revenue": rev,
                "cost": cost,
                "profit": profit,
                "margin": m,
                "discount": float(row["discount"]),
            })
        prod_history.sort(key=lambda x: x["month"])

    return render_template(
        "product_analysis.html",
        active_dataset=active_dataset,
        products_perf=products_perf,
        all_products=all_products,
        selected_product=selected_product,
        prod_history=prod_history,
    )
