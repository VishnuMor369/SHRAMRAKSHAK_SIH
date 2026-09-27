"""
SHRAMRAKSHAK: CCTV Pipeline & NLP Pipeline Independence Final Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gates G10, G11, G12, & G13:
1. Camera offline / disconnected does NOT degrade or crash the NLP / SIF pipeline.
2. CCTV detections normalize into canonical SafetyEvent instances.
3. SIFPathwayEngine remains the SINGLE authoritative evaluator for CCTV-derived events.
4. NLP safety analysis operates completely independently of CCTV hardware availability.
5. All operations run strictly isolated with zero production storage mutation.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
tests_dir = os.path.join(ROOT_DIR, "tests")
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from test_isolation import isolated_test_environment
from backend.models_canonical import (
    SafetyEvent,
    SIFStatus,
    ExposureStatus,
    AssertionStatus,
    TemporalStatus,
    BarrierState
)
from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
from backend.main import app

client = TestClient(app)


def test_cctv_camera_offline_nlp_continues_operating():
    """Verify that camera disconnect/error does not impair NLP SIF pathway analysis."""
    # 1. Simulate camera offline / malformed frame submission
    bad_res = client.post("/api/cv/frame", json={"frame": "", "camera_id": "C-OFFLINE"})
    # Must fail gracefully (400) without crashing the process
    assert bad_res.status_code in (400, 422)

    # 2. In this camera-offline state, verify NLP analysis succeeds completely
    nlp_res = client.post("/api/analyze", json={
        "narrative": "Worker stepped into the unbarricaded swing radius while mobile crane slewed drill pipe."
    })
    assert nlp_res.status_code == 200, f"NLP analysis failed when camera offline: {nlp_res.text}"
    data = nlp_res.json()
    assert data["sif_status"] == "SIF-POTENTIAL"
    assert any("lifting" in r.lower() for r in data["life_saving_rules"])
    assert len(data["sif_reasons"]) > 0


def test_cctv_alert_normalization_to_canonical_safety_event():
    """Verify CCTV observation normalizes into canonical SafetyEvent and evaluates through SIFPathwayEngine."""
    # Machine observation from CCTV analytics
    cctv_event = SafetyEvent(
        event_id="EVT-CCTV-CAM01-901",
        report_id="RPT-CCTV-901",
        source="CCTV",
        site="Site-Bravo",
        location="Zone-4 Compressor Skid",
        activity="Overhead Rigging & Lifting",
        energy="Gravity / Suspended Load",
        exposure="Technician standing directly under 5T hoist hook",
        exposure_status=ExposureStatus.CONFIRMED,
        barrier=["Physical Exclusion Perimeter"],
        barrier_state=["BYPASSED"],
        consequence="Catastrophic crush trauma from dropped load",
        assertion=AssertionStatus.AFFIRMED,
        temporal_status=TemporalStatus.DURING_EVENT,
        sif_status=SIFStatus.REVIEW_REQUIRED,
        lsr=["SAFE_MECHANICAL_LIFTING"],
        narrative="AI CCTV detected unhelmeted contractor inside active hoisting perimeter beneath suspended drill collar.",
        machine_observation=True
    )

    # Must be evaluated authoritatively by SIFPathwayEngine
    evaluated = sif_pathway_engine.evaluate(cctv_event)
    assert evaluated.sif_status == SIFStatus.SIF_POTENTIAL
    assert evaluated.machine_observation is True
    assert evaluated.source == "CCTV"
    assert "SAFE_MECHANICAL_LIFTING" in evaluated.lsr
    assert any("suspended" in r.lower() or "gravity" in r.lower() or "lifting" in r.lower() or "hazard" in r.lower() for r in evaluated.sif_reasons)


def test_independent_ingestion_and_storage_isolation():
    """Verify human report and CCTV machine observation coexist in isolated DB without cross-pollution."""
    with isolated_test_environment(prefix="test_cctv_nlp_iso_") as ctx:
        db = ctx["db"]
        sm = ctx["semantic_memory"]

        # Human report
        ev_human = sif_pathway_engine.evaluate_narrative(
            "Operator noticed scaffold pole dropped 12 feet near walkway with no toe boards."
        )
        ev_human.source = "HUMAN_REPORT"
        ev_human.event_id = "EVT-H-001"
        db.save_event(ev_human)
        sm.add_event(ev_human)

        # CCTV machine observation
        ev_cctv = SafetyEvent(
            event_id="EVT-C-002",
            source="CCTV",
            site="Site-Alpha",
            location="Drill Floor",
            activity="Pipe Handling",
            energy="High Pressure Hydraulics",
            exposure="Rigger in line of fire of iron roughneck",
            exposure_status=ExposureStatus.CONFIRMED,
            barrier=["Interlock Guard"],
            barrier_state=["DEGRADED"],
            consequence="High pressure hydraulic pinch / crush",
            assertion=AssertionStatus.AFFIRMED,
            temporal_status=TemporalStatus.DURING_EVENT,
            sif_status=SIFStatus.REVIEW_REQUIRED,
            narrative="CCTV Vision: Person entered roughneck operating boundary during makeup sequence.",
            machine_observation=True
        )
        ev_cctv = sif_pathway_engine.evaluate(ev_cctv)
        db.save_event(ev_cctv)
        sm.add_event(ev_cctv)

        # Validate database contents
        saved_h = db.get_event("EVT-H-001")
        saved_c = db.get_event("EVT-C-002")
        assert saved_h is not None and saved_h.source == "HUMAN_REPORT"
        assert saved_c is not None and saved_c.source == "CCTV"
        assert saved_c.sif_status == SIFStatus.SIF_POTENTIAL

        # Validate FAISS index count in isolated environment
        assert sm.index.ntotal == 2
        assert len(sm.id_to_event) == 2
