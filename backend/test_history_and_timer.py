"""
SHRAMRAKSHAK Test Suite:
1. 20-Second Response SLA & Backend Countdown
2. Escalation reason validation ("20 seconds")
3. Real Alert History Management & Lifecycle Isolation
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models import Alert
from state import state_manager, RESPONSE_SLA_SECONDS, ACTION_SLA_SECONDS

def run_all_tests():
    print("=" * 60)
    print(" Running 20s Timer & Alert History Test Suite")
    print("=" * 60)

    # Clean initial state
    state_manager.reset_demo()
    assert len(state_manager.get_active_alerts_list()) == 0
    assert len(state_manager.get_history_list()) == 0
    print("[OK] State manager initialized to clean IDLE state.")

    # -------------------------------------------------------------------------
    # PART 1: RESPONSE TIMER (20s SLA)
    # -------------------------------------------------------------------------
    print("\n--- PART 1: 20-SECOND RESPONSE SLA TESTS ---")

    print("\n[TEST T1] Verifying configured response window is 20 seconds...")
    assert RESPONSE_SLA_SECONDS == 20, f"Expected RESPONSE_SLA_SECONDS=20, got {RESPONSE_SLA_SECONDS}"
    assert ACTION_SLA_SECONDS == 60, f"Expected ACTION_SLA_SECONDS=60, got {ACTION_SLA_SECONDS}"
    print("  [PASS] RESPONSE_SLA_SECONDS = 20, ACTION_SLA_SECONDS = 60 confirmed.")

    print("\n[TEST T2] Triggering alert and verifying response_deadline = created_at + 20s...")
    alert = state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        location="Demo Work Zone",
        camera="C-01",
        person_count=1
    )
    assert alert is not None
    assert alert.response_duration_sec == 20, f"Expected response_duration_sec=20, got {alert.response_duration_sec}"
    created = datetime.fromisoformat(alert.created_at)
    deadline = datetime.fromisoformat(alert.response_deadline)
    diff = (deadline - created).total_seconds()
    assert abs(diff - 20) < 0.5, f"Expected ~20s between created_at and deadline, got {diff}s"
    print(f"  [PASS] Backend deadline starts at alert creation: diff = {diff:.2f}s (exact 20s window).")

    print("\n[TEST T3] Verifying supervisor responds before 20s -> transitions to RESPONDING...")
    responded = state_manager.respond_to_alert(supervisor_id="SUP-FIELD-01", alert_id=alert.id)
    assert responded is not None
    assert responded.status == "RESPONDING"
    assert responded.stage == "ACTION"
    assert responded.responded_at is not None
    print(f"  [PASS] Stage 1 response confirmed within 20s window -> RESPONDING.")

    print("\n[TEST T4] Resolving alert and verifying clean transition...")
    resolved = state_manager.resolve_alert(supervisor_id="SUP-FIELD-01", notes="Worker donned helmet", alert_id=alert.id)
    assert resolved.status == "RESOLVED"
    print("  [PASS] Alert successfully marked RESOLVED.")

    print("\n[TEST T5] Verifying no response after 20s -> ESCALATED with 20-second reason...")
    # Trigger a new alert
    esc_alert = state_manager.trigger_alert(
        alert_type="Restricted Zone Entry",
        location="Compressor Exclusion Area",
        camera="C-01",
        person_count=1
    )
    # Simulate expiration by setting response_deadline in the past
    with state_manager.lock:
        state_manager._active_alerts[esc_alert.id].response_deadline = (datetime.now() - timedelta(seconds=2)).isoformat()

    # Wait for watchdog check (runs every 0.2s)
    time.sleep(0.35)

    active_alerts = {a.id: a for a in state_manager.get_active_alerts_list()}
    assert esc_alert.id in active_alerts, "Escalated alert should remain in active alerts"
    escalated_alert = active_alerts[esc_alert.id]
    assert escalated_alert.status == "ESCALATED", f"Expected ESCALATED, got {escalated_alert.status}"
    assert escalated_alert.was_escalated is True
    assert escalated_alert.assigned_to == "HSE CONTROL DESK"
    assert "20 seconds" in escalated_alert.reason, f"Expected '20 seconds' in reason, got: {escalated_alert.reason}"
    print(f"  [PASS] Alert escalated to HSE CONTROL DESK. Reason: '{escalated_alert.reason}'")

    # Clean up for Part 2
    state_manager.reset_demo()

    # -------------------------------------------------------------------------
    # PART 2: MOBILE ALERT HISTORY TESTS (PART 22 FROM SPECIFICATION)
    # -------------------------------------------------------------------------
    print("\n--- PART 2: MOBILE HISTORY TESTS ---")

    print("\n[TEST H1] Create alert -> Appears in ACTIVE ALERTS...")
    h_alert1 = state_manager.trigger_alert(
        alert_type="Restricted Zone Entry",
        location="Compressor Restricted Area",
        camera="C-01",
        person_count=1,
        title="RESTRICTED ZONE ENTRY"
    )
    active = state_manager.get_active_alerts_list()
    assert len(active) == 1
    assert active[0].id == h_alert1.id
    print("  [PASS] Alert successfully created and present in ACTIVE ALERTS.")

    print("\n[TEST H2] Resolve alert -> Removed from ACTIVE ALERTS...")
    state_manager.resolve_alert(supervisor_id="SUP-FIELD-01", notes="Worker escorted out", alert_id=h_alert1.id)
    active_after = state_manager.get_active_alerts_list()
    assert len(active_after) == 0, f"Expected 0 active alerts, got {len(active_after)}"
    print("  [PASS] Alert removed from ACTIVE ALERTS upon resolution.")

    print("\n[TEST H3] Resolved alert appears in HISTORY...")
    hist = state_manager.get_history_list()
    assert len(hist) == 1, f"Expected 1 history item, got {len(hist)}"
    assert hist[0].id == h_alert1.id
    print(f"  [PASS] Resolved alert {hist[0].id} is present in HISTORY.")

    print("\n[TEST H4] History contains correct alert type...")
    assert hist[0].type == "Restricted Zone Entry"
    print(f"  [PASS] Correct alert type preserved: {hist[0].type}")

    print("\n[TEST H5] History contains correct people count...")
    assert hist[0].person_count == 1
    print(f"  [PASS] Correct people count preserved: {hist[0].person_count}")

    print("\n[TEST H6] History contains correct location and camera...")
    assert hist[0].location == "Compressor Restricted Area"
    assert hist[0].camera == "C-01"
    print(f"  [PASS] Location ({hist[0].location}) and Camera ({hist[0].camera}) preserved.")

    print("\n[TEST H7] History contains correct final status (RESOLVED)...")
    assert hist[0].status == "RESOLVED"
    assert hist[0].resolved_at is not None
    print(f"  [PASS] Final status is RESOLVED with resolved_at={hist[0].resolved_at}.")

    print("\n[TEST H8] Escalated alert resolved later -> History shows was_escalated = True...")
    esc_alert2 = state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        location="Demo Work Zone",
        camera="C-01",
        person_count=2,
        title="2 PEOPLE WITHOUT HELMETS"
    )
    # Force watchdog escalation
    with state_manager.lock:
        state_manager._active_alerts[esc_alert2.id].response_deadline = (datetime.now() - timedelta(seconds=1)).isoformat()
    time.sleep(0.35)

    assert state_manager._active_alerts[esc_alert2.id].status == "ESCALATED"
    # Now resolve the escalated alert on site
    state_manager.resolve_alert(supervisor_id="SUP-FIELD-01", notes="On-site hard-hat donning enforced", alert_id=esc_alert2.id)

    hist_after_esc = state_manager.get_history_list()
    assert len(hist_after_esc) == 2, f"Expected 2 history items, got {len(hist_after_esc)}"
    # Newest resolved first
    latest_hist = hist_after_esc[0]
    assert latest_hist.id == esc_alert2.id
    assert latest_hist.status == "RESOLVED"
    assert latest_hist.was_escalated is True, "Expected was_escalated=True for escalated->resolved alert"
    assert latest_hist.escalated_at is not None
    print(f"  [PASS] Escalated alert preserved in history with was_escalated=True (ESCALATED -> RESOLVED).")

    print("\n[TEST H9] Two simultaneous alerts: resolve ONLY one -> One history record, other remains active...")
    state_manager.reset_demo()
    a_zone = state_manager.trigger_alert(alert_type="Restricted Zone Entry", location="Compressor Area", camera="C-01")
    time.sleep(0.01)
    a_ppe = state_manager.trigger_alert(alert_type="Helmet/PPE Violation", location="Work Zone", camera="C-01")

    assert len(state_manager.get_active_alerts_list()) == 2
    assert len(state_manager.get_history_list()) == 0

    # Resolve only Restricted Zone
    state_manager.resolve_alert(supervisor_id="SUP-01", alert_id=a_zone.id)

    active_now = state_manager.get_active_alerts_list()
    assert len(active_now) == 1, f"Expected 1 remaining active alert, got {len(active_now)}"
    assert active_now[0].id == a_ppe.id

    history_now = state_manager.get_history_list()
    assert len(history_now) == 1, f"Expected 1 history item, got {len(history_now)}"
    assert history_now[0].id == a_zone.id
    print("  [PASS] Resolving Zone moved Zone to History; Helmet remains active with independent lifecycle.")

    print("\n[TEST H10] Resolve second alert -> Both appear separately in HISTORY...")
    state_manager.resolve_alert(supervisor_id="SUP-01", alert_id=a_ppe.id)
    assert len(state_manager.get_active_alerts_list()) == 0
    final_history = state_manager.get_history_list()
    assert len(final_history) == 2, f"Expected 2 history items, got {len(final_history)}"
    ids = [h.id for h in final_history]
    assert a_zone.id in ids and a_ppe.id in ids
    print(f"  [PASS] Both alerts appear separately in history: {ids}")

    print("\n[TEST H11] Empty history state works upon reset...")
    state_manager.reset_demo()
    assert len(state_manager.get_history_list()) == 0
    print("  [PASS] Empty history state confirmed after reset_demo().")

    print("\n" + "=" * 60)
    print(" ALL 20s TIMER & ALERT HISTORY TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_all_tests()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
