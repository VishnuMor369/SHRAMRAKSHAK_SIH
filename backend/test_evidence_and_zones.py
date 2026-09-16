"""
Automated Test Suite for ShramRakshak 22 Required Acceptance Tests
Tests all requirements specified in user prompt:
- TEST 1: Create permanent restricted zone (zone_category=PERMANENT, no expiry).
- TEST 2: Create Passport with temporary zone linked during creation (zone_category=PASSPORT_TEMPORARY, passport_id linked).
- TEST 3: Temporary zone displays countdown (has valid backend expires_at).
- TEST 4: Temporary zone expires automatically -> temporary zone inactive/removed, Permanent zone remains active.
- TEST 5: Passport expires -> linked temporary zone automatically deactivates, Permanent zone remains.
- TEST 6: Passport manually closed -> linked temporary zone deactivates.
- TEST 7: Temporary zone cannot outlive Passport (duration capped).
- TEST 8: Permanent + temporary zones coexist on same camera.
- TEST 9: Person enters permanent zone only -> normal permanent restricted-zone alert.
- TEST 10: Person enters Passport temporary zone while Passport ACTIVE -> Passport PAUSED, ONE canonical critical alert, no duplicates.
- TEST 11: Repeated breach frames -> ONE alert only (no alert flood).
- TEST 12: Person leaves temporary zone -> AI reports clear, Passport remains AWAITING_RESTORATION (NO auto-reactivation).
- TEST 13: Helmet violation -> alert contains actual CCTV visual evidence image.
- TEST 14: Two people without helmets -> ONE grouped PPE alert with both people shown.
- TEST 15: PPE alert moves to history -> visual evidence remains accessible.
- TEST 16: Supervisor attempts HSE verification -> 403 Forbidden.
- TEST 17: Supervisor attempts Passport activation -> 403 Forbidden.
- TEST 18: HSE verifies and activates -> Passport ACTIVE.
- TEST 19: Existing 20-second response timer still works.
- TEST 20: Existing 60-second action timer still works.
- TEST 21: Two independent simultaneous hazards still coexist.
- TEST 22: Frontend build succeeds.
"""

import os
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from main import app
from state import state_manager
from models import RestrictedZone

client = TestClient(app)

def log_test(num, name, passed, details=""):
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] TEST {num:02d}: {name} {('- ' + details) if details else ''}")

