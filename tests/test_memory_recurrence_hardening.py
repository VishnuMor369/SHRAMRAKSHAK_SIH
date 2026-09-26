"""
SHRAMRAKSHAK: Dedicated Memory & Recurrence Hardening Test Suite (Phase 2)
SIH 2026 Problem Statement: SIH26165

Covers all Phase 2 Hardening Requirements:
1. FAISS / SQLite synchronization via batch insertion and check_index_integrity()
2. Configurable similarity thresholds (0.95, 0.80, 0.65, 0.50)
3. Structured reasoning objects in RecurrenceResult
4. Safe control separation (Polarity Conflict and Safe Observation)
5. Pattern formation gating (SIF-potential requirement & CANDIDATE status)
6. Precondition generation gating (Strictly HSE_VALIDATED required)
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
from backend.models_canonical import (
    SafetyEvent, AssertionStatus, ExposureStatus,
    BarrierState, SIFStatus, ReviewStatus, RecurrenceRelationship,
    SafetyPattern
)
from backend.nlp_engine.semantic_memory import semantic_memory
from backend.nlp_engine.recurrence_engine import (
    recurrence_engine,
    SIMILARITY_DUPLICATE_THRESHOLD,
    SIMILARITY_RECURRENCE_THRESHOLD,
    SIMILARITY_RELATED_THRESHOLD,
    SIMILARITY_MIN_RETRIEVAL
)
from backend.nlp_engine.precondition_engine import precondition_engine


def test_similarity_threshold_constants():
    """Verify similarity thresholds are defined as configurable constants (Rule 14)."""
    assert SIMILARITY_DUPLICATE_THRESHOLD == 0.95
    assert SIMILARITY_RECURRENCE_THRESHOLD == 0.80
    assert SIMILARITY_RELATED_THRESHOLD == 0.65
    assert SIMILARITY_MIN_RETRIEVAL == 0.50


def test_batch_insertion_sqlite_synchronization():
    """Verify add_events_batch updates both FAISS and SQLite embeddings table (Rule 13)."""
    with isolated_test_environment() as env:
        db = env["db"]
        ev1 = SafetyEvent(
            event_id="EVT-BATCH-01",
            activity="Mechanical Lifting",
            energy="Gravitational Potential",
            exposure="Worker in zone",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush hazard",
            narrative="Worker in zone during lift",
            sif_status=SIFStatus.SIF_POTENTIAL
        )
        ev2 = SafetyEvent(
            event_id="EVT-BATCH-02",
            activity="Working at Height",
            energy="Gravitational Fall",
            exposure="Worker on scaffold",
            barrier=["SAFETY_HARNESS"],
            barrier_state=["FAILED"],
            consequence="Fall hazard",
            narrative="Worker slipped from scaffold without lanyard anchored",
            sif_status=SIFStatus.SIF_POTENTIAL
        )
        db.save_event(ev1)
        db.save_event(ev2)

        added = semantic_memory.add_events_batch([ev1, ev2])
        assert added == 2

        with db.get_connection() as conn:
            cur = conn.execute("SELECT event_id FROM embeddings WHERE event_id IN ('EVT-BATCH-01', 'EVT-BATCH-02')")
            embedded_ids = [r[0] for r in cur.fetchall()]
        assert "EVT-BATCH-01" in embedded_ids
        assert "EVT-BATCH-02" in embedded_ids


def test_check_index_integrity():
    """Verify check_index_integrity provides deterministic diagnostic metrics."""
    with isolated_test_environment():
        report = semantic_memory.check_index_integrity()
        assert "faiss_total_vectors" in report
        assert "faiss_mapped_events" in report
        assert "sqlite_total_events" in report
        assert "sqlite_embeddings_count" in report
        assert "orphan_faiss_mappings_count" in report
        assert "unindexed_sqlite_events_count" in report


def test_duplicate_narrative_detection():
    """Verify semantic similarity >= 0.95 with matching narrative resolves to DUPLICATE."""
    ev_a = SafetyEvent(
        event_id="EVT-ORIG-01",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker inside zone",
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"],
        consequence="Crush trauma",
        narrative="Rigger entered the exclusion zone while the pipe was hoisted."
    )
    ev_b = SafetyEvent(
        event_id="EVT-DUP-02",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker inside zone",
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"],
        consequence="Crush trauma",
        narrative="Rigger entered the exclusion zone while the pipe was hoisted."
    )
    res = recurrence_engine.evaluate_pair(ev_a, ev_b, similarity=0.97)
    assert res.final_relationship == RecurrenceRelationship.DUPLICATE
    assert "DUPLICATE" in res.final_relationship.value
    assert res.reasoning_details is not None
    assert "0.95" in res.reasoning_details["why_chosen"]


def test_safe_control_polarity_separation():
    """Verify Rule 16: Safe control confirmation vs failure breach is NEVER recurrent."""
    ev_failed = SafetyEvent(
        event_id="EVT-FAIL-01",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker inside zone",
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"],
        consequence="Crush trauma",
        sif_status=SIFStatus.SIF_POTENTIAL
    )
    ev_safe = SafetyEvent(
        event_id="EVT-SAFE-01",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker remained outside zone",
        exposure_status=ExposureStatus.NEGATED,
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["EFFECTIVE_VERIFIED"],
        consequence="Safe operation",
        sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    )

    # Even with high semantic similarity (e.g. 0.88), polarity conflict must prevail
    res = recurrence_engine.evaluate_pair(ev_failed, ev_safe, similarity=0.88)
    assert res.final_relationship != RecurrenceRelationship.INDEPENDENT_RECURRENCE
    assert res.final_relationship == RecurrenceRelationship.RELATED_BUT_DIFFERENT
    assert any("POLARITY_CONFLICT" in c for c in res.structured_conflicts)
    assert res.reasoning_details["polarity_check"] == "FAILED_POLARITY_CHECK"


def test_two_safe_controls_observation():
    """Verify two effective control observations classify as RELATED_BUT_DIFFERENT (safe observation)."""
    ev_safe1 = SafetyEvent(
        event_id="EVT-SAFE-01",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker outside perimeter",
        exposure_status=ExposureStatus.NEGATED,
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["EFFECTIVE_VERIFIED"],
        sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    )
    ev_safe2 = SafetyEvent(
        event_id="EVT-SAFE-02",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Zone kept clear",
        exposure_status=ExposureStatus.NEGATED,
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["EFFECTIVE_VERIFIED"],
        sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
    )
    res = recurrence_engine.evaluate_pair(ev_safe1, ev_safe2, similarity=0.84)
    assert res.final_relationship == RecurrenceRelationship.RELATED_BUT_DIFFERENT
    assert res.reasoning_details["polarity_check"] == "SAFE_OBSERVATION"


def test_independent_recurrence_structured_reasoning():
    """Verify Rule 15: Independent recurrence produces rich structured reasoning object."""
    ev1 = SafetyEvent(
        event_id="EVT-REC-01",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker inside zone",
        exposure_status=ExposureStatus.CONFIRMED,
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"],
        sif_status=SIFStatus.SIF_POTENTIAL
    )
    ev2 = SafetyEvent(
        event_id="EVT-REC-02",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Rigger in line of fire",
        exposure_status=ExposureStatus.CONFIRMED,
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"],
        sif_status=SIFStatus.SIF_POTENTIAL
    )
    res = recurrence_engine.evaluate_pair(ev1, ev2, similarity=0.86)
    assert res.final_relationship == RecurrenceRelationship.INDEPENDENT_RECURRENCE
    assert res.reasoning_details is not None
    assert "EXCLUSION_ZONE" in res.reasoning_details["why_chosen"]
    assert "Decisive" in res.reasoning_details["barrier_comparison"]
    assert res.reasoning_details["similarity_score"] == 0.86


def test_low_similarity_unrelated():
    """Verify similarity below retrieval threshold yields UNRELATED."""
    ev1 = SafetyEvent(
        event_id="EVT-A-01",
        activity="Mechanical Lifting",
        energy="Suspended Load",
        exposure="Worker in zone",
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"]
    )
    ev2 = SafetyEvent(
        event_id="EVT-Z-99",
        activity="Office Administration",
        energy="Ergonomic",
        exposure="Desk seated",
        barrier=["CABLE_MANAGEMENT"],
        barrier_state=["FAILED"]
    )
    res = recurrence_engine.evaluate_pair(ev1, ev2, similarity=0.35)
    assert res.final_relationship == RecurrenceRelationship.UNRELATED
    assert res.reasoning_details["why_chosen"] is not None


def test_pattern_formation_gating_sif_required():
    """Verify Rule 17: Pattern is NOT created if neither event has SIF potential."""
    with isolated_test_environment() as env:
        db = env["db"]
        ev_low1 = SafetyEvent(
            event_id="EVT-LOW-01",
            activity="Routine Inspection",
            energy="Thermal",
            exposure="Worker touched warm pipe",
            exposure_status=ExposureStatus.CONFIRMED,
            barrier=["PPE_GLOVES"],
            barrier_state=["BYPASSED"],
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
        )
        ev_low2 = SafetyEvent(
            event_id="EVT-LOW-02",
            activity="Routine Inspection",
            energy="Thermal",
            exposure="Worker touched warm pipe without gloves",
            exposure_status=ExposureStatus.CONFIRMED,
            barrier=["PPE_GLOVES"],
            barrier_state=["BYPASSED"],
            sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
        )
        db.save_event(ev_low1)
        db.save_event(ev_low2)
        semantic_memory.add_event(ev_low1)

        results, pattern = recurrence_engine.process_event(ev_low2)
        # Because neither event had SIF potential, pattern must NOT be formed
        assert pattern is None


def test_precondition_generation_strictly_gated_on_hse_validation():
    """Verify Rule 17: Precondition creation strictly fails if pattern is CANDIDATE or REJECTED."""
    with isolated_test_environment() as env:
        db = env["db"]
        pat_candidate = SafetyPattern(
            pattern_id="PAT-CANDIDATE-ONLY",
            title="Candidate Pattern for Lifting",
            activity="Mechanical Lifting",
            energy="Suspended Load",
            exposure="Zone breach",
            barrier="EXCLUSION_ZONE",
            validation_status=ReviewStatus.CANDIDATE
        )
        db.save_pattern(pat_candidate)

        # Attempting to derive a precondition from a CANDIDATE pattern must raise ValueError
        with pytest.raises(ValueError) as excinfo:
            precondition_engine.create_precondition_from_pattern("PAT-CANDIDATE-ONLY")
        assert "Only HSE_VALIDATED patterns can generate active work preconditions" in str(excinfo.value)
