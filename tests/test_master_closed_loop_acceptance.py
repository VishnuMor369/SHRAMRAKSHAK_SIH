"""
SHRAMRAKSHAK: MASTER FORENSIC REPAIR 15-STEP CLOSED-LOOP ACCEPTANCE TEST
SIH 2026 Problem Statement: SIH26165

Implements Section 38: Final End-to-End Acceptance Test
Narrative: "Worker entered the exclusion zone while the load was suspended."

STEP 1:  Human Safety Report Ingestion -> Canonical Safety Event created
STEP 2:  Contextual NLP -> AFFIRMED, Exposure present, Barrier compromised, SIF-POTENTIAL, LSR mapped, Evidence span
STEP 3:  Safety Memory -> Seed prior event & vector search
STEP 4:  Recurrence -> INDEPENDENT_RECURRENCE identified on same control breach
STEP 5:  Candidate Pattern -> CANDIDATE SafetyPattern proposed
STEP 6:  HSE Validation -> Candidate -> HSE_VALIDATED by human reviewer
STEP 7:  Validated Safety Learning -> Precondition automatically created
STEP 8:  Future Work -> Create lifting work package referencing validated learning
STEP 9:  Evidence Check -> Missing evidence flags MISSING_EVIDENCE (NO autonomous permit rejection)
STEP 10: Action -> Corrective action taken -> AWAITING_VERIFICATION
STEP 11: Verification -> On-site / human verification recorded & persisted
STEP 12: CCTV Verification -> Observable condition verified & resolved
STEP 13: Re-breach -> Unauthorized entry re-detected -> VERIFICATION_FAILED -> Action Reopened
STEP 14: Learning Feedback -> New Safety Event generated from re-breach
STEP 15: Safety Memory -> Re-breach evidence available for recurrence learning
"""

import sys
import os
import uuid
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

import backend
from backend.models_canonical import (
    SafetyEvent, EvidenceSpan, AssertionStatus, TemporalStatus,
    BarrierState, SIFStatus, ReviewStatus, RecurrenceRelationship,
    SafetyPattern, WorkPrecondition, WorkCheckResult
)
from backend.database import db
from backend.nlp_engine.assertion_detector import assertion_detector
from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
from backend.nlp_engine.lsr_classifier import lsr_classifier
from backend.nlp_engine.semantic_memory import semantic_memory
from backend.nlp_engine.recurrence_engine import recurrence_engine
from backend.nlp_engine.propagation import propagation_engine
from backend.nlp_engine.precondition_engine import precondition_engine
from backend.state import state_manager

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)
from test_isolation import isolated_test_environment