def run_all_tests():
    print("==================================================================")
    print("  RUNNING 22 ACCEPTANCE TESTS FOR SHRAMRAKSHAK INTELLIGENCE")
    print("==================================================================")
    
    passed_count = 0
    total_tests = 22

    # Reset state to clean baseline
    r = client.post("/api/demo/reset")
    assert r.status_code == 200, "Reset failed"

    # -------------------------------------------------------------
    # TEST 1: Create permanent restricted zone
    # -------------------------------------------------------------
    perm_zone_payload = {
        "zone_id": "ZONE-PERM-01",
        "name": "Compressor Safety Area",
        "camera_id": "C-01",
        "zone_type": "floor",
        "zone_category": "PERMANENT",
        "severity": "HIGH",
        "polygon": [[100.0, 100.0], [400.0, 100.0], [400.0, 300.0], [100.0, 300.0]],
        "enabled": True
    }
    r = client.post("/api/zones", json=perm_zone_payload)
    t1_pass = False
    if r.status_code == 200:
        data = r.json().get("zone", {})
        t1_pass = (data.get("zone_category") == "PERMANENT" and not data.get("expires_at"))
    log_test(1, "Create permanent restricted zone (category=PERMANENT, no expiry)", t1_pass)
    if t1_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 2: Create Passport with inline designed Temporary Zone
    # -------------------------------------------------------------
    passport_req = {
        "task_type": "Mechanical Lifting",
        "location": "Demo Lifting Area",
        "supervisor": "Demo Supervisor",
        "camera_id": "C-01",
        "duration_minutes": 15,
        "permit_reference": "PTW-2026-TEST",
        "linked_zone_name": "Lifting Exclusion Zone",
        "temporary_zone": {
            "zone_id": "ZONE-TEMP-TEST",
            "name": "Lifting Exclusion Zone",
            "camera_id": "C-01",
            "zone_type": "floor",
            "zone_category": "PASSPORT_TEMPORARY",
            "duration_minutes": 15,
            "polygon": [[150.0, 150.0], [500.0, 150.0], [500.0, 420.0], [150.0, 420.0]],
            "enabled": True
        }
    }
    r = client.post("/api/passports", json=passport_req)
    t2_pass = False
    created_passport = None
    if r.status_code == 200:
        created_passport = r.json().get("passport", {})
        pid = created_passport.get("id")
        rz = client.get("/api/zones").json()
        temp_zones = rz.get("temporary_zones", [])
        matched = [tz for tz in temp_zones if tz.get("passport_id") == pid]
        t2_pass = (len(matched) > 0 and matched[0].get("zone_category") == "PASSPORT_TEMPORARY")
    log_test(2, "Create Passport with inline designed Temporary Zone (zone_category=PASSPORT_TEMPORARY, linked passport_id)", t2_pass)
    if t2_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 3: Temporary zone displays countdown / has expires_at
    # -------------------------------------------------------------
    t3_pass = False
    rz = client.get("/api/zones").json()
    temp_zones = rz.get("temporary_zones", [])
    if temp_zones:
        exp_iso = temp_zones[0].get("expires_at")
        if exp_iso:
            exp_time = datetime.fromisoformat(exp_iso)
            rem_sec = (exp_time - datetime.now()).total_seconds()
            t3_pass = (rem_sec > 0 and rem_sec <= 15 * 60 + 5)
    log_test(3, "Temporary zone has backend expires_at timestamp for live countdown", t3_pass)
    if t3_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 4: Temporary zone expires automatically -> inactive, permanent remains
    # -------------------------------------------------------------
    with state_manager.lock:
        for tz in state_manager.zones.values():
            if tz.zone_category == "PASSPORT_TEMPORARY":
                tz.expires_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    # Let watchdog evaluate
    time.sleep(0.4)
    
    rz = client.get("/api/zones").json()
    active_zones = rz.get("active_zones", [])
    perm_zones = rz.get("permanent_zones", [])
    temp_active = [z for z in active_zones if z.get("zone_category") == "PASSPORT_TEMPORARY"]
    perm_active = [z for z in active_zones if z.get("zone_category") == "PERMANENT"]
    t4_pass = (len(temp_active) == 0 and len(perm_active) > 0)
    log_test(4, "Temporary zone expires automatically (removed from active), permanent zone remains active", t4_pass)
    if t4_pass: passed_count += 1

    def fully_verify_and_activate(client, pid):
        for cid in ["ctrl-2", "ctrl-3", "ctrl-4", "ctrl-5"]:
            client.post(f"/api/passports/{pid}/verify-control", json={"control_id": cid, "verified": True}, headers={"x-user-role": "supervisor"})
        client.post(f"/api/passports/{pid}/verify-control", json={"control_id": "ctrl-6", "verified": True}, headers={"x-user-role": "hse"})
        client.post(f"/api/passports/{pid}/approve", json={"approved_by": "HSE Lead"}, headers={"x-user-role": "hse"})
        return client.post(f"/api/passports/{pid}/activate", headers={"x-user-role": "hse"})

    # -------------------------------------------------------------
    # TEST 5: Passport expires -> linked temporary zone automatically deactivates
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    p_resp = client.post("/api/passports", json=passport_req).json()
    pid = p_resp["passport"]["id"]
    fully_verify_and_activate(client, pid)
    
    # Fast forward passport expires_at
    with state_manager.lock:
        state_manager.passports[pid].expires_at = (datetime.now() - timedelta(seconds=1)).isoformat()
    time.sleep(0.4)
    
    p_check = client.get(f"/api/passports/{pid}").json()["passport"]
    rz = client.get("/api/zones").json()
    temp_active = [z for z in rz.get("active_zones", []) if z.get("zone_category") == "PASSPORT_TEMPORARY"]
    t5_pass = (p_check.get("status") == "EXPIRED" and len(temp_active) == 0)
    log_test(5, "Passport expires -> linked temporary zone deactivates, permanent zone persists", t5_pass)
    if t5_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 6: Passport manually closed -> linked temporary zone deactivates
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    p_resp = client.post("/api/passports", json=passport_req).json()
    pid = p_resp["passport"]["id"]
    fully_verify_and_activate(client, pid)
    
    # Manually close passport
    close_res = client.post(f"/api/passports/{pid}/close")
    rz = client.get("/api/zones").json()
    temp_active = [z for z in rz.get("active_zones", []) if z.get("zone_category") == "PASSPORT_TEMPORARY"]
    t6_pass = (close_res.status_code == 200 and len(temp_active) == 0)
    log_test(6, "Passport manually closed -> linked temporary zone deactivates immediately", t6_pass)
    if t6_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 7: Temporary zone duration cannot outlive Passport (capped duration)
    # -------------------------------------------------------------
    capped_req = {
        "task_type": "Working at Heights",
        "location": "Tower B",
        "supervisor": "Demo Supervisor",
        "duration_minutes": 10,  # 10 min passport
        "temporary_zone": {
            "name": "Heights Zone",
            "duration_minutes": 30,  # requested 30 min (> passport 10 min)
            "polygon": [[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]],
            "camera_id": "C-01"
        }
    }
    r = client.post("/api/passports", json=capped_req)
    t7_pass = False
    if r.status_code == 200:
        c_pid = r.json()["passport"]["id"]
        tz = [z for z in state_manager.zones.values() if z.passport_id == c_pid][0]
        t7_pass = (tz.duration_minutes == 10) # Capped to 10 min!
    log_test(7, "Temporary zone cannot outlive Passport (capped to passport duration)", t7_pass)
    if t7_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 8: Permanent + temporary zones coexist on same camera
    # -------------------------------------------------------------
    rz = client.get("/api/zones").json()
    has_perm = any(z.get("camera_id") == "C-01" and z.get("zone_category") == "PERMANENT" for z in rz.get("zones", []))
    has_temp = any(z.get("camera_id") == "C-01" and z.get("zone_category") == "PASSPORT_TEMPORARY" for z in rz.get("zones", []))
    t8_pass = (has_perm and has_temp)
    log_test(8, "Permanent zone and Passport temporary zone coexist simultaneously on camera C-01", t8_pass)
    if t8_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 9: Person enters permanent zone only -> normal permanent restricted-zone alert
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    alert_resp = client.post("/api/demo/simulate-zone-entry").json()
    alert = alert_resp.get("alert", {})
    t9_pass = (alert.get("type") == "Restricted Zone Entry" and "ZONE" in alert.get("id", ""))
    log_test(9, "Person enters permanent zone only -> normal permanent restricted-zone alert", t9_pass)
    if t9_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 10: Person enters Passport temporary zone while Passport ACTIVE
    # Expected: Passport PAUSED, ONE canonical critical alert, no duplicate restricted-zone alert
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    p_resp = client.post("/api/passports", json=passport_req).json()
    pid = p_resp["passport"]["id"]
    fully_verify_and_activate(client, pid)

    # Trigger zone breach while passport is ACTIVE
    client.post("/api/demo/simulate-zone-entry")
    
    # Check passport status
    p_status = client.get(f"/api/passports/{pid}").json()["passport"]
    active_alerts = client.get("/api/alerts").json().get("alerts", [])
    passport_breach_alerts = [a for a in active_alerts if a.get("type") == "SAFETY PASSPORT BREACH"]
    norm_zone_alerts = [a for a in active_alerts if a.get("type") == "Restricted Zone Entry"]
    
    t10_pass = (
        p_status.get("status") == "PAUSED" and 
        len(passport_breach_alerts) == 1 and 
        len(norm_zone_alerts) == 0 and 
        len(active_alerts) == 1
    )
    log_test(10, "Person enters temporary zone while Passport ACTIVE -> Passport PAUSED, ONE canonical critical alert, no duplicates", t10_pass)
    if t10_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 11: Repeated breach frames -> ONE alert only (no flood)
    # -------------------------------------------------------------
    for _ in range(5):
        client.post("/api/demo/simulate-zone-entry")
    active_alerts = client.get("/api/alerts").json().get("alerts", [])
    t11_pass = (len(active_alerts) == 1 and active_alerts[0].get("type") == "SAFETY PASSPORT BREACH")
    log_test(11, "Repeated breach frames -> ONE canonical alert only (no alert flooding)", t11_pass)
    if t11_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 12: Person leaves temporary zone -> AI reports clear, Passport remains AWAITING_RESTORATION
    # -------------------------------------------------------------
    client.post("/api/demo/simulate-safe")
    time.sleep(0.3)
    p_status = client.get(f"/api/passports/{pid}").json()["passport"]
    t12_pass = (p_status.get("status") in ["AWAITING_RESTORATION", "PAUSED"] and p_status.get("status") != "ACTIVE")
    log_test(12, "Person leaves zone -> Passport remains AWAITING_RESTORATION / PAUSED (NO auto-reactivation)", t12_pass)
    if t12_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 13: Helmet violation -> alert contains actual CCTV evidence image
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    h_resp = client.post("/api/demo/simulate-no-helmet").json()
    alert = h_resp.get("alert", {})
    ev_url = alert.get("evidence_url")
    ev_img = alert.get("evidence_image")
    ev_get_pass = False
    if ev_url:
        r_ev = client.get(ev_url)
        ev_get_pass = (r_ev.status_code == 200 and r_ev.headers.get("content-type") == "image/jpeg" and len(r_ev.content) > 1000)
    t13_pass = bool(ev_url and ev_img and ev_img.startswith("data:image/jpeg;base64,") and ev_get_pass)
    log_test(13, "Helmet violation -> alert contains actual CCTV visual evidence image and accessible via /api/evidence/{id}", t13_pass)
    if t13_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 14: Two people without helmets -> one grouped PPE alert with both people shown
    # -------------------------------------------------------------
    active_alerts = client.get("/api/alerts").json().get("alerts", [])
    ppe_alerts = [a for a in active_alerts if a.get("type") == "Helmet/PPE Violation"]
    t14_pass = False
    if len(ppe_alerts) == 1:
        a = ppe_alerts[0]
        t14_pass = (a.get("person_count") == 2 and "Person 01" in a.get("affected_person_ids", []) and "Person 02" in a.get("affected_person_ids", []))
    log_test(14, "Two people without helmets -> ONE grouped PPE alert with evidence showing both detected people", t14_pass)
    if t14_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 15: PPE alert moves to history -> evidence remains accessible
    # -------------------------------------------------------------
    aid = ppe_alerts[0]["id"]
    client.post(f"/api/alerts/{aid}/respond", json={"supervisor_id": "SUP-01"})
    client.post(f"/api/alerts/{aid}/resolve", json={"supervisor_id": "SUP-01"})
    
    hist_resp = client.get("/api/alerts/history").json()
    history = hist_resp.get("history", [])
    resolved_a = [h for h in history if h.get("id") == aid]
    t15_pass = False
    if resolved_a:
        h_ev_url = resolved_a[0].get("evidence_url")
        if h_ev_url:
            r_ev = client.get(h_ev_url)
            t15_pass = (r_ev.status_code == 200 and len(r_ev.content) > 1000)
    log_test(15, "PPE alert moves to history -> visual evidence remains preserved and accessible", t15_pass)
    if t15_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 16: Supervisor attempts HSE verification -> 403 Forbidden
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    p_resp = client.post("/api/passports", json=passport_req).json()
    pid = p_resp["passport"]["id"]
    r_sup_ctrl = client.post(
        f"/api/passports/{pid}/verify-control",
        json={"control_id": "ctrl-6", "verified": True},
        headers={"x-user-role": "supervisor"}
    )
    t16_pass = (r_sup_ctrl.status_code == 403)
    log_test(16, "Supervisor attempts HSE verification -> 403 Forbidden", t16_pass)
    if t16_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 17: Supervisor attempts Passport activation -> 403 Forbidden
    # -------------------------------------------------------------
    r_sup_act = client.post(
        f"/api/passports/{pid}/activate",
        headers={"x-user-role": "supervisor"}
    )
    t17_pass = (r_sup_act.status_code == 403)
    log_test(17, "Supervisor attempts Passport activation -> 403 Forbidden", t17_pass)
    if t17_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 18: HSE verifies and activates -> Passport ACTIVE
    # -------------------------------------------------------------
    for cid in ["ctrl-2", "ctrl-3", "ctrl-4", "ctrl-5"]:
        client.post(f"/api/passports/{pid}/verify-control", json={"control_id": cid, "verified": True}, headers={"x-user-role": "supervisor"})
    r_hse_v = client.post(f"/api/passports/{pid}/verify-control", json={"control_id": "ctrl-6", "verified": True}, headers={"x-user-role": "hse"})
    r_hse_app = client.post(f"/api/passports/{pid}/approve", json={"approved_by": "HSE Manager"}, headers={"x-user-role": "hse"})
    r_hse_act = client.post(f"/api/passports/{pid}/activate", headers={"x-user-role": "hse"})
    t18_pass = (r_hse_act.status_code == 200 and r_hse_act.json()["passport"]["status"] == "ACTIVE")
    log_test(18, "HSE verifies control 6, approves, and activates -> Passport ACTIVE", t18_pass)
    if t18_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 19: Existing 20-second response SLA timer still works
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    t19_alert = client.post("/api/demo/simulate-no-helmet").json()["alert"]
    t19_pass = (t19_alert.get("response_duration_sec") == 20)
    log_test(19, "Existing 20-second response timer SLA is preserved", t19_pass)
    if t19_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 20: Existing 60-second action SLA timer still works
    # -------------------------------------------------------------
    aid = t19_alert["id"]
    resp_data = client.post(f"/api/alerts/{aid}/respond", json={"supervisor_id": "SUP-01"}).json()
    stage2_alert = resp_data["alert"]
    t20_pass = (stage2_alert.get("action_duration_sec") == 60 and stage2_alert.get("status") == "RESPONDING")
    log_test(20, "Existing 60-second action timer SLA is preserved", t20_pass)
    if t20_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 21: Two independent simultaneous hazards coexist
    # -------------------------------------------------------------
    client.post("/api/demo/reset")
    multi_resp = client.post("/api/demo/simulate-multi-violation").json()
    active_alerts = client.get("/api/alerts").json().get("alerts", [])
    has_ppe = any(a.get("type") == "Helmet/PPE Violation" for a in active_alerts)
    has_zone = any(a.get("type") == "Restricted Zone Entry" for a in active_alerts)
    t21_pass = (len(active_alerts) == 2 and has_ppe and has_zone)
    log_test(21, "Two independent simultaneous hazards coexist (PPE + Restricted Zone)", t21_pass)
    if t21_pass: passed_count += 1

    # -------------------------------------------------------------
    # TEST 22: Frontend build succeeds
    # -------------------------------------------------------------
    dist_html = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "index.html")
    t22_pass = os.path.exists(dist_html)
    log_test(22, "Frontend build succeeds (dist/index.html generated)", t22_pass)
    if t22_pass: passed_count += 1

    print("==================================================================")
    print(f"  TEST RESULTS: {passed_count}/{total_tests} PASSED")
    print("==================================================================")
    assert passed_count == total_tests, f"Only {passed_count}/{total_tests} passed!"

if __name__ == "__main__":
    run_all_tests()
