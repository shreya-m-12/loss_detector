# Entity-Relationship Diagram (ER_DIAGRAM.md)

The following Mermaid diagram visualizes the relational schema of the Business Loss Detection and Decision Support System, showing foreign keys, cardinality, and cascade deletion paths.

```mermaid
erDiagram
    BUSINESSES ||--o{ DATASETS : "owns"
    BUSINESSES ||--o{ PRODUCTS : "catalogs"
    BUSINESSES ||--o{ SALES_TRANSACTIONS : "records"
    BUSINESSES ||--o{ EXPENSES : "incurs"
    BUSINESSES ||--o{ ANALYSIS_REPORTS : "receives"

    DATASETS ||--o{ SALES_TRANSACTIONS : "contains"
    DATASETS ||--o{ EXPENSES : "contains"
    DATASETS ||--o{ REJECTED_RECORDS : "logs"
    DATASETS ||--o{ ANALYSIS_REPORTS : "evaluates"
    DATASETS ||--o{ ALERTS : "triggers"

    PRODUCTS ||--o{ SALES_TRANSACTIONS : "transacts"

    ANALYSIS_REPORTS ||--o{ ALERTS : "summarizes"

    BUSINESSES {
        int business_id PK
        string business_name
        timestamp created_at
    }

    DATASETS {
        int dataset_id PK
        int business_id FK
        string dataset_name
        string source_type
        string sales_filename
        string expense_filename
        string file_hash
        int total_rows
        int accepted_rows
        int rejected_rows
        date date_min
        date date_max
        tinyint is_active
        timestamp uploaded_at
    }

    PRODUCTS {
        int product_id PK
        int business_id FK
        string product_name
        string normalized_name
    }

    SALES_TRANSACTIONS {
        int transaction_id PK
        int dataset_id FK
        int business_id FK
        int product_id FK
        date transaction_date
        decimal quantity_sold
        decimal selling_price
        decimal discount_amount
        decimal sales_revenue
        decimal product_cost
        decimal inventory_quantity
        string row_fingerprint
    }

    EXPENSES {
        int expense_id PK
        int dataset_id FK
        int business_id FK
        date expense_date
        string expense_category
        decimal expense_amount
    }

    REJECTED_RECORDS {
        int rejected_id PK
        int dataset_id FK
        string source_file
        int line_number
        json raw_data
        text reason
    }

    ANALYSIS_REPORTS {
        int report_id PK
        int dataset_id FK
        int business_id FK
        timestamp generated_at
        date period_start
        date period_end
        decimal total_revenue
        decimal total_product_cost
        decimal total_expenses
        decimal gross_profit
        decimal net_profit
        int alert_count
    }

    ALERTS {
        int alert_id PK
        int report_id FK
        int dataset_id FK
        string rule_code
        string category
        string subject_type
        string subject_name
        string period_month
        string severity
        json trigger_values
        json threshold_json
        text explanation
        text recommendation
        timestamp created_at
    }
```
