"""
CSV Export service with formula injection neutralization.
Safeguards spreadsheet applications against CSV formula injection (DDE attacks).
"""
import csv
import io

def neutralize_cell(value) -> str:
    """
    Prevents CSV injection by prepending a single quote if the value begins
    with '=', '+', '-', '@', or tab/CR characters.
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        # For purely numeric negative values (e.g. -20.5), keep number readable,
        # but for string formulas or non-numeric negative text, neutralize.
        try:
            float(val_str)
            return val_str
        except ValueError:
            return f"'{val_str}"
    return val_str

def generate_csv_string(headers: list, rows: list) -> str:
    """
    Produces a CSV string with UTF-8 BOM for Excel compatibility on Windows.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([neutralize_cell(h) for h in headers])
    
    # Write rows
    for row in rows:
        if isinstance(row, dict):
            row_vals = [row.get(h, "") for h in headers]
        else:
            row_vals = row
        writer.writerow([neutralize_cell(v) for v in row_vals])
        
    return output.getvalue()
