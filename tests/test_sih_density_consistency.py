"""
SHRAMRAKSHAK: Authoritative SIH Density Consistency Tests
SIH 2026 Problem Statement: SIH26165

Validates Gate G14 & G15:
1. Authoritative formula: (SIF-Potential / Total Eligible) * 100.
2. If denominator == 0: returns None and formats as 'N/A' (no division by zero).
3. Database, API, and Dashboard metrics adhere to single calculation source.
4. Mandatory regulatory disclaimer is present.
5. SIF status corrections propagate to recalculated density immediately.
6. Zero production storage mutation (isolated_test_environment).
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
from backend.nlp_engine.sih_density import (
    compute_sih_density,
    format_sih_density,
    sih_density_service,
    SIHDensityService,
    SIH_DENSITY_DISCLAIMER
)
from backend.models_canonical import SafetyEvent, SIFStatus, ExposureStatus, AssertionStatus, TemporalStatus


def test_formula_mathematical_precision():
    """Verify exact formula (SIF-Potential / Total Eligible) * 100 and zero-denominator handling."""
    # 5 SIF out of 20 = 25.0%
    assert compute_sih_density(5, 20) == 25.0
    assert format_sih_density(compute_sih_density(5, 20)) == "25.0%"

    # 1 SIF out of 3 = 33.3%
    assert compute_sih_density(1, 3) == 33.3
    assert format_sih_density(compute_sih_density(1, 3)) == "33.3%"

    # 0 SIF out of 10 = 0.0%
    assert compute_sih_density(0, 10) == 0.0
    assert format_sih_density(compute_sih_density(0, 10)) == "0.0%"

    # 0 eligible reports -> None ("N/A")
    assert compute_sih_density(0, 0) is None
    assert format_sih_density(compute_sih_density(0, 0)) == "N/A"
    assert compute_sih_density(5, -1) is None
    assert format_sih_density(compute_sih_density(5, -1)) == "N/A"


def test_calculate_from_events_consistency():
    """Verify SIHDensityService.calculate_from_events generates identical metrics."""
    events = [
        SafetyEvent(
            event_id="EVT-D-01",
            activity="Lifting",
            energy="Gravity",
            exposure="Exposed",
            sif_status=SIFStatus.SIF_POTENTIAL,
            site="Site-A",
            lsr=["SAFE_MECHANICAL_LIFTING"]
        ),
        SafetyEvent(
            event_id="EVT-D-02",
            activity="Lifting",
            energy="Gravity",
            exposure="Exposed",
            sif_status=SIFStatus.SIF_POTENTIAL,
            site="Site-A",
            lsr=["SAFE_MECHANICAL_LIFTING"]
        ),
        SafetyEvent(
            event_id="EVT-D-03",
            activity="Maintenance",
            energy="Low",
            exposure="None",
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
            site="Site-B",
            lsr=[]
        ),
        SafetyEvent(
            event_id="EVT-D-04",
            activity="Maintenance",
            energy="Low",
            exposure="None",
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
            site="Site-B",
            lsr=[]
        ),
        SafetyEvent(
            event_id="EVT-D-05",
            activity="Electrical",
            energy="480V",
            exposure="Unclear",
            sif_status=SIFStatus.REVIEW_REQUIRED,
            site="Site-A",
            lsr=["ENERGY_ISOLATION"]
        )
    ]

    metrics = sih_density_service.calculate_from_events(events)

    assert metrics["total_eligible_reports"] == 5
    assert metrics["sif_potential_count"] == 2
    assert metrics["review_required_count"] == 1
    assert metrics["no_sif_count"] == 2
    # Density: (2 / 5) * 100 = 40.0%
    assert metrics["sih_density_pct"] == 40.0
    assert metrics["sih_density_formatted"] == "40.0%"
    assert metrics["disclaimer"] == SIH_DENSITY_DISCLAIMER


def test_database_density_consistency_isolated():
    """Verify SIHDensityService.calculate_from_db computes true density from isolated database."""
    with isolated_test_environment(prefix="test_density_db_") as ctx:
        db = ctx["db"]

        # Initially empty database -> 0 reports, density is None ("N/A")
        initial_metrics = sih_density_service.calculate_from_db(db)
        assert initial_metrics["total_eligible_reports"] == 0
        assert initial_metrics["sih_density_pct"] is None
        assert initial_metrics["sih_density_formatted"] == "N/A"

        # Insert 3 events: 1 SIF, 2 Non-SIF -> Density = 33.3%
        db.save_event(SafetyEvent(
            event_id="DB-SIF-01",
            activity="Lifting",
            energy="Gravity",
            exposure="Direct",
            sif_status=SIFStatus.SIF_POTENTIAL,
            site="Drill Rig 04"
        ))
        db.save_event(SafetyEvent(
            event_id="DB-NON-01",
            activity="Housekeeping",
            energy="Low",
            exposure="None",
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
            site="Drill Rig 04"
        ))
        db.save_event(SafetyEvent(
            event_id="DB-NON-02",
            activity="Housekeeping",
            energy="Low",
            exposure="None",
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
            site="Drill Rig 04"
        ))

        metrics = sih_density_service.calculate_from_db(db)
        assert metrics["total_eligible_reports"] == 3
        assert metrics["sif_potential_count"] == 1
        assert metrics["sih_density_pct"] == 33.3
        assert metrics["sih_density_formatted"] == "33.3%"


def test_density_updates_on_sif_status_correction():
    """Verify that updating SIF status of an event recalculates density immediately."""
    with isolated_test_environment(prefix="test_density_update_") as ctx:
        db = ctx["db"]

        ev1 = SafetyEvent(
            event_id="DB-EVT-01",
            activity="Lifting",
            energy="Gravity",
            exposure="Exposed",
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
        )
        ev2 = SafetyEvent(
            event_id="DB-EVT-02",
            activity="Lifting",
            energy="Gravity",
            exposure="Exposed",
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
        )
        db.save_event(ev1)
        db.save_event(ev2)

        m1 = sih_density_service.calculate_from_db(db)
        assert m1["sih_density_pct"] == 0.0

        # Correct ev1 to SIF-POTENTIAL
        ev1.sif_status = SIFStatus.SIF_POTENTIAL
        db.save_event(ev1)

        m2 = sih_density_service.calculate_from_db(db)
        # Now 1 out of 2 = 50.0%
        assert m2["sih_density_pct"] == 50.0
        assert m2["sih_density_formatted"] == "50.0%"
