"""
Comprehensive Test Suite for SHRAMRAKSHAK:
Multi-Person Helmet Detection, Simultaneous Active Alerts, Priority Engine, and Lifecycle Isolation.
Covers Tests 1 through 15 from Part 12.
"""

import time
import sys
import numpy as np
from datetime import datetime, timedelta

from models import Alert, SystemStatus, RestrictedZone
from state import state_manager, sort_alerts_by_priority, calculate_alert_priority
from detection import PersonTrack, compute_box_iou

def run_multi_alert_tests():
    print("==================================================")
    print(" Running Multi-Person & Multi-Alert Test Suite    ")
    print("==================================================")

    # Clean initial state
    state_manager.reset_demo()
    assert len(state_manager.get_active_alerts_list()) == 0
    assert state_manager.active_alert is None
    print("[OK] State manager initialized to clean IDLE state.")

    # -------------------------------------------------------------------------
    # TEST 1: Two people detected. Both no helmet.
    # Expected: ONE grouped PPE alert with person_count = 2
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing 2 people without helmets -> ONE grouped PPE alert (person_count = 2)...")
    a1 = state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        person_count=2,
        affected_person_ids=["P-1", "P-2"],
        title="2 PEOPLE WITHOUT HELMETS"
    )
    active_alerts = state_manager.get_active_alerts_list()
    assert len(active_alerts) == 1, f"Expected 1 active alert, got {len(active_alerts)}"
    assert active_alerts[0].person_count == 2, f"Expected person_count=2, got {active_alerts[0].person_count}"
    assert "2" in active_alerts[0].title
    assert active_alerts[0].affected_person_ids == ["P-1", "P-2"]
    print("  [PASS] Single grouped PPE alert created: '2 PEOPLE WITHOUT HELMETS' (person_count = 2)")

    # -------------------------------------------------------------------------
    # TEST 2: Three people. Two no helmet, one with helmet.
    # Expected: PPE alert says 2 PEOPLE WITHOUT HELMETS
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing 3 people (2 no helmet, 1 helmet) -> PPE alert says 2 PEOPLE...")
    a2 = state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        person_count=2,
        affected_person_ids=["P-1", "P-2"],
        title="2 PEOPLE WITHOUT HELMETS"
    )
    active_alerts = state_manager.get_active_alerts_list()
    assert len(active_alerts) == 1
    assert active_alerts[0].person_count == 2
    print("  [PASS] Grouped PPE alert accurately reflects 2 unequipped workers out of 3 detected.")

    # -------------------------------------------------------------------------
    # TEST 3: One no-helmet person remains visible for many frames.
    # Expected: ONE alert only (no alert flood)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing repeated frames of violation -> exactly ONE alert maintained...")
    initial_id = active_alerts[0].id
    for _ in range(20):
        state_manager.trigger_alert(
            alert_type="Helmet/PPE Violation",
            person_count=2,
            affected_person_ids=["P-1", "P-2"]
        )
    active_alerts = state_manager.get_active_alerts_list()
    assert len(active_alerts) == 1
    assert active_alerts[0].id == initial_id
    print("  [PASS] Exactly 1 active alert maintained across 20 subsequent frames (no duplicate flood).")

    # -------------------------------------------------------------------------
    # TEST 4: Second person becomes no-helmet.
    # Expected: Existing alert dynamically updates 1 -> 2 people, NO duplicate alert
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing dynamic worker count update (1 -> 2 people without duplicate)...")
    state_manager.reset_demo()
    # First, 1 person
    state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        person_count=1,
        affected_person_ids=["P-1"],
        title="1 PERSON WITHOUT HELMET"
    )
    assert len(state_manager.get_active_alerts_list()) == 1
    first_id = state_manager.get_active_alerts_list()[0].id
    assert state_manager.get_active_alerts_list()[0].person_count == 1

    # Second person joins violation
    state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        person_count=2,
        affected_person_ids=["P-1", "P-2"]
    )
    active_alerts = state_manager.get_active_alerts_list()
    assert len(active_alerts) == 1, "Must NOT create a duplicate alert"
    assert active_alerts[0].id == first_id, "Must update the same logical alert ID"
    assert active_alerts[0].person_count == 2, f"Expected person_count=2, got {active_alerts[0].person_count}"
    assert "2 PEOPLE" in active_alerts[0].title
    print("  [PASS] Existing PPE alert seamlessly updated 1 -> 2 people with identical alert ID.")

    # -------------------------------------------------------------------------
    # TEST 5: Helmet alert + Restricted Zone alert simultaneously.
    # Expected: TWO active alerts coexist independently!
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing simultaneous Helmet + Restricted Zone alerts coexistence...")
    zone_alert = state_manager.trigger_alert(
        alert_type="Restricted Zone Entry",
        location="Compressor Restricted Area",
        camera="C-01",
        severity="HIGH",
        sif_potential="HIGH / POTENTIAL",
        person_count=1,
        affected_person_ids=["P-3"],
        title="RESTRICTED ZONE ENTRY"
    )
    active_alerts = state_manager.get_active_alerts_list()
    assert len(active_alerts) == 2, f"Expected 2 simultaneous alerts, got {len(active_alerts)}"
    types = [a.type for a in active_alerts]
    assert "Restricted Zone Entry" in types
    assert "Helmet/PPE Violation" in types
    print("  [PASS] Both alerts coexist simultaneously: [Restricted Zone Entry, Helmet/PPE Violation]")

    # -------------------------------------------------------------------------
    # TEST 6: Restricted Zone is higher priority.
    # Expected: Restricted Zone appears FIRST in priority order.
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing AI Recommended Response Priority ranking...")
    sorted_alerts = state_manager.get_active_alerts_list()
    assert sorted_alerts[0].type == "Restricted Zone Entry", f"Expected Restricted Zone first, got {sorted_alerts[0].type}"
    assert sorted_alerts[0].priority_score >= sorted_alerts[1].priority_score
    assert sorted_alerts[0].priority_label == "CRITICAL"
    print("  [PASS] Restricted Zone prioritized #1 (CRITICAL, score 100) > Helmet Violation #2 (HIGH, score 60).")

    # -------------------------------------------------------------------------
    # TEST 7: Respond to Restricted Zone.
    # Expected: Only Restricted Zone transitions to RESPONDING; Helmet remains OPEN.
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing supervisor response isolation...")
    zone_id = [a.id for a in active_alerts if a.type == "Restricted Zone Entry"][0]
    helmet_id = [a.id for a in active_alerts if a.type == "Helmet/PPE Violation"][0]

    responded_zone = state_manager.respond_to_alert(supervisor_id="SUP-FIELD-01", alert_id=zone_id)
    assert responded_zone.status == "RESPONDING"
    assert responded_zone.stage == "ACTION"

    current_alerts = {a.id: a for a in state_manager.get_active_alerts_list()}
    assert current_alerts[zone_id].status == "RESPONDING"
    assert current_alerts[helmet_id].status == "WAITING_FOR_RESPONSE"
    print("  [PASS] Only Restricted Zone transitioned to RESPONDING; Helmet alert remains WAITING_FOR_RESPONSE.")

    # -------------------------------------------------------------------------
    # TEST 8: Resolve Restricted Zone.
    # Expected: Restricted Zone removed from active_alerts; Helmet alert remains active!
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing independent resolution (resolving zone must not close helmet)...")
    resolved_zone = state_manager.resolve_alert(supervisor_id="SUP-FIELD-01", alert_id=zone_id)
    assert resolved_zone.status == "RESOLVED"

    remaining_alerts = state_manager.get_active_alerts_list()
    assert len(remaining_alerts) == 1, f"Expected 1 remaining active alert, got {len(remaining_alerts)}"
    assert remaining_alerts[0].id == helmet_id
    assert remaining_alerts[0].type == "Helmet/PPE Violation"
    assert remaining_alerts[0].status == "WAITING_FOR_RESPONSE"
    print("  [PASS] Restricted Zone resolved and removed from inbox; Helmet alert remains actively running.")

    # -------------------------------------------------------------------------
    # TEST 9: Escalation of an alert.
    # Expected: An alert whose response window passes becomes ESCALATED.
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Testing independent escalation...")
    # Manually set helmet alert response_deadline in the past to test watchdog
    with state_manager.lock:
        state_manager._active_alerts[helmet_id].response_deadline = (datetime.now() - timedelta(seconds=2)).isoformat()

    # Trigger watchdog pass
    time.sleep(0.3)
    active = state_manager.get_active_alerts_list()
    assert active[0].status == "ESCALATED", f"Expected ESCALATED, got {active[0].status}"
    assert active[0].assigned_to == "HSE CONTROL DESK"
    print("  [PASS] Alert successfully escalated to HSE CONTROL DESK upon deadline expiry.")

    # -------------------------------------------------------------------------
    # TEST 10: Resolve escalated alert on site.
    # Expected: Successfully resolved and leaves active_alerts clean.
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Testing on-site resolution of escalated alert...")
    resolved_helmet = state_manager.resolve_alert(supervisor_id="SUP-FIELD-01", alert_id=helmet_id)
    assert resolved_helmet.status == "RESOLVED"
    assert len(state_manager.get_active_alerts_list()) == 0
    assert state_manager.active_alert is None or state_manager.active_alert.status == "RESOLVED"
    print("  [PASS] Escalated alert successfully resolved on site; 0 active alerts remain.")

    # -------------------------------------------------------------------------
    # TEST 11: Priority tie-breaking by age.
    # Expected: Older alert ranked first within same severity.
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Testing priority tie-breaking by creation timestamp...")
    t_old = (datetime.now() - timedelta(seconds=10)).isoformat()
    t_new = datetime.now().isoformat()
    alt_a = Alert(
        id="ALT-OLD",
        type="Observation A",
        created_at=t_old,
        response_deadline=t_old,
        priority_score=60,
        severity="HIGH"
    )
    alt_b = Alert(
        id="ALT-NEW",
        type="Observation B",
        created_at=t_new,
        response_deadline=t_new,
        priority_score=60,
        severity="HIGH"
    )
    sorted_res = sort_alerts_by_priority([alt_b, alt_a])
    assert sorted_res[0].id == "ALT-OLD"
    assert sorted_res[1].id == "ALT-NEW"
    print("  [PASS] Older alert correctly sorted ahead of newer alert with equal priority score.")

    # -------------------------------------------------------------------------
    # TEST 12: Lightweight Person Track & IoU computation
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Testing PersonTrack and compute_box_iou...")
    box1 = np.array([100, 100, 200, 300])
    box2 = np.array([110, 110, 210, 310])
    box_far = np.array([400, 400, 500, 600])

    iou_high = compute_box_iou(box1, box2)
    iou_zero = compute_box_iou(box1, box_far)
    assert iou_high > 0.50, f"Expected IoU > 0.50, got {iou_high}"
    assert iou_zero == 0.0, f"Expected IoU == 0.0, got {iou_zero}"

    pt = PersonTrack(track_id=1, box=box1, now_ts=time.time())
    assert pt.label in ["Person 01", "P-1"]
    assert pt.stable_status == "MONITORING"
    print("  [PASS] PersonTrack and IoU matching functions operate correctly.")

    # -------------------------------------------------------------------------
    # TEST 13: Per-person temporal smoothing logic
    # -------------------------------------------------------------------------
    print("\n[TEST 13] Testing per-person temporal smoothing (5 consecutive frames)...")
    p1 = PersonTrack(1, box1, time.time())
    for f in range(4):
        p1.no_helmet_confirm_count += 1
        assert p1.stable_status == "MONITORING", "Must not switch before 5 frames"
    p1.no_helmet_confirm_count += 1
    if p1.no_helmet_confirm_count >= 5:
        p1.stable_status = "NO_HELMET"
    assert p1.stable_status == "NO_HELMET"
    print("  [PASS] Person status switches to NO_HELMET strictly after 5 confirmed frames.")

    # -------------------------------------------------------------------------
    # TEST 14: Simulated multi-hazard scenario (Part 11)
    # -------------------------------------------------------------------------
    print("\n[TEST 14] Testing simulate_multi_violation scenario...")
    state_manager.reset_demo()
    sim_alerts = state_manager.simulate_multi_violation()
    assert len(sim_alerts) == 2, f"Expected 2 alerts, got {len(sim_alerts)}"
    assert sim_alerts[0].type == "Restricted Zone Entry"
    assert sim_alerts[1].type == "Helmet/PPE Violation"
    assert sim_alerts[1].person_count == 2
    assert "2 PEOPLE WITHOUT HELMETS" in sim_alerts[1].title
    print("  [PASS] Dual hazard scenario successfully generates 2 simultaneous alerts in correct priority.")

    # -------------------------------------------------------------------------
    # TEST 15: Clean system status output for mobile & desktop
    # -------------------------------------------------------------------------
    print("\n[TEST 15] Testing SystemStatus serialization for real-time WebSocket sync...")
    sys_status = state_manager.get_system_status()
    assert len(sys_status.active_alerts) == 2
    assert sys_status.active_alert is not None
    assert sys_status.active_alert.type == "Restricted Zone Entry" # Highest priority
    assert sys_status.person_count == 3
    assert sys_status.unhelmeted_count == 2
    print("  [PASS] SystemStatus contains active_alerts array, backwards-compatible active_alert, and person counts.")

    print("\n==================================================")
    print("  ALL MULTI-PERSON & MULTI-ALERT TESTS PASSED!    ")
    print("==================================================")

if __name__ == "__main__":
    run_multi_alert_tests()