def run_master_acceptance():
    with isolated_test_environment():
        print("======================================================================")
        print(" SHRAMRAKSHAK: MASTER 15-STEP CLOSED-LOOP ACCEPTANCE TEST")
        print("======================================================================")

        # -------------------------------------------------------------
        # STEP 1: CREATE HUMAN SAFETY REPORT
        # -------------------------------------------------------------
        narrative = "Worker entered the exclusion zone while the load was suspended."
        rpt_id = f"RPT-{uuid.uuid4().hex[:6]}"
        db.insert_report(rpt_id, narrative, site="OIL Duliajan", location="Drilling Rig 04 - Lifting Zone")
        print(f"\n[STEP 1] Human Safety Report Recorded: {rpt_id}")
        assert db.get_report(rpt_id) is not None, "Report must exist in SQLite database"

        # -------------------------------------------------------------
        # STEP 2: CONTEXTUAL NLP & CANONICAL SAFETY EVENT
        # -------------------------------------------------------------
        ev = assertion_detector.analyze(narrative, context={"event_id": f"EVT-HUMAN-{uuid.uuid4().hex[:6]}"})
        ev = sif_pathway_engine.evaluate(ev)
        ev = lsr_classifier.classify(ev)
        db.save_event(ev)

        print(f"[STEP 2] Canonical Safety Event Analyzed: {ev.event_id}")
        print(f" -> Assertion: {ev.assertion}")
        print(f" -> Exposure: {ev.exposure}")
        print(f" -> Barrier: {ev.barrier}, State: {ev.barrier_state}")
        print(f" -> SIF Potential: {ev.sif_status}")
        print(f" -> LSR: {ev.lsr}")
        print(f" -> Evidence Spans: {[sp.text for sp in ev.evidence]}")

        assert ev.assertion == AssertionStatus.AFFIRMED
        assert "inside" in ev.exposure.lower() or "worker" in ev.exposure.lower()
        assert "EXCLUSION_ZONE" in ev.barrier
        assert BarrierState.BYPASSED in ev.barrier_state or BarrierState.COMPROMISED in ev.barrier_state
        assert ev.sif_status == SIFStatus.SIF_POTENTIAL
        assert any("LIFT" in r or "LINE_OF_FIRE" in r for r in ev.lsr)
        assert len(ev.evidence) > 0
        for sp in ev.evidence:
            assert sp.verify_against(narrative), f"Span offset mismatch: {sp.text}"

        # -------------------------------------------------------------
        # STEP 3 & 4: SAFETY MEMORY SEEDING & RECURRENCE
        # -------------------------------------------------------------
        # Seed prior historical event
        prior_narrative = "Rigger crossed the barrier into the crane exclusion zone under suspended drill pipe."
        prior_ev = assertion_detector.analyze(prior_narrative, context={"event_id": f"EVT-PRIOR-{uuid.uuid4().hex[:6]}"})
        prior_ev = sif_pathway_engine.evaluate(prior_ev)
        db.save_event(prior_ev)
        semantic_memory.add_event(prior_ev)

        # Evaluate pair recurrence
        pair_res = recurrence_engine.evaluate_pair(ev, prior_ev, similarity=0.86)
        print(f"\n[STEP 3 & 4] Recurrence Evaluation between Current and Prior:")
        print(f" -> Relationship: {pair_res.final_relationship}")
        print(f" -> Reason: {pair_res.reason}")
        assert pair_res.final_relationship == RecurrenceRelationship.INDEPENDENT_RECURRENCE

        # -------------------------------------------------------------
        # STEP 5: CANDIDATE PATTERN CREATION
        # -------------------------------------------------------------
        results, pattern = recurrence_engine.process_event(ev)
        assert pattern is not None, "Candidate pattern must be created"
        print(f"\n[STEP 5] Candidate Pattern Proposed:")
        print(f" -> Pattern ID: {pattern.pattern_id}")
        print(f" -> Title: {pattern.title}")
        print(f" -> Validation Status: {pattern.validation_status}")
        assert pattern.validation_status == ReviewStatus.CANDIDATE, "AI must only create CANDIDATE, never auto-validated"

        # -------------------------------------------------------------
        # STEP 6: HSE VALIDATION
        # -------------------------------------------------------------
        validated_pattern = propagation_engine.validate_safety_pattern(
            pattern_id=pattern.pattern_id,
            reviewer_role="HSE_MANAGER_OIL",
            action="VALIDATE",
            review_notes="Confirmed recurring failure of exclusion zone physical segregation."
        )
        print(f"\n[STEP 6] HSE Governance Decision Recorded:")
        print(f" -> New Status: {validated_pattern.validation_status}")
        print(f" -> Reviewer: {validated_pattern.reviewer_role}")
        assert validated_pattern.validation_status == ReviewStatus.HSE_VALIDATED

        # -------------------------------------------------------------
        # STEP 7: VALIDATED SAFETY LEARNING & PRECONDITION
        # -------------------------------------------------------------
        precondition = precondition_engine.create_precondition_from_pattern(validated_pattern.pattern_id)
        print(f"\n[STEP 7] Validated Safety Learning Precondition Derived:")
        print(f" -> Precondition ID: {precondition.precondition_id}")
        print(f" -> Title: {precondition.title}")
        print(f" -> Required Evidence: {precondition.required_evidence_types}")
        assert precondition.status == "ACTIVE"
        assert len(precondition.required_evidence_types) >= 2

        # -------------------------------------------------------------
        # STEP 8 & 9: FUTURE WORK CHECK (MISSING EVIDENCE)
        # -------------------------------------------------------------
        wp_pkg_id = "WP-2026-LIFT-OIL-01"
        incomplete_evidence = {
            "PHYSICAL_PERIMETER_DEMARCATION": "Barricade tape installed",
            # Missing: AUTHORIZED_ENTRANTS_PASSPORT and OBSERVABLE_CCTV_CLEAR_ZONE
        }
        check_result = precondition_engine.evaluate_work_package(
            package_id=wp_pkg_id,
            activity="Mechanical Lifting Operations",
            location="Drilling Rig 04",
            submitted_evidence=incomplete_evidence
        )
        print(f"\n[STEP 8 & 9] Future-Work Precondition Check (Incomplete Evidence):")
        print(f" -> Check Status: {check_result.status}")
        print(f" -> Findings: {check_result.findings}")
        print(f" -> Missing: {check_result.missing_evidence}")
        assert check_result.status == "REVIEW_REQUIRED" or check_result.status == "MISSING_EVIDENCE"
        assert len(check_result.missing_evidence) > 0
        # Critical SIH rule: No autonomous permit rejection; decision-support only
        assert "NOT_APPLICABLE" != check_result.status

        # Satisfy all evidence
        complete_evidence = {
            "PHYSICAL_PERIMETER_DEMARCATION": "Heavy-duty steel barrier erected",
            "AUTHORIZED_ENTRANTS_PASSPORT": "Passport #PASS-2026-004 verified active",
            "OBSERVABLE_CCTV_CLEAR_ZONE": True
        }
        passed_check = precondition_engine.evaluate_work_package(
            package_id=wp_pkg_id,
            activity="Mechanical Lifting Operations",
            location="Drilling Rig 04",
            submitted_evidence=complete_evidence
        )
        print(f" -> With All Evidence Provided: Status = {passed_check.status}")
        assert passed_check.status == "PASS"

        # -------------------------------------------------------------
        # STEP 10: ACTION STATE MACHINE & WORKFLOW
        # -------------------------------------------------------------
        alert = state_manager.trigger_alert(
            alert_type="Restricted Zone Entry",
            location="Drilling Rig 04 - Lifting Zone",
            camera="C-01",
            severity="CRITICAL",
            sif_potential="SIF Potential",
            hazard="Suspended Load Kinetic Energy"
        )
        assert alert is not None
        alert_id = alert.id
        print(f"\n[STEP 10] Alert Generated & Assigned: {alert_id}")
        assert alert.status == "WAITING_FOR_RESPONSE"

        # Supervisor responds
        alert = state_manager.respond_to_alert("SUP-OIL-01", "Supervisor en route to hold crane", alert_id)
        assert alert.status == "RESPONDING"
        assert alert.action_status == "IN_PROGRESS"

        # Corrective action taken
        alert = state_manager.mark_action_taken(alert_id, "SUP-OIL-01", "Cleared all personnel from lifting perimeter")
        assert alert.action_status == "COMPLETED"
        assert alert.verification_status == "AWAITING_VERIFICATION"
        assert alert.status == "AWAITING_VERIFICATION"
        print(" -> Corrective action taken -> Status: AWAITING_VERIFICATION ('Completion is not proof')")

        # -------------------------------------------------------------
        # STEP 11: ON-SITE / HUMAN VERIFICATION
        # -------------------------------------------------------------
        alert_human_verified = state_manager.verify_alert(
            alert_id=alert_id,
            supervisor_id="SUP-OIL-01",
            decision="VERIFIED",
            verification_method="ON_SITE_PHYSICAL_INSPECTION",
            notes="Physical inspection confirmed exclusion perimeter secure"
        )
        assert alert_human_verified.verification_status == "VERIFIED"
        assert alert_human_verified.status == "RESOLVED"
        
        # Persist verification record
        db.save_verification_record(
            verification_id=f"VERIF-{uuid.uuid4().hex[:8]}",
            event_id=alert_id,
            source="ON_SITE_PHYSICAL_INSPECTION",
            status="VERIFIED",
            details={"notes": "Physical inspection confirmed secure"}
        )
        records = db.list_verifications()
        assert len(records) > 0
        print(f"[STEP 11] On-Site Verification Recorded & Persisted: {records[0]['verification_id']}")

        # -------------------------------------------------------------
        # STEP 12: CCTV OBSERVABLE CONDITION VERIFICATION
        # -------------------------------------------------------------
        # Trigger fresh alert awaiting CCTV verification
        cctv_alert = state_manager.trigger_alert(
            alert_type="Restricted Zone Entry",
            location="Drilling Rig 04 - Lifting Zone",
            camera="C-01"
        )
        state_manager.mark_action_taken(cctv_alert.id, "SUP-OIL-01", "Rigger stepped back")
        
        # Test clear condition CCTV verification
        state_manager.zone_violation = False
        state_manager.persons_in_zone = 0
        cctv_res = state_manager.verify_cctv_condition(cctv_alert.id, "SUP-OIL-01", simulate_rebreach=False)
        print(f"\n[STEP 12] CCTV Verification (Clear Zone):")
        print(f" -> Decision: {cctv_res.get('decision')}, Verified: {cctv_res.get('verified')}")
        assert cctv_res.get("verified") is True
        assert cctv_res.get("decision") == "VERIFIED"

        # -------------------------------------------------------------
        # STEP 13, 14, 15: RE-BREACH, REOPEN & LEARNING FEEDBACK
        # -------------------------------------------------------------
        # Re-trigger and set to awaiting verification
        rebreach_alert = state_manager.trigger_alert(
            alert_type="Restricted Zone Entry",
            location="Drilling Rig 04 - Lifting Zone",
            camera="C-01"
        )
        state_manager.mark_action_taken(rebreach_alert.id, "SUP-OIL-01", "Worker instructed to exit")

        # Simulate Re-breach
        rebreach_res = state_manager.verify_cctv_condition(rebreach_alert.id, "SUP-OIL-01", simulate_rebreach=True)
        print(f"\n[STEP 13] CCTV Verification (Re-Breach Simulation):")
        print(f" -> Decision: {rebreach_res.get('decision')}, Verified: {rebreach_res.get('verified')}")
        safe_msg = str(rebreach_res.get('message', '')).encode('ascii', 'replace').decode('ascii')
        print(f" -> Message: {safe_msg}")
        assert rebreach_res.get("verified") is False
        assert rebreach_res.get("decision") == "FAILED"
        assert rebreach_alert.action_status == "IN_PROGRESS"
        assert rebreach_alert.lifecycle_state == "REOPENED"

        # Learning Feedback: Emit new SafetyEvent into Safety Memory
        rebreach_event = SafetyEvent(
            event_id=f"EVT-CCTV-REBREACH-{uuid.uuid4().hex[:6]}",
            source="CCTV",
            timestamp=datetime.now().isoformat(),
            site="OIL Field Duliajan",
            location="Drilling Rig 04 - Lifting Zone",
            activity="Mechanical Crane Hoisting",
            energy="Gravitational / Kinetic Energy (Suspended Load)",
            exposure="Worker re-entered lifting exclusion zone post-corrective action",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=[BarrierState.BYPASSED],
            consequence="Crush trauma / struck-by suspended load",
            sif_status=SIFStatus.SIF_POTENTIAL,
            sif_reasons=["CCTV Verification Failed: Re-breach detected in active zone while load suspended."],
            lsr=["SAFE_MECHANICAL_LIFTING", "LINE_OF_FIRE"],
            machine_observation=True,
            narrative="CCTV automated verification detected worker re-entry into restricted zone following corrective action sign-off."
        )
        db.save_event(rebreach_event)
        semantic_memory.add_event(rebreach_event)

        print(f"\n[STEP 14 & 15] Learning Feedback:")
        print(f" -> New Safety Event Created: {rebreach_event.event_id}")
        print(f" -> SIF: {rebreach_event.sif_status}")
        print(f" -> Committed to Safety Memory SQLite & FAISS")

        assert db.get_event(rebreach_event.event_id) is not None, "Re-breach event must be persisted in SQLite"
        rebreach_search = semantic_memory.search_similar_events(rebreach_event, top_k=5)
        assert len(rebreach_search) > 0, "Re-breach event must be retrievable from FAISS semantic memory"
        print(f" -> FAISS Retrieval Candidates: {len(rebreach_search)} matches")

        print("\n======================================================================")
        print(" MASTER 15-STEP CLOSED-LOOP ACCEPTANCE TEST PASSED 100%!")
        print("======================================================================")


if __name__ == "__main__":
    run_master_acceptance()
