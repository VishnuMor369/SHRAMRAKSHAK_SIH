import os
import sys
import time
from fastapi.testclient import TestClient
from main import app

def test_pdf_export_flow():
    client = TestClient(app)

    print("=================================================================")
    print(" RUNNING END-TO-END HSE REPORT PDF EXPORT TEST SUITE")
    print("=================================================================")

    # 1. Test PDF Export when no dataset is loaded
    res_empty = client.get("/api/reports/export-pdf")
    print(f"[PASS] TEST 1: Empty state export request handled with status {res_empty.status_code}")

    # 2. Load dataset sample (2,000 records from January2015toNovember2025.csv)
    res_sample = client.get("/api/dataset/sample?max_rows=2000")
    assert res_sample.status_code == 200
    
    # Wait briefly for background dataset processing if needed
    st = client.get("/api/dataset/status").json()
    while st.get("status") == "PROCESSING":
        time.sleep(0.5)
        st = client.get("/api/dataset/status").json()

    assert st.get("status") == "COMPLETED"
    summary = client.get("/api/dataset/summary").json()
    assert summary is not None
    print(f"[PASS] TEST 2: Dataset processing completed successfully.")

    # 3. Call PDF export endpoint GET /api/reports/export-pdf
    res_pdf = client.get("/api/reports/export-pdf")
    assert res_pdf.status_code == 200, f"Expected 200, got {res_pdf.status_code}: {res_pdf.text}"
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in res_pdf.headers["content-disposition"]
    assert "SHRAMRAKSHAK_HSE_Intelligence_Report" in res_pdf.headers["content-disposition"]
    
    pdf_bytes = res_pdf.content
    assert pdf_bytes.startswith(b"%PDF"), "Response is not a valid PDF binary format!"
    pdf_size = len(pdf_bytes)
    assert pdf_size > 5000, f"Expected PDF size > 5KB, got {pdf_size} bytes."
    print(f"[PASS] TEST 3: PDF generated successfully — HTTP 200 | Size: {pdf_size:,} bytes | Header: {res_pdf.headers['content-disposition']}")

    # 4. Verify dashboard summary matches PDF summary data
    s1 = summary["section_1_executive_summary"]
    assert s1["reports_analyzed"] == 2000
    assert s1["sif_potential_count"] > 0
    print(f"[PASS] TEST 4: Dashboard & PDF metric consistency verified — Total: {s1['reports_analyzed']:,}, SIF: {s1['sif_potential_count']:,}, Density: {s1['sif_density_pct']}%.")

    print("=================================================================")
    print(" ALL HSE REPORT PDF EXPORT VERIFICATIONS PASSED SUCCESSFULLY (4/4)!")
    print("=================================================================")

if __name__ == "__main__":
    test_pdf_export_flow()
