# Data Dictionary (DATA_DICTIONARY.md)

This dictionary defines all entity tables, columns, data types, constraints, and operational business meanings.

---

## 1. Table: `businesses`
Stores registered retail business profiles (single-user default seeded).

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `business_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `business_name` | VARCHAR(255) | NO | None | Name of retail business (e.g., 'Corner Store Mart') |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation timestamp |

---

## 2. Table: `datasets`
Tracks batch uploads and active datasets.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `dataset_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `business_id` | INT | NO | None | Foreign Key referencing `businesses(business_id)` |
| `dataset_name` | VARCHAR(255) | NO | 'Uploaded Dataset' | User-provided batch name |
| `source_type` | ENUM('upload','sample') | NO | 'upload' | Upload method |
| `sales_filename` | VARCHAR(255) | NO | None | Original transactions file name |
| `expense_filename` | VARCHAR(255) | NO | None | Original expenses file name |
| `file_hash` | VARCHAR(64) | NO | None | SHA-256 hash of combined file contents |
| `total_rows` | INT | NO | 0 | Total lines parsed |
| `accepted_rows` | INT | NO | 0 | Valid lines committed |
| `rejected_rows` | INT | NO | 0 | Invalid lines rejected |
| `date_min` | DATE | YES | NULL | Earliest date in batch |
| `date_max` | DATE | YES | NULL | Latest date in batch |
| `is_active` | TINYINT(1) | NO | 0 | 1 if active dataset for analysis, 0 otherwise |
| `uploaded_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Commit timestamp |

---

## 3. Table: `products`
Master catalog of normalized retail products per business.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `product_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `business_id` | INT | NO | None | Foreign Key referencing `businesses(business_id)` |
| `product_name` | VARCHAR(100) | NO | None | Display product name from first occurrence |
| `normalized_name` | VARCHAR(100) | NO | None | Whitespace-collapsed lowercase comparison key |

*Constraints:* `UNIQUE KEY (business_id, normalized_name)`

---

## 4. Table: `sales_transactions`
Individual line item product sales.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `transaction_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `dataset_id` | INT | NO | None | Foreign Key referencing `datasets(dataset_id)` |
| `business_id` | INT | NO | None | Foreign Key referencing `businesses(business_id)` |
| `product_id` | INT | NO | None | Foreign Key referencing `products(product_id)` |
| `transaction_date` | DATE | NO | None | ISO YYYY-MM-DD transaction date |
| `quantity_sold` | DECIMAL(12,3) | NO | None | Number of units or weight sold (> 0) |
| `selling_price` | DECIMAL(12,2) | NO | None | List price per unit before discounts |
| `discount_amount` | DECIMAL(12,2) | NO | 0.00 | Total discount surrendered on this line |
| `sales_revenue` | DECIMAL(14,2) | NO | None | Realized revenue after discount |
| `product_cost` | DECIMAL(14,2) | NO | None | Total wholesale acquisition cost for this sale |
| `inventory_quantity` | DECIMAL(12,3) | NO | None | Closing inventory snapshot after sale |
| `row_fingerprint` | VARCHAR(64) | NO | None | Hash fingerprint to prevent exact file duplicates |

---

## 5. Table: `expenses`
Operational store overhead records.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `expense_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `dataset_id` | INT | NO | None | Foreign Key referencing `datasets(dataset_id)` |
| `business_id` | INT | NO | None | Foreign Key referencing `businesses(business_id)` |
| `expense_date` | DATE | NO | None | ISO YYYY-MM-DD expense date |
| `expense_category` | VARCHAR(100) | NO | None | Category (Rent, Salaries, Utilities, etc.) |
| `expense_amount` | DECIMAL(14,2) | NO | None | Incurred expense amount (> 0) |

---

## 6. Table: `rejected_records`
Audit log of rejected CSV lines.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `rejected_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `dataset_id` | INT | NO | None | Foreign Key referencing `datasets(dataset_id)` |
| `source_file` | ENUM('transactions','expenses') | NO | None | File source |
| `line_number` | INT | NO | None | Original CSV row line number |
| `raw_data` | JSON | NO | None | Raw dictionary of row values |
| `reason` | TEXT | NO | None | Specific validation failure message |

---

## 7. Table: `analysis_reports`
Audit summaries generated per dataset analysis.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `report_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `dataset_id` | INT | NO | None | Foreign Key referencing `datasets(dataset_id)` |
| `business_id` | INT | NO | None | Foreign Key referencing `businesses(business_id)` |
| `generated_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Analysis timestamp |
| `period_start` | DATE | YES | NULL | Period start date |
| `period_end` | DATE | YES | NULL | Period end date |
| `total_revenue` | DECIMAL(14,2) | NO | 0.00 | Realized top-line revenue |
| `total_product_cost` | DECIMAL(14,2) | NO | 0.00 | Cost of goods sold |
| `total_expenses` | DECIMAL(14,2) | NO | 0.00 | Store operating overheads |
| `gross_profit` | DECIMAL(14,2) | NO | 0.00 | Revenue - Product Cost |
| `net_profit` | DECIMAL(14,2) | NO | 0.00 | Gross Profit - Expenses |
| `alert_count` | INT | NO | 0 | Total alerts triggered |

---

## 8. Table: `alerts`
Persistent anomalies and decision-support recommendations.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `alert_id` | INT | NO | AUTO_INCREMENT | Primary Key |
| `report_id` | INT | YES | NULL | Foreign Key referencing `analysis_reports(report_id)` |
| `dataset_id` | INT | NO | None | Foreign Key referencing `datasets(dataset_id)` |
| `rule_code` | VARCHAR(10) | NO | None | Rule code (R1 - R6) |
| `category` | VARCHAR(100) | NO | None | Category (Profitability, Inventory, etc.) |
| `subject_type` | ENUM('product','expense_category') | NO | None | Subject classification |
| `subject_name` | VARCHAR(100) | NO | None | Product name or expense category |
| `period_month` | VARCHAR(7) | NO | None | Calendar month (YYYY-MM) |
| `severity` | ENUM('Low','Medium','High') | NO | None | Deterministic severity level |
| `trigger_values` | JSON | NO | None | Key-value pairs of triggering inputs |
| `threshold_json` | JSON | NO | None | Threshold parameters applied |
| `explanation` | TEXT | NO | None | Transparent explanation with formula |
| `recommendation` | TEXT | NO | None | Actionable operational recommendation |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Detection timestamp |

*Constraints:* `UNIQUE KEY (dataset_id, rule_code, subject_name, period_month)`
