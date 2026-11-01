# Analytical Scope & Known Limitations (LIMITATIONS.md)

This document formalizes the known design limitations and operational boundaries of the Business Loss Detection and Decision Support System as specified in Sections 0, 5, 7, and 14.

---

### 1. Single-User Local Architecture (No Multi-User Login)
- **Constraint:** The application does not implement user authentication (passwords, JWTs, multi-tenant roles).
- **Design Context:** Built as an academic CSE mini-project designed to run locally on Windows with VS Code for single retail shop owners or store managers.
- **Viva Implication:** Transparent, single-tenant schema where all tables are keyed to `business_id = 1` by default.

---

### 2. Rule-Based Retrospective Analytics vs Predictive AI
- **Constraint:** The system is an explainable decision support system (DSS), not an artificial intelligence forecasting tool.
- **Design Context:** Alerts indicate **potential**, **flagged**, and historical risk anomalies requiring manager investigation. The UI strictly avoids misleading phrases like "guaranteed loss" or "predicted loss".
- **Viva Implication:** Every metric can be verified with pen and paper from the stored CSV transactions.

---

### 3. Configurable Default Thresholds
- **Constraint:** The default thresholds in `config.py` (`ANALYSIS_THRESHOLDS`) are tailored for general grocery retail operations (e.g., 10% gross margin target, 30% overhead surge limit).
- **Design Context:** Different retail verticals (e.g., electronics with 5% margins or apparel with 50% margins) must tune these parameters in `config.py` to match their operational reality.

---

### 4. Sales Returns and Multi-Currency Unsupported
- **Constraint:** The validation engine rejects zero or negative sales quantities (`quantity_sold <= 0`).
- **Design Context:** Product returns, refunds, credit notes, and multi-currency exchange adjustments are not supported in this version.
- **Viva Implication:** Prevents distorted negative revenue calculations and simplifies gross margin definitions.

---

### 5. Calendar Month Grain & Preceding Available Month Semantics
- **Constraint:** Anomaly detection evaluates transactions aggregated by full calendar months (`YYYY-MM`).
- **Design Context:**
  - For rules R3 (Declining Sales) and R4 (Expense Surge), the change percentage compares against the *preceding month that has records*.
  - If a product had sales in 2026-05 and 2026-07 with zero sales in 2026-06, R3 compares 2026-07 directly against 2026-05. Months with zero sales are not treated as zero quantity.
  - For R5 (Inventory Overstock), at least 3 distinct sales months (`MIN_HISTORY_MONTHS = 3`) are required to establish an average sales velocity. Products with 1 or 2 months of history produce "insufficient data" and no alert.

---

### 6. Store-Wide Operating Expenses vs SKU-Level Allocation
- **Constraint:** Operating expenses (rent, electricity, store salaries) are incurred at the store level and are not divided across individual products.
- **Design Context:** When viewing store-wide metrics, Net Profit is computed as `Gross Profit - Operating Expenses`. When filtering by a single product, Operating Expenses and Net Profit are displayed as `"N/A"`, while Product Cost, Gross Profit, and Gross Margin remain fully available.
