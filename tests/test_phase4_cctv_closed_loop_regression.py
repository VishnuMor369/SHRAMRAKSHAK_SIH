"""
SHRAMRAKSHAK: Phase 4 CCTV & Operational Closed-Loop Regression Test Suite
SIH 2026 Problem Statement: SIH26165

Rigorous verification of Phase 4 requirements:
1. Action State Lifecycle (ASSIGNED -> IN_PROGRESS -> COMPLETED -> AWAITING_VERIFICATION -> VERIFIED / FAILED -> REOPENED -> CLOSED)
2. Awaiting Verification ("Completion is not proof" - supervisor completion cannot close pattern)
3. CCTV Verification (Objective observable condition check restores verified state)
4. Re-breach Detection (Re-breach triggers VERIFICATION_FAILED and reopens action)
5. Safety Memory Feedback (Re-breach emits canonical SafetyEvent into SQLite and FAISS semantic memory; links to pattern without duplicate pattern)
6. Pattern History Preservation (HSE closed pattern transitions to CLOSED_HISTORY and remains accessible, never deleted)
7. Coexistence (Class 1 Emergency Alert and Class 2 Pattern Action coexist without collision)
"""

import os
import sys
import unittest
import uuid
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
    ReviewStatus,
    SafetyEvent,
    SIFStatus,
    BarrierState
)
from backend.models import Alert
from backend.state import AlertStateManager
from backend.nlp_engine.semantic_memory import semantic_memory


