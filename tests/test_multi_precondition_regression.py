"""
SHRAMRAKSHAK: Multi-Precondition Evaluation Regression Test Suite
SIH 2026 Problem Statement: SIH26165

Covers all 5 mandatory multi-precondition test scenarios:
a) One applicable precondition
b) Two applicable preconditions, both satisfied -> PASS
c) Two applicable preconditions, one missing evidence -> REVIEW_REQUIRED
d) Two applicable preconditions, both missing different evidence -> REVIEW_REQUIRED / MISSING_EVIDENCE
e) Unrelated preconditions must NOT be evaluated
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
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from test_isolation import isolated_test_environment
from backend.models_canonical import SafetyPattern, WorkPrecondition, ReviewStatus
from backend.nlp_engine.precondition_engine import precondition_engine


def setup_test_patterns_and_preconditions(db):
    """Helper to seed validated patterns and preconditions for lifting and isolation."""
    # Pattern 1: Lifting Zone Barrier
    pat1 = SafetyPattern(
        pattern_id="PAT-LIFT-01",
        title="Lifting Zone Breach Pattern",
        activity="Mechanical Lifting Operations",
        energy="Gravitational / Suspended Load",
        exposure="Personnel under or near suspended load",
        barrier="EXCLUSION_ZONE",
        validation_status=ReviewStatus.HSE_VALIDATED
    )
    db.save_pattern(pat1)

    # Precondition 1: Lifting Zone Exclusion
    prec1 = WorkPrecondition(
        precondition_id="PREC-LIFT-01",
        pattern_id="PAT-LIFT-01",
        title="Mandatory Exclusion Zone for Lifting",
        required_barrier="EXCLUSION_ZONE",
        required_evidence_types=["PHYSICAL_PERIMETER_DEMARCATION", "OBSERVABLE_CCTV_CLEAR_ZONE"],
        status="ACTIVE"
    )
    db.save_precondition(prec1)

    # Pattern 2: Rigging & Load Control for Lifting
    pat2 = SafetyPattern(
        pattern_id="PAT-LIFT-02",
        title="Tag Line & Rigging Certification Pattern",
        activity="Mechanical Lifting Operations",
        energy="Mechanical / Kinetic Tension",
        exposure="Riggers handling load line",
        barrier="LIFTING_CONTROL",
        validation_status=ReviewStatus.HSE_VALIDATED
    )
    db.save_pattern(pat2)

    # Precondition 2: Certified Rigging Inspection & Tagline
    prec2 = WorkPrecondition(
        precondition_id="PREC-LIFT-02",
        pattern_id="PAT-LIFT-02",
        title="Certified Rigging Inspection & Tag Line",
        required_barrier="LIFTING_CONTROL",
        required_evidence_types=["CERTIFIED_RIGGING_TAG", "NON_CONDUCTIVE_TAG_LINE"],
        status="ACTIVE"
    )
    db.save_precondition(prec2)

    # Pattern 3: Unrelated Confined Space Precondition
    pat3 = SafetyPattern(
        pattern_id="PAT-CONF-03",
        title="Mud Tank Gas Testing Pattern",
        activity="Confined Space Entry",
        energy="Atmospheric / Toxic Gas",
        exposure="Entrants in tank",
        barrier="GAS_TESTING",
        validation_status=ReviewStatus.HSE_VALIDATED
    )
    db.save_pattern(pat3)

    prec3 = WorkPrecondition(
        precondition_id="PREC-CONF-03",
        pattern_id="PAT-CONF-03",
        title="Mandatory 4-Gas Test Log",
        required_barrier="GAS_TESTING",
        required_evidence_types=["CALIBRATED_4GAS_TEST_RECORD", "STANDBY_RESCUE_PERSONNEL"],
        status="ACTIVE"
    )
    db.save_precondition(prec3)

    return prec1, prec2, prec3


def test_scenario_a_one_applicable_precondition():
    """Scenario A: Verify evaluation when exactly one precondition applies."""
    with isolated_test_environment() as env:
        db = env["db"]
        pat = SafetyPattern(
            pattern_id="PAT-LIFT-A",
            title="Single Lifting Pattern",
            activity="Mechanical Lifting Operations",
            energy="Gravitational / Suspended Load",
            exposure="Personnel under load",
            barrier="EXCLUSION_ZONE",
            validation_status=ReviewStatus.HSE_VALIDATED
        )
        db.save_pattern(pat)
        prec = WorkPrecondition(
            precondition_id="PREC-SINGLE-01",
            pattern_id="PAT-LIFT-A",
            title="Single Exclusion Precondition",
            required_barrier="EXCLUSION_ZONE",
            required_evidence_types=["PHYSICAL_PERIMETER_DEMARCATION"],
            status="ACTIVE"
        )
        db.save_precondition(prec)

        # Satisfied evidence
        chk_pass = precondition_engine.evaluate_work_package(
            package_id="PKG-SCENARIO-A1",
            activity="Mechanical Lifting",
            location="Drill Floor",
            submitted_evidence={"PHYSICAL_PERIMETER_DEMARCATION": "Barricade tape installed"}
        )
        assert chk_pass.status == "PASS"
        assert chk_pass.precondition_id == "PREC-SINGLE-01"
        assert len(chk_pass.missing_evidence) == 0

        # Missing evidence
        chk_fail = precondition_engine.evaluate_work_package(
            package_id="PKG-SCENARIO-A2",
            activity="Mechanical Lifting",
            location="Drill Floor",
            submitted_evidence={}
        )
        assert chk_fail.status == "MISSING_EVIDENCE"
        assert chk_fail.missing_evidence == ["PHYSICAL_PERIMETER_DEMARCATION"]


def test_scenario_b_two_applicable_preconditions_both_satisfied():
    """Scenario B: Two applicable preconditions, both satisfied -> PASS."""
    with isolated_test_environment() as env:
        db = env["db"]
        p1, p2, p3 = setup_test_patterns_and_preconditions(db)

        # Submitted evidence covers both PREC-LIFT-01 and PREC-LIFT-02
        full_evidence = {
            "PHYSICAL_PERIMETER_DEMARCATION": "Red warning barriers installed",
            "OBSERVABLE_CCTV_CLEAR_ZONE": True,
            "CERTIFIED_RIGGING_TAG": "Sling Tag #SL-2026-99 valid",
            "NON_CONDUCTIVE_TAG_LINE": "Polypropylene tagline attached"
        }

        chk = precondition_engine.evaluate_work_package(
            package_id="PKG-SCENARIO-B",
            activity="Mechanical Lifting Operations",
            location="Rig Floor 04",
            submitted_evidence=full_evidence
        )

        assert chk.status == "PASS"
        assert len(chk.missing_evidence) == 0
        assert any(p1.precondition_id in f for f in chk.findings)
        assert any(p2.precondition_id in f for f in chk.findings)
        assert not any(p3.precondition_id in f for f in chk.findings)


def test_scenario_c_two_applicable_preconditions_one_missing_evidence():
    """Scenario C: Two applicable preconditions, one completely satisfied, one missing evidence -> REVIEW_REQUIRED."""
    with isolated_test_environment() as env:
        db = env["db"]
        p1, p2, p3 = setup_test_patterns_and_preconditions(db)

        # Evidence satisfies PREC-LIFT-01, but completely misses PREC-LIFT-02
        partial_evidence = {
            "PHYSICAL_PERIMETER_DEMARCATION": "Red warning barriers installed",
            "OBSERVABLE_CCTV_CLEAR_ZONE": True
            # Missing: CERTIFIED_RIGGING_TAG and NON_CONDUCTIVE_TAG_LINE
        }

        chk = precondition_engine.evaluate_work_package(
            package_id="PKG-SCENARIO-C",
            activity="Mechanical Lifting Operations",
            location="Rig Floor 04",
            submitted_evidence=partial_evidence
        )

        assert chk.status == "REVIEW_REQUIRED"
        assert "CERTIFIED_RIGGING_TAG" in chk.missing_evidence
        assert "NON_CONDUCTIVE_TAG_LINE" in chk.missing_evidence
        assert "PHYSICAL_PERIMETER_DEMARCATION" not in chk.missing_evidence

        # Check that findings preserve which precondition each requirement belongs to
        p2_findings = [f for f in chk.findings if p2.precondition_id in f]
        assert len(p2_findings) >= 2
        assert any("CERTIFIED_RIGGING_TAG" in f for f in p2_findings)


def test_scenario_d_two_applicable_preconditions_both_missing_different_evidence():
    """Scenario D: Two applicable preconditions, both missing different items of evidence."""
    with isolated_test_environment() as env:
        db = env["db"]
        p1, p2, p3 = setup_test_patterns_and_preconditions(db)

        # One item from p1 satisfied, one item from p2 satisfied, other items missing
        mixed_evidence = {
            "PHYSICAL_PERIMETER_DEMARCATION": "Barricade in place",
            # p1 missing: OBSERVABLE_CCTV_CLEAR_ZONE
            "CERTIFIED_RIGGING_TAG": "Sling verified"
            # p2 missing: NON_CONDUCTIVE_TAG_LINE
        }

        chk = precondition_engine.evaluate_work_package(
            package_id="PKG-SCENARIO-D",
            activity="Mechanical Lifting Operations",
            location="Rig Floor 04",
            submitted_evidence=mixed_evidence
        )

        assert chk.status == "REVIEW_REQUIRED"
        assert "OBSERVABLE_CCTV_CLEAR_ZONE" in chk.missing_evidence
        assert "NON_CONDUCTIVE_TAG_LINE" in chk.missing_evidence
        assert len(chk.missing_evidence) == 2

        # Verify that findings attribute each missing item to its respective precondition
        p1_missing_findings = [f for f in chk.findings if p1.precondition_id in f and "OBSERVABLE_CCTV_CLEAR_ZONE" in f]
        p2_missing_findings = [f for f in chk.findings if p2.precondition_id in f and "NON_CONDUCTIVE_TAG_LINE" in f]
        assert len(p1_missing_findings) > 0
        assert len(p2_missing_findings) > 0


def test_scenario_e_unrelated_preconditions_must_not_be_evaluated():
    """Scenario E: Unrelated preconditions (e.g. Confined Space / Gas Testing) are NOT evaluated for Lifting."""
    with isolated_test_environment() as env:
        db = env["db"]
        p1, p2, p3 = setup_test_patterns_and_preconditions(db)

        chk = precondition_engine.evaluate_work_package(
            package_id="PKG-SCENARIO-E",
            activity="Mechanical Crane Lifting",
            location="Pipe Rack Area",
            submitted_evidence={}
        )

        # Only p1 and p2 should be evaluated. p3 (Confined Space / Gas Testing) must NOT be present!
        assert "CALIBRATED_4GAS_TEST_RECORD" not in chk.missing_evidence
        assert "STANDBY_RESCUE_PERSONNEL" not in chk.missing_evidence
        assert not any(p3.precondition_id in f for f in chk.findings)
        assert any(p1.precondition_id in f for f in chk.findings)
        assert any(p2.precondition_id in f for f in chk.findings)
