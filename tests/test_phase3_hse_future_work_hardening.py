"""
SHRAMRAKSHAK: Phase 3 HSE / Future-Work Hardening Test Suite
SIH 2026 Problem Statement: SIH26165

Covers all Phase 3 Hardening Requirements:
1. Rule 16: Human Correction Propagation (SIF recomputation, pattern dissolution, precondition deactivation)
2. Rule 17: Precondition Governance (Lifecycle: CANDIDATE -> HSE_VALIDATED -> PROPOSED -> ACTIVE / REJECTED)
3. Rule 19: Evidence Quality ("COMPLETION IS NOT PROOF", DECLARED vs DOCUMENTED/EVIDENCED verification)
4. Rule 20: Closed-Loop Reopening (CRITICAL NEGATIVE: Duplicate != Reopen; Independent Recurrence == Reopen)
"""

import os
import sys
import pytest
from datetime import datetime

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
    SafetyEvent, SafetyPattern, WorkPrecondition,
    ReviewStatus, SIFStatus, RecurrenceRelationship
)
from backend.nlp_engine.propagation import propagation_engine
from backend.nlp_engine.precondition_engine import precondition_engine
from backend.nlp_engine.recurrence_engine import recurrence_engine


def test_rule_16_correction_propagation_and_dependency_recomputation():
    """Rule 16: When HSE corrects barrier from FAILED to EFFECTIVE, recompute SIF, pattern, and preconditions."""
    with isolated_test_environment() as env:
        db = env["db"]

        # Create pattern with 1 occurrence
        pat = SafetyPattern(
            pattern_id="PAT-CORR-01",
            title="Lifting Barrier Failure Pattern",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Personnel near load",
            barrier="EXCLUSION_ZONE",
            occurrence_count=1,
            validation_status=ReviewStatus.HSE_VALIDATED
        )
        db.save_pattern(pat)

        # Create active precondition associated with this pattern
        prec = WorkPrecondition(
            precondition_id="PREC-CORR-01",
            pattern_id="PAT-CORR-01",
            title="Exclusion Zone Precondition",
            required_barrier="EXCLUSION_ZONE",
            required_evidence_types=["PHYSICAL_PERIMETER_DEMARCATION"],
            status="ACTIVE"
        )
        db.save_precondition(prec)

        # Create event with BYPASSED barrier and SIF-POTENTIAL linked to pattern
        evt = SafetyEvent(
            event_id="EVT-CORR-001",
            source="HUMAN",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Personnel inside lifting zone",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma",
            narrative="Worker entered perimeter under suspended load.",
            sif_status=SIFStatus.SIF_POTENTIAL,
            pattern_id="PAT-CORR-01"
        )
        db.save_event(evt)

        # Apply HSE Correction: Barrier was actually intact and verified
        res = propagation_engine.apply_human_correction(
            event_id="EVT-CORR-001",
            corrections={"barrier_state": ["EFFECTIVE_VERIFIED"]},
            reviewer_role="HSE_LEAD",
            reason="CCTV review shows physical tape was fully intact and respected."
        )

        # 1. SIF recomputed to NO_SIF_POTENTIAL_IDENTIFIED
        assert res["recomputed_sif"] == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED.value

        # 2. Pattern occurrences decremented to 0 -> pattern retired
        updated_pat = db.get_pattern("PAT-CORR-01")
        assert updated_pat.occurrence_count == 0
        assert updated_pat.validation_status == ReviewStatus.REJECTED

        # 3. Associated preconditions deactivated
        precs = db.list_preconditions(active_only=True)
        assert not any(p.precondition_id == "PREC-CORR-01" for p in precs)

        # 4. Review audit trail logged
        reviews = db.list_reviews()
        assert any(r["target_id"] == "EVT-CORR-001" and r["action"] == "CORRECT" for r in reviews)


