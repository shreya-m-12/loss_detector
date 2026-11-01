"""
Database operations for Business Loss Detection System.
All queries are parameterized to prevent SQL injection.
Transactions are strictly managed with atomic commits and rollbacks.
"""
import json
import re
from decimal import Decimal
import pandas as pd
from database.connection import get_db

def normalize_text(text: str) -> str:
    """Normalize text: strip, collapse multiple internal spaces, case-insensitive comparison."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip()).lower()

def get_active_dataset(conn=None):
    """Fetch the currently active dataset row, or None."""
    db = conn or get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM datasets 
            WHERE is_active = 1 
            ORDER BY uploaded_at DESC 
            LIMIT 1
            """
        )
        return cursor.fetchone()

def list_datasets(conn=None):
    """List all loaded datasets with row counts and date spans."""
    db = conn or get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT d.*, b.business_name,
                   (SELECT COUNT(*) FROM alerts a WHERE a.dataset_id = d.dataset_id) AS alert_count
            FROM datasets d
            JOIN businesses b ON d.business_id = b.business_id
            ORDER BY d.uploaded_at DESC
            """
        )
        return cursor.fetchall()

def get_dataset_by_id(dataset_id: int, conn=None):
    db = conn or get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM datasets WHERE dataset_id = %s", (dataset_id,))
        return cursor.fetchone()

def find_dataset_by_hash(file_hash: str, conn=None):
    db = conn or get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM datasets WHERE file_hash = %s LIMIT 1", (file_hash,))
        return cursor.fetchone()

def set_active_dataset(dataset_id: int, conn=None):
    """Deactivate all datasets and set the chosen one to active."""
    db = conn or get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("UPDATE datasets SET is_active = 0")
            cursor.execute("UPDATE datasets SET is_active = 1 WHERE dataset_id = %s", (dataset_id,))
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e

def delete_dataset(dataset_id: int, conn=None):
    """Delete a dataset and cascade deletion to sales, expenses, rejected, and alerts."""
    db = conn or get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM datasets WHERE dataset_id = %s", (dataset_id,))
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e

def get_or_create_products(business_id: int, product_tuples: list, conn=None):
    """
    Ensure all products exist in products table and return a mapping of normalized_name -> product_id.
    product_tuples: list of (display_name, normalized_name)
    """
    db = conn or get_db()
    product_map = {}
    with db.cursor() as cursor:
        # Fetch existing products
        cursor.execute("SELECT product_id, normalized_name FROM products WHERE business_id = %s", (business_id,))
        for row in cursor.fetchall():
            product_map[row["normalized_name"]] = row["product_id"]

        new_products = []
        for display_name, norm_name in product_tuples:
            if norm_name not in product_map:
                new_products.append((business_id, display_name, norm_name))
                # Temporary placeholder to avoid duplicates in list
                product_map[norm_name] = None

        if new_products:
            cursor.executemany(
                """
                INSERT IGNORE INTO products (business_id, product_name, normalized_name)
                VALUES (%s, %s, %s)
                """,
                new_products,
            )
            # Re-fetch newly inserted IDs
            cursor.execute("SELECT product_id, normalized_name FROM products WHERE business_id = %s", (business_id,))
            for row in cursor.fetchall():
                product_map[row["normalized_name"]] = row["product_id"]

    return product_map

def commit_staged_dataset(dataset_meta: dict, sales_rows: list, expense_rows: list, rejected_rows: list, conn=None):
    """
    Atomic transaction committing a validated dataset:
    1. Insert dataset record
    2. Upsert products
    3. Bulk insert sales_transactions
    4. Bulk insert expenses
    5. Bulk insert rejected_records
    6. Mark dataset as active
    """
    db = conn or get_db()
    try:
        with db.cursor() as cursor:
            # 1. Insert dataset row
            cursor.execute(
                """
                INSERT INTO datasets (
                    business_id, dataset_name, source_type, sales_filename, expense_filename,
                    file_hash, total_rows, accepted_rows, rejected_rows, date_min, date_max, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    dataset_meta.get("business_id", 1),
                    dataset_meta.get("dataset_name", "Uploaded Dataset"),
                    dataset_meta.get("source_type", "upload"),
                    dataset_meta.get("sales_filename", "transactions.csv"),
                    dataset_meta.get("expense_filename", "expenses.csv"),
                    dataset_meta.get("file_hash", ""),
                    dataset_meta.get("total_rows", 0),
                    dataset_meta.get("accepted_rows", 0),
                    dataset_meta.get("rejected_rows", 0),
                    dataset_meta.get("date_min"),
                    dataset_meta.get("date_max"),
                    1,  # Set as active
                ),
            )
            dataset_id = cursor.lastrowid

            # Deactivate previous active datasets
            cursor.execute("UPDATE datasets SET is_active = 0 WHERE dataset_id != %s", (dataset_id,))

            # 2. Prepare and resolve products
            unique_products = {}
            for row in sales_rows:
                pname = row["product_name"]
                norm = normalize_text(pname)
                if norm not in unique_products:
                    unique_products[norm] = pname

            prod_tuples = [(pname, norm) for norm, pname in unique_products.items()]
            prod_map = get_or_create_products(dataset_meta.get("business_id", 1), prod_tuples, conn=db)

            # 3. Bulk insert sales_transactions
            if sales_rows:
                sales_insert_data = []
                for row in sales_rows:
                    norm = normalize_text(row["product_name"])
                    pid = prod_map[norm]
                    sales_insert_data.append((
                        dataset_id,
                        dataset_meta.get("business_id", 1),
                        pid,
                        row["transaction_date"],
                        row["quantity_sold"],
                        row["selling_price"],
                        row.get("discount_amount", 0.0),
                        row["sales_revenue"],
                        row["product_cost"],
                        row["inventory_quantity"],
                        row.get("row_fingerprint", ""),
                    ))
                cursor.executemany(
                    """
                    INSERT INTO sales_transactions (
                        dataset_id, business_id, product_id, transaction_date,
                        quantity_sold, selling_price, discount_amount, sales_revenue,
                        product_cost, inventory_quantity, row_fingerprint
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    sales_insert_data,
                )

            # 4. Bulk insert expenses
            if expense_rows:
                exp_insert_data = [
                    (
                        dataset_id,
                        dataset_meta.get("business_id", 1),
                        row["expense_date"],
                        row["expense_category"],
                        row["expense_amount"],
                    )
                    for row in expense_rows
                ]
                cursor.executemany(
                    """
                    INSERT INTO expenses (
                        dataset_id, business_id, expense_date, expense_category, expense_amount
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    exp_insert_data,
                )

            # 5. Bulk insert rejected_records
            if rejected_rows:
                rej_insert_data = [
                    (
                        dataset_id,
                        row["source_file"],
                        row["line_number"],
                        json.dumps(row["raw_data"]),
                        row["reason"],
                    )
                    for row in rejected_rows
                ]
                cursor.executemany(
                    """
                    INSERT INTO rejected_records (
                        dataset_id, source_file, line_number, raw_data, reason
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    rej_insert_data,
                )

        db.commit()
        return dataset_id
    except Exception as exc:
        db.rollback()
        raise exc

def get_rejected_records(dataset_id: int, source_file=None, conn=None):
    db = conn or get_db()
    with db.cursor() as cursor:
        if source_file:
            cursor.execute(
                """
                SELECT * FROM rejected_records 
                WHERE dataset_id = %s AND source_file = %s
                ORDER BY line_number ASC
                """,
                (dataset_id, source_file),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM rejected_records 
                WHERE dataset_id = %s
                ORDER BY source_file, line_number ASC
                """,
                (dataset_id,),
            )
        rows = cursor.fetchall()
        for r in rows:
            if isinstance(r.get("raw_data"), str):
                try:
                    r["raw_data"] = json.loads(r["raw_data"])
                except Exception:
                    pass
        return rows

def store_analysis_report(dataset_id: int, summary: dict, alerts_list: list, conn=None):
    """
    Idempotently stores the report summary and alerts for a dataset.
    Deletes existing report & alerts for this dataset before inserting new ones.
    """
    db = conn or get_db()
    try:
        with db.cursor() as cursor:
            # Delete existing alerts and reports for this dataset
            cursor.execute("DELETE FROM alerts WHERE dataset_id = %s", (dataset_id,))
            cursor.execute("DELETE FROM analysis_reports WHERE dataset_id = %s", (dataset_id,))

            # Insert new report row
            cursor.execute(
                """
                INSERT INTO analysis_reports (
                    dataset_id, business_id, period_start, period_end,
                    total_revenue, total_product_cost, total_expenses,
                    gross_profit, net_profit, alert_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    dataset_id,
                    summary.get("business_id", 1),
                    summary.get("period_start"),
                    summary.get("period_end"),
                    summary.get("total_revenue", 0.0),
                    summary.get("total_product_cost", 0.0),
                    summary.get("total_expenses", 0.0),
                    summary.get("gross_profit", 0.0),
                    summary.get("net_profit", 0.0),
                    len(alerts_list),
                ),
            )
            report_id = cursor.lastrowid

            # Insert alerts
            if alerts_list:
                alert_insert_data = [
                    (
                        report_id,
                        dataset_id,
                        alert["rule_code"],
                        alert["category"],
                        alert["subject_type"],
                        alert["subject_name"],
                        alert["period_month"],
                        alert["severity"],
                        json.dumps(alert["trigger_values"]),
                        json.dumps(alert["threshold_json"]),
                        alert["explanation"],
                        alert["recommendation"],
                    )
                    for alert in alerts_list
                ]
                cursor.executemany(
                    """
                    INSERT INTO alerts (
                        report_id, dataset_id, rule_code, category,
                        subject_type, subject_name, period_month, severity,
                        trigger_values, threshold_json, explanation, recommendation
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    alert_insert_data,
                )

        db.commit()
        return report_id
    except Exception as exc:
        db.rollback()
        raise exc

def get_alerts_for_dataset(dataset_id: int, filters: dict = None, conn=None):
    db = conn or get_db()
    sql = "SELECT * FROM alerts WHERE dataset_id = %s"
    params = [dataset_id]

    if filters:
        if filters.get("severity"):
            sql += " AND severity = %s"
            params.append(filters["severity"])
        if filters.get("rule_code"):
            sql += " AND rule_code = %s"
            params.append(filters["rule_code"])
        if filters.get("month"):
            sql += " AND period_month = %s"
            params.append(filters["month"])
        if filters.get("product"):
            sql += " AND subject_type = 'product' AND subject_name = %s"
            params.append(filters["product"])
        if filters.get("category"):
            sql += " AND category = %s"
            params.append(filters["category"])

    sql += " ORDER BY FIELD(severity, 'High', 'Medium', 'Low'), period_month DESC, rule_code ASC"

    with db.cursor() as cursor:
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for r in rows:
            if isinstance(r.get("trigger_values"), str):
                try:
                    r["trigger_values"] = json.loads(r["trigger_values"])
                except Exception:
                    pass
            if isinstance(r.get("threshold_json"), str):
                try:
                    r["threshold_json"] = json.loads(r["threshold_json"])
                except Exception:
                    pass
        return rows

def load_sales_dataframe(dataset_id: int, conn=None) -> pd.DataFrame:
    """Load sales transactions with product names into a Pandas DataFrame."""
    db = conn or get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                s.transaction_id,
                s.transaction_date,
                p.product_name,
                p.normalized_name,
                CAST(s.quantity_sold AS DOUBLE) AS quantity_sold,
                CAST(s.selling_price AS DOUBLE) AS selling_price,
                CAST(s.discount_amount AS DOUBLE) AS discount_amount,
                CAST(s.sales_revenue AS DOUBLE) AS sales_revenue,
                CAST(s.product_cost AS DOUBLE) AS product_cost,
                CAST(s.inventory_quantity AS DOUBLE) AS inventory_quantity,
                s.row_fingerprint
            FROM sales_transactions s
            JOIN products p ON s.product_id = p.product_id
            WHERE s.dataset_id = %s
            ORDER BY s.transaction_date ASC, s.transaction_id ASC
            """,
            (dataset_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return pd.DataFrame(columns=[
            "transaction_id", "transaction_date", "product_name", "normalized_name",
            "quantity_sold", "selling_price", "discount_amount", "sales_revenue",
            "product_cost", "inventory_quantity", "row_fingerprint"
        ])
    df = pd.DataFrame(rows)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    return df

def load_expenses_dataframe(dataset_id: int, conn=None) -> pd.DataFrame:
    """Load operating expenses into a Pandas DataFrame."""
    db = conn or get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                expense_id,
                expense_date,
                expense_category,
                CAST(expense_amount AS DOUBLE) AS expense_amount
            FROM expenses
            WHERE dataset_id = %s
            ORDER BY expense_date ASC, expense_id ASC
            """,
            (dataset_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return pd.DataFrame(columns=["expense_id", "expense_date", "expense_category", "expense_amount"])
    df = pd.DataFrame(rows)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    return df
