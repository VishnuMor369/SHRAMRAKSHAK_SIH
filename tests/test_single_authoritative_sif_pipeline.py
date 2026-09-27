"""
SHRAMRAKSHAK: Single Authoritative SIF Pipeline Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gate G01 & G02:
1. SIFPathwayEngine strictly governs all safety truth.
2. NLPSafetyAnalyzer delegates 100% of SIF classification to SIFPathwayEngine.
3. sif_classifier is a pure delegation shim with zero divergent logic.
4. CCTV SafetyEvent processing evaluates through SIFPathwayEngine.
5. Canonical SafetyEvent serialization and deserialization preserve SIF status and reasons.
6. Zero mutation of production storage (enforced via isolated_test_environment).
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
from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine, SIFPathwayEngine
from backend.nlp_engine.analyzer import nlp_analyzer, NLPSafetyAnalyzer
from backend.nlp_engine.sif_classifier import sif_classifier, SIFClassifier
from backend.models_canonical import SafetyEvent, SIFStatus, ExposureStatus, AssertionStatus, TemporalStatus
from backend.models import Alert, SafetyReport


def test_analyzer_delegates_to_sif_pathway_engine():
    """Verify that NLPSafetyAnalyzer uses SIFPathwayEngine as its pathway_engine."""
    assert nlp_analyzer.pathway_engine.__class__.__name__ == "SIFPathwayEngine"
    
    # Test analyze_event directly through analyzer pathway engine
    test_narratives = [
        ("Worker entered the lifting exclusion zone while tubular load was suspended overhead.", True),
        ("No technician entered the confined separator vessel prior to gas testing.", False),
        ("Operator unbuttoned high-visibility vest in the administrative parking lot.", False)
    ]

    for narrative, expected_sif in test_narratives:
        ev = sif_pathway_engine.evaluate_narrative(narrative)
        pathway_dict = nlp_analyzer.pathway_engine.analyze_event(ev)
        assert pathway_dict.get("sif_potential") == expected_sif, (
            f"Divergence in pathway_dict for: {narrative}"
        )


def test_sif_classifier_shim_delegation():
    """Verify sif_classifier shim delegates directly to SIFPathwayEngine."""
    test_cases = [
        ("Worker was inside crane swing perimeter with no barricade when web sling severed.", True),
        ("Physical barricade was present and verified intact; rigger remained outside.", False),
        ("Paper flyer unpinned from notice board in tool shed; retrieved and pinned.", False)
    ]

    for narrative, expected_sif in test_cases:
        is_sif, risk_score, risk_level, reason, why_flagged = sif_classifier.classify(narrative)
        ev = sif_pathway_engine.evaluate_narrative(narrative)
        expected_sif_from_engine = (ev.sif_status == SIFStatus.SIF_POTENTIAL)
        
        assert is_sif == expected_sif_from_engine == expected_sif
        assert isinstance(why_flagged, list)
        assert len(why_flagged) > 0


def test_cctv_safety_event_pipeline():
    """Verify CCTV observation SafetyEvent evaluates strictly through SIFPathwayEngine."""
    cctv_event = SafetyEvent(
        event_id="CCTV-TEST-001",
        report_id="R-CCTV-001",
        source="CCTV_ANALYTICS",
        site="Site-Alpha",
        location="Rig 04 - Drill Floor",
        activity="Mechanical Lifting Operations",
        energy="Gravity / Suspended Load",
        exposure="Person inside lifting exclusion zone",
        exposure_status=ExposureStatus.CONFIRMED,
        barrier=["EXCLUSION_ZONE"],
        barrier_state=["BYPASSED"],
        consequence="Crush trauma / blunt force impact",
        assertion=AssertionStatus.AFFIRMED,
        temporal_status=TemporalStatus.DURING_EVENT,
        sif_status=SIFStatus.REVIEW_REQUIRED,
        sif_reasons=[],
        lsr=["SAFE_MECHANICAL_LIFTING"],
        narrative="Camera C-01 detected unauthorized worker inside active lifting exclusion zone beneath moving hoist."
    )

    evaluated = sif_pathway_engine.evaluate(cctv_event)
    assert evaluated.sif_status == SIFStatus.SIF_POTENTIAL
    assert any("suspended" in r.lower() or "hazard" in r.lower() for r in evaluated.sif_reasons)


def test_serialization_preserves_sif_truth():
    """Verify Canonical SafetyEvent serialization and dict export preserve authoritative SIF status."""
    narrative = "Electrician opened 480V motor control center without applying personal lockout padlock."
    event = sif_pathway_engine.evaluate_narrative(narrative)

    event_dict = event.to_dict()
    assert event_dict["sif_status"] == "SIF-POTENTIAL"
    assert isinstance(event_dict["sif_reasons"], list)
    assert len(event_dict["sif_reasons"]) > 0

    reconstructed = SafetyEvent(
        event_id=event_dict["event_id"],
        report_id=event_dict.get("report_id"),
        narrative=event_dict.get("narrative", ""),
        sif_status=SIFStatus(event_dict["sif_status"]),
        sif_reasons=event_dict.get("sif_reasons", [])
    )
    assert reconstructed.sif_status == SIFStatus.SIF_POTENTIAL
    assert reconstructed.narrative == narrative


def test_pipeline_isolated_execution():
    """Verify that running pipeline ingestion and event generation does not touch production storage."""
    with isolated_test_environment(prefix="test_sif_pipe_") as ctx:
        db = ctx["db"]
        event = sif_pathway_engine.evaluate_narrative("Helper traversed active crane drop zone while lifting shackle failed.")
        db.save_event(event)

        saved = db.get_event(event.event_id)
        assert saved is not None
        assert saved.sif_status == SIFStatus.SIF_POTENTIAL
