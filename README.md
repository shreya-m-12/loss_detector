# Business Loss Detection & Decision Support System (Retail Analytics DSS)

A production-grade, transparent, rule-based analytics web application built with **Flask**, **MySQL**, **Pandas**, and **Chart.js** for small retail shops, supermarkets, and grocery stores.

The system ingests two separate CSV files (`transactions.csv` and `expenses.csv`), validates every row with mathematical consistency checks, stages records for review, stores valid data in MySQL, computes financial performance indicators with Pandas, executes six auditable loss detection rules, and presents data-linked recommendations on an interactive dashboard with downloadable PDF and CSV reports.

---

## 🚀 Quick Start on Windows with VS Code

### Prerequisites
1. **Python 3.10 or 3.11** installed from [python.org](https://www.python.org/) *(ensure "Add Python to PATH" is checked during setup)*.
2. **MySQL 8.0+** or **MariaDB 10.3+** installed and running on `localhost:3306` (e.g., via MySQL Community Server or XAMPP).
3. **VS Code** with Python extension.

---

### Step-by-Step Installation

#### 1. Open Project in VS Code
Open VS Code, press `Ctrl + Shift + \`` to open the integrated Terminal, and navigate to the project directory:
```bash
cd business-loss-detector
```

#### 2. Create and Activate Virtual Environment
```powershell
# Create venv
python -m venv venv

# Activate venv on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# (If PowerShell displays execution policy error, run once: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
```

#### 3. Install Pinned Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` in VS Code and adjust MySQL credentials to match your local installation:
```ini
SECRET_KEY=dev_loss_detector_secret_key_89234823904820394820
FLASK_ENV=development
FLASK_PORT=5000

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=loss_detector
DB_USER=root
DB_PASSWORD=your_mysql_password

TEST_DB_NAME=loss_detector_test
```

#### 5. Initialize Database Schema
Run the idempotent initialization script to create the `loss_detector` database and all 8 relational tables:
```bash
python init_db.py
```
*(Optional: initialize isolated test database with `python init_db.py --test`)*.

#### 6. Start the Flask Application
```bash
python app.py
```
Output:
```
Starting Loss Detection System on http://0.0.0.0:5000 ...
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

#### 7. Open the Web Browser
Open your browser and navigate to:
**`http://localhost:5000`** (or port 3000 if using reverse proxy gateway).

---

## 🖥️ What to Expect on Each Page

1. **Executive Dashboard (`/` or `/dashboard`)**:
   - **6 KPI Cards:** Sales Revenue, Product Cost (COGS), Gross Profit & Margin %, Operating Expenses, Net Operating Profit & Margin %, Flagged Loss Alerts.
   - **6 Interactive Chart.js Visualizations:**
     1. *Monthly Revenue vs Total Costs & Expenses* (Bar chart)
     2. *Monthly Profitability Trend* (Gross & Net Profit line chart)
     3. *Product-Wise Profitability* (Top 8 SKUs bar chart)
     4. *Operating Expense Distribution* (Overhead breakdown doughnut chart)
     5. *Monthly Sales Volume* (Units sold trend)
     6. *Discount Volume vs Realized Revenue* (Margin sacrifice tracking)
   - **Dynamic AJAX Filters:** Filter by Date Range and SKU with live re-rendering without page reload.
   - **Product Health Table:** SKU ranking with units sold, revenue, gross margin, closing inventory snapshot, and risk badges.

2. **Upload Dataset (`/upload`)**:
   - **Two-Step Staging Pipeline:** Upload `transactions.csv` and `expenses.csv` or click **"Load 6-Month Demo Dataset"** to immediately test verified real-world cases.
   - Download sample CSV templates directly from the UI.
   - Combined SHA-256 batch fingerprinting warns on duplicate uploads.

3. **Staging Review Page (`/upload/review/<token>`)**:
   - Displays accepted counts, rejected counts, and business warnings.
   - First 20 accepted rows table preview.
   - Full line-by-line rejected records table with exact rejection reasons.
   - **"Download Rejected Rows as CSV"** button.
   - Atomic **"Confirm & Run Analysis"** commits all records in one transaction.

4. **Financial Analysis (`/financial-analysis`)**:
   - Monthly P&L table with calendar-month revenue, costs, gross profit, operating expenses, and net profit margins.
   - Operating expense breakdown with overhead percentage shares.

5. **Product Analysis (`/product-analysis`)**:
   - Complete product performance audit table with units sold, average price, revenue, gross margin, and closing inventory snapshots.
   - Single SKU historical drill-down selector to inspect monthly unit economics.

6. **Loss Detection & Alerts (`/alerts`)**:
   - Interactive alerts list filterable by Severity (High, Medium, Low), Rule (R1 to R6), Month, and SKU.
   - Complete formula breakdown with substituted numbers and applied threshold on every card.
   - Related alert links connecting multiple rules triggered by the same product in a month.
   - Full **"How Severity is Decided"** deterministic classification matrix.

7. **Operational Recommendations (`/recommendations`)**:
   - Decision support center grouping alerts into High, Medium, and Low operational priorities.
   - Clear investigation checklists (supplier invoice audits, price testing, markdown controls, stock liquidation).

8. **Reports & Exports (`/reports`)**:
   - Downloadable formal executive PDF report built with **ReportLab** and **Matplotlib** charts.
   - Four formula-neutralized CSV exports (Product Performance, Monthly Trends, Expense Breakdown, Loss Alerts).

9. **Data Management (`/data-management`)**:
   - List all loaded batches, toggle active datasets, inspect rejection logs, re-run analysis idempotently, or cascade-delete batches.

10. **System Health (`/health`)**:
    - JSON endpoint reporting MySQL server connectivity, tables found, and engine status.

---

## 🧪 Running Automated Tests

Run the full automated test suite containing 23 comprehensive tests:
```bash
python -m pytest tests/ -v
```
All 23 tests pass in ~2.2 seconds across validation, financial math, boundary safeguards, rule detection, MySQL cascade integrity, and Flask route integration.

---

## 🎓 Viva Cheat Sheet (Examiner Reference)

### 1. Architecture in 5 Lines
- **Presentation Layer:** Semantic HTML5, CSS3 (navy/teal palette), Vanilla JavaScript, and Chart.js 4.4 (vendored locally for offline execution).
- **Application Layer:** Python 3.10+ with Flask application factory, Flask-WTF CSRF protection, and modular Blueprints.
- **Data Analytics Engine:** Pandas & NumPy executing deterministic, pure-function financial algorithms and guarded division.
- **Database Layer:** MySQL 8.0+ / MariaDB using InnoDB, utf8mb4 encoding, parameterized queries via PyMySQL, and atomic transactions.
- **Reporting Services:** ReportLab document generation with Matplotlib figures and DDE formula-neutralized CSV exporters.

### 2. The Six Detection Rules & Formulas

1. **R1: Loss-Making Product**
   $$\text{Condition: } \text{Sales Revenue} - \text{Product Cost} < 0$$
   - *Severity:* Margin $\le -20\%$ or zero revenue $\rightarrow$ **High**; Any other loss $\rightarrow$ **Medium**.
   - *Safeguards:* Loss amount = $\text{Cost} - \text{Revenue}$.

2. **R2: Low-Margin Product**
   $$\text{Condition: } 0 < \text{Gross Margin} < 10\% \quad (\text{Revenue} > 0)$$
   - *Severity:* Margin $< 5.0\% \rightarrow$ **Medium**; $5.0\%$ to $10.0\% \rightarrow$ **Low**.
   - *Boundary Safeguard:* Margin of exactly $10.0\%$ does NOT trigger.

3. **R3: Declining Sales Volume**
   $$\text{Condition: } \left(\frac{\text{Qty}_{\text{curr}} - \text{Qty}_{\text{prev}}}{\text{Qty}_{\text{prev}}}\right) \times 100 < -20\%$$
   - *Severity:* Decline $> 50\% \rightarrow$ **High**; $> 35\% \rightarrow$ **Medium**; $> 20\% \rightarrow$ **Low**.
   - *Safeguards:* Requires $\text{Qty}_{\text{prev}} \ge 10$ units; compares against preceding available sales month (skips gap months). Exactly $-19.0\%$ does NOT trigger.

4. **R4: Unusual Expense Increase**
   $$\text{Condition: } \left(\frac{\text{Exp}_{\text{curr}} - \text{Exp}_{\text{prev}}}{\text{Exp}_{\text{prev}}}\right) \times 100 > +30\%$$
   - *Severity:* Increase $> 100\% \rightarrow$ **High**; $> 50\% \rightarrow$ **Medium**; $> 30\% \rightarrow$ **Low**.
   - *Safeguards:* Requires $\text{Exp}_{\text{prev}} \ge ₹1,000$. Exactly $+29.0\%$ does NOT trigger.

5. **R5: Inventory Overstock Risk**
   $$\text{Condition: } \frac{\text{Closing Stock as of Month-End}}{\text{Trailing 3-Month Mean Monthly Sales}} > 3.0x$$
   - *Severity:* Ratio $\ge 6.0x \rightarrow$ **High**; $\ge 4.0x \rightarrow$ **Medium**; $> 3.0x \rightarrow$ **Low**.
   - *Safeguards:* Requires at least 3 months of sales history (`MIN_HISTORY_MONTHS = 3`). Exactly $3.0x$ does NOT trigger.

6. **R6: Discount Margin Risk**
   $$\text{Condition: } \text{Margin}_{\text{before}} - \text{Margin}_{\text{after}} > 15 \text{ percentage points}$$
   - *Severity:* Drop $> 30 \text{ points} \rightarrow$ **High**; $> 20 \text{ points} \rightarrow$ **Medium**; $> 15 \text{ points} \rightarrow$ **Low**.
   - *Safeguards:* Skipped if discount is 0. If revenue after discount is 0 with discount > 0, flags High. Exactly $15.0$ points does NOT trigger.

### 3. Core Data Flow Summary
1. `transactions.csv` & `expenses.csv` $\rightarrow$ Ingested in memory.
2. `analytics/data_validation.py` $\rightarrow$ Checks ISO dates, consistency $\text{qty} \times \text{price} - \text{discount} = \text{revenue}$, non-negativity.
3. `staging/{token}.json` $\rightarrow$ User reviews metrics, previews accepted rows, inspects rejections.
4. `database/operations.py` $\rightarrow$ Atomic commit across `datasets`, `products`, `sales_transactions`, `expenses`, `rejected_records`.
5. `analytics/financial_analysis.py` $\rightarrow$ Computes financial KPIs, monthly trends, and closing inventory snapshots.
6. `analytics/loss_detection.py` $\rightarrow$ Pure functions generate deduplicated alerts with substituted formulas.
7. `routes/` & `templates/` $\rightarrow$ Visualizes data with Chart.js, dynamic AJAX filters, and ReportLab PDF downloads.

### 4. Known Analytical Limitations
- Single-user local workstation architecture (no login system).
- Deterministic rule-based decision support system; flags historical anomalies and potential risks, not guaranteed future loss predictions.
- Store-wide operating expenses are recorded at business level and not allocated to individual SKUs.
- Sales returns and multi-currency are unsupported.
- Inventory is calculated as the latest recorded closing stock snapshot, never summed.
