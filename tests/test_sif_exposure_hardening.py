"""
SHRAMRAKSHAK: Phase 1 SIF Pathway & Exposure Hardening Test Suite
SIH 2026 Problem Statement: SIH26165

Validates all Phase 1 requirements:
- Rule 6: Explicit Exposure Status (CONFIRMED, NEGATED, POSSIBLE, UNKNOWN)
- Rule 7: Physical Evidence-Based SIF Pathway
- Rule 8: Assertion & Temporal Reasoning
- Rule 9: Character-Exact Evidence Traceability
- Rule 10: Barrier State Distinction
"""

import sys
import os
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
backend_dir = os.path.join(ROOT_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.models_canonical import (
    SafetyEvent, AssertionStatus, TemporalStatus, BarrierState, SIFStatus, ExposureStatus
)
from backend.nlp_engine.assertion_detector import assertion_detector
from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine


def test_mandatory_case_1_explicit_negation_known_correct():
    """
    KNOWN CORRECT CASE:
    'No person entered the exclusion zone.'
    Expected:
    assertion = NEGATED
    exposure = NEGATED / NO_HUMAN_EXPOSURE
    SIF = NO_SIF_POTENTIAL_IDENTIFIED
    """
    text = "No person entered the exclusion zone."
    ev = assertion_detector.analyze(text)
    assert ev.assertion == AssertionStatus.NEGATED
    assert ev.exposure_status == ExposureStatus.NEGATED
    assert "NO_HUMAN_EXPOSURE" in ev.exposure or "outside" in ev.exposure.lower()
    assert ev.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_mandatory_case_2_unknown_personnel_location_barrier_failed():
    """
    MANDATORY CASE:
    'No information on personnel location; barrier failed during lift.'
    Expected:
    exposure = UNKNOWN
    SIF = REVIEW_REQUIRED
    """
    text = "No information on personnel location; barrier failed during lift."
    ev = assertion_detector.analyze(text)
    assert ev.exposure_status == ExposureStatus.UNKNOWN
    assert ev.sif_status == SIFStatus.REVIEW_REQUIRED
    assert any("UNKNOWN" in r for r in ev.sif_reasons)
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_mandatory_case_3_confirmed_exposure_suspended_load():
    """
    MANDATORY CASE:
    'Worker entered the exclusion zone while a suspended load was moving.'
    Expected:
    exposure = CONFIRMED
    high-energy hazard = TRUE
    appropriate compromised barrier if supported
    credible consequence
    SIF-POTENTIAL if complete pathway is satisfied
    """
    text = "Worker entered the exclusion zone while a suspended load was moving."
    ev = assertion_detector.analyze(text)
    assert ev.exposure_status == ExposureStatus.CONFIRMED
    assert ev.sif_status == SIFStatus.SIF_POTENTIAL
    assert "BYPASSED" in ev.barrier_state or "FAILED" in ev.barrier_state
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_mandatory_case_4_barrier_failed_but_no_person_entered():
    """
    MANDATORY CASE:
    'Suspended load was moving and the exclusion barrier failed, but no person entered the area.'
    Expected:
    NO_HUMAN_EXPOSURE
    NO_SIF_POTENTIAL_IDENTIFIED
    """
    text = "Suspended load was moving and the exclusion barrier failed, but no person entered the area."
    ev = assertion_detector.analyze(text)
    assert ev.exposure_status == ExposureStatus.NEGATED
    assert ev.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    assert "NO_HUMAN_EXPOSURE" in ev.exposure or "negated" in ev.sif_reasons[0].lower()
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_mandatory_case_5_suspended_load_barrier_failed_location_unknown():
    """
    MANDATORY CASE:
    'Suspended load was moving and the exclusion barrier failed; personnel location is unknown.'
    Expected:
    UNKNOWN
    REVIEW_REQUIRED
    """
    text = "Suspended load was moving and the exclusion barrier failed; personnel location is unknown."
    ev = assertion_detector.analyze(text)
    assert ev.exposure_status == ExposureStatus.UNKNOWN
    assert ev.sif_status == SIFStatus.REVIEW_REQUIRED
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_mandatory_case_6_possible_exposure():
    """
    MANDATORY CASE:
    'Worker may have entered the exclusion zone while the suspended load was moving.'
    Expected:
    POSSIBLE
    REVIEW_REQUIRED
    """
    text = "Worker may have entered the exclusion zone while the suspended load was moving."
    ev = assertion_detector.analyze(text)
    assert ev.exposure_status == ExposureStatus.POSSIBLE
    assert ev.sif_status == SIFStatus.REVIEW_REQUIRED
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_mandatory_case_7_unrecorded_personnel_location():
    """
    MANDATORY CASE:
    'The exclusion barrier failed during lifting; personnel location was not recorded.'
    Expected:
    UNKNOWN
    REVIEW_REQUIRED
    """
    text = "The exclusion barrier failed during lifting; personnel location was not recorded."
    ev = assertion_detector.analyze(text)
    assert ev.exposure_status == ExposureStatus.UNKNOWN
    assert ev.sif_status == SIFStatus.REVIEW_REQUIRED
    for sp in ev.evidence:
        assert sp.verify_against(text), f"Evidence offset mismatch: {sp}"


def test_sif_pathway_direct_exposure_gating():
    """
    Directly tests SIFPathwayEngine against all 4 ExposureStatus values:
    CONFIRMED -> SIF_POTENTIAL (if high-energy + failed barrier)
    NEGATED -> NO_SIF_POTENTIAL_IDENTIFIED
    UNKNOWN -> REVIEW_REQUIRED
    POSSIBLE -> REVIEW_REQUIRED
    """
    base_evt = SafetyEvent(
        event_id="EVT-UNIT-01",
        activity="Mechanical Lifting Operations",
        energy="Gravitational / Suspended Load (15T Drill Collar)",
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["FAILED"],
        consequence="Catastrophic crush trauma",
        assertion=AssertionStatus.AFFIRMED,
        temporal_status=TemporalStatus.DURING_EVENT
    )

    # 1. Confirmed Exposure
    base_evt.exposure = "Worker standing directly in crane path"
    base_evt.exposure_status = ExposureStatus.CONFIRMED
    res1 = sif_pathway_engine.evaluate(base_evt)
    assert res1.sif_status == SIFStatus.SIF_POTENTIAL

    # 2. Negated Exposure
    base_evt.exposure = "No worker in line of fire"
    base_evt.exposure_status = ExposureStatus.NEGATED
    res2 = sif_pathway_engine.evaluate(base_evt)
    assert res2.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED

    # 3. Unknown Exposure
    base_evt.exposure = "Personnel location not recorded"
    base_evt.exposure_status = ExposureStatus.UNKNOWN
    res3 = sif_pathway_engine.evaluate(base_evt)
    assert res3.sif_status == SIFStatus.REVIEW_REQUIRED

    # 4. Possible Exposure
    base_evt.exposure = "Worker may have been in radius"
    base_evt.exposure_status = ExposureStatus.POSSIBLE
    res4 = sif_pathway_engine.evaluate(base_evt)
    assert res4.sif_status == SIFStatus.REVIEW_REQUIRED


def test_barrier_state_distinction_bypassed_vs_removed():
    """
    Rule 10: Barrier states must distinguish BYPASSED from REMOVED.
    """
    t_bypassed = "Worker ducked under the barricade tape into the zone."
    ev_bypassed = assertion_detector.analyze(t_bypassed)
    assert "BYPASSED" in ev_bypassed.barrier_state

    t_removed = "The perimeter guard was removed prior to operation."
    ev_removed = assertion_detector.analyze(t_removed)
    assert "REMOVED" in ev_removed.barrier_state
    assert BarrierState.BYPASSED != BarrierState.REMOVED


if __name__ == "__main__":
    print("============================================================")
    print("RUNNING PHASE 1 SIF & EXPOSURE HARDENING TESTS")
    print("============================================================")
    test_mandatory_case_1_explicit_negation_known_correct()
    print(" [x] 1. Explicit Negation (Known Correct) Passed")
    test_mandatory_case_2_unknown_personnel_location_barrier_failed()
    print(" [x] 2. Unknown Personnel Location + Failed Barrier -> REVIEW_REQUIRED Passed")
    test_mandatory_case_3_confirmed_exposure_suspended_load()
    print(" [x] 3. Confirmed Exposure + Suspended Load -> SIF_POTENTIAL Passed")
    test_mandatory_case_4_barrier_failed_but_no_person_entered()
    print(" [x] 4. Barrier Failed BUT No Person Entered -> NO_SIF Passed")
    test_mandatory_case_5_suspended_load_barrier_failed_location_unknown()
    print(" [x] 5. Suspended Load + Barrier Failed + Location Unknown -> REVIEW_REQUIRED Passed")
    test_mandatory_case_6_possible_exposure()
    print(" [x] 6. Possible Exposure -> REVIEW_REQUIRED Passed")
    test_mandatory_case_7_unrecorded_personnel_location()
    print(" [x] 7. Unrecorded Personnel Location -> REVIEW_REQUIRED Passed")
    test_sif_pathway_direct_exposure_gating()
    print(" [x] 8. SIFPathwayEngine Direct 4-State Gating Passed")
    test_barrier_state_distinction_bypassed_vs_removed()
    print(" [x] 9. Barrier State Distinction (BYPASSED != REMOVED) Passed")
    print("============================================================")
    print("ALL PHASE 1 SIF & EXPOSURE HARDENING TESTS PASSED 100%!")
    print("============================================================")
