"""
Reports and Export routes for Business Loss Detection System.
Serves HTML executive report, downloadable ReportLab PDF, and formula-neutralized CSV exports.
"""
from datetime import datetime
from flask import Blueprint, render_template, Response, flash, redirect, url_for
from database.operations import (
    get_active_dataset, load_sales_dataframe, load_expenses_dataframe,
    get_alerts_for_dataset, store_analysis_report
)
from analytics.financial_analysis import (
    compute_overall_kpis, compute_monthly_trends, compute_product_performance,
    compute_expense_distribution
)
from services.exports import generate_csv_string
from services.report_pdf import build_pdf_report
from config import Config

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

@reports_bp.route("/")
def index():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return render_template("reports.html", active_dataset=None)

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)
    alerts_list = get_alerts_for_dataset(dataset_id)

    kpis = compute_overall_kpis(sales_df, expenses_df)
    monthly_trends = compute_monthly_trends(sales_df, expenses_df)
    products_perf = compute_product_performance(sales_df, alerts_list)
    expense_dist = compute_expense_distribution(expenses_df)

    # Save audit record in analysis_reports
    report_summary = {
        "business_id": active_dataset.get("business_id", 1),
        "period_start": active_dataset.get("date_min"),
        "period_end": active_dataset.get("date_max"),
        "total_revenue": kpis["total_revenue"],
        "total_product_cost": kpis["total_product_cost"],
        "total_expenses": kpis["operating_expenses"] or 0.0,
        "gross_profit": kpis["gross_profit"],
        "net_profit": kpis["net_profit"] or 0.0,
    }
    store_analysis_report(dataset_id, report_summary, alerts_list)

    return render_template(
        "reports.html",
        active_dataset=active_dataset,
        kpis=kpis,
        monthly_trends=monthly_trends,
        products_perf=products_perf,
        expense_dist=expense_dist,
        alerts_list=alerts_list,
        thresholds=Config.ANALYSIS_THRESHOLDS,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

@reports_bp.route("/download-pdf")
def download_pdf():
    active_dataset = get_active_dataset()
    if not active_dataset:
        flash("No active dataset found to generate PDF report.", "error")
        return redirect(url_for("reports.index"))

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)
    alerts_list = get_alerts_for_dataset(dataset_id)

    kpis = compute_overall_kpis(sales_df, expenses_df)
    monthly_trends = compute_monthly_trends(sales_df, expenses_df)
    products_perf = compute_product_performance(sales_df, alerts_list)
    expense_dist = compute_expense_distribution(expenses_df)

    pdf_bytes = build_pdf_report(
        business_name="Corner Store Mart",
        dataset_info=active_dataset,
        kpis=kpis,
        monthly_trends=monthly_trends,
        product_performance=products_perf,
        expense_dist=expense_dist,
        alerts_list=alerts_list,
    )

    filename = f"Loss_Detection_Report_Dataset_{dataset_id}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@reports_bp.route("/export/products-csv")
def export_products_csv():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return "No active dataset", 404

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    alerts_list = get_alerts_for_dataset(dataset_id)
    products_perf = compute_product_performance(sales_df, alerts_list)

    headers = [
        "Product Name", "Quantity Sold", "Avg Selling Price (INR)",
        "Sales Revenue (INR)", "Product Cost (INR)", "Gross Profit (INR)",
        "Gross Margin (%)", "Latest Inventory Snapshot", "Risk Status"
    ]
    rows = []
    for p in products_perf:
        m_val = f"{p['gross_margin']:.2f}" if p['gross_margin'] is not None else "N/A"
        rows.append([
            p["product_name"],
            p["quantity_sold"],
            p["average_selling_price"],
            p["sales_revenue"],
            p["product_cost"],
            p["gross_profit"],
            m_val,
            p["latest_inventory"],
            p["risk_status"],
        ])

    csv_data = generate_csv_string(headers, rows)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=product_performance_report.csv"}
    )

@reports_bp.route("/export/monthly-csv")
def export_monthly_csv():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return "No active dataset", 404

    dataset_id = active_dataset["dataset_id"]
    sales_df = load_sales_dataframe(dataset_id)
    expenses_df = load_expenses_dataframe(dataset_id)
    monthly_trends = compute_monthly_trends(sales_df, expenses_df)

    headers = [
        "Month (YYYY-MM)", "Revenue (INR)", "Product Cost (INR)", "Gross Profit (INR)",
        "Gross Margin (%)", "Operating Expenses (INR)", "Net Profit (INR)", "Net Margin (%)", "Units Sold"
    ]
    rows = []
    for m in monthly_trends:
        gm = f"{m['gross_margin']:.2f}" if m['gross_margin'] is not None else "N/A"
        nm = f"{m['net_margin']:.2f}" if m['net_margin'] is not None else "N/A"
        rows.append([
            m["month"],
            m["revenue"],
            m["product_cost"],
            m["gross_profit"],
            gm,
            m["operating_expenses"],
            m["net_profit"],
            nm,
            m["quantity_sold"],
        ])

    csv_data = generate_csv_string(headers, rows)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=monthly_financial_trends.csv"}
    )

@reports_bp.route("/export/expenses-csv")
def export_expenses_csv():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return "No active dataset", 404

    dataset_id = active_dataset["dataset_id"]
    expenses_df = load_expenses_dataframe(dataset_id)
    expense_dist = compute_expense_distribution(expenses_df)

    headers = ["Expense Category", "Total Incurred (INR)", "Share of Operating Expenses (%)"]
    rows = [[e["category"], e["amount"], f"{e['percentage']:.2f}"] for e in expense_dist]

    csv_data = generate_csv_string(headers, rows)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expense_breakdown.csv"}
    )

@reports_bp.route("/export/alerts-csv")
def export_alerts_csv():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return "No active dataset", 404

    dataset_id = active_dataset["dataset_id"]
    alerts_list = get_alerts_for_dataset(dataset_id)

    headers = [
        "Rule Code", "Category", "Subject Type", "Subject Name",
        "Period Month", "Severity", "Explanation", "Actionable Recommendation"
    ]
    rows = []
    for a in alerts_list:
        rows.append([
            a["rule_code"],
            a["category"],
            a["subject_type"],
            a["subject_name"],
            a["period_month"],
            a["severity"],
            a["explanation"],
            a["recommendation"],
        ])

    csv_data = generate_csv_string(headers, rows)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=detected_loss_alerts.csv"}
    )
