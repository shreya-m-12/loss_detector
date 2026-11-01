"""
Loss Detection Alerts and Recommendations routes for Business Loss Detection System.
Provides interactive alert filtering, severity explanations, and grouped recommendation workflows.
"""
from flask import Blueprint, render_template, request
from database.operations import get_active_dataset, get_alerts_for_dataset
from analytics.filters import filter_alerts
from config import Config

alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/alerts")
def index():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return render_template("alerts.html", active_dataset=None)

    dataset_id = active_dataset["dataset_id"]
    all_alerts = get_alerts_for_dataset(dataset_id)

    # Filter parameters
    severity = request.args.get("severity", "All")
    rule_code = request.args.get("rule_code", "All")
    month = request.args.get("month", "All")
    product = request.args.get("product", "All")
    category = request.args.get("category", "All")

    filters = {
        "severity": severity,
        "rule_code": rule_code,
        "month": month,
        "product": product,
        "category": category,
    }
    filtered_alerts = filter_alerts(all_alerts, filters)

    # Unique filter options
    months_list = sorted(list(set(a["period_month"] for a in all_alerts)), reverse=True)
    products_list = sorted(list(set(a["subject_name"] for a in all_alerts if a["subject_type"] == "product")))
    categories_list = sorted(list(set(a["category"] for a in all_alerts)))

    # Compute related alerts mapping
    # A product in the same month might have triggered multiple rules (e.g. R1 and R6)
    related_map = {}
    for a in all_alerts:
        key = (a["subject_name"], a["period_month"])
        related = [other for other in all_alerts if (other["subject_name"], other["period_month"]) == key and other["rule_code"] != a["rule_code"]]
        if related:
            related_map[a["alert_id"]] = related

    severity_rules = [
        {"rule": "R1 (Loss-making product)", "high": "Margin <= -20% or zero revenue", "medium": "Any other loss (cost > revenue)", "low": "N/A"},
        {"rule": "R2 (Low-margin product)", "high": "N/A", "medium": "Margin < 5.0%", "low": "Margin 5.0% to 10.0%"},
        {"rule": "R3 (Declining sales volume)", "high": "Decline > 50.0%", "medium": "Decline 35.0% to 50.0%", "low": "Decline 20.0% to 35.0%"},
        {"rule": "R4 (Unusual expense surge)", "high": "Surge > 100.0%", "medium": "Surge 50.0% to 100.0%", "low": "Surge 30.0% to 50.0%"},
        {"rule": "R5 (Inventory overstock risk)", "high": "Stock >= 6.0x monthly sales", "medium": "Stock 4.0x to 6.0x monthly sales", "low": "Stock 3.0x to 4.0x monthly sales"},
        {"rule": "R6 (Discount margin erosion)", "high": "Impact > 30.0 points drop or 100% discount", "medium": "Impact 20.0 to 30.0 points drop", "low": "Impact 15.0 to 20.0 points drop"},
    ]

    return render_template(
        "alerts.html",
        active_dataset=active_dataset,
        alerts_list=filtered_alerts,
        total_alerts=len(all_alerts),
        filtered_count=len(filtered_alerts),
        filters=filters,
        months_list=months_list,
        products_list=products_list,
        categories_list=categories_list,
        related_map=related_map,
        severity_rules=severity_rules,
        thresholds=Config.ANALYSIS_THRESHOLDS,
    )

@alerts_bp.route("/recommendations")
def recommendations():
    active_dataset = get_active_dataset()
    if not active_dataset:
        return render_template("recommendations.html", active_dataset=None)

    dataset_id = active_dataset["dataset_id"]
    all_alerts = get_alerts_for_dataset(dataset_id)

    # Group by Severity
    high_alerts = [a for a in all_alerts if a["severity"] == "High"]
    med_alerts = [a for a in all_alerts if a["severity"] == "Medium"]
    low_alerts = [a for a in all_alerts if a["severity"] == "Low"]

    # Group by Rule
    by_rule = {}
    for a in all_alerts:
        by_rule.setdefault(a["rule_code"], []).append(a)

    return render_template(
        "recommendations.html",
        active_dataset=active_dataset,
        all_alerts=all_alerts,
        high_alerts=high_alerts,
        med_alerts=med_alerts,
        low_alerts=low_alerts,
        by_rule=by_rule,
        thresholds=Config.ANALYSIS_THRESHOLDS,
    )