class TestPhase4CCTVClosedLoopRegression(unittest.TestCase):

    def test_item_1_and_2_action_state_and_awaiting_verification(self):
        """
        Phase 4 Items 1 & 2: Action State Lifecycle & Awaiting Verification
        Demonstrates that supervisor action moves status to COMPLETED and
        verification_status to AWAITING_VERIFICATION, but DOES NOT resolve or close.
        """
        with isolated_test_environment(prefix="p4_state_") as env:
            test_db = env["db"]
            state = AlertStateManager()

            # Trigger fresh alert
            alert = state.trigger_alert(
                alert_type="Restricted Zone Entry",
                location="Drilling Rig 04 - Lifting Zone",
                camera="C-01",
                severity="CRITICAL",
                sif_potential="SIF Potential",
                hazard="Suspended Load Kinetic Energy"
            )
            self.assertIsNotNone(alert)
            alert_id = alert.id
            self.assertEqual(alert.status, "WAITING_FOR_RESPONSE")
            self.assertEqual(alert.action_status, "ASSIGNED")

            # Supervisor responds: IN_PROGRESS
            resp_alert = state.respond_to_alert("SUP-OIL-01", "Supervisor moving to hold crane", alert_id)
            self.assertEqual(resp_alert.status, "RESPONDING")
            self.assertEqual(resp_alert.action_status, "IN_PROGRESS")

            # Supervisor completes physical barrier fix: AWAITING_VERIFICATION
            comp_alert = state.mark_action_taken(alert_id, "SUP-OIL-01", "Demarcated 15m radius with red barrier tape")
            self.assertEqual(comp_alert.action_status, "COMPLETED")
            self.assertEqual(comp_alert.verification_status, "AWAITING_VERIFICATION")
            self.assertEqual(comp_alert.status, "AWAITING_VERIFICATION")

            # CRITICAL SAFETY INVARIANT: "Completion is not proof"
            # Supervisor marking completed does NOT mean resolved or closed!
            self.assertNotEqual(comp_alert.status, "RESOLVED")
            self.assertNotEqual(comp_alert.verification_status, "VERIFIED")

    def test_item_3_cctv_verification_observable_condition_restored(self):
        """
        Phase 4 Item 3: CCTV Verification (Clear Zone)
        Objective vision verification checks physical condition and restores verified status.
        """
        with isolated_test_environment(prefix="p4_cctv_clear_") as env:
            test_db = env["db"]
            state = AlertStateManager()

            alert = state.trigger_alert(
                alert_type="Restricted Zone Entry",
                location="Lifting Zone 03",
                camera="C-01"
            )
            state.mark_action_taken(alert.id, "SUP-01", "Personnel cleared from zone")

            # Simulate clear zone: no violations, 0 persons in restricted perimeter
            state.zone_violation = False
            state.persons_in_zone = 0
            verif_res = state.verify_cctv_condition(alert.id, "SUP-01", simulate_rebreach=False)

            self.assertTrue(verif_res["verified"])
            self.assertEqual(verif_res["decision"], "VERIFIED")
            self.assertEqual(verif_res["status"], "VERIFIED")

            # Alert state transitions to VERIFIED / RESOLVED in history
            target_alert = verif_res.get("alert") or [h for h in state.history if h.id == alert.id][0]
            self.assertEqual(target_alert.verification_status, "VERIFIED")
            self.assertEqual(target_alert.lifecycle_state, "VERIFIED")
            self.assertEqual(target_alert.status, "RESOLVED")

    def test_item_4_and_5_rebreach_and_safety_memory_feedback(self):
        """
        Phase 4 Items 4 & 5: Re-breach Detection & Safety Memory Feedback
        1. When re-breach occurs, CCTV verification returns FAILED and reopens the action.
        2. A new canonical SafetyEvent is emitted with SIF_POTENTIAL into SQLite and FAISS.
        3. The re-breach event is linked to the existing pattern; NO duplicate pattern is created.
        """
        with isolated_test_environment(prefix="p4_rebreach_") as env:
            test_db = env["db"]
            state = AlertStateManager()

            # Seed a prior event in SQLite and semantic memory
            prior_ev = SafetyEvent(
                event_id="EVT-PRIOR-01",
                source="HUMAN",
                location="Lifting Zone 03",
                activity="Mechanical Lifting Operations",
                energy="Gravitational Energy (Suspended Load)",
                exposure="Personnel in line of fire",
                barrier=["EXCLUSION_ZONE"],
                barrier_state=[BarrierState.BYPASSED],
                sif_status=SIFStatus.SIF_POTENTIAL,
                narrative="Contractor breached marked exclusion zone under crane."
            )
            test_db.save_event(prior_ev)
            semantic_memory.add_event(prior_ev)

            # Seed a validated recurring pattern in SQLite
            pattern_id = "PAT-EXCLUSION-REBREACH-01"
            pat = SafetyPattern(
                pattern_id=pattern_id,
                title="Recurring Exclusion Zone Breach during Hoisting",
                activity="Mechanical Lifting Operations",
                energy="Gravitational / Kinetic Energy (Suspended Load)",
                exposure="Personnel in line of fire under crane boom",
                barrier="EXCLUSION_ZONE",
                occurrence_count=3,
                duplicate_count=0,
                validation_status=ReviewStatus.HSE_VALIDATED,
                operational_status="ACTIVE"
            )
            test_db.save_pattern(pat)

            # Assign pattern action
            assign_res = state.assign_pattern_action(
                pattern_id=pattern_id,
                supervisor_id="SUP-01",
                supervisor_name="Field Lead Rajesh",
                required_action="Clear lifting exclusion zone",
                location="Lifting Zone 03"
            )
            self.assertTrue(assign_res["success"])
            action_alert_id = assign_res["alert_id"]

            # Supervisor takes action: moves to AWAITING_VERIFICATION
            state.mark_action_taken(action_alert_id, "Cleared contractors out", "SUP-01")
            self.assertEqual(state.get_pattern_operational_status(pattern_id), "AWAITING_VERIFICATION")

            # CCTV Verification: RE-BREACH OCCURS
            fail_verif = state.verify_cctv_condition(
                alert_id=action_alert_id,
                supervisor_id="SUP-01",
                simulate_rebreach=True
            )

            # Assert Verification Failed & Action Reopened
            self.assertFalse(fail_verif["verified"])
            self.assertEqual(fail_verif["decision"], "FAILED")
            self.assertEqual(fail_verif["status"], "VERIFICATION_FAILED_REBREACH")

            reopened_alert = state._active_alerts[action_alert_id]
            self.assertEqual(reopened_alert.lifecycle_state, "REOPENED")
            self.assertEqual(reopened_alert.status, "WAITING_FOR_RESPONSE")
            self.assertEqual(reopened_alert.action_status, "IN_PROGRESS")
            self.assertEqual(state.get_pattern_operational_status(pattern_id), "REOPENED")

            # Assert Verification Record saved in SQLite
            verif_records = test_db.list_verifications()
            self.assertTrue(any(v.get("status") == "FAILED" for v in verif_records))

            # Safety Memory Feedback:
            # 1. New SafetyEvent persisted in SQLite
            events = test_db.list_events()
            rebreach_events = [e for e in events if "REBREACH" in e.event_id or e.source == "CCTV"]
            self.assertGreaterEqual(len(rebreach_events), 1)
            rebreach_ev = rebreach_events[0]
            self.assertEqual(rebreach_ev.sif_status, SIFStatus.SIF_POTENTIAL)

            # 2. Re-breach event indexed in FAISS Semantic Memory
            self.assertIn(rebreach_ev.event_id, semantic_memory.event_to_id)
            search_matches = semantic_memory.search_similar_events(rebreach_ev, top_k=5)
            self.assertGreaterEqual(len(search_matches), 1)
            self.assertEqual(search_matches[0][0], "EVT-PRIOR-01")

            # 3. Linked to existing pattern with incremented occurrence count
            updated_pat = test_db.get_pattern(pattern_id)
            self.assertEqual(updated_pat.occurrence_count, 4)
            members = test_db.get_pattern_members(pattern_id)
            self.assertTrue(any(m["event_id"] == rebreach_ev.event_id for m in members))

            # 4. CRITICAL NEGATIVE: NO DUPLICATE PATTERN CREATED
            all_patterns = test_db.list_patterns()
            exclusion_patterns = [p for p in all_patterns if "EXCLUSION" in p.barrier]
            self.assertEqual(len(exclusion_patterns), 1, "Re-breach must NOT create a duplicate pattern")

    def test_item_6_pattern_history_preservation(self):
        """
        Phase 4 Item 6: Pattern History Preservation
        HSE closes verified pattern.
        Pattern is moved to CLOSED_HISTORY and remains preserved in database.
        """
        with isolated_test_environment(prefix="p4_history_") as env:
            test_db = env["db"]
            state = AlertStateManager()

            pattern_id = "PAT-HIST-01"
            pat = SafetyPattern(
                pattern_id=pattern_id,
                title="Historical Lifting Barrier Pattern",
                activity="Mechanical Crane Hoisting",
                energy="Gravitational Energy",
                exposure="Personnel in hazard radius",
                barrier="EXCLUSION_ZONE",
                occurrence_count=2,
                duplicate_count=0,
                validation_status=ReviewStatus.HSE_VALIDATED,
                operational_status="ACTIVE"
            )
            test_db.save_pattern(pat)

            # HSE assigns, supervisor takes action, CCTV verifies clear
            assign_res = state.assign_pattern_action(pattern_id=pattern_id)
            state.mark_action_taken(assign_res["alert_id"], "Secured zone", "SUP-01")
            verif_res = state.verify_cctv_condition(assign_res["alert_id"], "SUP-01", simulate_rebreach=False)
            self.assertTrue(verif_res["verified"])
            self.assertEqual(state.get_pattern_operational_status(pattern_id), "VERIFIED")

            # HSE Formal Closure Authority
            close_res = state.close_pattern_action(
                pattern_id=pattern_id,
                closed_by="Chief HSE Officer (OIL India)",
                closure_notes="Zone verified 100% clear. Shift operations stabilized."
            )
            self.assertTrue(close_res["success"])
            self.assertEqual(close_res["operational_status"], "CLOSED_HISTORY")
            self.assertEqual(state.get_pattern_operational_status(pattern_id), "CLOSED_HISTORY")

            # Invariant: Pattern remains preserved in SQLite (NOT deleted!)
            preserved_pat = test_db.get_pattern(pattern_id)
            self.assertIsNotNone(preserved_pat)
            self.assertEqual(preserved_pat.pattern_id, pattern_id)
            self.assertEqual(state.get_pattern_operational_status(pattern_id), "CLOSED_HISTORY")

            # Invariant: Auditable review record logged in SQLite
            reviews = test_db.list_reviews()
            self.assertTrue(any(r.get("target_id") == pattern_id and r.get("action") == "CLOSE_PATTERN" for r in reviews))

    def test_item_7_coexistence_emergency_alert_and_pattern_action(self):
        """
        Phase 4 Item 7: Coexistence of Live Emergency Alert and Pattern Action
        Class 1 (Emergency Alert) and Class 2 (Pattern Action) coexist without colliding or overwriting.
        """
        with isolated_test_environment(prefix="p4_coexist_") as env:
            state = AlertStateManager()

            # Class 1: Live Emergency Alert
            now_t = datetime.now()
            emerg = Alert(
                id="ALERT-EMERG-999",
                alert_class="EMERGENCY",
                type="ZONE_VIOLATION",
                title="EMERGENCY — Live CCTV Alert",
                severity="CRITICAL",
                source="CCTV",
                status="WAITING_FOR_RESPONSE",
                created_at=now_t.isoformat(),
                response_deadline=(now_t + timedelta(seconds=20)).isoformat()
            )
            state._active_alerts[emerg.id] = emerg

            # Class 2: Pattern Action Alert
            pat_res = state.assign_pattern_action(
                pattern_id="PAT-COEXIST-01",
                supervisor_id="SUP-02",
                supervisor_name="Vikram Singh",
                required_action="Audit crane barrier logs"
            )
            self.assertTrue(pat_res["success"])
            action_id = pat_res["alert_id"]

            # Both alerts exist concurrently in state manager
            self.assertIn("ALERT-EMERG-999", state._active_alerts)
            self.assertIn(action_id, state._active_alerts)
            self.assertEqual(state._active_alerts["ALERT-EMERG-999"].alert_class, "EMERGENCY")
            self.assertEqual(state._active_alerts[action_id].alert_class, "PATTERN_ACTION")
            self.assertNotEqual(state._active_alerts["ALERT-EMERG-999"].title, state._active_alerts[action_id].title)


if __name__ == "__main__":
    unittest.main()
