"""
Unit tests for data_validation.py module.
Verifies rejection of invalid schemas, negative values, date formatting, and math consistency.
"""
import os
import pytest
from analytics.data_validation import (
    validate_transactions_csv, validate_expenses_csv, parse_iso_date, parse_decimal
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVALID_DIR = os.path.join(BASE_DIR, "datasets", "invalid_examples")

def test_parse_iso_date_strictness():
    # Valid ISO date
    d, err = parse_iso_date("2026-08-15")
    assert err is None
    assert str(d) == "2026-08-15"

    # Invalid non-ISO dates
    d, err = parse_iso_date("15/08/2026")
    assert err is not None
    assert "strictly be ISO format YYYY-MM-DD" in err

    d, err = parse_iso_date("08-15-2026")
    assert err is not None

    d, err = parse_iso_date("invalid-date")
    assert err is not None

    d, err = parse_iso_date("")
    assert err is not None

def test_missing_column_example():
    path = os.path.join(INVALID_DIR, "missing_column.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert res["error"] is not None
    assert "missing required columns" in res["error"]
    assert len(res["accepted_rows"]) == 0

def test_bad_dates_example():
    path = os.path.join(INVALID_DIR, "bad_dates.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert len(res["rejected_rows"]) == 1
    assert "strictly be ISO format YYYY-MM-DD" in res["rejected_rows"][0]["reason"]
    assert res["rejected_rows"][0]["line_number"] == 2

def test_negative_values_example():
    path = os.path.join(INVALID_DIR, "negative_values.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert len(res["rejected_rows"]) == 1
    assert "strictly positive" in res["rejected_rows"][0]["reason"]

def test_non_numeric_example():
    path = os.path.join(INVALID_DIR, "non_numeric.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert len(res["rejected_rows"]) == 1
    assert "Non-numeric value" in res["rejected_rows"][0]["reason"]

def test_duplicate_rows_example():
    path = os.path.join(INVALID_DIR, "duplicates.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    # First row is accepted, second exact duplicate is rejected
    assert len(res["accepted_rows"]) == 1
    assert len(res["rejected_rows"]) == 1
    assert "Duplicate row" in res["rejected_rows"][0]["reason"]

def test_revenue_mismatch_example():
    path = os.path.join(INVALID_DIR, "revenue_mismatch.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert len(res["rejected_rows"]) == 1
    assert "revenue does not equal quantity x price - discount" in res["rejected_rows"][0]["reason"]

def test_semicolon_and_bom_example():
    path = os.path.join(INVALID_DIR, "semicolon_bom.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert len(res["accepted_rows"]) == 1
    assert len(res["rejected_rows"]) == 0

def test_empty_file_example():
    path = os.path.join(INVALID_DIR, "empty_file.csv")
    with open(path, "rb") as f:
        res = validate_transactions_csv(f.read())
    assert res["error"] is not None
    assert "file is empty" in res["error"]
