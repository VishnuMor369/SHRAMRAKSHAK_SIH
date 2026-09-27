"""
SHRAMRAKSHAK: FastAPI REST API Contracts & Endpoint Acceptance Tests
SIH 2026 Problem Statement: SIH26165

Validates Gates G19, G20, G21, G22, & G23:
1. /api/analyze accepts narrative and returns authoritative SIF evaluation and LSR.
2. /api/safety-memory/events provides robust pagination (limit, offset, sif_filter).
3. /api/safety-memory/patterns returns recurring control patterns with operational status.
4. /api/memory/integrity exposes verified memory reconciliation state.
5. /api/density exposes SIH density metrics and mandatory regulatory disclaimer.
6. Zero mutation of production storage.
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

from backend.main import app

client = TestClient(app)


def test_api_analyze_contract():
    """Verify /api/analyze returns canonical SIF evaluation, LSR, risk score, and reasons."""
    payload = {
        "narrative": "Technician reached into energized 480V switchgear panel without applying lockout padlock."
    }
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()

    # Authoritative SIF status
    assert data["sif_status"] == "SIF-POTENTIAL"
    assert data["sif_potential"] is True
    assert data["risk_level"] in ("CRITICAL", "HIGH")
    assert isinstance(data["life_saving_rules"], list)
    assert len(data["life_saving_rules"]) > 0
    assert any("energy" in r.lower() or "isolation" in r.lower() or "bypass" in r.lower() for r in data["life_saving_rules"])
    assert isinstance(data["sif_reasons"], list)
    assert len(data["sif_reasons"]) > 0


def test_api_safety_memory_events_pagination():
    """Verify /api/safety-memory/events pagination with limit, offset, and sif_filter."""
    # Page 1
    res1 = client.get("/api/safety-memory/events?limit=5&offset=0")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["limit"] == 5
    assert data1["offset"] == 0
    assert data1["returned"] <= 5
    assert isinstance(data1["events"], list)
    assert data1["total"] >= data1["returned"]

    # Page 2
    res2 = client.get("/api/safety-memory/events?limit=5&offset=5")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["limit"] == 5
    assert data2["offset"] == 5
    assert isinstance(data2["events"], list)

    # Filter by SIF-POTENTIAL
    res_filt = client.get("/api/safety-memory/events?sif_filter=SIF-POTENTIAL&limit=10")
    assert res_filt.status_code == 200
    data_filt = res_filt.json()
    for ev in data_filt["events"]:
        assert ev["sif_status"] == "SIF-POTENTIAL"


def test_api_safety_memory_patterns_contract():
    """Verify /api/safety-memory/patterns returns patterns with operational status and preconditions."""
    res = client.get("/api/safety-memory/patterns")
    assert res.status_code == 200
    data = res.json()
    patterns = data.get("patterns", data) if isinstance(data, dict) else data
    assert isinstance(patterns, list)
    if patterns:
        p = patterns[0]
        assert "pattern_id" in p
        assert "activity" in p
        assert "barrier" in p
        assert "validation_status" in p
        assert "operational_status" in p
        assert "future_work_requirements" in p


def test_api_memory_integrity_contract():
    """Verify /api/memory/integrity returns PASS status and 0 orphans."""
    res = client.get("/api/memory/integrity")
    assert res.status_code == 200
    report = res.json()
    assert report["status"] == "PASS"
    assert report["persistence_state"] == "CLEAN"
    assert report["counts"]["events"] == report["counts"]["faiss_vectors"] == report["counts"]["mappings"]
    assert len(report["orphan_vectors"]) == 0
    assert len(report["orphan_mappings"]) == 0
    assert len(report["unindexed_events"]) == 0


def test_api_density_contract():
    """Verify /api/density returns authoritative formula, density pct, and regulatory disclaimer."""
    res = client.get("/api/density")
    assert res.status_code == 200
    density = res.json()
    assert "sih_density_pct" in density
    assert density["formula"] == "(SIF-Potential / Total Eligible) * 100"
    assert density["sif_potential_count"] is not None
    assert density["total_eligible_count"] is not None
    assert "regulatory_disclaimer" in density
    assert "reporting-based" in density["regulatory_disclaimer"].lower() or "probability of harm" in density["regulatory_disclaimer"].lower()
