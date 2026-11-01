"""
Configuration and detection thresholds for Business Loss Detection System.
All detection parameters live centrally in ANALYSIS_THRESHOLDS for transparency and auditability.
"""
import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_loss_detector_default_secret_key_fixed")
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"

    # 5 MB maximum file upload limit as specified in Section 3
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # Database Configuration
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_NAME = os.environ.get("DB_NAME", "loss_detector")
    DB_USER = os.environ.get("DB_USER", "detector_user")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "detector_pass123")
    TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "loss_detector_test")

    # Staging directory for two-step upload
    STAGING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staging")

    # Centralized Rule Thresholds (Module 3 & Section 5)
    ANALYSIS_THRESHOLDS = {
        "R1": {
            "name": "Loss-making product",
            "condition": "product_revenue - product_cost < 0",
            "loss_threshold": 0.0,
            "high_severity_margin": -20.0,  # margin <= -20% -> High; else Medium
            "unit": "INR",
        },
        "R2": {
            "name": "Low-margin product",
            "condition": "0 < margin < 10% (revenue > 0)",
            "min_margin": 0.0,
            "max_margin": 10.0,
            "medium_severity_threshold": 5.0,  # margin < 5% -> Medium; 5% to 10% -> Low
            "unit": "%",
        },
        "R3": {
            "name": "Declining sales",
            "condition": "% change in quantity vs preceding sales month < -20%",
            "threshold_pct": -20.0,
            "min_prev_qty": 10.0,
            "high_severity_decline": -50.0,  # decline > 50% -> High
            "medium_severity_decline": -35.0,  # > 35% -> Medium; else Low
            "unit": "%",
        },
        "R4": {
            "name": "Unusual expense increase",
            "condition": "% increase vs preceding expense month > 30%",
            "threshold_pct": 30.0,
            "min_prev_expense": 1000.0,
            "high_severity_increase": 100.0,  # increase > 100% -> High
            "medium_severity_increase": 50.0,  # > 50% -> Medium; else Low
            "unit": "%",
        },
        "R5": {
            "name": "Inventory risk",
            "condition": "latest inventory snapshot > 3 x 3-month average monthly quantity sold",
            "multiple_threshold": 3.0,
            "min_history_months": 3,
            "high_severity_multiple": 6.0,  # inventory >= 6x -> High
            "medium_severity_multiple": 4.0,  # >= 4x -> Medium; else Low
            "unit": "ratio",
        },
        "R6": {
            "name": "Discount margin risk",
            "condition": "margin_before - margin_after > 15 percentage points",
            "drop_threshold_points": 15.0,
            "high_severity_drop": 30.0,  # impact > 30 points -> High
            "medium_severity_drop": 20.0,  # > 20 points -> Medium; else Low
            "unit": "percentage points",
        },
    }

os.makedirs(Config.STAGING_DIR, exist_ok=True)
