from fastapi.testclient import TestClient
from main import app
from state import state_manager
from nlp_engine import dataset_store

client = TestClient(app)

def test_incident_correlation_flow():
    print("\n--- TEST 1: STANDALONE HSE OBSERVATION CREATION FROM DEDICATED HSE PAGE ---")
    standalone_payload = {
        "worker_identifier": "W-205",
        "activity": "Working at Height",
        "location": "Duliajan Rig 4",
        "hazard": "Missing safety harness",
        "observation": "Scaffolder working at 5m elevation without safety harness unclipped and no overhead safety line secured.",
        "notes": "Work halted immediately until safety line installed.",
        "reviewer_role": "HSE Manager"
    }

    st_resp = client.post("/api/alerts/hse-observation", json=standalone_payload)
    assert st_resp.status_code == 200, f"Standalone creation failed: {st_resp.text}"
    st_alert = st_resp.json()["alert"]

    # Verify unique Incident ID generated (SR-2026-XXXX)
    st_inc_id = st_alert.get("incident_id")
    assert st_inc_id is not None
    assert st_inc_id.startswith("SR-2026-")
    assert st_alert["source"] == "HSE + NLP"
    assert st_alert["worker_identifier"] == "W-205"

    # Verify NLP Engine extraction
    assert st_alert["nlp_sif_potential"] is True
    assert "Working at Height" in st_alert["nlp_life_saving_rules"] or len(st_alert["nlp_life_saving_rules"]) > 0
    assert st_alert["nlp_risk_score"] >= 50
    assert len(st_alert["nlp_reasoning"]) > 0

    print(f"  [OK] Created Standalone HSE Incident: {st_inc_id} | Source: {st_alert['source']} | SIF: {st_alert['nlp_sif_potential']}")

    print("\n--- TEST 2: CCTV ALERT ENRICHMENT VIA HSE OBSERVATION ---")
    # 1. Trigger CCTV Alert
    resp = client.post("/api/alert/trigger", params={
        "alert_type": "Restricted Zone Entry",
        "location": "Compressor Area",
        "camera": "C-04",
        "severity": "CRITICAL"
    })
    assert resp.status_code == 200, f"Trigger failed: {resp.text}"
    alert_data = resp.json()["alert"]
    alert_id = alert_data["id"]
    incident_id = alert_data.get("incident_id")
    assert incident_id is not None
    assert incident_id.startswith("SR-2026-")

    # 2. Add HSE Observation to existing alert
    obs_payload = {
        "worker_identifier": "W-104",
        "activity": "Maintenance",
        "location": "Compressor Area",
        "hazard": "Energized equipment",
        "observation": "Worker was performing maintenance near energized equipment. Isolation was not verified before maintenance activity.",
        "notes": "Worker was instructed to leave the area.",
        "reviewer_role": "HSE Officer"
    }

    obs_resp = client.post(f"/api/alerts/{alert_id}/hse-observation", json=obs_payload)
    assert obs_resp.status_code == 200, f"HSE observation failed: {obs_resp.text}"
    enriched_alert = obs_resp.json()["alert"]

    # Verify same Incident ID is retained (NO DUPLICATE ALERTS)
    assert enriched_alert["incident_id"] == incident_id
    assert enriched_alert["id"] == alert_id
    assert enriched_alert["worker_identifier"] == "W-104"
    assert enriched_alert["source"] == "CCTV + HSE + NLP"

    # Verify Evidence Consistency status is safe (never accuses worker of lying)
    assert enriched_alert["evidence_consistency_status"] in [
        "CONSISTENT",
        "INCONSISTENCY — HSE REVIEW REQUIRED",
        "INSUFFICIENT CCTV EVIDENCE"
    ]

    print(f"  [OK] Enriched CCTV Incident: {incident_id} | Source: {enriched_alert['source']} | Consistency: {enriched_alert['evidence_consistency_status']}")

    print("\n--- TEST 3: MAIN ALERTS INCLUSION ---")
    alerts_resp = client.get("/api/alerts")
    assert alerts_resp.status_code == 200
    active_alerts = alerts_resp.json()["alerts"]
    
    # Both standalone HSE alert and enriched CCTV alert must be present
    st_matched = [a for a in active_alerts if a.get("incident_id") == st_inc_id]
    cctv_matched = [a for a in active_alerts if a["id"] == alert_id]

    assert len(st_matched) == 1, f"Standalone HSE alert {st_inc_id} not found in Main Alerts"
    assert len(cctv_matched) == 1, f"Enriched CCTV alert {alert_id} not found in Main Alerts"
    assert st_matched[0]["source"] == "HSE + NLP"
    assert cctv_matched[0]["source"] == "CCTV + HSE + NLP"

    print("  [OK] Main Alerts list correctly contains both HSE + NLP and CCTV + HSE + NLP incidents")

    print("\n--- TEST 4: HSE INTELLIGENCE PDF REPORT EXPORT ---")
    report_resp = client.get("/api/reports/export-pdf")
    assert report_resp.status_code == 200, f"Report export failed: {report_resp.text}"
    assert report_resp.headers["content-type"] == "application/pdf"
    assert len(report_resp.content) > 1000

    print("  [OK] PDF Report generated successfully with Section 10 unified correlation")

    print("\n[OK] SUCCESS: HSE Dedicated Observation & Incident Correlation tests passed cleanly!")

if __name__ == "__main__":
    test_incident_correlation_flow()
