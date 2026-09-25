"""
SHRAMRAKSHAK: Mandatory 8-Case Assertion & Evidence Span Test Suite
SIH 2026 Problem Statement: SIH26165

Directly verifies P0.3 and P0.5 requirements at Canonical SafetyEvent level.
"""

import sys
import os

# Add root and backend to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

import backend
from backend.models_canonical import AssertionStatus, TemporalStatus, BarrierState, SIFStatus
from backend.nlp_engine.assertion_detector import assertion_detector


def test_assertion_8_cases():
    print("============================================================")
    print("RUNNING 8 MANDATORY ADVERSARIAL ASSERTION TESTS")
    print("============================================================")

    # -----------------------------------------------------------------
    # TEST 1
    # -----------------------------------------------------------------
    t1_text = "Worker entered the exclusion zone while the load was suspended."
    ev1 = assertion_detector.analyze(t1_text)
    print(f"\n[TEST 1] Raw: '{t1_text}'")
    print(f" -> Assertion: {ev1.assertion}")
    print(f" -> Exposure: {ev1.exposure}")
    print(f" -> SIF Status: {ev1.sif_status}")
    print(f" -> Barriers: {ev1.barrier}, States: {ev1.barrier_state}")
    assert ev1.assertion == AssertionStatus.AFFIRMED
    assert "entered the exclusion zone" in [sp.text for sp in ev1.evidence] or "exclusion zone" in [sp.text for sp in ev1.evidence]
    assert ev1.sif_status == SIFStatus.SIF_POTENTIAL
    for sp in ev1.evidence:
        assert sp.verify_against(t1_text), f"Offset mismatch in Test 1: {sp}"
    print(" [x] TEST 1 PASSED: AFFIRMED + human exposure + SIF-POTENTIAL candidate")

    # -----------------------------------------------------------------
    # TEST 2
    # -----------------------------------------------------------------
    t2_text = "Worker remained outside the exclusion zone while the load was suspended."
    ev2 = assertion_detector.analyze(t2_text)
    print(f"\n[TEST 2] Raw: '{t2_text}'")
    print(f" -> Assertion: {ev2.assertion}")
    print(f" -> Exposure: {ev2.exposure}")
    print(f" -> SIF Status: {ev2.sif_status}")
    assert ev2.assertion == AssertionStatus.AFFIRMED
    assert ev2.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    assert "outside" in ev2.exposure.lower() or "no_person" in ev2.exposure.lower()
    for sp in ev2.evidence:
        assert sp.verify_against(t2_text), f"Offset mismatch in Test 2: {sp}"
    print(" [x] TEST 2 PASSED: AFFIRMED + NO person-inside-zone exposure")

    # -----------------------------------------------------------------
    # TEST 3
    # -----------------------------------------------------------------
    t3_text = "No worker entered the exclusion zone."
    ev3 = assertion_detector.analyze(t3_text)
    print(f"\n[TEST 3] Raw: '{t3_text}'")
    print(f" -> Assertion: {ev3.assertion}")
    print(f" -> SIF Status: {ev3.sif_status}")
    assert ev3.assertion == AssertionStatus.NEGATED
    assert ev3.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    for sp in ev3.evidence:
        assert sp.verify_against(t3_text), f"Offset mismatch in Test 3: {sp}"
    print(" [x] TEST 3 PASSED: NEGATED + no observed SIF exposure generated")

    # -----------------------------------------------------------------
    # TEST 4
    # -----------------------------------------------------------------
    t4_text = "If the sling fails, personnel could be struck."
    ev4 = assertion_detector.analyze(t4_text)
    print(f"\n[TEST 4] Raw: '{t4_text}'")
    print(f" -> Assertion: {ev4.assertion}")
    print(f" -> Temporal: {ev4.temporal_status}")
    print(f" -> SIF Status: {ev4.sif_status}")
    assert ev4.assertion == AssertionStatus.HYPOTHETICAL
    assert ev4.temporal_status == TemporalStatus.HYPOTHETICAL
    assert ev4.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    for sp in ev4.evidence:
        assert sp.verify_against(t4_text), f"Offset mismatch in Test 4: {sp}"
    print(" [x] TEST 4 PASSED: HYPOTHETICAL + not an observed incident")

    # -----------------------------------------------------------------
    # TEST 5
    # -----------------------------------------------------------------
    t5_text = "The exclusion zone was inspected and confirmed intact before lifting."
    ev5 = assertion_detector.analyze(t5_text)
    print(f"\n[TEST 5] Raw: '{t5_text}'")
    print(f" -> Assertion: {ev5.assertion}")
    print(f" -> Barrier: {ev5.barrier}")
    print(f" -> Barrier State: {ev5.barrier_state}")
    print(f" -> SIF Status: {ev5.sif_status}")
    assert ev5.assertion == AssertionStatus.AFFIRMED
    assert "EXCLUSION_ZONE" in ev5.barrier
    assert "EFFECTIVE_VERIFIED" in ev5.barrier_state
    assert ev5.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    for sp in ev5.evidence:
        assert sp.verify_against(t5_text), f"Offset mismatch in Test 5: {sp}"
    print(" [x] TEST 5 PASSED: AFFIRMED + EXCLUSION_ZONE + EFFECTIVE_VERIFIED (NOT FAILED)")

    # -----------------------------------------------------------------
    # TEST 6
    # -----------------------------------------------------------------
    t6_text = "It is not true that no barrier was present."
    ev6 = assertion_detector.analyze(t6_text)
    print(f"\n[TEST 6] Raw: '{t6_text}'")
    print(f" -> Assertion: {ev6.assertion}")
    print(f" -> SIF Status: {ev6.sif_status}")
    print(f" -> Uncertainty: {ev6.uncertainty}")
    assert ev6.assertion == AssertionStatus.UNCERTAIN
    assert ev6.sif_status == SIFStatus.REVIEW_REQUIRED
    assert "NEGATION_AMBIGUITY" in ev6.uncertainty
    for sp in ev6.evidence:
        assert sp.verify_against(t6_text), f"Offset mismatch in Test 6: {sp}"
    print(" [x] TEST 6 PASSED: UNCERTAIN + REVIEW_REQUIRED + NEGATION_AMBIGUITY (Abstain rather than guess)")

    # -----------------------------------------------------------------
    # TEST 7
    # -----------------------------------------------------------------
    t7_text = "The exclusion zone was fine; the real issue was a dropped tool."
    ev7 = assertion_detector.analyze(t7_text)
    print(f"\n[TEST 7] Raw: '{t7_text}'")
    print(f" -> Barrier: {ev7.barrier}")
    print(f" -> Barrier State: {ev7.barrier_state}")
    print(f" -> SIF Reasons: {ev7.sif_reasons}")
    assert "EXCLUSION_ZONE" in ev7.barrier
    assert "EFFECTIVE_VERIFIED" in ev7.barrier_state
    assert any("dropped tool" in r.lower() or "dropped-object" in r.lower() for r in ev7.sif_reasons)
    for sp in ev7.evidence:
        assert sp.verify_against(t7_text), f"Offset mismatch in Test 7: {sp}"
    print(" [x] TEST 7 PASSED: exclusion zone intact + dropped tool identified as separate hazard pathway")

    # -----------------------------------------------------------------
    # TEST 8
    # -----------------------------------------------------------------
    t8_text = "The barricade was installed after the event."
    ev8 = assertion_detector.analyze(t8_text)
    print(f"\n[TEST 8] Raw: '{t8_text}'")
    print(f" -> Assertion: {ev8.assertion}")
    print(f" -> Temporal: {ev8.temporal_status}")
    print(f" -> SIF Reasons: {ev8.sif_reasons}")
    assert ev8.assertion == AssertionStatus.POST_EVENT
    assert ev8.temporal_status == TemporalStatus.POST_EVENT
    assert any("after the event" in r.lower() or "not prove incident-time" in r.lower() for r in ev8.sif_reasons)
    for sp in ev8.evidence:
        assert sp.verify_against(t8_text), f"Offset mismatch in Test 8: {sp}"
    print(" [x] TEST 8 PASSED: POST_EVENT (Installation NOT interpreted as incident-time barrier effectiveness)")

    print("\n============================================================")
    print("ALL 8 MANDATORY ADVERSARIAL ASSERTION TESTS PASSED 100%!")
    print("============================================================")


if __name__ == "__main__":
    test_assertion_8_cases()
