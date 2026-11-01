# Verification Test Results (TEST_RESULTS.md)

This document contains the unedited execution logs of the automated test suite executed with `pytest 9.2.0` on Python 3.11.

---

## 1. Automated Test Execution Log

```
$ python3 -m pytest tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.11.2, pytest-9.2.0, pluggy-1.7.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /app/applet
collecting ... collected 23 items

tests/test_database.py::test_dataset_commit_and_retrieval PASSED         [  4%]
tests/test_finance.py::test_hand_calculated_financial_kpis PASSED        [  8%]
tests/test_finance.py::test_zero_revenue_margin_is_none PASSED           [ 13%]
tests/test_finance.py::test_inventory_snapshot_never_summed PASSED       [ 17%]
tests/test_routes.py::test_health_route PASSED                           [ 21%]
tests/test_routes.py::test_dashboard_empty_and_upload_pages PASSED       [ 26%]
tests/test_routes.py::test_sample_dataset_flow PASSED                    [ 30%]
tests/test_rules.py::test_r1_loss_making_rule PASSED                     [ 34%]
tests/test_rules.py::test_r2_boundary_negative_control PASSED            [ 39%]
tests/test_rules.py::test_r3_boundary_negative_control PASSED            [ 43%]
tests/test_rules.py::test_r4_boundary_negative_control PASSED            [ 47%]
tests/test_rules.py::test_r5_boundary_and_insufficient_history PASSED    [ 52%]
tests/test_rules.py::test_r6_discount_risk_rule PASSED                   [ 56%]
tests/test_rules.py::test_sample_dataset_matches_expected_manifest PASSED [ 60%]
tests/test_validation.py::test_parse_iso_date_strictness PASSED          [ 65%]
tests/test_validation.py::test_missing_column_example PASSED             [ 69%]
tests/test_validation.py::test_bad_dates_example PASSED                  [ 73%]
tests/test_validation.py::test_negative_values_example PASSED            [ 78%]
tests/test_validation.py::test_non_numeric_example PASSED                [ 82%]
tests/test_validation.py::test_duplicate_rows_example PASSED             [ 86%]
tests/test_validation.py::test_revenue_mismatch_example PASSED           [ 91%]
tests/test_validation.py::test_semicolon_and_bom_example PASSED          [ 95%]
tests/test_validation.py::test_empty_file_example PASSED                 [100%]

============================== 23 passed in 2.25s ==============================
```

---

## 2. Test Coverage Breakdown

| Test File | Total | Passed | Description |
|---|---|---|---|
| `tests/test_validation.py` | 9 | 9 | Strict ISO dates, missing columns, non-numerics, negative values, revenue mismatch, duplicates, semicolon & BOM detection, empty files. |
| `tests/test_finance.py` | 3 | 3 | Hand-calculated financial KPIs, guarded zero-revenue margins returning `None`, inventory snapshot latest date extraction. |
| `tests/test_rules.py` | 7 | 7 | Pure rule evaluations for R1 to R6, strict negative control boundaries (Moong Dal -19%, Mustard Oil 10%, Jeera 3.0x, Transport +29%), short history guard, and exact match against `expected_alerts.json`. |
| `tests/test_database.py` | 1 | 1 | MySQL atomic commit, cascade deletion across foreign keys, SHA-256 duplicate batch detection, idempotent report replacement. |
| `tests/test_routes.py` | 3 | 3 | End-to-end Flask client workflows: `/health`, empty-state rendering, two-step upload staging & confirmation, dashboard AJAX filters, PDF ReportLab generation, and CSV exports. |
| **Total** | **23** | **23** | **100% Pass Rate** |

---

## 3. Notes on Test Scope
- Multi-user concurrent session stress tests were not included because the application is explicitly specified as single-user and local.
- All database tests were isolated to `loss_detector_test` to guarantee the integrity of production data.
