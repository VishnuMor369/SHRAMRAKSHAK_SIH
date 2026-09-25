"""
SHRAMRAKSHAK: SIH 2026 Enterprise Pipeline Test Suite
Problem Statement: SIH26165

Comprehensive test verifying:
1. Context-Aware NLP: Negation, Hypothetical, Post-event temporal detection
2. Explainable Evidence Spans extraction
3. Safety Memory & Recurrence:
   - Duplicate detection (no count inflation)
   - Independent recurrence clustering (underlying control mechanism)
4. HSE Validation Governance: Candidate -> HSE Validated
5. Future-Work Safety Preconditions & Evidence Verification
6. Machine-Generated Safety Observation from CCTV
7. Corrective Action Lifecycle & CCTV Verification ("Completion is not proof")
8. CCTV Verification Failure / Re-breach -> Automatic Reopening
9. Human Report + CCTV Corroboration (Corroborated vs CCTV Only)
"""

import sys
import os
import unittest
from datetime import datetime
from fastapi.testclient import TestClient

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from state import state_manager
from safety_memory import (
    safety_memory, SafetyEvent, AssertionStatus, RecurrenceClassification,
    HSEValidationStatus
)
from nlp_engine.assertion_detector import AssertionDetector
from nlp_engine.corroboration import corroboration_engine

client = TestClient(app)


