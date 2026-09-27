"""
SHRAMRAKSHAK: Semantic Memory Reconciliation & Integrity Final Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gate G07, G08, & G09:
1. check_memory_integrity() detects discrepancies and fails loudly (zero silent corruption).
2. semantic_memory.reconcile_and_rebuild() restores bijective alignment:
   SQLite Events == SQLite Embeddings == FAISS Vectors == Mapping Entries.
3. 0 orphan vectors, 0 orphan mappings, 0 missing embeddings after reconciliation.
4. Zero production storage mutation (isolated_test_environment).
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
tools_dir = os.path.join(ROOT_DIR, "tools")
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

from test_isolation import isolated_test_environment
from backend.nlp_engine.semantic_memory import semantic_memory
from backend.models_canonical import SafetyEvent, SIFStatus
from check_memory_integrity import check_memory_integrity


def test_clean_environment_integrity_pass():
    """Verify that a properly indexed isolated environment produces PASS status."""
    with isolated_test_environment(prefix="test_recon_clean_") as ctx:
        db = ctx["db"]
        sm = ctx["semantic_memory"]

        ev1 = SafetyEvent(
            event_id="EVT-REC-01",
            activity="Lifting Operations",
            energy="Gravity / Suspended Load",
            exposure="Inside exclusion zone",
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Rigger entered crane perimeter during pipe hoisting."
        )
        ev2 = SafetyEvent(
            event_id="EVT-REC-02",
            activity="LOTO",
            energy="Live Electrical",
            exposure="MCC panel",
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Electrician worked on energized busbar without padlock."
        )
        db.save_event(ev1)
        db.save_event(ev2)

        # Index both events into isolated FAISS & mapping
        sm.index_event(ev1)
        sm.index_event(ev2)

        report = check_memory_integrity(
            db_path=db.db_path,
            index_path=sm.index_path,
            map_path=sm.map_path
        )

        assert report["status"] == "PASS"
        assert report["counts"]["events"] == 2
        assert report["counts"]["faiss_vectors"] == 2
        assert report["counts"]["mappings"] == 2
        assert len(report["orphan_vectors"]) == 0
        assert len(report["orphan_mappings"]) == 0
        assert len(report["unindexed_events"]) == 0
        assert report["persistence_state"] == "CLEAN"


def test_detect_discrepancy_and_reconcile():
    """Verify that corruption is detected and cleanly resolved via reconcile_and_rebuild()."""
    with isolated_test_environment(prefix="test_recon_corrupt_") as ctx:
        db = ctx["db"]
        sm = ctx["semantic_memory"]

        # Step 1: Add and index ev1
        ev1 = SafetyEvent(
            event_id="EVT-CORRUPT-01",
            activity="Lifting",
            energy="Suspended Load",
            exposure="Exposed",
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Worker in drop radius."
        )
        db.save_event(ev1)
        sm.index_event(ev1)

        # Step 2: Inject unindexed event directly into SQLite (deliberate discrepancy)
        ev2 = SafetyEvent(
            event_id="EVT-CORRUPT-02",
            activity="Hot Work",
            energy="Thermal",
            exposure="Nearby sparks",
            sif_status=SIFStatus.SIF_POTENTIAL,
            narrative="Sparks flew near open vent."
        )
        db.save_event(ev2)
        # Note: ev2 is intentionally NOT indexed in FAISS or mapping

        # Step 3: Integrity check must fail loudly
        report_fail = check_memory_integrity(
            db_path=db.db_path,
            index_path=sm.index_path,
            map_path=sm.map_path
        )
        assert report_fail["status"] == "FAIL"
        assert "EVT-CORRUPT-02" in report_fail["unindexed_events"]
        assert report_fail["counts"]["events"] == 2
        assert report_fail["counts"]["faiss_vectors"] == 1

        # Step 4: Reconcile and rebuild atomically
        reconcile_res = sm.reconcile_and_rebuild(force=True)
        assert reconcile_res["status"] == "PASS"
        assert reconcile_res["events_count"] == 2
        assert reconcile_res["faiss_vectors"] == 2
        assert reconcile_res["embeddings_count"] == 2

        # Step 5: Integrity check must now pass with 100% alignment
        report_pass = check_memory_integrity(
            db_path=db.db_path,
            index_path=sm.index_path,
            map_path=sm.map_path
        )
        assert report_pass["status"] == "PASS"
        assert report_pass["counts"]["events"] == 2
        assert report_pass["counts"]["faiss_vectors"] == 2
        assert report_pass["counts"]["mappings"] == 2
        assert len(report_pass["orphan_vectors"]) == 0
        assert len(report_pass["orphan_mappings"]) == 0
        assert len(report_pass["unindexed_events"]) == 0
        assert report_pass["persistence_state"] == "CLEAN"
