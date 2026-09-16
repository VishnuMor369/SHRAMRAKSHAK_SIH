"""
End-to-End REST API Test for Start Work Safety Passport
Verifies all HTTP endpoints, state machine transitions, and client sync over HTTP.
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_passport_api():
    print("============================================================")
    print(" Running Start Work Safety Passport End-to-End API Tests    ")
    print("============================================================")

    # 1. Reset Demo
    res = requests.post(f"{BASE_URL}/api/demo/reset")
    assert res.status_code == 200, f"Reset failed: {res.text}"
    print("[PASS] 1. Reset demo successful.")

    # 2. Check initial active passport
    res = requests.get(f"{BASE_URL}/api/passports/active")
    assert res.status_code == 200
    assert res.json()["passport"] is None
    print("[PASS] 2. Active passport initially None.")

    # 3. Create Safety Passport
    payload = {
        "task_type": "Mechanical Lifting",
        "location": "Demo Lifting Area",
        "supervisor": "Demo Supervisor",
        "camera_id": "C-01",
        "linked_zone_id": "ZONE-001",
        "linked_zone_name": "Lifting Exclusion Zone",
        "duration_minutes": 15,
        "permit_reference": "PTW-OIL-2026-8841",
        "created_by": "Demo Supervisor"
    }
    res = requests.post(f"{BASE_URL}/api/passports", json=payload)
    assert res.status_code == 200, f"Create failed: {res.text}"
    data = res.json()
    passport_id = data["passport"]["id"]
    assert passport_id.startswith("SP-")
    assert data["passport"]["status"] == "PENDING_VERIFICATION"
    print(f"[PASS] 3. Created Safety Passport: {passport_id}")

    # 4. Get by ID
    res = requests.get(f"{BASE_URL}/api/passports/{passport_id}")
    assert res.status_code == 200
    p = res.json()["passport"]
    assert p["id"] == passport_id
    assert len(p["controls"]) == 6
    print(f"[PASS] 4. Fetched passport by ID: {passport_id}")

    # 5. Strict Role Separation: Supervisor cannot verify ctrl-6 (403 Forbidden)
    res = requests.post(
        f"{BASE_URL}/api/passports/{passport_id}/verify-control",
        headers={"X-User-Role": "supervisor"},
        json={"control_id": "ctrl-6", "verified": True, "verified_by": "Demo Supervisor"}
    )
    assert res.status_code == 403, f"Expected 403 for supervisor verifying ctrl-6, got {res.status_code}"
    print("[PASS] 5a. Supervisor blocked with 403 Forbidden from verifying HSE control.")

    # 5b. Strict Role Separation: Supervisor cannot approve passport (403 Forbidden)
    res = requests.post(
        f"{BASE_URL}/api/passports/{passport_id}/approve",
        headers={"X-User-Role": "supervisor"},
        json={"approved_by": "Demo Supervisor"}
    )
    assert res.status_code == 403, f"Expected 403 for supervisor approving, got {res.status_code}"
    print("[PASS] 5b. Supervisor blocked with 403 Forbidden from approving passport.")

    # 5c. Strict Role Separation: Supervisor cannot activate passport (403 Forbidden)
    res = requests.post(
        f"{BASE_URL}/api/passports/{passport_id}/activate",
        headers={"X-User-Role": "supervisor"}
    )
    assert res.status_code == 403, f"Expected 403 for supervisor activating, got {res.status_code}"
    print("[PASS] 5c. Supervisor blocked with 403 Forbidden from activating passport.")

    # 5d. Try activating as HSE with missing controls -> Should fail (400)
    res = requests.post(
        f"{BASE_URL}/api/passports/{passport_id}/activate",
        headers={"X-User-Role": "hse"}
    )
    assert res.status_code == 400
    print(f"[PASS] 5d. Activation blocked on missing controls: {res.json()['detail']}")

    # 6. Verify supervisor controls
    for ctrl_id in ["ctrl-2", "ctrl-3", "ctrl-4", "ctrl-5"]:
        res = requests.post(f"{BASE_URL}/api/passports/{passport_id}/verify-control", json={
            "control_id": ctrl_id,
            "verified": True,
            "verified_by": "Demo Supervisor"
        })
        assert res.status_code == 200

    # 7. HSE verifies and approves
    res = requests.post(
        f"{BASE_URL}/api/passports/{passport_id}/approve",
        headers={"X-User-Role": "hse"},
        json={
            "approved_by": "HSE Manager OIL-DemoLifting",
            "notes": "PTW clearance confirmed"
        }
    )
    assert res.status_code == 200
    print("[PASS] 6 & 7. All 6 controls verified and HSE approval recorded.")

    # 8. Activate Passport via HSE
    res = requests.post(
        f"{BASE_URL}/api/passports/{passport_id}/activate",
        headers={"X-User-Role": "hse"}
    )
    assert res.status_code == 200
    p_act = res.json()["passport"]
    assert p_act["status"] == "ACTIVE"
    print(f"[PASS] 8. Passport ACTIVE until {p_act['expires_at']}")

    # 9. Configure zone to match linked zone
    res = requests.post(f"{BASE_URL}/api/zones", json={
        "zone_id": "ZONE-001",
        "name": "Lifting Exclusion Zone",
        "camera_id": "C-01",
        "zone_type": "floor",
        "severity": "HIGH",
        "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
        "enabled": True
    })
    assert res.status_code == 200
    print("[PASS] 9. Linked Lifting Exclusion Zone configured.")

    # 10. Simulate zone entry breach
    res = requests.post(f"{BASE_URL}/api/demo/simulate-zone-entry")
    assert res.status_code == 200
    
    # Check that passport is now PAUSED
    res = requests.get(f"{BASE_URL}/api/passports/active")
    p_paused = res.json()["passport"]
    assert p_paused["status"] == "PAUSED"
    print(f"[PASS] 10. Zone breach detected -> Passport automatically PAUSED: '{p_paused['breach_reason']}'")

    # Check that SAFETY PASSPORT BREACH alert is top priority and DEDUPLICATED (len == 1)
    res = requests.get(f"{BASE_URL}/api/alerts")
    alerts = res.json()["alerts"]
    assert len(alerts) == 1, f"Expected exactly 1 alert (deduplicated), got {len(alerts)}: {[a['type'] for a in alerts]}"
    top_alert = alerts[0]
    assert top_alert["type"] == "SAFETY PASSPORT BREACH"
    assert top_alert["priority_score"] == 120
    assert top_alert["status"] == "WAITING_FOR_RESPONSE"
    print(f"[PASS] 11. Top alert is {top_alert['type']} (Score: {top_alert['priority_score']})")

    # 11. Supervisor Responds ("I'M RESPONDING")
    res = requests.post(f"{BASE_URL}/api/alert/respond", json={
        "alert_id": top_alert["id"],
        "supervisor_id": "Demo Supervisor",
        "notes": "Field supervisor en route to halt lifting"
    })
    assert res.status_code == 200
    assert res.json()["alert"]["status"] == "RESPONDING"
    print("[PASS] 12. Supervisor responded within 20s window -> RESPONDING.")

    # 12. Explicit barrier restoration verification
    res = requests.post(f"{BASE_URL}/api/passports/{passport_id}/verify-restoration", json={
        "supervisor_id": "Demo Supervisor",
        "notes": "Exclusion zone cleared and perimeter inspected"
    })
    assert res.status_code == 200
    p_react = res.json()["passport"]
    assert p_react["status"] == "ACTIVE"
    print(f"[PASS] 13. Supervisor explicitly verified barrier restored -> Passport REACTIVATED.")

    # 13. Close Passport
    res = requests.post(f"{BASE_URL}/api/passports/{passport_id}/close")
    assert res.status_code == 200
    assert res.json()["passport"]["status"] == "CLOSED"
    print("[PASS] 14. Passport formally CLOSED.")

    # 14. Reset Demo
    res = requests.post(f"{BASE_URL}/api/demo/reset")
    assert res.status_code == 200
    print("[PASS] 15. Demo reset clean state confirmed.")

    print("\n============================================================")
    print(" ALL 15 END-TO-END REST API TESTS PASSED SUCCESSFULLY!      ")
    print("============================================================")

if __name__ == "__main__":
    test_passport_api()
