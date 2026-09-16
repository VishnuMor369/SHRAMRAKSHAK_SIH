"""
Automated Verification Script for SHRAMRAKSHAK Backend
Tests the complete alert lifecycle, 2-stage timers, and automatic escalation.
"""

import time
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_full_lifecycle():
    print("==================================================")
    print(" Running SHRAMRAKSHAK End-to-End API Test Suite  ")
    print("==================================================")

    # 1. Reset Demo
    print("\n[Step 1] Resetting demo state...")
    res = requests.post(f"{BASE_URL}/api/demo/reset")
    assert res.status_code == 200, f"Reset failed: {res.text}"
    print("[OK] Demo reset to IDLE")

    # 2. Check System Status
    print("\n[Step 2] Checking /api/status...")
    res = requests.get(f"{BASE_URL}/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["system_status"] == "ONLINE"
    assert data["active_alert"] is None
    print(f"[OK] System status ONLINE, Host LAN IP: {data['lan_ip']}")

    # 3. Simulate No-Helmet Violation
    print("\n[Step 3] Simulating NO-HELMET violation...")
    res = requests.post(f"{BASE_URL}/api/demo/simulate-no-helmet")
    assert res.status_code == 200
    alert = res.json()["alert"]
    assert alert["status"] == "WAITING_FOR_RESPONSE"
    assert alert["response_duration_sec"] == 20
    print(f"[OK] Alert generated: {alert['id']}")
    print(f"  Stage 1 Response Deadline: {alert['response_deadline']}")

    # 4. Supervisor responds before 20s expires
    print("\n[Step 4] Supervisor clicks 'I'M RESPONDING'...")
    res = requests.post(f"{BASE_URL}/api/alert/respond", json={"supervisor_id": "SUP-TEST-01"})
    assert res.status_code == 200
    alert = res.json()["alert"]
    assert alert["status"] == "RESPONDING"
    assert alert["action_deadline"] is not None
    print(f"[OK] Stage 1 successfully acknowledged! Transitioned to RESPONDING.")
    print(f"  Stage 2 Action Deadline: {alert['action_deadline']}")

    # 5. Supervisor resolves issue
    print("\n[Step 5] Supervisor clicks 'FIXED / RESOLVED'...")
    res = requests.post(f"{BASE_URL}/api/alert/resolve", json={"supervisor_id": "SUP-TEST-01", "notes": "Test resolved"})
    assert res.status_code == 200
    alert = res.json()["alert"]
    assert alert["status"] == "RESOLVED"
    print(f"[OK] Alert RESOLVED by {alert['resolved_by']}")

    # 5b. Verify Alert appears in History API
    print("\n[Step 5b] Checking /api/alerts/history...")
    res = requests.get(f"{BASE_URL}/api/alerts/history")
    assert res.status_code == 200
    hist = res.json()["history"]
    assert len(hist) >= 1
    assert hist[0]["id"] == alert["id"]
    assert hist[0]["status"] == "RESOLVED"
    print(f"[OK] Resolved alert found in History API: {hist[0]['id']} ({hist[0]['title']})")

    # 6. Test Escalation Flow
    print("\n[Step 6] Testing Automatic Escalation Flow...")
    requests.post(f"{BASE_URL}/api/demo/reset")
    # Trigger violation with short 2-second response window for fast automated testing
    res = requests.post(f"{BASE_URL}/api/alert/trigger", params={"response_sec": 2})
    alert = res.json()["alert"]
    print(f"  Triggered alert with 2s response window: {alert['id']}")
    print("  Waiting 2.5 seconds for escalation watchdog to fire...")
    time.sleep(2.5)

    res = requests.get(f"{BASE_URL}/api/alert/current")
    current_alert = res.json()
    assert current_alert is not None, "Expected active alert"
    assert current_alert["status"] == "ESCALATED", f"Expected ESCALATED, got {current_alert['status']}"
    print(f"[OK] Alert successfully transitioned to ESCALATED: {current_alert['escalated_at']}")

    # 7. Clean up
    requests.post(f"{BASE_URL}/api/demo/reset")
    print("\n==================================================")
    print("  ALL API & LIFECYCLE TESTS PASSED SUCCESSFULLY!  ")
    print("==================================================")

if __name__ == "__main__":
    try:
        test_full_lifecycle()
    except Exception as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
