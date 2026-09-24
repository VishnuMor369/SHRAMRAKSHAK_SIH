import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import app

client = TestClient(app)

def run_simulation_e2e():
    print("==================================================================")
    print(" SHRAMRAKSHAK: END-TO-END SIF PRECURSOR SIMULATION FLOW (PHASE 11)")
    print("==================================================================")

    # 1. Reset Demo
    print("\n--- STEP 1: RESET DEMO STATE ---")
    res_reset = client.post("/api/demo/reset")
    assert res_reset.status_code == 200, res_reset.text
    print("  [OK] Demo state cleanly reset to IDLE/MONITORING")

    # 2. Simulate Zone Breach / SIF Precursor
    print("\n--- STEP 2: SIMULATE RESTRICTED ZONE BREACH ---")
    res_breach = client.post("/api/demo/simulate-breach")
    assert res_breach.status_code == 200, res_breach.text
    breach_data = res_breach.json()
    alert = breach_data.get("alert")
    assert alert is not None, "Expected alert object in simulation response"
    alert_id = alert["id"]
    print(f"  [OK] Simulated breach triggered: Alert ID {alert_id}")
    print(f"       - Event ID: {alert.get('event_id')}")
    print(f"       - SIF Potential: {alert.get('sif_potential')}")
    print(f"       - SIF Level: {alert.get('sif_level')}")
    print(f"       - Immediate Action: {alert.get('immediate_action')}")
    print(f"       - Action Status: {alert.get('action_status')}")
    print(f"       - Verification Status: {alert.get('verification_status')}")
    assert alert.get("sif_potential") == "SIF Potential", f"Expected 'SIF Potential', got {alert.get('sif_potential')}"
    assert alert.get("action_status") == "ASSIGNED"
    assert alert.get("verification_status") == "PENDING"
    assert alert.get("immediate_action") is not None
    assert alert.get("consequence_if_not_addressed") is not None

    # 3. Check System Status reflects 1 Active Alert and SIF Precursor
    print("\n--- STEP 3: VERIFY DASHBOARD SYSTEM STATUS ---")
    res_stat1 = client.get("/api/status")
    assert res_stat1.status_code == 200
    stat1 = res_stat1.json()
    assert stat1["current_safety_state"] == "VIOLATION"
    assert len(stat1.get("active_alerts", [])) >= 1
    assert stat1["sif_potential_count"] >= 1
    assert stat1["open_actions_count"] >= 1
    print(f"  [OK] Dashboard Status: state={stat1['current_safety_state']}, active_alerts={len(stat1.get('active_alerts', []))}, SIF={stat1['sif_potential_count']}")

    # 4. Supervisor Mobile Acknowledges Alert
    print("\n--- STEP 4: SUPERVISOR MOBILE ACKNOWLEDGES ALERT ---")
    res_ack = client.post("/api/alert/respond", json={
        "supervisor_id": "SUP-FIELD-01",
        "notes": "Supervisor acknowledging alert and heading to zone",
        "alert_id": alert_id
    })
    assert res_ack.status_code == 200, res_ack.text
    ack_data = res_ack.json()
    assert ack_data["alert"]["action_status"] == "IN_PROGRESS"
    assert ack_data["alert"]["status"] == "RESPONDING"
    print(f"  [OK] Alert {alert_id} status moved to: action_status=IN_PROGRESS, status=RESPONDING")

    # 5. Supervisor Executes Action Taken
    print("\n--- STEP 5: SUPERVISOR MARKS CORRECTIVE ACTION TAKEN ---")
    res_act = client.post("/api/alert/action", json={
        "supervisor_id": "SUP-FIELD-01",
        "notes": "Worker evacuated from restricted perimeter; barricade tape reinstated",
        "action_taken": "Personnel removed and barrier reinstated",
        "alert_id": alert_id
    })
    assert res_act.status_code == 200, res_act.text
    act_data = res_act.json()
    assert act_data["alert"]["action_status"] == "COMPLETED"
    assert act_data["alert"]["verification_status"] == "AWAITING_VERIFICATION"
    print(f"  [OK] Alert {alert_id} marked: action_status=COMPLETED, verification_status=AWAITING_VERIFICATION")

    # 6. Verify Dashboard KPI counts in System Status
    print("\n--- STEP 6: VERIFY AWAITING VERIFICATION KPI IN DASHBOARD ---")
    res_stat2 = client.get("/api/status")
    stat2 = res_stat2.json()
    assert stat2["awaiting_verification_count"] >= 1
    print(f"  [OK] Awaiting verification KPI count = {stat2['awaiting_verification_count']}")

    # 7. Formally Verify Fix via CCTV
    print("\n--- STEP 7: SAFETY VERIFICATION VIA CCTV ---")
    res_ver = client.post("/api/alert/verify", json={
        "supervisor_id": "SUP-FIELD-01",
        "decision": "VERIFIED",
        "verification_method": "CCTV_VERIFIED",
        "notes": "Live CCTV camera confirms exclusion zone is 100% clear of all personnel",
        "alert_id": alert_id
    })
    assert res_ver.status_code == 200, res_ver.text
    ver_data = res_ver.json()
    assert ver_data["alert"]["verification_status"] == "VERIFIED"
    assert ver_data["alert"]["action_status"] == "COMPLETED"
    assert ver_data["alert"]["status"] == "RESOLVED"
    print(f"  [OK] Alert {alert_id} verified: verification_status=VERIFIED, status=RESOLVED")

    # 8. Verify Dashboard State Updates
    print("\n--- STEP 8: VERIFY DASHBOARD STATE UPDATES AFTER CLOSURE ---")
    res_stat3 = client.get("/api/status")
    stat3 = res_stat3.json()
    assert stat3["verified_count"] >= 1
    print(f"  [OK] Verified KPI count = {stat3['verified_count']}")

    # 9. Reset Demo for Clean Standby
    print("\n--- STEP 9: RESET DEMO STATE TO CLEAN STANDBY ---")
    res_final_reset = client.post("/api/demo/reset")
    assert res_final_reset.status_code == 200
    stat_final = client.get("/api/status").json()
    assert len(stat_final.get("active_alerts", [])) == 0
    print("  [OK] Clean standby confirmed: 0 active alerts, ready for live operations")

    print("\n==================================================================")
    print(" END-TO-END SIF PRECURSOR SIMULATION FLOW 100% VALIDATED!")
    print("==================================================================")

if __name__ == "__main__":
    run_simulation_e2e()
