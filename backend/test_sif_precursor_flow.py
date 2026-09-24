import sys
import os
import time
from fastapi.testclient import TestClient

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from state import state_manager, get_sif_action_recommendation
from models import AlertActionRequest, AlertVerificationRequest

client = TestClient(app)

def test_sif_precursor_action_recommendations():
    """Test event-specific action recommendations across all hazard types."""
    print("\n--- TEST: SIF Precursor Action Recommendations ---")
    
    # 1. Lifting zone
    rec_lift = get_sif_action_recommendation("Restricted Lifting Zone", "CCTV", ["Suspended load"])
    assert rec_lift["verification_type"] == "CCTV_VERIFIABLE"
    assert "lift" in rec_lift["immediate_action"].lower() or "suspension" in rec_lift["immediate_action"].lower() or "halt" in rec_lift["immediate_action"].lower()
    assert rec_lift["sif_potential"] == "SIF Potential"
    assert rec_lift["sif_level"] in ["HIGH", "CRITICAL"]
    assert len(rec_lift["sif_why"]) > 0
    print("  [OK] Lifting Zone recommendation verified")

    # 2. Vehicle proximity
    rec_veh = get_sif_action_recommendation("Person–Vehicle Proximity", "CCTV", ["Vehicle within 3m"])
    assert rec_veh["verification_type"] == "CCTV_VERIFIABLE"
    assert "vehicle" in rec_veh["immediate_action"].lower() or "stop" in rec_veh["immediate_action"].lower()
    assert rec_veh["sif_potential"] == "SIF Potential"
    print("  [OK] Vehicle Proximity recommendation verified")

    # 3. Active fire
    rec_fire = get_sif_action_recommendation("Fire Detected", "CCTV", ["Open flame"])
    assert rec_fire["verification_type"] == "FIELD_HSE_VERIFICATION"
    assert "fire" in rec_fire["immediate_action"].lower() or "evacuate" in rec_fire["immediate_action"].lower()
    assert rec_fire["sif_level"] == "CRITICAL"
    print("  [OK] Fire Detection recommendation verified (Field HSE)")

    # 4. Working at height
    rec_height = get_sif_action_recommendation("Working at Height Hazard", "HSE_MANUAL", ["No harness"])
    assert rec_height["verification_type"] == "FIELD_HSE_VERIFICATION"
    assert "height" in rec_height["immediate_action"].lower() or "harness" in rec_height["immediate_action"].lower() or "stop" in rec_height["immediate_action"].lower()
    print("  [OK] Working at Height recommendation verified (Field HSE)")

    # 5. Electrical isolation
    rec_elec = get_sif_action_recommendation("Electrical Isolation Hazard", "HSE_MANUAL", ["Lockout tagout"])
    assert rec_elec["verification_type"] == "FIELD_HSE_VERIFICATION"
    assert "isolation" in rec_elec["immediate_action"].lower() or "stop" in rec_elec["immediate_action"].lower()
    print("  [OK] Electrical Isolation recommendation verified (Field HSE)")

    # 6. PPE
    rec_ppe = get_sif_action_recommendation("PPE Non-Compliance", "CCTV", ["NO HELMET"])
    assert rec_ppe["verification_type"] == "CCTV_VERIFIABLE"
    assert "ppe" in rec_ppe["immediate_action"].lower() or "helmet" in rec_ppe["immediate_action"].lower()
    print("  [OK] PPE Non-Compliance recommendation verified")

def test_sif_precursor_state_machine_flow():
    """Test full lifecycle: ASSIGNED -> IN_PROGRESS -> COMPLETED -> AWAITING_VERIFICATION -> FAILED -> COMPLETED -> VERIFIED."""
    print("\n--- TEST: SIF Precursor State Machine Lifecycle ---")
    
    # Trigger alert
    alert = state_manager.trigger_alert(
        alert_type="Restricted Zone Entry",
        severity="HIGH",
        source="CCTV",
        violations=["RESTRICTED ZONE"],
        camera="C-03",
        location="Drilling Floor - Zone 01",
        person_count=1,
        activity="Crane Rigging and Pipe Transfer"
    )
    alert_id = alert.id
    
    # 1. Initial State: ASSIGNED, PENDING
    assert alert.action_status == "ASSIGNED", f"Expected ASSIGNED, got {alert.action_status}"
    assert alert.verification_status == "PENDING", f"Expected PENDING, got {alert.verification_status}"
    assert alert.sif_potential in ["SIF Potential", True]
    assert alert.verification_type == "CCTV_VERIFIABLE"
    assert alert.immediate_action is not None
    assert alert.consequence_if_not_addressed is not None
    print(f"  [OK] 1. Alert {alert_id} created with action_status=ASSIGNED, verification_status=PENDING")

    # 2. Supervisor Acknowledges -> IN_PROGRESS
    alert = state_manager.respond_to_alert("SUP-01", "Supervisor en route to secure exclusion zone", alert_id)
    assert alert.action_status == "IN_PROGRESS", f"Expected IN_PROGRESS, got {alert.action_status}"
    assert alert.verification_status == "PENDING"
    print(f"  [OK] 2. Alert acknowledged -> action_status=IN_PROGRESS")

    # 3. Supervisor Takes Action -> COMPLETED & AWAITING_VERIFICATION
    alert = state_manager.mark_action_taken(alert_id, "SUP-01", "Personnel moved out of zone, barricade secured", "Exclusion zone cleared")
    assert alert.action_status == "COMPLETED", f"Expected COMPLETED, got {alert.action_status}"
    assert alert.verification_status == "AWAITING_VERIFICATION", f"Expected AWAITING_VERIFICATION, got {alert.verification_status}"
    assert alert.action_taken_by == "SUP-01"
    assert alert.action_taken_at is not None
    print(f"  [OK] 3. Action marked taken -> action_status=COMPLETED, verification_status=AWAITING_VERIFICATION")

    # 4. Verification Fails -> re-opens to IN_PROGRESS & FAILED
    alert = state_manager.verify_alert(alert_id, "SUP-01", decision="FAILED", verification_method="CCTV_VERIFIED", notes="Worker re-entered zone")
    assert alert.action_status == "IN_PROGRESS", f"Expected IN_PROGRESS on fail, got {alert.action_status}"
    assert alert.verification_status == "FAILED", f"Expected FAILED, got {alert.verification_status}"
    print(f"  [OK] 4. Verification FAILED -> reopens action_status=IN_PROGRESS, verification_status=FAILED")

    # 5. Supervisor Takes Action Again -> COMPLETED & AWAITING_VERIFICATION
    alert = state_manager.mark_action_taken(alert_id, "SUP-01", "Worker re-instructed and supervisor posted guard", "Guard posted")
    assert alert.action_status == "COMPLETED"
    assert alert.verification_status == "AWAITING_VERIFICATION"
    print(f"  [OK] 5. Action taken again -> COMPLETED & AWAITING_VERIFICATION")

    # 6. Verification Verified -> VERIFIED & RESOLVED
    alert = state_manager.verify_alert(alert_id, "SUP-01", decision="VERIFIED", verification_method="CCTV_VERIFIED", notes="Live CCTV confirms zone is 100% clear")
    assert alert.action_status == "COMPLETED"
    assert alert.verification_status == "VERIFIED"
    assert alert.status == "RESOLVED"
    assert alert.verified_by == "SUP-01"
    assert alert.verified_at is not None
    print(f"  [OK] 6. Formally VERIFIED -> verification_status=VERIFIED, status=RESOLVED")

