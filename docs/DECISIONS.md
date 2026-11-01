# Architectural Decisions Log (DECISIONS.md)

This log documents key architectural, algorithmic, and engineering trade-offs chosen to satisfy the requirements of the academic CSE mini-project.

---

### Decision 1: Two-File Upload Architecture (`transactions.csv` and `expenses.csv`)
- **Context:** Many naive retail systems attempt to put operating expenses directly on sales rows.
- **Problem:** Repeating store-wide expenses (e.g. monthly rent of ₹15,000) on each SKU transaction row leads to severe double-counting when summing rows, and makes product-level gross margin calculation impossible.
- **Decision:** Strictly separate sales lines from operating expenses. Sales lines contain product-specific quantities, prices, discounts, and costs. Operating expenses represent store-wide overheads (Rent, Salaries, Utilities, Transport).
- **Consequence:** Clean normalization, mathematical integrity, and zero double-counting.

---

### Decision 2: 2-Step Staging Upload Pipeline
- **Context:** Uploading directly to the permanent database without inspection causes dirty state on validation failures.
- **Problem:** If a file of 1,000 rows has one error on line 850, either partial rows remain or a rollback leaves the user confused about which lines failed.
- **Decision:** Uploaded files are parsed, validated, and held in server-side staging (`staging/{token}.json`). The user reviews accepted counts, rejected counts with line numbers and reasons, previews rows, and can download rejected records as CSV. Nothing touches MySQL until the user explicitly clicks "Confirm and Analyse".
- **Consequence:** Full transparency, atomic transactions, and zero orphaned data.

---

### Decision 3: Deterministic Rule-Based Analytics vs AI/ML Black Boxes
- **Context:** Viva evaluations require absolute mathematical explainability.
- **Problem:** Machine learning or generative models produce probabilistic, non-reproducible predictions that cannot be mathematically proven in a viva exam.
- **Decision:** The system strictly uses rule-based financial formulas (R1 to R6) executed as pure functions on Pandas DataFrames. All thresholds are centralized in `config.py` (`ANALYSIS_THRESHOLDS`).
- **Consequence:** 100% reproducible, verifiable, and explainable in a viva.

---

### Decision 4: Inventory Snapshot Treatment (Never Summed)
- **Context:** `inventory_quantity` on a sales row represents the closing stock of that product *after* that transaction.
- **Problem:** Summing inventory values across rows produces absurd quantities (e.g. 50 + 45 + 30 = 125 units instead of 30).
- **Decision:** Product inventory is strictly defined as the most recent recorded snapshot (highest date, ties broken by transaction ID).
- **Consequence:** Accurate warehouse stock representation.

---

### Decision 5: Filter Semantics for Single-Product Selection
- **Context:** When a user filters the dashboard by a specific product (e.g. "Rice 1kg"), what should happen to Operating Expenses and Net Profit?
- **Problem:** Rent and electricity are store-wide costs; allocating arbitrary fractions to single products creates distorted financial figures.
- **Decision:** When a product filter is active, Operating Expenses and Net Profit cards display `"N/A (expenses are store-wide)"`, while Sales Revenue, Product Cost, Gross Profit, and Gross Margin remain fully available.
- **Consequence:** Accounting accuracy without artificial cost allocation assumptions.

---

### Decision 6: PDF Generation with ReportLab instead of WeasyPrint
- **Context:** The system must run smoothly on local Windows workstations with VS Code.
- **Problem:** WeasyPrint requires external native C libraries (GTK, Pango, Cairo) which frequently fail to compile or install on standard Windows machines.
- **Decision:** Use ReportLab paired with Matplotlib. Both are 100% pure Python wheels that install with zero external C-dependencies on Windows.
- **Consequence:** Effortless cross-platform portability.

---

### Decision 7: Formula Injection (DDE) Neutralization on CSV Exports
- **Context:** Store owners open CSV reports in Microsoft Excel or Google Sheets.
- **Problem:** CSV cells starting with `=`, `+`, `-`, or `@` can be interpreted by spreadsheet applications as formulas or DDE execution payloads.
- **Decision:** All exported CSV cells starting with these characters (unless they are valid numbers) are prepended with a single quote (`'`).
- **Consequence:** Industry-standard spreadsheet injection defense.
