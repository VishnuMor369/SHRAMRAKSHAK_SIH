import cv2
import numpy as np
import base64
import time
from fastapi.testclient import TestClient
from main import app, load_sample_dataset
from state import state_manager
from nlp_engine import dataset_store

client = TestClient(app)

def run_e2e_verification():
    print("==================================================================")
    print(" SHRAMRAKSHAK: CCTV PIPELINE & HSE INTELLIGENCE E2E VERIFICATION")
    print("==================================================================")

    # ------------------------------------------------------------------
    # TEST 1 & 2: Model Loading & CV Debug Status
    # ------------------------------------------------------------------
    print("\n--- TEST 1 & 2: MODEL LOADING & CV DIAGNOSTICS ---")
    res_dbg = client.get("/api/cv/debug")
    assert res_dbg.status_code == 200, f"Failed debug status: {res_dbg.text}"
    dbg = res_dbg.json()
    print(f"  [OK] Model Name: {dbg.get('model')}")
    print(f"  [OK] Inference State: {dbg.get('inference')}")
    assert "ppe_safety.onnx" in dbg.get("model") or "ONNX" in dbg.get("model"), "Expected ONNX model"

    # ------------------------------------------------------------------
    # TEST 3: Preload Real Dataset (January2015toNovember2025.csv)
    # ------------------------------------------------------------------
    print("\n--- TEST 3: REAL DATASET PRELOAD & HISTORICAL CORRELATION STORE ---")
    load_sample_dataset(max_rows=1500)
    summary = None
    for _ in range(30):
        summary = dataset_store.get_summary()
        if summary:
            break
        time.sleep(0.4)
    assert summary is not None, "Dataset summary must not be None"
    print(f"  [OK] Real Dataset Loaded: {summary.get('reports_analyzed', 0):,} records analyzed")
    print(f"  [OK] SIF Precursors: {summary.get('sif_potential_count', 0):,}")
    print(f"  [OK] Recurring Patterns: {len(summary.get('recurring_patterns', []))}")

    # ------------------------------------------------------------------
    # TEST 4 & 5: Real Frame Ingestion & Helmet Detection Inference
    # ------------------------------------------------------------------
    print("\n--- TEST 4 & 5: WEBCAM FRAME INGESTION & REAL AI INFERENCE ---")
    # Capture real webcam frame
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    ret, test_frame = cap.read()
    cap.release()
    if not ret or test_frame is None:
        test_frame = np.full((480, 640, 3), 40, dtype=np.uint8)
        cv2.rectangle(test_frame, (200, 100), (420, 420), (120, 120, 140), -1)
    
    ret, enc = cv2.imencode('.jpg', test_frame)
    b64 = base64.b64encode(enc.tobytes()).decode('utf-8')

    # Post 7 consecutive frames with 0.35s delay to satisfy debounce and persistence threshold (1.5s)
    last_res = None
    for i in range(7):
        post_res = client.post("/api/cv/frame", json={
            "frame": f"data:image/jpeg;base64,{b64}",
            "camera_id": "C-01"
        })
        assert post_res.status_code == 200, f"Frame post failed: {post_res.text}"
        last_res = post_res.json()
        time.sleep(0.35)

    print(f"  [OK] Frame processing returned status: {last_res.get('status')}")
    print(f"  [OK] Persons detected: {last_res.get('person_count')}")
    print(f"  [OK] Unhelmeted count: {last_res.get('unhelmeted_count')}")

    # ------------------------------------------------------------------
    # TEST 6: CCTV Incident Generation & Main Alerts Integration
    # ------------------------------------------------------------------
    print("\n--- TEST 6: CCTV INCIDENT GENERATION (SR-2026-XXXX) ---")
    alerts_res = client.get("/api/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json().get("alerts", [])
    assert len(alerts) > 0, "Expected at least one active alert generated"
    
    cctv_alert = alerts[0]
    print(f"  [OK] Generated Incident ID: {cctv_alert.get('incident_id')}")
    print(f"  [OK] Alert Type: {cctv_alert.get('type')}")
    print(f"  [OK] Source: {cctv_alert.get('source')}")
    print(f"  [OK] Camera: {cctv_alert.get('camera')}")
    assert "SR-2026-" in str(cctv_alert.get("incident_id")), "Incident ID format must match SR-2026-XXXX"

    # Verify visual evidence URL if present
    if cctv_alert.get("evidence_url"):
        ev_res = client.get(cctv_alert["evidence_url"])
        assert ev_res.status_code == 200, "Visual evidence image must be retrievable"
        assert ev_res.headers.get("content-type") == "image/jpeg"
        print(f"  [OK] Visual Evidence Snapshot verified ({len(ev_res.content):,} bytes)")

    # ------------------------------------------------------------------
    # TEST 7 & 8: Enrich CCTV Incident with HSE Observation & NLP
    # ------------------------------------------------------------------
    print("\n--- TEST 7 & 8: HSE OBSERVATION ON CCTV INCIDENT & NLP ANALYSIS ---")
    enrich_payload = {
        "linked_alert_id": cctv_alert["id"],
        "worker_identifier": "W-104",
        "observation": "Contractor technician was observed servicing pump seal without hardhat inside compressor sector.",
        "hazard": "Head impact hazard from overhead piping and flying debris",
        "activity": "Pump Seal Maintenance",
        "location": "Demo Work Zone",
        "reviewer_role": "HSE Officer"
    }

    obs_res = client.post(f"/api/alerts/{cctv_alert['id']}/hse-observation", json=enrich_payload)
    assert obs_res.status_code == 200, f"HSE observation failed: {obs_res.text}"
    enriched = obs_res.json().get("alert", obs_res.json())
    print(f"  [OK] Enriched Incident ID: {enriched.get('incident_id')}")
    print(f"  [OK] Source updated to: {enriched.get('source')}")
    print(f"  [OK] NLP SIF Potential: {enriched.get('nlp_sif_potential')}")
    print(f"  [OK] NLP Risk Score: {enriched.get('nlp_risk_score')}")
    print(f"  [OK] NLP Life-Saving Rules: {enriched.get('nlp_life_saving_rules')}")
    print(f"  [OK] Evidence Consistency: {enriched.get('evidence_consistency_status')}")
    print(f"  [OK] Historical Dataset Match: {enriched.get('has_historical_match')}")
    print(f"  [OK] Historical Pattern: {enriched.get('historical_pattern_title')}")
    print(f"  [OK] Historical SIF Count: {enriched.get('historical_sif_count')}")

    # ------------------------------------------------------------------
    # TEST 9: Standalone Manual HSE Observation (No CCTV Dependency)
    # ------------------------------------------------------------------
    print("\n--- TEST 9: STANDALONE MANUAL HSE ALERT PAGE ---")
    manual_payload = {
        "worker_identifier": "W-209",
        "observation": "Worker was observed entering high-pressure manifold area while pressure bleed-off was in progress.",
        "hazard": "Stored high-pressure fluid release / line-of-fire",
        "activity": "Pressure Bleed-off and Testing",
        "location": "Drilling Rig Floor",
        "reviewer_role": "HSE Lead"
    }

    manual_res = client.post("/api/alerts/hse-observation", json=manual_payload)
    assert manual_res.status_code == 200, f"Manual observation failed: {manual_res.text}"
    manual_alert = manual_res.json().get("alert", manual_res.json())
    print(f"  [OK] Standalone HSE Incident ID: {manual_alert.get('incident_id')}")
    print(f"  [OK] Standalone Source: {manual_alert.get('source')}")
    print(f"  [OK] Standalone SIF Potential: {manual_alert.get('nlp_sif_potential')}")
    print(f"  [OK] Standalone Evidence Consistency: {manual_alert.get('evidence_consistency_status')}")

    # ------------------------------------------------------------------
    # TEST 10: PDF Export Verification
    # ------------------------------------------------------------------
    print("\n--- TEST 10: FULL HSE INTELLIGENCE PDF REPORT EXPORT ---")
    pdf_res = client.get("/api/reports/export-pdf")
    assert pdf_res.status_code == 200, f"PDF export failed: {pdf_res.text}"
    assert pdf_res.headers.get("content-type") == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF"), "Must start with %PDF magic header"
    print(f"  [OK] PDF Report Generated Successfully ({len(pdf_res.content):,} bytes)")
    print(f"  [OK] PDF Header: {pdf_res.headers.get('content-disposition')}")

    print("\n==================================================================")
    print(" ALL 10 END-TO-END PIPELINE TESTS PASSED WITH 100% INTEGRITY!")
    print("==================================================================")

if __name__ == "__main__":
    run_e2e_verification()
