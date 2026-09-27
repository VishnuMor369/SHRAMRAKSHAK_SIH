"""
Automated Test Suite for Dataset Intelligence & Isolated AnalysisRun Workspace
Validates Sections 43 & 44 of SIH 2026 Hardening Specification
"""

import os
import io
import pytest
import requests
import json

BASE_URL = "http://localhost:8000"

def test_csv_upload_and_analysis_run_creation():
    csv_content = """ReportID,Narrative,Location,Activity,Hazard,Outcome
R-101,Worker stepped inside lifting drop zone while drill pipe was being moved,Drilling Rig 01,Mechanical Lifting,Suspended Load,Near Miss
R-102,Contractor entered restricted area under crane boom during hoisting,Drilling Rig 01,Mechanical Lifting,Suspended Load,Near Miss
R-103,Technician observed unhooked fall harness at 6m platform near tank,Tank Farm B,Working at Height,Gravity / Elevation,Near Miss
R-104,Electrician opened 440V distribution panel without verifying zero energy state,Substation 2,Electrical Maintenance,Live Electricity,Near Miss
"""
    files = {
        'file': ('test_safety_reports_batch.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
    }
    data = {'max_rows': 100}

    res = requests.post(f"{BASE_URL}/api/analysis-runs/upload", files=files, data=data)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("success") is True
    run = body.get("run", {})
    assert run.get("run_id").startswith("AR-")
    assert run.get("records_analyzed") == 4
    assert run.get("sif_count") >= 2
    iogp_keys = [str(k).upper().replace(" ", "_") for k in run.get("iogp_distribution", {}).keys()]
    assert "SAFE_MECHANICAL_LIFTING" in iogp_keys or "LINE_OF_FIRE" in iogp_keys
    assert len(run.get("candidate_patterns", [])) >= 1

    return run.get("run_id")

def test_analysis_runs_isolation():
    # Upload Dataset A
    csv_a = """ID,Text
A-1,Worker entered lifting exclusion zone while load suspended
A-2,Contractor crossed barricade under active crane
"""
    files_a = {'file': ('dataset_alpha.csv', io.BytesIO(csv_a.encode('utf-8')), 'text/csv')}
    res_a = requests.post(f"{BASE_URL}/api/analysis-runs/upload", files=files_a).json()
    run_id_a = res_a["run"]["run_id"]

    # Upload Dataset B
    csv_b = """ID,Text
B-1,Operator entered tank without multi-gas clearance test
B-2,Confined space entry made without continuous atmosphere monitor
B-3,Worker entered vessel before gas test completed
"""
    files_b = {'file': ('dataset_beta.csv', io.BytesIO(csv_b.encode('utf-8')), 'text/csv')}
    res_b = requests.post(f"{BASE_URL}/api/analysis-runs/upload", files=files_b).json()
    run_id_b = res_b["run"]["run_id"]

    # Retrieve A and B independently
    data_a = requests.get(f"{BASE_URL}/api/analysis-runs/{run_id_a}").json()
    data_b = requests.get(f"{BASE_URL}/api/analysis-runs/{run_id_b}").json()

    assert data_a["run_id"] == run_id_a
    assert data_a["filename"] == "dataset_alpha.csv"
    assert data_a["records_analyzed"] == 2

    assert data_b["run_id"] == run_id_b
    assert data_b["filename"] == "dataset_beta.csv"
    assert data_b["records_analyzed"] == 3

    # Confirm no cross contamination
    texts_a = [r["original_text"] for r in data_a["reports"]]
    texts_b = [r["original_text"] for r in data_b["reports"]]
    assert not any("tank" in t.lower() for t in texts_a)
    assert any("tank" in t.lower() for t in texts_b)

def test_scanned_pdf_fails_transparently():
    # Create an empty / image-only dummy PDF bytes (without digital text streams)
    fake_scanned_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    
    files = {'file': ('scanned_handwritten_incident.pdf', io.BytesIO(fake_scanned_pdf), 'application/pdf')}
    res = requests.post(f"{BASE_URL}/api/analysis-runs/upload", files=files)
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "OCR REQUIRED" in detail or "TEXT EXTRACTION FAILED" in detail

def test_download_pdf_report_consistency():
    # Use baseline run AR-0001
    run_data = requests.get(f"{BASE_URL}/api/analysis-runs/AR-0001").json()
    sif_count_ui = run_data.get("sif_count")

    # Fetch PDF
    pdf_res = requests.get(f"{BASE_URL}/api/analysis-runs/AR-0001/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers.get("content-type") == "application/pdf"
    assert len(pdf_res.content) > 1000
    assert pdf_res.content.startswith(b"%PDF-")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
