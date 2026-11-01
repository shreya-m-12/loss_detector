# Data Flow Architecture (DATA_FLOW.md)

This document traces the complete lifecycle of data through the Business Loss Detection & Decision Support System from file ingestion to executive PDF and CSV outputs.

---

## 1. High-Level Data Flow Diagram

```
[ User Files: transactions.csv & expenses.csv ]
                      │
                      ▼
[ Module 1: Validation Engine (analytics/data_validation.py) ]
      ├─ Enforce ISO YYYY-MM-DD
      ├─ Math check: quantity * price - discount == sales_revenue
      ├─ Enforce non-negativity & positive quantities
      ├─ Dedup exact lines inside file
      └─ Delimiter auto-detection (, or ;) & CP1252/UTF-8 BOM
                      │
                      ▼
[ Server-Side Staging (staging/{token}.json) ]
                      │
                      ▼
[ Step 2: Audit Review Page (/upload/review/{token}) ]
      ├─ Total rows, accepted count, rejected count, warning count
      ├─ Preview accepted rows (first 20)
      ├─ Inspect rejected rows table with line numbers & reasons
      ├─ Option: "Download rejected rows as CSV"
      └─ Action: "Cancel" (discards) OR "Confirm and Analyse"
                      │
                      ▼
[ Module 6: Atomic Database Commit (database/operations.py) ]
      ├─ Start Transaction
      ├─ Insert Dataset record (datasets)
      ├─ Upsert Products (products)
      ├─ Bulk Insert Sales (sales_transactions) via executemany
      ├─ Bulk Insert Expenses (expenses) via executemany
      ├─ Bulk Insert Rejections (rejected_records)
      └─ Commit Transaction (Atomic)
                      │
                      ▼
[ Module 2: Financial Aggregation Engine (analytics/financial_analysis.py) ]
      ├─ Load Pandas DataFrames with proper datatypes
      ├─ Compute Sales Revenue = sum(sales_revenue)
      ├─ Compute Product Cost = sum(product_cost)
      ├─ Compute Operating Expenses = sum(expense_amount)
      ├─ Compute Gross Profit = Revenue - Cost
      ├─ Compute Net Profit = Gross Profit - Expenses
      ├─ Compute Margins (guarded for zero revenue)
      └─ Compute Latest Inventory Snapshot per SKU
                      │
                      ▼
[ Module 3: Rule-Based Loss Detection (analytics/loss_detection.py) ]
      ├─ R1: Loss-making product (Revenue - Cost < 0)
      ├─ R2: Low-margin product (0 < Margin < 10%)
      ├─ R3: Declining sales volume (% change < -20%)
      ├─ R4: Unusual expense surge (% increase > 30%)
      ├─ R5: Inventory overstock risk (Stock > 3x trailing 3-month sales)
      └─ R6: Discount margin risk (Margin drop > 15 points)
                      │
                      ▼
[ Module 4: Recommendations Generator (analytics/recommendations.py) ]
      ├─ Populate rule templates with exact trigger metrics
      └─ Assign actionable investigation steps
                      │
                      ▼
[ Persistence & Idempotent Report Storage (database/operations.py) ]
      ├─ Delete prior alerts/reports for this dataset
      ├─ Insert Analysis Report summary (analysis_reports)
      └─ Bulk insert deduplicated Alerts (alerts)
                      │
                      ▼
[ Presentation & Export Layer (routes/) ]
      ├─ Executive Dashboard with 6 KPI cards & 6 Chart.js graphs
      ├─ Dynamic AJAX Filtering (/api/dashboard-data)
      ├─ Product SKU Performance & Closing Stock Audit
      ├─ Grouped Recommendations & Operational Action Playbook
      ├─ Downloadable Executive PDF Report via ReportLab
      └─ Formula-Sanitized CSV Exports
```
