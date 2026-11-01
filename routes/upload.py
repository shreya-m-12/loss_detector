"""
Upload and staging routes for Business Loss Detection System.
Implements the 2-step upload flow, validation review, sample loader, and atomic commit.
"""
import os
import uuid
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, current_app
from werkzeug.utils import secure_filename

from config import Config
from analytics.data_validation import (
    validate_transactions_csv, validate_expenses_csv, compute_combined_hash
)
from database.connection import get_db
from database.operations import (
    find_dataset_by_hash, commit_staged_dataset, set_active_dataset,
    load_sales_dataframe, load_expenses_dataframe, store_analysis_report
)
from analytics.loss_detection import run_all_detection_rules
from analytics.financial_analysis import compute_overall_kpis
from services.exports import generate_csv_string

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")

ALLOWED_EXTENSIONS = {"csv"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route("", methods=["GET", "POST"])
@upload_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Handle file upload
        sales_file = request.files.get("transactions_file")
        expenses_file = request.files.get("expenses_file")
        dataset_name = request.form.get("dataset_name", "").strip() or "Uploaded Dataset"

        if not sales_file or not expenses_file:
            flash("Please provide both transactions.csv and expenses.csv files.", "error")
            return redirect(url_for("upload.index"))

        if not (allowed_file(sales_file.filename) and allowed_file(expenses_file.filename)):
            flash("Only .csv files are permitted. Please check your file extensions.", "error")
            return redirect(url_for("upload.index"))

        sales_bytes = sales_file.read()
        expenses_bytes = expenses_file.read()

        if len(sales_bytes) == 0:
            flash("transactions.csv file is empty.", "error")
            return redirect(url_for("upload.index"))
        if len(expenses_bytes) == 0:
            flash("expenses.csv file is empty.", "error")
            return redirect(url_for("upload.index"))

        # Check duplicate batch via combined SHA-256
        batch_hash = compute_combined_hash(sales_bytes, expenses_bytes)
        existing = find_dataset_by_hash(batch_hash)
        if existing:
            flash(
                f"Warning: A dataset with identical file contents was already uploaded on {existing['uploaded_at']} "
                f"('{existing['dataset_name']}', ID #{existing['dataset_id']}). You can activate it from Data Management.",
                "warning"
            )

        # Parse & Validate
        s_val = validate_transactions_csv(sales_bytes)
        if s_val.get("error"):
            flash(s_val["error"], "error")
            return redirect(url_for("upload.index"))

        e_val = validate_expenses_csv(expenses_bytes)
        if e_val.get("error"):
            flash(e_val["error"], "error")
            return redirect(url_for("upload.index"))

        # Save to staging area
        staging_token = str(uuid.uuid4())
        staging_data = {
            "token": staging_token,
            "dataset_name": dataset_name,
            "source_type": "upload",
            "sales_filename": secure_filename(sales_file.filename),
            "expense_filename": secure_filename(expenses_file.filename),
            "file_hash": batch_hash,
            "s_val": s_val,
            "e_val": e_val,
        }

        staging_path = os.path.join(Config.STAGING_DIR, f"{staging_token}.json")
        with open(staging_path, "w", encoding="utf-8") as f:
            json.dump(staging_data, f)

        return redirect(url_for("upload.review", token=staging_token))

    return render_template("upload.html")

@upload_bp.route("/load-sample", methods=["POST"])
def load_sample():
    """Loads the verified 6-month sample dataset through the full validation and staging pipeline."""
    sample_sales_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets", "sample_transactions.csv")
    sample_exp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets", "sample_expenses.csv")

    if not os.path.isfile(sample_sales_path) or not os.path.isfile(sample_exp_path):
        flash("Sample datasets not found on server. Please run sample generator.", "error")
        return redirect(url_for("upload.index"))

    with open(sample_sales_path, "rb") as f:
        sales_bytes = f.read()
    with open(sample_exp_path, "rb") as f:
        exp_bytes = f.read()

    batch_hash = compute_combined_hash(sales_bytes, exp_bytes)
    s_val = validate_transactions_csv(sales_bytes)
    e_val = validate_expenses_csv(exp_bytes)

    staging_token = str(uuid.uuid4())
    staging_data = {
        "token": staging_token,
        "dataset_name": "Demo Grocery Store (6-Month Real Retail Audit)",
        "source_type": "sample",
        "sales_filename": "sample_transactions.csv",
        "expense_filename": "sample_expenses.csv",
        "file_hash": batch_hash,
        "s_val": s_val,
        "e_val": e_val,
    }

    staging_path = os.path.join(Config.STAGING_DIR, f"{staging_token}.json")
    with open(staging_path, "w", encoding="utf-8") as f:
        json.dump(staging_data, f)

    return redirect(url_for("upload.review", token=staging_token))

@upload_bp.route("/review/<token>")
def review(token):
    staging_path = os.path.join(Config.STAGING_DIR, f"{token}.json")
    if not os.path.isfile(staging_path):
        flash("Staging session expired or not found. Please upload again.", "error")
        return redirect(url_for("upload.index"))

    with open(staging_path, "r", encoding="utf-8") as f:
        staging_data = json.load(f)

    s_val = staging_data["s_val"]
    e_val = staging_data["e_val"]

    total_rows = s_val["total_rows"] + e_val["total_rows"]
    accepted_count = len(s_val["accepted_rows"]) + len(e_val["accepted_rows"])
    rejected_count = len(s_val["rejected_rows"]) + len(e_val["rejected_rows"])
    warnings_count = len(s_val["warnings"]) + len(e_val["warnings"])

    # Combine rejected records
    all_rejected = s_val["rejected_rows"] + e_val["rejected_rows"]
    all_warnings = s_val["warnings"] + e_val["warnings"]

    # Preview up to 20 accepted sales and 10 accepted expenses
    sales_preview = s_val["accepted_rows"][:20]
    expenses_preview = e_val["accepted_rows"][:10]

    return render_template(
        "review.html",
        token=token,
        dataset_name=staging_data["dataset_name"],
        source_type=staging_data["source_type"],
        sales_filename=staging_data["sales_filename"],
        expense_filename=staging_data["expense_filename"],
        total_rows=total_rows,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        warnings_count=warnings_count,
        sales_accepted=len(s_val["accepted_rows"]),
        sales_rejected=len(s_val["rejected_rows"]),
        expenses_accepted=len(e_val["accepted_rows"]),
        expenses_rejected=len(e_val["rejected_rows"]),
        date_min=s_val["date_min"] or e_val["date_min"],
        date_max=s_val["date_max"] or e_val["date_max"],
        sales_preview=sales_preview,
        expenses_preview=expenses_preview,
        all_rejected=all_rejected,
        all_warnings=all_warnings,
    )

@upload_bp.route("/confirm/<token>", methods=["POST"])
def confirm(token):
    staging_path = os.path.join(Config.STAGING_DIR, f"{token}.json")
    if not os.path.isfile(staging_path):
        flash("Staging session expired or not found.", "error")
        return redirect(url_for("upload.index"))

    with open(staging_path, "r", encoding="utf-8") as f:
        staging_data = json.load(f)

    s_val = staging_data["s_val"]
    e_val = staging_data["e_val"]

    sales_accepted = s_val["accepted_rows"]
    expenses_accepted = e_val["accepted_rows"]
    rejected_records = s_val["rejected_rows"] + e_val["rejected_rows"]

    total_accepted = len(sales_accepted) + len(expenses_accepted)
    if total_accepted == 0:
        flash("Cannot confirm dataset: 0 valid rows were accepted after validation.", "error")
        return redirect(url_for("upload.review", token=token))

    dates = [r["transaction_date"] for r in sales_accepted] + [r["expense_date"] for r in expenses_accepted]

    dataset_meta = {
        "business_id": 1,
        "dataset_name": staging_data["dataset_name"],
        "source_type": staging_data["source_type"],
        "sales_filename": staging_data["sales_filename"],
        "expense_filename": staging_data["expense_filename"],
        "file_hash": staging_data["file_hash"],
        "total_rows": s_val["total_rows"] + e_val["total_rows"],
        "accepted_rows": total_accepted,
        "rejected_rows": len(rejected_records),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }

    try:
        # Atomic database transaction
        dataset_id = commit_staged_dataset(
            dataset_meta=dataset_meta,
            sales_rows=sales_accepted,
            expense_rows=expenses_accepted,
            rejected_rows=rejected_records,
        )

        # Run detection engine and save report
        sales_df = load_sales_dataframe(dataset_id)
        expenses_df = load_expenses_dataframe(dataset_id)
        alerts = run_all_detection_rules(sales_df, expenses_df)
        kpis = compute_overall_kpis(sales_df, expenses_df)

        report_summary = {
            "business_id": 1,
            "period_start": dataset_meta["date_min"],
            "period_end": dataset_meta["date_max"],
            "total_revenue": kpis["total_revenue"],
            "total_product_cost": kpis["total_product_cost"],
            "total_expenses": kpis["operating_expenses"] or 0.0,
            "gross_profit": kpis["gross_profit"],
            "net_profit": kpis["net_profit"] or 0.0,
        }
        store_analysis_report(dataset_id, report_summary, alerts)

        # Remove staging file
        try:
            os.remove(staging_path)
        except Exception:
            pass

        flash(
            f"Dataset '{dataset_meta['dataset_name']}' committed successfully! "
            f"Stored {len(sales_accepted)} sales, {len(expenses_accepted)} expenses, "
            f"and flagged {len(alerts)} potential risk alerts.",
            "success"
        )
        return redirect(url_for("dashboard.index"))

    except Exception as exc:
        flash(f"Failed to commit dataset to database: {str(exc)}", "error")
        return redirect(url_for("upload.review", token=token))

@upload_bp.route("/cancel/<token>", methods=["POST"])
def cancel(token):
    staging_path = os.path.join(Config.STAGING_DIR, f"{token}.json")
    if os.path.isfile(staging_path):
        try:
            os.remove(staging_path)
        except Exception:
            pass
    flash("Upload staged session cancelled and discarded.", "info")
    return redirect(url_for("upload.index"))

@upload_bp.route("/rejected-csv/<token>")
def download_staged_rejected_csv(token):
    staging_path = os.path.join(Config.STAGING_DIR, f"{token}.json")
    if not os.path.isfile(staging_path):
        return "Session expired", 404

    with open(staging_path, "r", encoding="utf-8") as f:
        staging_data = json.load(f)

    rejected_records = staging_data["s_val"]["rejected_rows"] + staging_data["e_val"]["rejected_rows"]
    headers = ["source_file", "line_number", "rejection_reason", "raw_data"]
    rows = []
    for r in rejected_records:
        rows.append([
            r["source_file"],
            r["line_number"],
            r["reason"],
            json.dumps(r["raw_data"])
        ])

    csv_data = generate_csv_string(headers, rows)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rejected_records_{token[:8]}.csv"}
    )

@upload_bp.route("/template/<file_type>")
def download_template(file_type):
    """Provides downloadable CSV templates for users with clear header definitions."""
    if file_type == "transactions":
        headers = [
            "transaction_date", "product_name", "quantity_sold", "selling_price",
            "discount_amount", "sales_revenue", "product_cost", "inventory_quantity", "transaction_ref"
        ]
        sample_rows = [
            ["2026-08-01", "Basmati Rice 5kg", "10", "450.00", "0.00", "4500.00", "3600.00", "50", "TX-1001"],
            ["2026-08-01", "Toor Dal 1kg", "20", "160.00", "200.00", "3000.00", "2400.00", "40", "TX-1002"]
        ]
        filename = "transactions_template.csv"
    else:
        headers = ["expense_date", "expense_category", "expense_amount"]
        sample_rows = [
            ["2026-08-01", "Rent", "15000.00"],
            ["2026-08-05", "Salaries", "25000.00"]
        ]
        filename = "expenses_template.csv"

    csv_data = generate_csv_string(headers, sample_rows)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
