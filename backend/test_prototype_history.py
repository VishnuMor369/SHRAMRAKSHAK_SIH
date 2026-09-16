import os
import sys
from fastapi.testclient import TestClient
from main import app
from state import state_manager
from models import Alert

def run_tests():
    client = TestClient(app)

    print("=================================================================")
    print(" VERIFYING CLEAN ABSENCE OF DUMMY DATA & STABILITY OF REAL PIPELINE")
    print("=================================================================")

    # 1. Start clean and add a genuine CCTV event to verify CCTV engine stays intact
    state_manager.reset_demo()
    test_cctv_alert = Alert(
        id="ALT-ZONE-CCTV-001",
        type="Restricted Zone Entry",
        location="Demo Lifting Area",
        camera="C-01",
        hazard="Unauthorized Personnel in Active Lifting Perimeter",
        status="RESOLVED",
        created_at="2026-09-09T14:35:00",
        response_deadline="2026-09-09T14:35:20"
    )
    state_manager.history.append(test_cctv_alert)

    # 2. Check initial reports
    res_init = client.get("/api/reports/generated")
    assert res_init.status_code == 200
    data_init = res_init.json()
    assert data_init["total"] >= 1
    cctv_reports = [r for r in data_init["reports"] if r["source"] == "CCTV_EVENT"]
    proto_reports = [r for r in data_init["reports"] if r.get("source") == "PROTOTYPE_HISTORY"]
    assert len(proto_reports) == 0
    print(f"[PASS] TEST 1: Clean state verified — 0 PROTOTYPE_HISTORY dummy records present, {len(cctv_reports)} CCTV event intact.")

    # 3. Verify dataset sample loader works for real dataset
    res_sample = client.get("/api/dataset/sample?max_rows=100")
    assert res_sample.status_code == 200
    data_sample = res_sample.json()
    assert "quality_report" in data_sample
    assert data_sample["quality_report"]["total_rows"] >= 100
    print(f"[PASS] TEST 2: Real dataset engine successfully loaded {data_sample['quality_report']['total_rows']} OIL dataset records.")

    print("=================================================================")
    print(" ALL DUMMY DATA CLEANUP VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=================================================================")

if __name__ == "__main__":
    run_tests()
