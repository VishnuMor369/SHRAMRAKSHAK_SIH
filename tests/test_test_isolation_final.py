"""
SHRAMRAKSHAK: Test Isolation & Production Storage Immutability Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gates G01, G02, G03, G04, G05, & G06:
1. Ephemeral, hermetic test storage isolation (isolated_test_environment).
2. Production storage under backend/data/ is NEVER mutated during test runs.
3. Cryptographic SHA-256 hash audit before and after test lifecycle confirms 0 bit difference.
4. Temporary test storage is completely cleaned up upon test teardown.
5. Production memory integrity remains PASS with 0 orphans across 314 baseline events.
"""

import os
import sys
import hashlib
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
from backend.models_canonical import SafetyEvent, SIFStatus, ExposureStatus, AssertionStatus, TemporalStatus
from backend.nlp_engine.sih_density import sih_density_service
from check_memory_integrity import check_memory_integrity


def _file_sha256(filepath: str) -> str:
    """Calculates SHA256 hash of a file on disk."""
    if not os.path.exists(filepath):
        return "NON_EXISTENT"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_isolated_test_environment_zero_production_mutation():
    """Verify that heavy test execution inside isolated_test_environment causes ZERO bit changes in production storage."""
    prod_data_dir = os.path.join(ROOT_DIR, "backend", "data")
    prod_db = os.path.join(prod_data_dir, "shramrakshak.db")
    prod_index = os.path.join(prod_data_dir, "e5_faiss.index")
    prod_map = os.path.join(prod_data_dir, "e5_faiss_mapping.json")

    # Record pre-test production hashes
    pre_db_hash = _file_sha256(prod_db)
    pre_index_hash = _file_sha256(prod_index)
    pre_map_hash = _file_sha256(prod_map)

    temp_dir_recorded = None

    # Execute extensive write operations inside isolated environment
    with isolated_test_environment(prefix="test_iso_audit_") as ctx:
        temp_dir_recorded = ctx["temp_dir"]
        db = ctx["db"]
        sm = ctx["semantic_memory"]

        # Insert multiple safety events
        for i in range(5):
            ev = SafetyEvent(
                event_id=f"EVT-ISO-{i:03d}",
                activity="Rig Maintenance",
                energy="High Pressure Hydraulics",
                exposure="Line of fire",
                sif_status=SIFStatus.SIF_POTENTIAL if i % 2 == 0 else SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
                narrative=f"Isolated test event {i} verifying storage boundary separation."
            )
            db.save_event(ev)
            sm.add_event(ev)

        # Log a review
        db.log_review(
            review_id="REV-ISO-001",
            target_type="EVENT",
            target_id="EVT-ISO-000",
            reviewer_role="TEST_AUDITOR",
            action="VERIFY_ISOLATION",
            previous_value=None,
            new_value={"status": "TESTED"},
            reason="Formal zero-mutation audit"
        )

        # Calculate density
        density = sih_density_service.calculate_from_db(db)
        assert density["total_eligible_reports"] == 5

        # Verify isolated index has 5 vectors
        assert sm.index.ntotal == 5

    # Post-context: Verify temporary directory was removed
    assert not os.path.exists(temp_dir_recorded), f"Temporary directory {temp_dir_recorded} was not cleaned up"

    # Post-context: Verify production storage hashes are 100% IDENTICAL
    post_db_hash = _file_sha256(prod_db)
    post_index_hash = _file_sha256(prod_index)
    post_map_hash = _file_sha256(prod_map)

    assert pre_db_hash == post_db_hash, "Production database shramrakshak.db was mutated during test!"
    assert pre_index_hash == post_index_hash, "Production FAISS index e5_faiss.index was mutated during test!"
    assert pre_map_hash == post_map_hash, "Production mapping e5_faiss_mapping.json was mutated during test!"


def test_production_storage_integrity_remains_pass():
    """Verify that production storage maintains 100% integrity pass status with zero orphans."""
    report = check_memory_integrity()
    assert report["status"] == "PASS"
    assert report["persistence_state"] == "CLEAN"
    assert report["counts"]["events"] == 314
    assert report["counts"]["faiss_vectors"] == 314
    assert report["counts"]["mappings"] == 314
    assert len(report["orphan_vectors"]) == 0
    assert len(report["orphan_mappings"]) == 0
    assert len(report["unindexed_events"]) == 0
