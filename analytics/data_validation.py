"""
Data validation module for transactions.csv and expenses.csv.
Enforces strict schema contracts, ISO dates, mathematical consistency,
rejection logging with exact line numbers, and warnings for business edge cases.
"""
import csv
import io
import hashlib
import json
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

def normalize_column_name(col: str) -> str:
    """Normalize column header to lowercase with underscores, stripping whitespace and quotes."""
    clean = re.sub(r"[^\w\s]", "", str(col).strip())
    return re.sub(r"\s+", "_", clean).lower()

def normalize_text_val(text) -> str:
    """Normalize text: strip, collapse internal whitespace, case-preserved for display."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip())

def parse_iso_date(date_str: str):
    """
    Validates strictly ISO YYYY-MM-DD.
    Rejects DD/MM/YYYY or MM/DD/YYYY with informative error.
    """
    if not date_str or not isinstance(date_str, str):
        return None, "Date is empty"
    date_str = date_str.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return None, f"Invalid date format '{date_str}'. Must strictly be ISO format YYYY-MM-DD."
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
        return parsed, None
    except ValueError:
        return None, f"Invalid calendar date '{date_str}'. Check month and day values."

def parse_decimal(val_str, field_name: str):
    """Parses a numeric string to Decimal, rejecting non-numerics."""
    if val_str is None or str(val_str).strip() == "":
        return None, f"Missing or blank value for '{field_name}'"
    clean = str(val_str).strip().replace(",", "")
    try:
        d = Decimal(clean)
        return d, None
    except InvalidOperation:
        return None, f"Non-numeric value '{val_str}' in numeric field '{field_name}'"

def read_csv_content(file_bytes: bytes) -> tuple:
    """
    Reads CSV bytes using utf-8-sig with fallback to cp1252.
    Auto-detects comma or semicolon delimiter.
    """
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("cp1252")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")

    # Delimiter detection
    first_lines = "\n".join(text.splitlines()[:5])
    delimiter = ","
    if ";" in first_lines and first_lines.count(";") > first_lines.count(","):
        delimiter = ";"

    return text, delimiter

def validate_transactions_csv(file_bytes: bytes, today: date = None) -> dict:
    """
    Validates transactions.csv according to Section 2.1 and 3.
    Returns {
        'total_rows': int,
        'accepted_rows': list,
        'rejected_rows': list,
        'warnings': list,
        'date_min': str,
        'date_max': str
    }
    """
    if today is None:
        today = date.today()

    text, delimiter = read_csv_content(file_bytes)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    try:
        headers_raw = next(reader)
    except StopIteration:
        return {
            "error": "The transactions file is empty.",
            "total_rows": 0, "accepted_rows": [], "rejected_rows": [], "warnings": []
        }

    headers = [normalize_column_name(h) for h in headers_raw]
    required = [
        "transaction_date", "product_name", "quantity_sold",
        "selling_price", "sales_revenue", "product_cost", "inventory_quantity"
    ]
    missing = [req for req in required if req not in headers]
    if missing:
        return {
            "error": f"transactions.csv is missing required columns: {', '.join(missing)}",
            "total_rows": 0, "accepted_rows": [], "rejected_rows": [], "warnings": []
        }

    col_idx = {name: i for i, name in enumerate(headers)}
    accepted = []
    rejected = []
    warnings = []
    seen_fingerprints = set()

    line_number = 1
    for row in reader:
        line_number += 1
        if not row or all(c.strip() == "" for c in row):
            continue  # skip empty lines

        raw_dict = {headers_raw[i]: row[i] if i < len(row) else "" for i in range(len(headers_raw))}

        # 1. Check missing values in required columns
        row_errors = []
        for req in required:
            idx = col_idx[req]
            if idx >= len(row) or row[idx].strip() == "":
                row_errors.append(f"Missing required field '{req}'")

        if row_errors:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "; ".join(row_errors)
            })
            continue

        # 2. Parse Date
        date_raw = row[col_idx["transaction_date"]].strip()
        tx_date, date_err = parse_iso_date(date_raw)
        if date_err:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": date_err
            })
            continue

        if tx_date > today:
            warnings.append(f"Line {line_number}: Future transaction date '{date_raw}' detected.")

        # 3. Product Name
        prod_name = normalize_text_val(row[col_idx["product_name"]])
        if not prod_name:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "product_name cannot be empty"
            })
            continue

        if len(prod_name) > 100:
            prod_name = prod_name[:100]

        # 4. Numerics
        qty, qty_err = parse_decimal(row[col_idx["quantity_sold"]], "quantity_sold")
        price, price_err = parse_decimal(row[col_idx["selling_price"]], "selling_price")
        rev, rev_err = parse_decimal(row[col_idx["sales_revenue"]], "sales_revenue")
        cost, cost_err = parse_decimal(row[col_idx["product_cost"]], "product_cost")
        inv, inv_err = parse_decimal(row[col_idx["inventory_quantity"]], "inventory_quantity")

        # Optional discount_amount
        disc = Decimal("0.00")
        if "discount_amount" in col_idx and col_idx["discount_amount"] < len(row):
            disc_str = row[col_idx["discount_amount"]].strip()
            if disc_str:
                d_val, d_err = parse_decimal(disc_str, "discount_amount")
                if d_err:
                    row_errors.append(d_err)
                else:
                    disc = d_val

        for err in [qty_err, price_err, rev_err, cost_err, inv_err]:
            if err:
                row_errors.append(err)

        if row_errors:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "; ".join(row_errors)
            })
            continue

        # 5. Non-negativity & Quantity > 0
        if qty <= Decimal("0"):
            row_errors.append(f"quantity_sold must be strictly positive (got {qty}); returns not supported")
        if price < Decimal("0"):
            row_errors.append(f"selling_price cannot be negative (got {price})")
        if disc < Decimal("0"):
            row_errors.append(f"discount_amount cannot be negative (got {disc})")
        if rev < Decimal("0"):
            row_errors.append(f"sales_revenue cannot be negative (got {rev})")
        if cost < Decimal("0"):
            row_errors.append(f"product_cost cannot be negative (got {cost})")
        if inv < Decimal("0"):
            row_errors.append(f"inventory_quantity cannot be negative (got {inv})")

        if row_errors:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "; ".join(row_errors)
            })
            continue

        # 6. Consistency Checks
        # Derived: revenue_before_discount = quantity_sold * selling_price
        rev_before = (qty * price).quantize(Decimal("0.01"))
        if disc > rev_before:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": f"discount_amount ({disc}) cannot exceed revenue_before_discount ({rev_before})"
            })
            continue

        diff = abs(rev_before - disc - rev)
        if diff > Decimal("0.01"):
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": f"revenue does not equal quantity x price - discount: {qty} * {price} - {disc} = {rev_before - disc}, but sales_revenue is {rev}"
            })
            continue

        # 7. Duplicate Row Detection
        tx_ref = ""
        if "transaction_ref" in col_idx and col_idx["transaction_ref"] < len(row):
            tx_ref = row[col_idx["transaction_ref"]].strip()

        if tx_ref:
            fingerprint = f"{date_raw}|{prod_name}|{tx_ref}"
        else:
            fingerprint = f"{date_raw}|{prod_name}|{qty}|{price}|{disc}|{rev}|{cost}|{inv}"

        if fingerprint in seen_fingerprints:
            rejected.append({
                "source_file": "transactions",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "Duplicate row within transactions file"
            })
            continue
        seen_fingerprints.add(fingerprint)

        # 8. Business Warnings (accepted rows)
        if cost > rev:
            warnings.append(f"Line {line_number}: product_cost ({cost}) exceeds sales_revenue ({rev}) for '{prod_name}'. Flagged as loss.")
        if rev == Decimal("0"):
            warnings.append(f"Line {line_number}: zero revenue on '{prod_name}'.")
        if price == Decimal("0"):
            warnings.append(f"Line {line_number}: selling price of 0 for '{prod_name}'.")
        if rev_before > Decimal("0") and (disc / rev_before) > Decimal("0.50"):
            warnings.append(f"Line {line_number}: discount exceeds 50% for '{prod_name}'.")

        accepted.append({
            "transaction_date": str(tx_date),
            "product_name": prod_name,
            "quantity_sold": float(qty),
            "selling_price": float(price),
            "discount_amount": float(disc),
            "sales_revenue": float(rev),
            "product_cost": float(cost),
            "inventory_quantity": float(inv),
            "transaction_ref": tx_ref,
            "row_fingerprint": hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16],
            "line_number": line_number,
        })

    dates = [r["transaction_date"] for r in accepted]
    return {
        "error": None,
        "total_rows": len(accepted) + len(rejected),
        "accepted_rows": accepted,
        "rejected_rows": rejected,
        "warnings": warnings,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }

def validate_expenses_csv(file_bytes: bytes, today: date = None) -> dict:
    """
    Validates expenses.csv according to Section 2.2 and 3.
    """
    if today is None:
        today = date.today()

    text, delimiter = read_csv_content(file_bytes)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    try:
        headers_raw = next(reader)
    except StopIteration:
        return {
            "error": "The expenses file is empty.",
            "total_rows": 0, "accepted_rows": [], "rejected_rows": [], "warnings": []
        }

    headers = [normalize_column_name(h) for h in headers_raw]
    required = ["expense_date", "expense_category", "expense_amount"]
    missing = [req for req in required if req not in headers]
    if missing:
        return {
            "error": f"expenses.csv is missing required columns: {', '.join(missing)}",
            "total_rows": 0, "accepted_rows": [], "rejected_rows": [], "warnings": []
        }

    col_idx = {name: i for i, name in enumerate(headers)}
    accepted = []
    rejected = []
    warnings = []
    seen_fingerprints = set()

    line_number = 1
    for row in reader:
        line_number += 1
        if not row or all(c.strip() == "" for c in row):
            continue

        raw_dict = {headers_raw[i]: row[i] if i < len(row) else "" for i in range(len(headers_raw))}

        # 1. Missing values
        row_errors = []
        for req in required:
            idx = col_idx[req]
            if idx >= len(row) or row[idx].strip() == "":
                row_errors.append(f"Missing required field '{req}'")

        if row_errors:
            rejected.append({
                "source_file": "expenses",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "; ".join(row_errors)
            })
            continue

        # 2. Date
        date_raw = row[col_idx["expense_date"]].strip()
        exp_date, date_err = parse_iso_date(date_raw)
        if date_err:
            rejected.append({
                "source_file": "expenses",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": date_err
            })
            continue

        if exp_date > today:
            warnings.append(f"Line {line_number}: Future expense date '{date_raw}' detected.")

        # 3. Category
        cat_name = normalize_text_val(row[col_idx["expense_category"]])
        if not cat_name:
            rejected.append({
                "source_file": "expenses",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "expense_category cannot be empty"
            })
            continue

        # 4. Amount
        amt, amt_err = parse_decimal(row[col_idx["expense_amount"]], "expense_amount")
        if amt_err:
            rejected.append({
                "source_file": "expenses",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": amt_err
            })
            continue

        if amt <= Decimal("0"):
            rejected.append({
                "source_file": "expenses",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": f"expense_amount must be strictly positive (got {amt})"
            })
            continue

        # 5. Duplicates
        fingerprint = f"{date_raw}|{cat_name.lower()}|{amt}"
        if fingerprint in seen_fingerprints:
            rejected.append({
                "source_file": "expenses",
                "line_number": line_number,
                "raw_data": raw_dict,
                "reason": "Duplicate row within expenses file"
            })
            continue
        seen_fingerprints.add(fingerprint)

        accepted.append({
            "expense_date": str(exp_date),
            "expense_category": cat_name,
            "expense_amount": float(amt),
            "line_number": line_number,
        })

    dates = [r["expense_date"] for r in accepted]
    return {
        "error": None,
        "total_rows": len(accepted) + len(rejected),
        "accepted_rows": accepted,
        "rejected_rows": rejected,
        "warnings": warnings,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }

def compute_combined_hash(sales_bytes: bytes, expense_bytes: bytes) -> str:
    """Computes SHA-256 fingerprint of the combined uploaded files to detect duplicate batches."""
    h = hashlib.sha256()
    h.update(sales_bytes)
    h.update(b"|EXPENSE_SEPARATOR|")
    h.update(expense_bytes)
    return h.hexdigest()
