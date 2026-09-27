"""
SHRAMRAKSHAK: Re-Breach, Semantic Memory & Pattern Lifecycle Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gates G14, G15, G16, G17, & G18:
1. Two-stage recurrence engine retrieves candidates via FAISS and evaluates structured compatibility.
2. Independent recurrence creates CANDIDATE SafetyPattern (strictly CANDIDATE, never auto-validated).
3. Rule 20 Closed-Loop Reopening: An independent recurrence challenging a closed/validated pattern triggers REOPENED status.
4. Duplicate reports increment duplicate count but MUST NOT reopen closed patterns.
5. All operations run isolated without modifying production storage.
"""

import os
import sys
import pytest
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
tests_dir = os.path.join(ROOT_DIR, "tests")
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from test_isolation import isolated_test_environment
from backend.models_canonical import (
    SafetyEvent,
    SafetyPattern,
    SIFStatus,
    ExposureStatus,
    AssertionStatus,
    TemporalStatus,
    BarrierState,
    ReviewStatus,
    RecurrenceRelationship
)
from backend.nlp_engine.recurrence_engine import RecurrenceEngine
from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine


def test_independent_recurrence_creates_candidate_pattern():
    """Verify that multiple independent SIF precursor events create a CANDIDATE SafetyPattern."""
    with isolated_test_environment(prefix="test_rebreach_cand_") as ctx:
        db = ctx["db"]
        sm = ctx["semantic_memory"]
        rec_engine = RecurrenceEngine()
        rec_engine.semantic_memory = sm

        # Event 1: First lifting zone breach
        ev1 = SafetyEvent(
            event_id="EVT-LIFT-001",
            activity="Crane Hoisting",
            energy="Gravity / Suspended Load",
            exposure="Worker in drop radius",
            exposure_status=ExposureStatus.CONFIRMED,
            barrier=["PHYSICAL_EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma",
            assertion=AssertionStatus.AFFIRMED,
            temporal_status=TemporalStatus.DURING_EVENT,
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Rigger stepped into swing perimeter beneath 8T mud motor."
        )
        db.save_event(ev1)
        sm.add_event(ev1)

        # Event 2: Distinct independent occurrence 3 days later
        ev2 = SafetyEvent(
            event_id="EVT-LIFT-002",
            activity="Crane Hoisting",
            energy="Gravity / Suspended Load",
            exposure="Technician traversing under load",
            exposure_status=ExposureStatus.CONFIRMED,
            barrier=["PHYSICAL_EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush injury",
            assertion=AssertionStatus.AFFIRMED,
            temporal_status=TemporalStatus.DURING_EVENT,
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Contractor walked underneath suspended drill collar while crane slewed."
        )
        db.save_event(ev2)
        sm.add_event(ev2)

        # Evaluate recurrence
        results, pattern = rec_engine.process_event(ev2)

        # Must detect independent recurrence
        assert len(results) > 0
        cand_res = next((r for r in results if r.candidate_id == "EVT-LIFT-001"), None)
        assert cand_res is not None
        assert cand_res.final_relationship == RecurrenceRelationship.INDEPENDENT_RECURRENCE

        # Must propose CANDIDATE SafetyPattern (strictly CANDIDATE, never auto HSE_VALIDATED)
        assert pattern is not None
        assert pattern.validation_status == ReviewStatus.CANDIDATE
        assert pattern.occurrence_count >= 2


def test_closed_pattern_reopens_on_rebreach():
    """Verify Rule 20: When an independent recurrence challenges a closed/validated pattern, it reopens."""
    with isolated_test_environment(prefix="test_rebreach_reopen_") as ctx:
        db = ctx["db"]
        sm = ctx["semantic_memory"]
        rec_engine = RecurrenceEngine()
        rec_engine.semantic_memory = sm

        # Pre-existing established pattern that was formally validated and closed
        pat = SafetyPattern(
            pattern_id="PAT-TEST-LIFT-01",
            title="Recurring Control Breach: PHYSICAL_EXCLUSION_ZONE during Crane Hoisting",
            activity="Crane Hoisting",
            energy="Gravity / Suspended Load",
            exposure="Exclusion zone",
            barrier="PHYSICAL_EXCLUSION_ZONE",
            occurrence_count=2,
            duplicate_count=0,
            validation_status=ReviewStatus.HSE_VALIDATED,
            operational_status="CLOSED"
        )
        db.save_pattern(pat)

        # Pre-existing baseline event in memory
        ev_base = SafetyEvent(
            event_id="EVT-BASE-001",
            activity="Crane Hoisting",
            energy="Gravity / Suspended Load",
            exposure="Exclusion zone",
            barrier=["PHYSICAL_EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Worker breached perimeter under suspended crane load."
        )
        db.save_event(ev_base)
        sm.add_event(ev_base)

        # New re-breach event after corrective action was signed off
        ev_rebreach = SafetyEvent(
            event_id="EVT-REBREACH-002",
            activity="Crane Hoisting",
            energy="Gravity / Suspended Load",
            exposure="Exclusion zone re-entry",
            barrier=["PHYSICAL_EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Worker re-entered lifting exclusion zone while hoist was actively lowering drill string."
        )
        db.save_event(ev_rebreach)
        sm.add_event(ev_rebreach)

        # Process recurrence on rebreach event
        results, updated_pat = rec_engine.process_event(ev_rebreach)

        assert updated_pat is not None
        # Rule 20 invariant: Pattern must be REOPENED
        assert updated_pat.operational_status == "REOPENED"
        assert updated_pat.validation_status == ReviewStatus.REOPENED
        assert "challenged" in updated_pat.review_notes.lower()

        # Check SQLite audit log contains REOPEN_CHALLENGE review
        reviews = db.list_reviews(target_id=pat.pattern_id)
        assert any(r["action"] == "REOPEN_CHALLENGE" for r in reviews)


def test_duplicate_report_does_not_reopen_pattern():
    """Verify Rule 20 Negative Check: Duplicate reports increment duplicate count but MUST NOT reopen."""
    with isolated_test_environment(prefix="test_rebreach_dup_") as ctx:
        db = ctx["db"]
        sm = ctx["semantic_memory"]
        rec_engine = RecurrenceEngine()
        rec_engine.semantic_memory = sm

        # Validated, closed pattern
        pat = SafetyPattern(
            pattern_id="PAT-TEST-LOTO-01",
            title="Recurring Control Breach: LOTO_PADLOCK during Electrical Maintenance",
            activity="Electrical Maintenance",
            energy="Live 480V",
            exposure="Panel",
            barrier="LOTO_PADLOCK",
            occurrence_count=2,
            duplicate_count=0,
            validation_status=ReviewStatus.HSE_VALIDATED,
            operational_status="CLOSED"
        )
        db.save_pattern(pat)

        # Original event
        ev_orig = SafetyEvent(
            event_id="EVT-ELEC-001",
            activity="Electrical Maintenance",
            energy="Live 480V",
            exposure="Switchgear busbar",
            barrier=["LOTO_PADLOCK"],
            barrier_state=["FAILED"],
            sif_status=SIFStatus.SIF_POTENTIAL,
            timestamp="2026-09-25T08:00:00",
            narrative="Contractor opened 480V switchgear cabinet without padlock applied."
        )
        db.save_event(ev_orig)
        sm.add_event(ev_orig)

        # Duplicate report of the exact same incident (same time, identical narrative)
        ev_dup = SafetyEvent(
            event_id="EVT-ELEC-001-DUP",
            activity="Electrical Maintenance",
            energy="Live 480V",
            exposure="Switchgear busbar",
            barrier=["LOTO_PADLOCK"],
            barrier_state=["FAILED"],
            sif_status=SIFStatus.SIF_POTENTIAL,
            timestamp="2026-09-25T08:00:00",
            narrative="Contractor opened 480V switchgear cabinet without padlock applied."
        )
        db.save_event(ev_dup)
        sm.add_event(ev_dup)

        results, pattern_res = rec_engine.process_event(ev_dup)

        # Evaluates as DUPLICATE
        dup_match = next((r for r in results if r.candidate_id == "EVT-ELEC-001"), None)
        assert dup_match is not None
        assert dup_match.final_relationship == RecurrenceRelationship.DUPLICATE

        # Pattern remains CLOSED (must not reopen on duplicate)
        pat_fresh = db.get_pattern("PAT-TEST-LOTO-01")
        assert pat_fresh.operational_status == "CLOSED"
        assert pat_fresh.duplicate_count >= 1
