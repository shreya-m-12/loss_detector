-- Schema for Business Loss Detection and Decision Support System
-- MySQL 8.0+ / MariaDB 10.3+ compatible, utf8mb4 charset, InnoDB engine

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS businesses (
    business_id INT AUTO_INCREMENT PRIMARY KEY,
    business_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    source_type ENUM('upload', 'sample') NOT NULL DEFAULT 'upload',
    sales_filename VARCHAR(255) NOT NULL,
    expense_filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    total_rows INT NOT NULL DEFAULT 0,
    accepted_rows INT NOT NULL DEFAULT 0,
    rejected_rows INT NOT NULL DEFAULT 0,
    date_min DATE NULL,
    date_max DATE NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_datasets_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE CASCADE,
    INDEX idx_datasets_business (business_id),
    INDEX idx_datasets_active (is_active),
    INDEX idx_datasets_hash (file_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    normalized_name VARCHAR(100) NOT NULL,
    CONSTRAINT fk_products_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE CASCADE,
    UNIQUE KEY uq_business_normalized_name (business_id, normalized_name),
    INDEX idx_products_business (business_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sales_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    business_id INT NOT NULL,
    product_id INT NOT NULL,
    transaction_date DATE NOT NULL,
    quantity_sold DECIMAL(12, 3) NOT NULL,
    selling_price DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    sales_revenue DECIMAL(14, 2) NOT NULL,
    product_cost DECIMAL(14, 2) NOT NULL,
    inventory_quantity DECIMAL(12, 3) NOT NULL,
    row_fingerprint VARCHAR(64) NOT NULL,
    CONSTRAINT fk_sales_dataset FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    CONSTRAINT fk_sales_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE CASCADE,
    CONSTRAINT fk_sales_product FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE,
    INDEX idx_sales_dataset_date (dataset_id, transaction_date),
    INDEX idx_sales_dataset_product (dataset_id, product_id),
    INDEX idx_sales_business (business_id),
    INDEX idx_sales_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    business_id INT NOT NULL,
    expense_date DATE NOT NULL,
    expense_category VARCHAR(100) NOT NULL,
    expense_amount DECIMAL(14, 2) NOT NULL,
    CONSTRAINT fk_expenses_dataset FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    CONSTRAINT fk_expenses_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE CASCADE,
    INDEX idx_expenses_dataset_date (dataset_id, expense_date),
    INDEX idx_expenses_dataset_category (dataset_id, expense_category),
    INDEX idx_expenses_business (business_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rejected_records (
    rejected_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    source_file ENUM('transactions', 'expenses') NOT NULL,
    line_number INT NOT NULL,
    raw_data JSON NOT NULL,
    reason TEXT NOT NULL,
    CONSTRAINT fk_rejected_dataset FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    INDEX idx_rejected_dataset (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    business_id INT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    period_start DATE NULL,
    period_end DATE NULL,
    total_revenue DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    total_product_cost DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    total_expenses DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    gross_profit DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    net_profit DECIMAL(14, 2) NOT NULL DEFAULT 0.00,
    alert_count INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_reports_dataset FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    CONSTRAINT fk_reports_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE CASCADE,
    INDEX idx_reports_dataset (dataset_id),
    INDEX idx_reports_business (business_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT NULL,
    dataset_id INT NOT NULL,
    rule_code VARCHAR(10) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subject_type ENUM('product', 'expense_category') NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    period_month VARCHAR(7) NOT NULL,
    severity ENUM('Low', 'Medium', 'High') NOT NULL,
    trigger_values JSON NOT NULL,
    threshold_json JSON NOT NULL,
    explanation TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alerts_report FOREIGN KEY (report_id) REFERENCES analysis_reports (report_id) ON DELETE SET NULL,
    CONSTRAINT fk_alerts_dataset FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE,
    UNIQUE KEY uq_dataset_rule_subject_period (dataset_id, rule_code, subject_name, period_month),
    INDEX idx_alerts_dataset (dataset_id),
    INDEX idx_alerts_rule (rule_code),
    INDEX idx_alerts_severity (severity),
    INDEX idx_alerts_period (period_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