class TestEnterpriseSIHPipeline(unittest.TestCase):

    def setUp(self):
        state_manager.reset_demo()
        safety_memory.reset()

    def test_01_negation_handling(self):
        """Verify: 'No worker entered the exclusion zone' -> Exposure is NEGATED, NOT a positive SIF precursor."""
        text = "No worker entered the exclusion zone during the mechanical lifting operation."
        event = AssertionDetector.evaluate_safety_event(text, {"activity": "Mechanical Lifting"})
        
        self.assertEqual(event.assertion_status, AssertionStatus.NEGATED)
        self.assertEqual(event.sif_potential, "NOT_SIF")
        self.assertIn("NEGATED", event.exposure)
        self.assertEqual(event.barrier_state, "MAINTAINED")
        print("  [PASS] Test 1: Negation handling verified -> SIF=NOT_SIF, Exposure=NEGATED")

    def test_02_hypothetical_handling(self):
        """Verify: 'If the sling fails, the suspended load could fall' -> Potential/hypothetical consequence, not observed failure."""
        text = "If the sling fails, the suspended load could fall on the drill floor."
        event = AssertionDetector.evaluate_safety_event(text, {"activity": "Mechanical Lifting"})
        
        self.assertEqual(event.assertion_status, AssertionStatus.HYPOTHETICAL)
        self.assertEqual(event.consequence_type, "HYPOTHETICAL")
        self.assertEqual(event.barrier_state, "MAINTAINED")
        print("  [PASS] Test 2: Hypothetical handling verified -> Consequence=HYPOTHETICAL, Barrier=MAINTAINED")

    def test_03_temporal_post_event_handling(self):
        """Verify: 'Barricade was installed after the incident' -> Post-event temporal condition."""
        text = "Physical barricade was installed after the incident occurred near the compressor skid."
        event = AssertionDetector.evaluate_safety_event(text, {"activity": "Maintenance"})
        
        self.assertEqual(event.assertion_status, AssertionStatus.POST_EVENT)
        self.assertEqual(event.temporal_status, "POST_EVENT")
        self.assertEqual(event.barrier_state, "POST_INSTALLATION")
        print("  [PASS] Test 3: Temporal post-event handling verified -> Status=POST_EVENT, Barrier=POST_INSTALLATION")

    def test_04_evidence_spans_extraction(self):
        """Verify exact character evidence spans for Hazard, Exposure, Barrier, and Consequence."""
        text = "Contractor entered lifting exclusion zone while suspended pipe spool was being moved by crane."
        spans = AssertionDetector.extract_evidence_spans(text)
        
        categories = {s.category for s in spans}
        self.assertIn("hazard", categories)
        self.assertIn("exposure", categories)
        self.assertIn("barrier", categories)
        
        # Verify spans match actual substrings in the text
        for s in spans:
            sub = text[s.start:s.end]
            self.assertEqual(sub, s.text)
        print("  [PASS] Test 4: Explainable character evidence spans verified across Hazard, Exposure, Barrier")

    def test_05_safety_memory_duplicate_detection(self):
        """Verify duplicate reports do NOT inflate recurrence counts."""
        summary_before = safety_memory.get_summary()
        pat = safety_memory.patterns["PAT-LIFT-01"]
        count_before = pat.independent_occurrences_count
        
        # Ingest exact duplicate of EVT-HIST-001
        dup_event = SafetyEvent(
            event_id="EVT-DUP-TEST-001",
            source="HUMAN_REPORT",
            timestamp="2025-04-12T10:18:00",
            location="Drilling Rig Floor",
            activity="Mechanical Lifting",
            raw_narrative="Worker crossed crane exclusion zone while drill collar was suspended 1.5m above rotary table.",
            critical_barrier="Rig Floor Exclusion Zone",
            underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
        )
        res = safety_memory.record_safety_event(dup_event)
        
        self.assertEqual(res["classification"], "DUPLICATE")
        # Ensure independent occurrence count DID NOT change
        self.assertEqual(pat.independent_occurrences_count, count_before)
        print(f"  [PASS] Test 5: Duplicate detection verified -> Count not inflated ({count_before} independent occurrences)")

    def test_06_safety_memory_independent_recurrence(self):
        """Verify independent occurrence of the same underlying control mechanism increments count."""
        pat = safety_memory.patterns["PAT-LIFT-01"]
        initial_count = pat.independent_occurrences_count  # Baseline is 5
        
        # Ingest 6th independent occurrence
        new_event = SafetyEvent(
            event_id="EVT-INDEP-TEST-006",
            source="CCTV",
            timestamp=datetime.now().isoformat(),
            location="Compressor Bay 4",
            activity="Mechanical Lifting",
            raw_narrative="Person stepped into crane exclusion zone beneath suspended spool.",
            critical_barrier="Lifting Exclusion Zone",
            underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
        )
        res = safety_memory.record_safety_event(new_event)
        
        self.assertEqual(res["classification"], "INDEPENDENT_RECURRENCE")
        self.assertEqual(pat.independent_occurrences_count, initial_count + 1)
        print(f"  [PASS] Test 6: Independent recurrence verified -> Occurrences incremented: {initial_count} -> {pat.independent_occurrences_count}")

    def test_07_hse_validation_governance(self):
        """Verify Candidate Recurring Pattern transitions to HSE Validated, creating future-work requirement."""
        pat = safety_memory.patterns["PAT-LIFT-01"]
        self.assertEqual(pat.validation_status, HSEValidationStatus.CANDIDATE)
        
        # HSE Confirms pattern
        validated_pat = safety_memory.validate_pattern(
            pattern_id="PAT-LIFT-01",
            decision="CONFIRM",
            reviewer="Chief HSE Inspector (OIL Duliajan)",
            notes="Confirmed recurring failure in lifting perimeter control."
        )
        self.assertEqual(validated_pat.validation_status, HSEValidationStatus.HSE_VALIDATED)
        self.assertIsNotNone(validated_pat.hse_validated_at)
        
        # Verify Future-Work requirement was generated
        reqs = list(safety_memory.future_requirements.values())
        matching_req = [r for r in reqs if r.derived_from_pattern_id == "PAT-LIFT-01"]
        self.assertTrue(len(matching_req) > 0)
        self.assertEqual(matching_req[0].activity, "Mechanical Lifting")
        print(f"  [PASS] Test 7: HSE Validation governance verified -> Candidate -> HSE_VALIDATED, Requirement ID: {matching_req[0].requirement_id}")

    def test_08_future_work_requirement_missing_evidence(self):
        """Verify future work package without required evidence triggers 'REQUIRED_SAFETY_EVIDENCE_MISSING'."""
        work_package = {
            "package_id": "WP-TEST-LIFT-99",
            "activity": "Mechanical Lifting",
            "location": "Lifting Zone 03",
            "has_isolation_record": True,
            "has_exclusion_zone_evidence": False  # Missing required evidence
        }
        eval_res = safety_memory.check_work_package(work_package)
        
        self.assertEqual(eval_res.status, "REQUIRED_SAFETY_EVIDENCE_MISSING")
        self.assertTrue(eval_res.authorization_review_required)
        self.assertTrue(len(eval_res.missing_evidence_details) > 0)
        print("  [PASS] Test 8: Future-work safety learning enforced -> REQUIRED_SAFETY_EVIDENCE_MISSING flagged correctly")

    def test_09_cctv_machine_generated_safety_observation(self):
        """Verify CCTV generates a Machine-Generated Safety Observation that enters common SIF pipeline."""
        alert = state_manager.simulate_zone_entry()
        self.assertIsNotNone(alert)
        self.assertIsNotNone(alert.machine_observation)
        self.assertEqual(alert.machine_observation["source"], "CCTV")
        self.assertEqual(alert.machine_observation["barrier_state"], "VIOLATED")
        self.assertEqual(alert.machine_observation["pipeline_stage"], "OBSERVATION_SENT_TO_SIF_INTELLIGENCE")
        self.assertEqual(alert.lifecycle_state, "ACTION_REQUIRED")
        self.assertEqual(alert.sif_level, "HIGH")
        print(f"  [PASS] Test 9: Machine-generated safety observation verified -> Alert {alert.id} with machine_observation")

    def test_10_cctv_verification_success(self):
        """Verify: Action completed -> Awaiting verification -> CCTV check clear -> VERIFIED -> RESOLVED."""
        alert = state_manager.simulate_zone_entry()
        
        # 1. Take action
        state_manager.respond_to_alert("SUP-01", "Responding to clear zone", alert.id)
        state_manager.mark_action_taken(alert.id, "SUP-01", "Personnel cleared, barricade re-established")
        
        # Simulate zone clear
        state_manager.zone_violation = False
        state_manager.persons_in_zone = 0
        
        # 2. CCTV verification check
        verif_res = state_manager.verify_cctv_condition(alert.id, "SUP-01", simulate_rebreach=False)
        self.assertEqual(verif_res["decision"], "VERIFIED")
        self.assertEqual(verif_res["alert"].status, "RESOLVED")
        self.assertEqual(verif_res["alert"].lifecycle_state, "VERIFIED")
        print("  [PASS] Test 10: CCTV verification passed -> Condition restored, Alert RESOLVED")

    def test_11_cctv_verification_rebreach_reopen(self):
        """Verify: Action completed -> Awaiting verification -> Re-breach detected -> FAILED -> REOPENED."""
        alert = state_manager.simulate_zone_entry()
        
        state_manager.respond_to_alert("SUP-01", "Responding to clear zone", alert.id)
        state_manager.mark_action_taken(alert.id, "SUP-01", "Exclusion zone cleared")
        
        # Re-breach occurs!
        verif_res = state_manager.verify_cctv_condition(alert.id, "SUP-01", simulate_rebreach=True)
        self.assertEqual(verif_res["decision"], "FAILED")
        self.assertEqual(verif_res["status"], "VERIFICATION_FAILED_REBREACH")
        self.assertEqual(verif_res["alert"].lifecycle_state, "REOPENED")
        self.assertEqual(verif_res["alert"].status, "WAITING_FOR_RESPONSE")
        self.assertEqual(verif_res["alert"].action_status, "IN_PROGRESS")
        print("  [PASS] Test 11: Re-breach detected -> Verification FAILED, Corrective action automatically REOPENED")

    def test_12_corroboration_scenarios(self):
        """Verify Corroboration Engine: CORROBORATED vs CCTV_ONLY."""
        # Scenario A: Dual Evidence Corroboration
        human_ev = SafetyEvent(
            event_id="EVT-HUMAN-01",
            source="HUMAN_REPORT",
            location="Demo Lifting Area",
            activity="Mechanical Lifting",
            raw_narrative="Worker entered lifting exclusion zone."
        )
        cctv_ev = SafetyEvent(
            event_id="EVT-CCTV-01",
            source="CCTV",
            location="Demo Lifting Area",
            activity="Mechanical Lifting",
            raw_narrative="Person detected inside defined exclusion zone."
        )
        corr_a = corroboration_engine.corroborate_events(human_event=human_ev, cctv_event=cctv_ev)
        self.assertEqual(corr_a["status"], "CORROBORATED")
        self.assertTrue(corr_a["human_present"])
        self.assertTrue(corr_a["cctv_present"])
        
        # Scenario B: CCTV Only (Machine observation without human report)
        corr_b = corroboration_engine.corroborate_events(cctv_event=cctv_ev)
        self.assertEqual(corr_b["status"], "CCTV_ONLY")
        self.assertFalse(corr_b["human_present"])
        self.assertTrue(corr_b["cctv_present"])
        print("  [PASS] Test 12: Corroboration verified -> CORROBORATED and CCTV_ONLY scenarios")

    def test_13_rest_api_safety_memory_and_cctv_verify(self):
        """Verify REST API endpoints for Safety Memory and CCTV verification."""
        # 1. Safety Memory Summary
        res_sum = client.get("/api/safety-memory/summary")
        self.assertEqual(res_sum.status_code, 200)
        sum_data = res_sum.json()
        self.assertGreaterEqual(sum_data["total_patterns"], 2)
        self.assertGreaterEqual(sum_data["candidate_patterns"], 1)

        # 2. HSE Validate Pattern API
        res_val = client.post("/api/safety-memory/patterns/PAT-LIFT-01/validate", json={
            "decision": "CONFIRM",
            "reviewer": "Chief HSE Inspector",
            "notes": "Verified recurrence via REST API"
        })
        self.assertEqual(res_val.status_code, 200)
        self.assertEqual(res_val.json()["pattern"]["validation_status"], "HSE_VALIDATED")

        # 3. Work Package Check API
        res_wp = client.post("/api/safety-memory/check-work-package", json={
            "activity": "Mechanical Lifting",
            "has_exclusion_zone_evidence": False
        })
        self.assertEqual(res_wp.status_code, 200)
        self.assertEqual(res_wp.json()["status"], "REQUIRED_SAFETY_EVIDENCE_MISSING")

        # 4. Trigger alert and CCTV verify via REST API
        client.post("/api/demo/simulate-zone-entry")
        alert = state_manager.active_alert
        self.assertIsNotNone(alert)
        client.post(f"/api/alerts/{alert.id}/respond", json={"supervisor_id": "SUP-01"})
        client.post(f"/api/alerts/{alert.id}/action", json={"action_taken": "Cleared zone"})
        
        # Observable condition restored: person exits zone
        state_manager.zone_violation = False
        state_manager.persons_in_zone = 0

        # Verify via REST API
        res_verif = client.post(f"/api/alerts/{alert.id}/cctv-verify", json={"simulate_rebreach": False})
        self.assertEqual(res_verif.status_code, 200)
        self.assertEqual(res_verif.json()["decision"], "VERIFIED")
        print("  [PASS] Test 13: REST API endpoints for Safety Memory and CCTV Verification verified")

    def test_14_demo_9_phase_controller_flow(self):
        """Verify complete 9-Phase SIH Storyboard Controller execution through API."""
        for phase in range(1, 10):
            res = client.post(f"/api/demo/phase/{phase}")
            self.assertEqual(res.status_code, 200, f"Phase {phase} execution failed: {res.text}")
            data = res.json()
            self.assertEqual(data["phase"], phase)
            self.assertIn("title", data)
        print("  [PASS] Test 14: 9-Phase Demo Storyboard Controller executed smoothly from Phase 1 to Phase 9")


if __name__ == "__main__":
    print("=" * 70)
    print(" RUNNING SHRAMRAKSHAK SIH 2026 ENTERPRISE PIPELINE TEST SUITE")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnterpriseSIHPipeline)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    if res.wasSuccessful():
        print("\n" + "=" * 70)
        print(" ALL 12 ENTERPRISE PIPELINE INTEGRATION TESTS PASSED (100% OK)!")
        print("=" * 70)
    else:
        sys.exit(1)