def test_rule_17_precondition_governance_lifecycle():
    """Rule 17: Candidate patterns cannot generate preconditions; proposed preconditions must be accepted by HSE."""
    with isolated_test_environment() as env:
        db = env["db"]

        # Case 1: CANDIDATE pattern cannot generate preconditions
        candidate_pat = SafetyPattern(
            pattern_id="PAT-GOV-CAND",
            title="Candidate Lifting Pattern",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Personnel near load",
            barrier="EXCLUSION_ZONE",
            validation_status=ReviewStatus.CANDIDATE
        )
        db.save_pattern(candidate_pat)

        with pytest.raises(ValueError, match="Only HSE_VALIDATED patterns can generate"):
            precondition_engine.create_precondition_from_pattern("PAT-GOV-CAND")

        # Case 2: Validate pattern by HSE authority
        validated_pat = propagation_engine.validate_safety_pattern(
            pattern_id="PAT-GOV-CAND",
            reviewer_role="HSE_DIRECTOR",
            action="VALIDATE",
            review_notes="Approved recurring pattern based on field evidence."
        )
        assert validated_pat.validation_status == ReviewStatus.HSE_VALIDATED

        # Case 3: Propose precondition (status: PROPOSED, not yet active)
        proposed_prec = precondition_engine.propose_precondition_from_pattern("PAT-GOV-CAND")
        assert proposed_prec.status == "PROPOSED"
        assert proposed_prec.created_by == "AI_SAFETY_ENGINE"

        # Verify proposed precondition is NOT active in work package evaluations
        active_list = db.list_preconditions(active_only=True)
        assert not any(p.precondition_id == proposed_prec.precondition_id for p in active_list)

        # Case 4: HSE Rejection of proposed precondition
        rejected_prec = precondition_engine.reject_precondition(
            proposed_prec.precondition_id,
            reviewer_role="HSE_MANAGER",
            reason="Control deemed impractical for current rig geometry."
        )
        assert rejected_prec.status == "REJECTED"
        assert rejected_prec.reviewed_by == "HSE_MANAGER"

        # Case 5: Re-propose and HSE Acceptance into ACTIVE
        prop_2 = precondition_engine.propose_precondition_from_pattern("PAT-GOV-CAND")
        accepted_prec = precondition_engine.accept_precondition(
            prop_2.precondition_id,
            reviewer_role="HSE_MANAGER",
            notes="Revised perimeter accepted for all crane lifts."
        )
        assert accepted_prec.status == "ACTIVE"
        assert accepted_prec.reviewed_by == "HSE_MANAGER"

        # Verify accepted precondition is now active
        active_list_after = db.list_preconditions(active_only=True)
        assert any(p.precondition_id == prop_2.precondition_id for p in active_list_after)


def test_rule_19_evidence_quality_completion_is_not_proof():
    """Rule 19: Distinguish DECLARED vs DOCUMENTED/EVIDENCED; 'Isolation completed' is NOT proof."""
    with isolated_test_environment() as env:
        db = env["db"]

        # Validated pattern & active precondition for Electrical Isolation / LOTO
        pat = SafetyPattern(
            pattern_id="PAT-LOTO-01",
            title="LOTO Isolation Pattern",
            activity="Electrical Isolation / Switchgear Maintenance",
            energy="High Voltage Electrical",
            exposure="Technician at switchgear",
            barrier="ENERGY_ISOLATION",
            validation_status=ReviewStatus.HSE_VALIDATED
        )
        db.save_pattern(pat)

        prec = WorkPrecondition(
            precondition_id="PREC-LOTO-01",
            pattern_id="PAT-LOTO-01",
            title="Zero Energy Verification Precondition",
            required_barrier="ENERGY_ISOLATION",
            required_evidence_types=["ZERO_ENERGY_TEST_LOG", "ELECTRICAL_ISOLATION_CERTIFICATE"],
            status="ACTIVE"
        )
        db.save_precondition(prec)

        # 1. Negative Test: Naked verbal declaration ("Isolation completed")
        naked_evidence = {
            "ZERO_ENERGY_TEST_LOG": "Isolation completed",
            "ELECTRICAL_ISOLATION_CERTIFICATE": "Done"
        }
        chk_naked = precondition_engine.evaluate_work_package(
            package_id="PKG-LOTO-01",
            activity="Electrical Isolation / Switchgear Maintenance",
            location="Substation 02",
            submitted_evidence=naked_evidence
        )
        # MUST NOT PASS: Naked completion assertion is flagged as DECLARED only
        assert chk_naked.status in ["REVIEW_REQUIRED", "MISSING_EVIDENCE"]
        assert "ZERO_ENERGY_TEST_LOG" in chk_naked.missing_evidence
        assert any("Completion is not proof" in f for f in chk_naked.findings)
        assert any("DECLARED only" in f for f in chk_naked.findings)

        # 2. Positive Test: Legitimate documented & evidenced verification
        valid_evidence = {
            "ZERO_ENERGY_TEST_LOG": "Calibrated Fluke Multimeter Log #F87-029: 0.0V measured phase-to-phase and phase-to-ground",
            "ELECTRICAL_ISOLATION_CERTIFICATE": "Isolation Certificate #EIC-2026-884 signed by Authorized Electrical Person"
        }
        chk_valid = precondition_engine.evaluate_work_package(
            package_id="PKG-LOTO-02",
            activity="Electrical Isolation / Switchgear Maintenance",
            location="Substation 02",
            submitted_evidence=valid_evidence
        )
        assert chk_valid.status == "PASS"
        assert len(chk_valid.missing_evidence) == 0
        assert any("Evidence verified" in f for f in chk_valid.findings)


