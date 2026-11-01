"""
Route integration tests for Flask application.
Verifies health endpoint, sample loader flow, reports, CSV exports, and PDF generation.
"""
import pytest

def test_health_route(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"]["status"] == "ok"
    assert data["rules_active"] == 6

def test_dashboard_empty_and_upload_pages(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Executive Dashboard" in res.data

    res_upload = client.get("/upload", follow_redirects=True)
    assert res_upload.status_code == 200
    assert b"Upload Store CSV Files" in res_upload.data

def test_sample_dataset_flow(client):
    # Step 1: Load sample into staging
    res = client.post("/upload/load-sample", follow_redirects=True)
    assert res.status_code == 200
    assert b"Ready to Commit Dataset" in res.data
    assert b"Accepted Sales Transactions" in res.data

    # Extract staging token from review URL
    token = None
    for hist in res.history:
        if "/upload/review/" in hist.headers.get("Location", ""):
            token = hist.headers["Location"].split("/")[-1]
            break

    assert token is not None, "Staging review redirect token not found"

    # Step 2: Confirm staging commit
    res_confirm = client.post(f"/upload/confirm/{token}", follow_redirects=True)
    assert res_confirm.status_code == 200
    assert b"committed successfully" in res_confirm.data or b"Executive Dashboard" in res_confirm.data

    # Step 3: Check Dashboard displays metrics and charts
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert b"Sales Revenue" in res_dash.data
    assert b"Imported Olive Oil 1L" in res_dash.data

    # Step 4: Check API JSON filtering endpoint
    res_api = client.get("/api/dashboard-data")
    assert res_api.status_code == 200
    api_data = res_api.get_json()
    assert api_data["success"] is True
    assert "kpis" in api_data
    assert "charts" in api_data
    assert len(api_data["products_perf"]) > 0

    # Step 5: Check Financial & Product Analysis pages
    res_fin = client.get("/financial-analysis")
    assert res_fin.status_code == 200
    assert b"Monthly Financial Statement" in res_fin.data

    res_prod = client.get("/product-analysis")
    assert res_prod.status_code == 200
    assert b"Product Catalog Performance Audit" in res_prod.data

    # Step 6: Check Alerts and Recommendations pages
    res_alerts = client.get("/alerts")
    assert res_alerts.status_code == 200
    assert b"Flagged Operational Loss Alerts" in res_alerts.data

    res_recs = client.get("/recommendations")
    assert res_recs.status_code == 200
    assert b"Operational Recommendations" in res_recs.data

    # Step 7: Check PDF Report generation
    res_pdf = client.get("/reports/download-pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.mimetype == "application/pdf"
    assert res_pdf.data.startswith(b"%PDF"), "Response is not a valid PDF file"

    # Step 8: Check CSV exports
    res_p_csv = client.get("/reports/export/products-csv")
    assert res_p_csv.status_code == 200
    assert b"Product Name" in res_p_csv.data

    res_m_csv = client.get("/reports/export/monthly-csv")
    assert res_m_csv.status_code == 200
    assert b"Revenue (INR)" in res_m_csv.data

    # Step 9: Check Data Management page
    res_dm = client.get("/data-management")
    assert res_dm.status_code == 200
    assert b"Loaded Datasets" in res_dm.data
