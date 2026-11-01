# Detection Rules & Analytical Methodology (RULES.md)

All business loss detection rules are implemented as pure functions in `analytics/loss_detection.py` and configured in `config.py`. Every rule operates on full calendar months (`period_month: YYYY-MM`) to guarantee historical context.

---

## Summary Matrix

| Rule Code | Rule Name | Analytical Grain | Condition | Safeguards | High Severity | Medium Severity | Low Severity |
|---|---|---|---|---|---|---|---|
| **R1** | Loss-making product | Product x Month | `Revenue - Cost < 0` | Loss amount = Cost - Revenue | Margin <= -20% or 0 Revenue | Any other loss (Cost > Rev) | N/A |
| **R2** | Low-margin product | Product x Month | `0 < Margin < 10%` | Revenue > 0 | N/A | Margin < 5.0% | 5.0% to 10.0% |
| **R3** | Declining sales volume | Product x Month | `% change in Qty < -20%` | Prev Qty >= 10 units; Preceding available month | Decline > 50.0% | Decline 35.0% to 50.0% | Decline 20.0% to 35.0% |
| **R4** | Unusual expense increase | Category x Month | `% increase in Exp > 30%` | Prev Exp >= ₹1,000; Preceding available month | Increase > 100.0% | Increase 50.0% to 100.0% | Increase 30.0% to 50.0% |
| **R5** | Inventory overstock risk | Product as of Month-end | `Snapshot > 3 x 3-mo Avg Sales` | Requires >= 3 months history; Avg > 0 | Stock >= 6.0x avg | Stock 4.0x to 6.0x avg | Stock 3.0x to 4.0x avg |
| **R6** | Discount margin risk | Product x Month | `Margin Before - Margin After > 15 pts` | Rev Before > 0 and Discount > 0 | Impact > 30 pts or 100% discount | Impact 20.0 to 30.0 pts | Impact 15.0 to 20.0 pts |

---

## Detailed Rule Specifications

### R1: Loss-Making Product
- **Objective:** Detect SKUs that generated negative gross profit in a given month.
- **Formula:**
  $$\text{Loss Amount} = \text{Product Cost} - \text{Sales Revenue}$$
  $$\text{Gross Margin} = \left(\frac{\text{Sales Revenue} - \text{Product Cost}}{\text{Sales Revenue}}\right) \times 100$$
- **Safeguards:** If Sales Revenue is 0 with Cost > 0, margin is treated as -100% and severity is classified as High.
- **Investigation Advice:** Verify supplier invoice prices against wholesale agreements. Ensure retail promotional discounts do not undercut procurement unit costs.

### R2: Low-Margin Product
- **Objective:** Flag products that remain profitable but generate inadequate gross margins (< 10%).
- **Formula:**
  $$\text{Gross Margin} = \left(\frac{\text{Sales Revenue} - \text{Product Cost}}{\text{Sales Revenue}}\right) \times 100$$
- **Boundary Safeguard:** A product with margin of exactly 10.0% does NOT alert.
- **Investigation Advice:** Explore modest 3% to 5% price adjustments if competitor market pricing permits. Bundle with higher-margin companion goods.

### R3: Declining Sales Volume
- **Objective:** Detect sharp volume drop-offs compared to the preceding available month with sales.
- **Formula:**
  $$\Delta\% = \left(\frac{\text{Qty}_{\text{current}} - \text{Qty}_{\text{prev}}}{\text{Qty}_{\text{prev}}}\right) \times 100$$
- **Safeguards:** `Qty_prev` must be >= 10 units to avoid false positives on erratic low-volume items. Skips months with no sales history.
- **Boundary Safeguard:** A decline of exactly -20.0% or -19.0% does NOT alert.
- **Investigation Advice:** Audit stockout records, inspect competitor pricing pressure, and examine shelf visibility.

### R4: Unusual Expense Increase
- **Objective:** Alert store managers when operational overhead in any category surges over 30% month-over-month.
- **Formula:**
  $$\Delta\% = \left(\frac{\text{Expense}_{\text{current}} - \text{Expense}_{\text{prev}}}{\text{Expense}_{\text{prev}}}\right) \times 100$$
- **Safeguards:** `Expense_prev` must be >= ₹1,000.
- **Boundary Safeguard:** An increase of exactly +30.0% or +29.0% does NOT alert.
- **Investigation Advice:** Inspect utility bills, repair invoices, and verify whether a one-off annual charge occurred.

### R5: Inventory Overstock Risk
- **Objective:** Prevent working capital lockup and stock expiration by flagging inventory exceeding 3 months of trailing sales velocity.
- **Formula:**
  $$\text{Ratio} = \frac{\text{Latest Inventory Snapshot as of Month-end}}{\text{Mean Monthly Sales of Trailing 3 Months}}$$
- **Safeguards:** Requires at least 3 months of sales history (`MIN_HISTORY_MONTHS = 3`). Products with fewer than 3 months of history produce no alert.
- **Boundary Safeguard:** A ratio of exactly 3.0x does NOT alert.
- **Investigation Advice:** Halt replenishment orders, inspect batch expiration dates, and offer clearance bundles.

### R6: Discount Margin Risk
- **Objective:** Flag instances where promotional discounts erode gross margin by more than 15 percentage points.
- **Formula:**
  $$\text{Margin}_{\text{before}} = \left(\frac{\sum(\text{Qty} \times \text{Selling Price}) - \text{Cost}}{\sum(\text{Qty} \times \text{Selling Price})}\right) \times 100$$
  $$\text{Margin}_{\text{after}} = \left(\frac{\text{Sales Revenue} - \text{Cost}}{\text{Sales Revenue}}\right) \times 100$$
  $$\text{Drop} = \text{Margin}_{\text{before}} - \text{Margin}_{\text{after}}$$
- **Safeguards:** Skipped if `Discount = 0` or `Revenue_before = 0`. If `Revenue_after = 0` with `Discount > 0` (100% discount / free giveaways), flags High severity.
- **Boundary Safeguard:** A drop of exactly 15.0 points does NOT alert.
- **Investigation Advice:** Enforce a minimum gross profit margin floor (e.g., 15%) on all cashier promotional overrides.
