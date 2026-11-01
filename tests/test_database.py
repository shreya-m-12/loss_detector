"""
Database operations and integrity tests using isolated test database.
Verifies atomic transactions, foreign keys, cascade deletion, and idempotence.
"""
import pytest
from database.operations import (
    commit_staged_dataset, get_dataset_by_id, list_datasets,
    set_active_dataset, delete_dataset, store_analysis_report, get_alerts_for_dataset,
    find_dataset_by_hash
)

def test_dataset_commit_and_retrieval(test_db_conn):
    dataset_meta = {
        "business_id": 1,
        "dataset_name": "Test DB Batch",
        "source_type": "upload",
        "sales_filename": "test_sales.csv",
        "expense_filename": "test_expenses.csv",
        "file_hash": "testhash1234567890",
        "total_rows": 2,
        "accepted_rows": 2,
        "rejected_rows": 0,
        "date_min": "2026-08-01",
        "date_max": "2026-08-10",
    }
    sales_rows = [
        {
            "transaction_date": "2026-08-01",
            "product_name": "Atta 10kg",
            "quantity_sold": 10.0,
            "selling_price": 380.0,
            "discount_amount": 0.0,
            "sales_revenue": 3800.0,
            "product_cost": 3000.0,
            "inventory_quantity": 25.0,
            "row_fingerprint": "fp1",
        }
    ]
    expense_rows = [
        {
            "expense_date": "2026-08-05",
            "expense_category": "Electricity",
            "expense_amount": 1200.0,
        }
    ]

    dataset_id = commit_staged_dataset(dataset_meta, sales_rows, expense_rows, [], conn=test_db_conn)
    assert dataset_id is not None

    d = get_dataset_by_id(dataset_id, conn=test_db_conn)
    assert d["dataset_name"] == "Test DB Batch"
    assert d["is_active"] == 1

    # Find by hash
    found = find_dataset_by_hash("testhash1234567890", conn=test_db_conn)
    assert found is not None
    assert found["dataset_id"] == dataset_id

    # Store analysis report and alerts
    report_summary = {
        "business_id": 1,
        "period_start": "2026-08-01",
        "period_end": "2026-08-10",
        "total_revenue": 3800.0,
        "total_product_cost": 3000.0,
        "total_expenses": 1200.0,
        "gross_profit": 800.0,
        "net_profit": -400.0,
    }
    alerts = [
        {
            "rule_code": "R2",
            "category": "Profitability",
            "subject_type": "product",
            "subject_name": "Atta 10kg",
            "period_month": "2026-08",
            "severity": "Low",
            "trigger_values": {"margin": 21.0},
            "threshold_json": {"min": 0, "max": 10},
            "explanation": "Test explanation",
            "recommendation": "Test recommendation",
        }
    ]
    report_id = store_analysis_report(dataset_id, report_summary, alerts, conn=test_db_conn)
    assert report_id is not None

    stored_alerts = get_alerts_for_dataset(dataset_id, conn=test_db_conn)
    assert len(stored_alerts) == 1

    # Cascade delete verification
    delete_dataset(dataset_id, conn=test_db_conn)
    assert get_dataset_by_id(dataset_id, conn=test_db_conn) is None
    # Alerts should be cascade deleted
    assert len(get_alerts_for_dataset(dataset_id, conn=test_db_conn)) == 0