def test_kpi_counts_in_system_status():
    """Test dynamic KPI counts in SystemStatus."""
    print("\n--- TEST: Dynamic KPI Counts in SystemStatus ---")
    status = state_manager.get_system_status()
    assert hasattr(status, 'sif_potential_count')
    assert hasattr(status, 'open_actions_count')
    assert hasattr(status, 'awaiting_verification_count')
    assert hasattr(status, 'verified_count')
    print(f"  [OK] KPI fields present:")
    print(f"       - SIF Potential Count: {status.sif_potential_count}")
    print(f"       - Open Actions Count: {status.open_actions_count}")
    print(f"       - Awaiting Verification Count: {status.awaiting_verification_count}")
    print(f"       - Verified Count: {status.verified_count}")

def test_api_routes():
    """Test REST API endpoints for action and verification."""
    print("\n--- TEST: REST API Endpoints ---")
    
    # Create an alert
    alert = state_manager.trigger_alert(
        alert_type="Person–Vehicle Proximity",
        severity="CRITICAL",
        source="CCTV",
        violations=["PERSON-VEHICLE PROXIMITY"],
        camera="C-02",
        location="Loading Bay"
    )
    alert_id = alert.id

    # Test POST /api/alert/respond
    res_resp = client.post("/api/alert/respond", json={"supervisor_id": "SUP-TEST", "notes": "Responding"})
    assert res_resp.status_code == 200, res_resp.text
    print(f"  [OK] POST /api/alert/respond succeeded")

    # Test POST /api/alert/action
    res_act = client.post("/api/alert/action", json={
        "supervisor_id": "SUP-TEST",
        "notes": "Vehicle halted and distance established",
        "action_taken": "Vehicle stop executed",
        "alert_id": alert_id
    })
    assert res_act.status_code == 200, res_act.text
    data_act = res_act.json()
    assert data_act["alert"]["action_status"] == "COMPLETED"
    assert data_act["alert"]["verification_status"] == "AWAITING_VERIFICATION"
    print(f"  [OK] POST /api/alert/action succeeded")

    # Test POST /api/alert/verify
    res_ver = client.post("/api/alert/verify", json={
        "supervisor_id": "SUP-TEST",
        "decision": "VERIFIED",
        "verification_method": "CCTV_VERIFIED",
        "notes": "CCTV shows 5m clearance maintained",
        "alert_id": alert_id
    })
    assert res_ver.status_code == 200, res_ver.text
    data_ver = res_ver.json()
    assert data_ver["alert"]["verification_status"] == "VERIFIED"
    assert data_ver["alert"]["status"] == "RESOLVED"
    print(f"  [OK] POST /api/alert/verify succeeded")

    # Test GET /api/status includes new KPI fields
    res_stat = client.get("/api/status")
    assert res_stat.status_code == 200
    stat_json = res_stat.json()
    assert "sif_potential_count" in stat_json
    assert "open_actions_count" in stat_json
    assert "awaiting_verification_count" in stat_json
    assert "verified_count" in stat_json
    print(f"  [OK] GET /api/status returns all 4 KPI fields")

if __name__ == "__main__":
    print("==================================================================")
    print(" SHRAMRAKSHAK: SIF PRECURSOR ACTION & VERIFICATION TEST SUITE")
    print("==================================================================")
    test_sif_precursor_action_recommendations()
    test_sif_precursor_state_machine_flow()
    test_kpi_counts_in_system_status()
    test_api_routes()
    print("\n==================================================================")
    print(" ALL SIF PRECURSOR FLOW TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("==================================================================")
