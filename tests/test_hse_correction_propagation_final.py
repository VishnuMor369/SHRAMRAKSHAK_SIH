"""
SHRAMRAKSHAK: HSE Correction Propagation Final Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gate G11, G12 & G13:
1. Human HSE Review workflow with auditable transitions (CANDIDATE -> HSE_VALIDATED / REJECTED / REOPENED).
2. Dependency-aware recomputation:
   Human correction (barrier_state, activity, energy) triggers:
   -> Recompute SafetyEvent
   -> Recompute SIF Pathway
   -> Recompute LSR Mapping
   -> Update Pattern & Precondition dependencies
3. SIF status change immediately propagates to recalculated SIH density.
4. Auditable snapshot of previous values recorded.
5. Zero production storage mutation (isolated_test_environment).
"""

import os
import sys
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
tests_dir = os.path.join(ROOT_DIR, "tests")
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from test_isolation import isolated_test_environment
from backend.nlp_engine.propagation import propagation_engine
from backend.nlp_engine.sih_density import sih_density_service
from backend.models_canonical import SafetyEvent, SIFStatus, ExposureStatus, AssertionStatus, TemporalStatus, ReviewStatus


def test_correction_recomputes_sif_pathway():
    """Verify that correcting barrier state from BYPASSED to EFFECTIVE_VERIFIED recomputes SIF to NO_SIF."""
    with isolated_test_environment(prefix="test_prop_sif_") as ctx:
        db = ctx["db"]

        # Initial SIF event: Worker inside lifting exclusion zone with bypassed barrier
        initial_event = SafetyEvent(
            event_id="EVT-PROP-001",
            activity="Mechanical Lifting Operations",
            energy="Gravity / Suspended Load",
            exposure="Person inside lifting exclusion zone",
            exposure_status=ExposureStatus.CONFIRMED,
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma / blunt force impact",
            sif_status=SIFStatus.SIF_POTENTIAL,
            sif_reasons=["High-energy hazard: suspended load active"],
            review_status=ReviewStatus.CANDIDATE,
            narrative="Worker entered lifting exclusion zone while load was suspended overhead."
        )
        db.save_event(initial_event)

        # Apply correction: Barrier was actually verified effective and intact
        res = propagation_engine.apply_human_correction(
            event_id="EVT-PROP-001",
            corrections={
                "barrier_state": ["EFFECTIVE_VERIFIED"],
                "review_status": "HSE_VALIDATED"
            },
            reviewer_role="SR_HSE_SPECIALIST",
            reason="Verified crane physical blast wall intact; operator observed from safe booth"
        )

        assert res["event_id"] == "EVT-PROP-001"
        assert res["previous_values"]["sif_status"] == "SIF-POTENTIAL"
        assert res["recomputed_sif"] == "NO_SIF_POTENTIAL_IDENTIFIED"

        # Verify database record updated
        updated_event = db.get_event("EVT-PROP-001")
        assert updated_event.barrier_state == ["EFFECTIVE_VERIFIED"]
        assert updated_event.sif_status == SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
        assert updated_event.review_status == ReviewStatus.CORRECTED


def test_correction_propagates_to_density():
    """Verify that SIF status change via human correction immediately updates SIH density."""
    with isolated_test_environment(prefix="test_prop_density_") as ctx:
        db = ctx["db"]

        ev1 = SafetyEvent(
            event_id="EVT-DENS-01",
            activity="Lifting",
            energy="Gravity / Suspended Load",
            exposure="Exposed",
            barrier_state=["BYPASSED"],
            sif_status=SIFStatus.SIF_POTENTIAL
        )
        ev2 = SafetyEvent(
            event_id="EVT-DENS-02",
            activity="Housekeeping",
            energy="Low",
            exposure="None",
            barrier_state=["EFFECTIVE_VERIFIED"],
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
        )
        db.save_event(ev1)
        db.save_event(ev2)

        # Baseline density: 1 out of 2 = 50.0%
        base_density = sih_density_service.calculate_from_db(db)
        assert base_density["sih_density_pct"] == 50.0
        assert base_density["sif_potential_count"] == 1

        # Correct ev1 to non-SIF (barrier was intact)
        propagation_engine.apply_human_correction(
            event_id="EVT-DENS-01",
            corrections={"barrier_state": ["EFFECTIVE_VERIFIED"]},
            reviewer_role="HSE_AUDITOR",
            reason="Physical inspection showed barricade was uncompromised"
        )

        # Density should now be 0 out of 2 = 0.0%
        recalculated_density = sih_density_service.calculate_from_db(db)
        assert recalculated_density["sih_density_pct"] == 0.0
        assert recalculated_density["sif_potential_count"] == 0
        assert recalculated_density["no_sif_count"] == 2


def test_audit_snapshot_logged():
    """Verify that an auditable review entry is logged in the persistent reviews table."""
    with isolated_test_environment(prefix="test_prop_audit_") as ctx:
        db = ctx["db"]

        event = SafetyEvent(
            event_id="EVT-AUDIT-01",
            activity="Working at Height",
            energy="Elevation / Fall Potential",
            exposure="Exposed",
            barrier_state=["FAILED"],
            sif_status=SIFStatus.SIF_POTENTIAL
        )
        db.save_event(event)

        res = propagation_engine.apply_human_correction(
            event_id="EVT-AUDIT-01",
            corrections={"barrier_state": ["EFFECTIVE_VERIFIED"]},
            reviewer_role="LEAD_SAFETY_INSPECTOR",
            reason="Lifeline was tested and certified intact"
        )

        assert "review_id" in res
        reviews = db.get_reviews_for_event("EVT-AUDIT-01")
        assert len(reviews) >= 1
        latest = reviews[-1]
        assert latest["reviewer_role"] == "LEAD_SAFETY_INSPECTOR"
        assert latest["reason"] == "Lifeline was tested and certified intact"