def test_rule_20_closed_loop_reopening_and_duplicate_safety():
    """Rule 20: Closed pattern MUST reopen on independent recurrence, and MUST NOT reopen on duplicate."""
    with isolated_test_environment() as env:
        db = env["db"]

        # Seed an existing pattern in CLOSED_HISTORY state
        pattern_id = "PAT-LIFT-CLOSED-01"
        closed_pat = SafetyPattern(
            pattern_id=pattern_id,
            title="Recurring Lifting Zone Breach",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Personnel in lifting perimeter",
            barrier="EXCLUSION_ZONE",
            occurrence_count=3,
            duplicate_count=0,
            validation_status=ReviewStatus.HSE_VALIDATED,
            operational_status="CLOSED_HISTORY"
        )
        db.save_pattern(closed_pat)

        # Seed original event in persistent store
        orig_event = SafetyEvent(
            event_id="EVT-ORIG-01",
            source="HUMAN",
            timestamp="2026-09-20T08:00:00",
            location="Rig Floor 01",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Rigger under suspended casing",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma",
            narrative="Rigger entered the lifting exclusion perimeter while casing was suspended on Rig Floor 01.",
            sif_status=SIFStatus.SIF_POTENTIAL,
            pattern_id=pattern_id
        )
        db.save_event(orig_event)
        recurrence_engine.semantic_memory.add_event(orig_event)
        db.add_pattern_member(pattern_id, orig_event.event_id, "HISTORICAL_RECURRENCE", 1.0, "Original breach")

        # -------------------------------------------------------------
        # Part A: CRITICAL NEGATIVE TEST (Duplicate != Reopen)
        # -------------------------------------------------------------
        duplicate_event = SafetyEvent(
            event_id="EVT-DUP-REPORT-02",
            source="HUMAN",
            timestamp="2026-09-20T08:05:00",  # Same time, duplicate narrative
            location="Rig Floor 01",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Rigger under suspended casing",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma",
            narrative="Rigger entered the lifting exclusion perimeter while casing was suspended on Rig Floor 01.",
            sif_status=SIFStatus.SIF_POTENTIAL
        )

        _, pat_dup = recurrence_engine.evaluate_event(duplicate_event)
        
        # Verify duplicate count incremented, but pattern DID NOT REOPEN
        pat_after_dup = db.get_pattern(pattern_id)
        assert pat_after_dup.validation_status == ReviewStatus.HSE_VALIDATED
        assert pat_after_dup.duplicate_count >= 1

        # -------------------------------------------------------------
        # Part B: INDEPENDENT RECURRENCE TEST (Must Reopen)
        # -------------------------------------------------------------
        independent_recurrence_event = SafetyEvent(
            event_id="EVT-INDEP-RECUR-03",
            source="HUMAN",
            timestamp="2026-09-26T14:30:00",  # Days later, distinct shift/circumstances
            location="Drill Floor 04",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Assistant driller beneath drill collar",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma / blunt force impact",
            narrative="During secondary hoist operation, assistant driller crossed the barrier beneath the moving drill collar.",
            sif_status=SIFStatus.SIF_POTENTIAL
        )

        _, pat_recur = recurrence_engine.evaluate_event(independent_recurrence_event)

        # Pattern MUST REOPEN!
        pat_after_recur = db.get_pattern(pattern_id)
        assert pat_after_recur.validation_status == ReviewStatus.REOPENED
        assert "HSE Review Required" in pat_after_recur.review_notes

        # Verify reopening audit trail
        reviews = db.list_reviews()
        assert any(r["target_id"] == pattern_id and r["action"] == "REOPEN_CHALLENGE" for r in reviews)
