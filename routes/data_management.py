"""
Data Management and Health routes for Business Loss Detection System.
Provides dataset switching, rejection audit inspection, cascade deletion, and DB health checks.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from database.operations import (
    list_datasets, get_dataset_by_id, set_active_dataset, delete_dataset,
    get_rejected_records, load_sales_dataframe, load_expenses_dataframe,
    store_analysis_report
)
from analytics.loss_detection import run_all_detection_rules
from analytics.financial_analysis import compute_overall_kpis
from database.connection import check_db_health

data_mgmt_bp = Blueprint("data_mgmt", __name__)

@data_mgmt_bp.route("/data-management")
def index():
    datasets = list_datasets()
    return render_template("data_management.html", datasets=datasets)

@data_mgmt_bp.route("/data-management/activate/<int:dataset_id>", methods=["POST"])
def activate(dataset_id):
    try:
        set_active_dataset(dataset_id)
        flash(f"Dataset #{dataset_id} is now active.", "success")
    except Exception as exc:
        flash(f"Failed to activate dataset: {str(exc)}", "error")
    return redirect(url_for("data_mgmt.index"))

@data_mgmt_bp.route("/data-management/delete/<int:dataset_id>", methods=["POST"])
def delete(dataset_id):
    try:
        delete_dataset(dataset_id)
        flash(f"Dataset #{dataset_id} and all associated sales, expenses, and alerts deleted.", "success")
    except Exception as exc:
        flash(f"Failed to delete dataset: {str(exc)}", "error")
    return redirect(url_for("data_mgmt.index"))

@data_mgmt_bp.route("/data-management/reanalyze/<int:dataset_id>", methods=["POST"])
def reanalyze(dataset_id):
    """Idempotently re-runs detection rules on an existing dataset, refreshing alerts and report."""
    try:
        sales_df = load_sales_dataframe(dataset_id)
        expenses_df = load_expenses_dataframe(dataset_id)
        alerts = run_all_detection_rules(sales_df, expenses_df)
        kpis = compute_overall_kpis(sales_df, expenses_df)

        dataset = get_dataset_by_id(dataset_id)
        report_summary = {
            "business_id": dataset.get("business_id", 1),
            "period_start": dataset.get("date_min"),
            "period_end": dataset.get("date_max"),
            "total_revenue": kpis["total_revenue"],
            "total_product_cost": kpis["total_product_cost"],
            "total_expenses": kpis["operating_expenses"] or 0.0,
            "gross_profit": kpis["gross_profit"],
            "net_profit": kpis["net_profit"] or 0.0,
        }
        store_analysis_report(dataset_id, report_summary, alerts)
        flash(f"Dataset #{dataset_id} re-analyzed successfully! {len(alerts)} alerts generated.", "success")
    except Exception as exc:
        flash(f"Failed to re-analyze dataset: {str(exc)}", "error")
    return redirect(url_for("data_mgmt.index"))

@data_mgmt_bp.route("/data-management/rejected/<int:dataset_id>")
def view_rejected(dataset_id):
    dataset = get_dataset_by_id(dataset_id)
    if not dataset:
        flash("Dataset not found", "error")
        return redirect(url_for("data_mgmt.index"))

    rejected_records = get_rejected_records(dataset_id)
    return render_template(
        "rejected_records.html",
        dataset=dataset,
        rejected_records=rejected_records,
    )

@data_mgmt_bp.route("/health")
def health():
    """System health check endpoint reporting DB connectivity and active dataset."""
    db_ok, message, details = check_db_health()
    status_code = 200 if db_ok else 503
    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "database": {
            "status": "ok" if db_ok else "error",
            "message": message,
            "details": details,
        },
        "engine": "rule-based-pandas-v1",
        "rules_active": 6,
    }), status_code
