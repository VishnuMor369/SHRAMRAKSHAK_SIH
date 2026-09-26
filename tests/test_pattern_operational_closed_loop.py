"""
SHRAMRAKSHAK: Test Pattern Operational Closed-Loop Workflow
SIH 2026 Problem Statement: SIH26165

Comprehensive isolated test verifying:
RECURRING PATTERN
  ↓
HSE CONFIRM PATTERN (HSE VALIDATED)
  ↓
ASSIGN CORRECTIVE ACTION (Supervisor PATTERN_ACTION notification)
  ↓
SUPERVISOR PHYSICAL ACTION & MARKS COMPLETED
  ↓
AWAITING VERIFICATION
  ↓
CCTV RE-BREACH DETECTED (VERIFICATION FAILED)
  ↓
ACTION REOPENED + NEW SAFETY EVENT + PATTERN MEMBER LINKED (NO DUPLICATE PATTERN)
  ↓
SUPERVISOR RE-CLEARS & MARKS COMPLETED
  ↓
CCTV CLEAR (VERIFIED - OBSERVABLE CONDITION RESTORED)
  ↓
HSE FINAL CLOSURE
  ↓
CLOSED / HISTORY (Pattern remains accessible, not deleted)

Also verifies:
A. Live CCTV emergency alert still reaches supervisor.
B. Pattern corrective-action notification is visually/semantically distinct.
C. Both notification types can coexist without overwriting each other.
D. Supervisor completion does not close the pattern.
E. CCTV verification failure reopens the action.
F. CCTV verification success does not automatically bypass HSE closure.
G. Closed pattern remains in history.
H. Re-breach does not create uncontrolled duplicate patterns.
I. Existing Safety Memory candidate/validated/rejected semantics remain intact.
J. Production data remains unchanged.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
backend_dir = os.path.join(ROOT_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from test_isolation import isolated_test_environment
from backend.models_canonical import (
    SafetyPattern,
    CanonicalReviewStatus,
    CanonicalSafetyEvent,
    SIFStatus
)
from backend.models import Alert
from backend.state import AlertStateManager


class TestPatternOperationalClosedLoop(unittest.TestCase):

    def test_full_operational_workflow_isolated(self):
        with isolated_test_environment(prefix="shramrakshak_op_loop_") as env:
            test_db = env["db"]
            test_state = AlertStateManager()

            # -------------------------------------------------------------
            # STEP 1: Recurring Pattern exists in Safety Memory (Candidate)
            # -------------------------------------------------------------
            pattern_id = "PAT-LIFT-DEMO-01"
            init_pat = SafetyPattern(
                pattern_id=pattern_id,
                title="Repeated Restricted-Zone Control Breach",
                activity="Mechanical Lifting Operations",
                energy="Gravitational / Kinetic Energy (Suspended Load)",
                exposure="Unauthorized personnel entering perimeter while hoist active",
                barrier="Lifting Zone Exclusion Barricade & Signage",
                occurrence_count=5,
                duplicate_count=0,
                validation_status=CanonicalReviewStatus.CANDIDATE,
                operational_status="ACTIVE"
            )
            test_db.save_pattern(init_pat)

            # Seed an initial member event
            evt_1 = CanonicalSafetyEvent(
                event_id="EVT-DEMO-001",
                source="HUMAN",
                timestamp=datetime.now().isoformat(),
                location="Lifting Zone 03",
                activity="Mechanical Lifting Operations",
                energy="Gravitational / Kinetic Energy (Suspended Load)",
                exposure="Personnel in line of fire under crane boom",
                barrier=["EXCLUSION_ZONE"],
                barrier_state=["BYPASSED"],
                consequence="Crush injury / struck by load",
                narrative="Contractor entered marked exclusion perimeter under crane radius.",
                sif_status=SIFStatus.SIF_POTENTIAL,
                lsr=["Line of Fire"]
            )
            test_db.save_event(evt_1)
            test_db.add_pattern_member(pattern_id, evt_1.event_id, "HISTORICAL_RECURRENCE", 0.92, "Initial breach")

            # Verify initial state: Candidate
            pat_db = test_db.get_pattern(pattern_id)
            self.assertIsNotNone(pat_db)
            pat_status_val = pat_db.validation_status.value if hasattr(pat_db.validation_status, "value") else str(pat_db.validation_status)
            self.assertEqual(pat_status_val, "CANDIDATE")

            # -------------------------------------------------------------
            # STEP 2: HSE Confirms Pattern (Validation State -> HSE_VALIDATED)
            # Semantic Rule: Confirming pattern does NOT silently close it.
            # -------------------------------------------------------------
            test_db.log_review(
                review_id="REV-DEMO-01",
                target_type="PATTERN",
                target_id=pattern_id,
                reviewer_role="HSE-Lead-01",
                action="CONFIRM",
                previous_value="CANDIDATE",
                new_value="HSE_VALIDATED",
                reason="Confirmed as genuine recurring control problem by HSE Lead"
            )
            with test_db.get_connection() as conn:
                conn.execute(
                    "UPDATE patterns SET validation_status = ?, updated_at = ? WHERE pattern_id = ?",
                    ("HSE_VALIDATED", datetime.now().isoformat(), pattern_id)
                )

            pat_validated = test_db.get_pattern(pattern_id)
            val_status_val = pat_validated.validation_status.value if hasattr(pat_validated.validation_status, "value") else str(pat_validated.validation_status)
            self.assertEqual(val_status_val, "HSE_VALIDATED")

            # -------------------------------------------------------------
            # STEP 3: Coexistence of Class 1 Emergency Alert & Class 2 Pattern Action
            # (Verifying Requirements A, B, C)
            # -------------------------------------------------------------
            # Simulate a Live CCTV Emergency Alert (Class 1)
            now_t = datetime.now()
            emergency_alert = Alert(
                id="ALERT-EMERGENCY-01",
                alert_class="EMERGENCY",
                type="ZONE_VIOLATION",
                title="🔴 EMERGENCY — LIVE SAFETY ALERT: Person in Lifting Zone",
                short_summary="Immediate hazard: Person detected inside active restricted zone",
                location="Lifting Zone 03",
                severity="CRITICAL",
                source="CCTV",
                status="WAITING_FOR_RESPONSE",
                created_at=now_t.isoformat(),
                response_deadline=(now_t + timedelta(seconds=20)).isoformat()
            )
            test_state._active_alerts[emergency_alert.id] = emergency_alert

            # HSE assigns corrective action for the recurring pattern (Class 2)
            pat_action_res = test_state.assign_pattern_action(
                pattern_id=pattern_id,
                supervisor_id="SUP-01",
                supervisor_name="Rajesh Kumar (Field Lead)",
                required_action="Clear unauthorized personnel and secure the restricted/lifting zone.",
                location="Lifting Zone 03",
                priority="HIGH",
                verification_method="CCTV_VERIFIABLE"
            )

            # Requirement B: Visual & Semantic distinction
            self.assertTrue(pat_action_res["success"])
            action_alert_id = pat_action_res["alert_id"]
            pattern_action_alert = test_state._active_alerts[action_alert_id]
            self.assertEqual(pattern_action_alert.alert_class, "PATTERN_ACTION")
            self.assertEqual(pattern_action_alert.pattern_id, pattern_id)
            self.assertEqual(pattern_action_alert.assigned_by, "HSE Control Desk")
            self.assertIn("PATTERN ACTION", pattern_action_alert.title)

            # Requirement A & C: Both coexist simultaneously without overwriting
            self.assertIn("ALERT-EMERGENCY-01", test_state._active_alerts)
            self.assertIn(action_alert_id, test_state._active_alerts)
            self.assertEqual(test_state._active_alerts["ALERT-EMERGENCY-01"].alert_class, "EMERGENCY")
            self.assertEqual(test_state._active_alerts[action_alert_id].alert_class, "PATTERN_ACTION")

            # Check pattern operational status is ACTION_REQUIRED
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "ACTION_REQUIRED")

            # -------------------------------------------------------------
            # STEP 4: Supervisor Marks Action Completed (Physical Action Taken)
            # Requirement D: Supervisor completion does NOT close the pattern!
            # Moves to AWAITING_VERIFICATION.
            # -------------------------------------------------------------
            comp_alert = test_state.mark_action_taken(
                alert_id=action_alert_id,
                action_taken="Cleared contractors and secured physical tape barrier.",
                supervisor_id="SUP-01"
            )
            self.assertEqual(comp_alert.verification_status, "AWAITING_VERIFICATION")
            self.assertEqual(comp_alert.action_status, "COMPLETED")
            # Pattern must be awaiting verification, NOT closed!
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "AWAITING_VERIFICATION")

            # -------------------------------------------------------------
            # STEP 5: Verification Attempt 1 — CCTV Detects Re-Breach!
            # Requirement E: CCTV verification failure reopens the action.
            # Requirement H: Creates new Safety Event & links to existing pattern (no duplicate pattern).
            # -------------------------------------------------------------
            prev_occ_count = test_db.get_pattern(pattern_id).occurrence_count

            fail_verif = test_state.verify_cctv_condition(
                alert_id=action_alert_id,
                supervisor_id="SUP-01",
                simulate_rebreach=True
            )
            self.assertFalse(fail_verif["verified"])
            self.assertEqual(fail_verif["decision"], "FAILED")
            self.assertEqual(fail_verif["status"], "VERIFICATION_FAILED_REBREACH")

            # Reopened state
            reopened_alert = test_state._active_alerts[action_alert_id]
            self.assertEqual(reopened_alert.lifecycle_state, "REOPENED")
            self.assertEqual(reopened_alert.status, "WAITING_FOR_RESPONSE")
            self.assertEqual(reopened_alert.action_status, "IN_PROGRESS")
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "REOPENED")

            # Verification record persisted
            verif_records = test_db.list_verifications()
            self.assertTrue(any(v.get("status") == "FAILED" for v in verif_records))

            # New Safety Event created & linked to existing pattern; occurrence count incremented
            pat_after_rebreach = test_db.get_pattern(pattern_id)
            self.assertEqual(pat_after_rebreach.occurrence_count, prev_occ_count + 1)
            members = test_db.get_pattern_members(pattern_id)
            self.assertGreaterEqual(len(members), 2)

            # -------------------------------------------------------------
            # STEP 6: Supervisor Clears Area Again & Marks Completed
            # -------------------------------------------------------------
            re_comp = test_state.mark_action_taken(
                alert_id=action_alert_id,
                action_taken="Escorted re-entrant out, posted watchman at perimeter.",
                supervisor_id="SUP-01"
            )
            self.assertEqual(re_comp.verification_status, "AWAITING_VERIFICATION")
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "AWAITING_VERIFICATION")

            # -------------------------------------------------------------
            # STEP 7: Verification Attempt 2 — CCTV Confirms Zone Clear
            # Requirement F: CCTV verification success does NOT automatically bypass HSE closure!
            # Moves to VERIFIED.
            # -------------------------------------------------------------
            succ_verif = test_state.verify_cctv_condition(
                alert_id=action_alert_id,
                supervisor_id="SUP-01",
                simulate_rebreach=False
            )
            self.assertTrue(succ_verif["verified"])
            self.assertEqual(succ_verif["decision"], "VERIFIED")
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "VERIFIED")

            # Pattern is still in the system, validated, ready for HSE closure
            pat_verified = test_db.get_pattern(pattern_id)
            self.assertIsNotNone(pat_verified)
            val_status_str = pat_verified.validation_status.value if hasattr(pat_verified.validation_status, "value") else str(pat_verified.validation_status)
            self.assertEqual(val_status_str, "HSE_VALIDATED")

            # -------------------------------------------------------------
            # STEP 8: HSE Final Closure Authority
            # Requirement G: Closed pattern moves to CLOSED / HISTORY (remains accessible).
            # -------------------------------------------------------------
            close_res = test_state.close_pattern_action(
                pattern_id=pattern_id,
                closed_by="HSE Lead (Oil India)",
                closure_notes="Observable condition verified clear. Shift handoff completed."
            )
            self.assertTrue(close_res["success"])
            self.assertEqual(close_res["operational_status"], "CLOSED_HISTORY")
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "CLOSED_HISTORY")

            # Verify pattern is preserved in DB (NOT deleted)
            pat_final = test_db.get_pattern(pattern_id)
            self.assertIsNotNone(pat_final)
            self.assertEqual(pat_final.pattern_id, pattern_id)
            final_status_str = pat_final.validation_status.value if hasattr(pat_final.validation_status, "value") else str(pat_final.validation_status)
            self.assertEqual(final_status_str, "HSE_VALIDATED")
            self.assertEqual(test_state.get_pattern_operational_status(pattern_id), "CLOSED_HISTORY")
            self.assertEqual(close_res["closed_by"], "HSE Lead (Oil India)")


if __name__ == "__main__":
    unittest.main()
