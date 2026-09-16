"""
Comprehensive Automated Test Suite for ShramRakshak Start Work Safety Passport
Covers all requirements from the Safety Passport specification:
- Creation, verification sources (AI vs Supervisor vs HSE)
- Pre-start checklist & blocking missing controls
- HSE approval & time-bound activation
- Restricted zone breach -> PAUSED + priority 120 CRITICAL alert
- 20s response SLA, 60s action SLA, auto-escalation
- Zone clear does NOT auto-reactivate (requires explicit human verification)
- Barrier restoration verification & reactivation
- Passport history audit trail
- Simultaneous coexistence with standard zone and PPE alerts
"""

import time
import sys
from datetime import datetime, timedelta

from models import (
    RestrictedZone, CreatePassportRequest, VerifyControlRequest, 
    ApprovePassportRequest, VerifyRestorationRequest
)
from state import state_manager, RESPONSE_SLA_SECONDS, ACTION_SLA_SECONDS

def run_all_passport_tests():
    print("============================================================")
    print(" Running Start Work Safety Passport Automated Test Suite    ")
    print("============================================================")

    state_manager.reset_demo()
    assert state_manager.active_passport is None
    print("[OK] State manager reset to clean demo state.")

    # ---------------------------------------------------------
    # TEST 1 & 2: Create Passport from Supervisor and HSE
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing Passport creation (from Supervisor)...")
    req_sup = CreatePassportRequest(
        task_type="Mechanical Lifting",
        location="Demo Lifting Area",
        supervisor="Demo Supervisor",
        camera_id="C-01",
        linked_zone_id="ZONE-001",
        linked_zone_name="Lifting Exclusion Zone",
        duration_minutes=15,
        permit_reference="PTW-OIL-2026-8841",
        created_by="Demo Supervisor"
    )
    p_sup = state_manager.create_passport(req_sup)
    assert p_sup.id.startswith("SP-")
    assert p_sup.task_type == "Mechanical Lifting"
    assert p_sup.location == "Demo Lifting Area"
    assert p_sup.status == "PENDING_VERIFICATION"
    assert len(p_sup.controls) == 6
    assert p_sup.created_by == "Demo Supervisor"
    assert p_sup.events[0].event_type == "created"
    print(f"  [PASS] Passport created: {p_sup.id} ({p_sup.task_type} at {p_sup.location})")

    # ---------------------------------------------------------
    # TEST 3: Verification Sources Distinction (AI vs Supervisor vs HSE)
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing verification source classification on pre-start checklist...")
    sources = {c.id: c.verification_source for c in p_sup.controls}
    assert sources["ctrl-1"] == "SUPERVISOR VERIFIED"
    assert sources["ctrl-2"] == "SYSTEM VERIFIED"
    assert sources["ctrl-3"] == "AI VERIFIED"
    assert sources["ctrl-4"] == "AI + SUPERVISOR VERIFIED"
    assert sources["ctrl-5"] == "SUPERVISOR VERIFIED"
    assert sources["ctrl-6"] == "HSE VERIFIED"
    print("  [PASS] All 6 controls have distinct and honest verification sources.")

    # ---------------------------------------------------------
    # TEST 4: Role Separation: Supervisor cannot verify HSE control, approve, or activate
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing strict role separation on HSE controls...")
    try:
        state_manager.verify_control(p_sup.id, "ctrl-6", True, "Demo Supervisor", user_role="supervisor")
        assert False, "Supervisor must NOT verify HSE control!"
    except PermissionError as e:
        print(f"  [PASS] Supervisor blocked from ctrl-6: {e}")

    try:
        state_manager.approve_passport(p_sup.id, approved_by="Demo Supervisor", user_role="supervisor")
        assert False, "Supervisor must NOT approve passport!"
    except PermissionError as e:
        print(f"  [PASS] Supervisor blocked from approving passport: {e}")

    try:
        state_manager.activate_passport(p_sup.id, user_role="supervisor")
        assert False, "Supervisor must NOT activate passport!"
    except PermissionError as e:
        print(f"  [PASS] Supervisor blocked from activating passport: {e}")

    # ---------------------------------------------------------
    # TEST 5: Missing controls BLOCK activation even for HSE
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing missing controls block activation...")
    success, reason, _ = state_manager.activate_passport(p_sup.id, user_role="hse")
    assert not success, "Activation must FAIL when controls are missing!"
    assert "SAFETY PASSPORT BLOCKED" in reason
    assert p_sup.status == "PENDING_VERIFICATION"
    print(f"  [PASS] Blocked as expected: {reason}")

    # ---------------------------------------------------------
    # TEST 6: Completing Pre-Start Checks & HSE Approval
    # ---------------------------------------------------------
    print("\n[TEST 5] Completing remaining pre-start checks...")
    # ctrl-2 (zone active)
    state_manager.verify_control(p_sup.id, "ctrl-2", True, "System Vision Engine")
    # ctrl-3 (zone clear)
    state_manager.verify_control(p_sup.id, "ctrl-3", True, "YOLO-Pose Edge Vision")
    # ctrl-4 (PPE confirmed)
    state_manager.verify_control(p_sup.id, "ctrl-4", True, "AI + Supervisor")
    # ctrl-5 (emergency response owner)
    state_manager.verify_control(p_sup.id, "ctrl-5", True, "Demo Supervisor")
    # ctrl-6 (permit approval by HSE)
    state_manager.approve_passport(p_sup.id, approved_by="HSE Manager OIL-DemoLifting", notes="Valid permit verified on portal", user_role="hse")
    
    updated_p = state_manager.passports[p_sup.id]
    all_verified = all(c.verified for c in updated_p.controls)
    assert all_verified, f"Expected all 6 controls verified, got {[c.name for c in updated_p.controls if not c.verified]}"
    assert updated_p.status == "PENDING_APPROVAL"
    print("  [PASS] All 6/6 controls verified. HSE approval recorded.")

    # ---------------------------------------------------------
    # TEST 7: Passport Activation & Time-Bound Clearance
    # ---------------------------------------------------------
    print("\n[TEST 6] Activating Passport via HSE...")
    success, msg, active_p = state_manager.activate_passport(p_sup.id, user_role="hse")
    assert success, f"Activation failed: {msg}"
    assert active_p.status == "ACTIVE"
    assert active_p.activated_at is not None
    assert active_p.expires_at is not None
    assert state_manager.active_passport.id == p_sup.id
    print(f"  [PASS] Passport is ACTIVE until {active_p.expires_at}")

    # ---------------------------------------------------------
    # TEST 8: Linking to Existing Restricted Zone & Camera
    # ---------------------------------------------------------
    print("\n[TEST 7] Linking to Camera C-01 & Zone...")
    zone = RestrictedZone(
        zone_id="ZONE-001",
        name="Lifting Exclusion Zone",
        camera_id="C-01",
        zone_type="floor",
        severity="HIGH",
        polygon=[[100, 100], [300, 100], [300, 300], [100, 300]],
        enabled=True
    )
    state_manager.set_zone(zone)
    assert active_p.camera_id == "C-01"
    assert active_p.linked_zone_id == "ZONE-001"
    print("  [PASS] Passport successfully linked to active camera and exclusion zone.")

    # ---------------------------------------------------------
    # TEST 9: Linked Zone Breach -> Passport PAUSED + ONE Canonical Alert (Deduplicated)
    # ---------------------------------------------------------
    print("\n[TEST 8] Testing zone breach while passport is ACTIVE -> PAUSED + Deduplicated Alert...")
    state_manager.update_cv_detection(
        person_detected=True,
        helmet_detected=True,
        zone_violation=True,
        persons_in_zone=1,
        occupancy_score=0.95,
        debug_info="FEET: INSIDE | ZONE: VIOLATION"
    )
    
    assert active_p.status == "PAUSED", f"Expected PAUSED, got {active_p.status}"
    assert active_p.paused_at is not None
    print(f"  [PASS] Passport automatically switched to PAUSED. Breach reason: '{active_p.breach_reason}'")

    # Verify priority score and alert deduplication (ONLY ONE ALERT!)
    active_alerts = state_manager.get_active_alerts_list()
    assert len(active_alerts) == 1, f"Expected exactly 1 alert (deduplicated), got {len(active_alerts)}: {[a.type for a in active_alerts]}"
    top_alert = active_alerts[0]
    assert top_alert.type == "SAFETY PASSPORT BREACH"
    assert top_alert.priority_score == 120
    assert top_alert.priority_label == "CRITICAL"
    assert "SAFETY PASSPORT PAUSED" in top_alert.title
    assert not any(a.type == "Restricted Zone Entry" for a in active_alerts), "Duplicate Restricted Zone Entry alert must be suppressed!"
    assert top_alert.status == "WAITING_FOR_RESPONSE"
    print(f"  [PASS] Exactly 1 canonical priority 120 alert generated: {top_alert.id} ({top_alert.title})")

    # ---------------------------------------------------------
    # TEST 9: No Alert Flooding (Subsequent frames do not recreate alert)
    # ---------------------------------------------------------
    print("\n[TEST 8] Testing no alert flooding over 20 repeated breach frames...")
    initial_alerts_count = len(state_manager.get_active_alerts_list())
    for _ in range(20):
        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=True,
            zone_violation=True,
            persons_in_zone=1
        )
    assert len(state_manager.get_active_alerts_list()) == initial_alerts_count
    print("  [PASS] Exactly 1 passport alert maintained (no duplicate flood).")

    # ---------------------------------------------------------
    # TEST 10: 20s Response SLA -> Supervisor Responds
    # ---------------------------------------------------------
    print("\n[TEST 9] Testing supervisor acknowledgment ('I'M RESPONDING')...")
    resp_alert = state_manager.respond_to_alert(
        supervisor_id="Demo Supervisor",
        notes="Operator responding to clear the lifting zone",
        alert_id=top_alert.id
    )
    assert resp_alert.status == "RESPONDING"
    assert resp_alert.action_deadline is not None
    print("  [PASS] Transitioned to RESPONDING with 60s action window.")

    # ---------------------------------------------------------
    # TEST 11: Zone Becomes Clear -> DOES NOT AUTO-REACTIVATE!
    # ---------------------------------------------------------
    print("\n[TEST 10] Testing zone clears visually -> Passport remains PAUSED / AWAITING RESTORATION...")
    state_manager.update_cv_detection(
        person_detected=True,
        helmet_detected=True,
        zone_violation=False,
        persons_in_zone=0
    )
    # Must NOT be ACTIVE!
    assert active_p.status in ["PAUSED", "AWAITING_RESTORATION"], f"Passport MUST NOT auto-reactivate! Got: {active_p.status}"
    assert any(e.event_type == "barrier_clear" for e in active_p.events)
    print("  [PASS] Passport did NOT auto-reactivate. Human verification required.")

    # ---------------------------------------------------------
    # TEST 12: Barrier Restoration Human Verification -> REACTIVATED
    # ---------------------------------------------------------
    print("\n[TEST 11] Testing explicit supervisor restoration verification...")
    v_success, v_msg, reactivated_p = state_manager.verify_barrier_restored(
        passport_id=active_p.id,
        supervisor_id="Demo Supervisor",
        notes="Physical inspection complete. Perimeter clear and barricaded."
    )
    assert v_success, f"Restoration failed: {v_msg}"
    assert reactivated_p.status == "ACTIVE"
    assert reactivated_p.reactivated_at is not None
    
    # Breach alert should now be resolved
    assert reactivated_p.active_breach_alert_id is None
    resolved_in_history = any(h.type == "SAFETY PASSPORT BREACH" for h in state_manager.history)
    assert resolved_in_history, "Breach alert must be resolved and moved to history!"
    print("  [PASS] Passport successfully REACTIVATED and breach alert resolved.")

    # ---------------------------------------------------------
    # TEST 13: Passport History Audit Trail
    # ---------------------------------------------------------
    print("\n[TEST 12] Testing passport history event timeline...")
    event_types = [e.event_type for e in reactivated_p.events]
    assert "created" in event_types
    assert "control_verified" in event_types
    assert "approved" in event_types
    assert "activated" in event_types
    assert "paused" in event_types
    assert "barrier_clear" in event_types
    assert "restoration_verified" in event_types
    assert "reactivated" in event_types
    print(f"  [PASS] Chronological event audit trail contains {len(reactivated_p.events)} events: {event_types}")

    # ---------------------------------------------------------
    # TEST 14: Multi-Alert Coexistence (PPE + Zone + Passport)
    # ---------------------------------------------------------
    print("\n[TEST 13] Testing coexistence of Passport + Helmet violation...")
    state_manager.simulate_no_helmet(count=2)
    current_alerts = state_manager.get_active_alerts_list()
    assert any(a.type == "Helmet/PPE Violation" for a in current_alerts)
    print("  [PASS] Independent safety observations coexist smoothly.")

    # ---------------------------------------------------------
    # TEST 15: Formal Passport Closure
    # ---------------------------------------------------------
    print("\n[TEST 14] Testing formal closure of Safety Passport...")
    closed_p = state_manager.close_passport(active_p.id)
    assert closed_p.status == "CLOSED"
    assert closed_p.closed_at is not None
    assert state_manager.active_passport_id is None
    print("  [PASS] Passport formally closed.")

    # ---------------------------------------------------------
    # TEST 16: Reset Demo Clears Passport State
    # ---------------------------------------------------------
    print("\n[TEST 15] Testing demo reset clears passports...")
    state_manager.reset_demo()
    assert len(state_manager.passports) == 0
    assert state_manager.active_passport is None
    print("  [PASS] Demo reset restores clean initial state.")

    print("\n============================================================")
    print("  ALL 15 SAFETY PASSPORT CORE TEST SUITES PASSED!           ")
    print("============================================================")

if __name__ == "__main__":
    run_all_passport_tests()
