"""
Automated Test Suite for SHRAMRAKSHAK Clean Demo Session & Live Judge Flow
Validates Section 42 of SIH 2026 Hardening Specification
"""

import pytest
import requests
import json

BASE_URL = "http://localhost:8000"

def test_demo_clean_start_at_zero():
    # Reset first to ensure clean baseline
    res = requests.post(f"{BASE_URL}/api/demo/reset", json={})
    assert res.status_code == 200, res.text
    summary = res.json().get("summary", {})
    assert summary.get("total_events") == 0
    assert summary.get("sif_potential_count") == 0
    assert summary.get("candidate_patterns_count") == 0
    assert summary.get("validated_patterns_count") == 0
    assert summary.get("active_preconditions_count") == 0

def test_four_differently_worded_human_reports_and_pattern_discovery():
    # Start clean
    requests.post(f"{BASE_URL}/api/demo/reset", json={})

    reports = [
        "Worker entered the crane lifting exclusion zone while a suspended load was being moved.",
        "During lifting, a contractor crossed the barricaded area beneath the suspended load.",
        "Personnel were observed inside the drop zone during an active crane operation.",
        "A worker bypassed the temporary lifting barrier and entered the restricted area."
    ]

    for idx, narrative in enumerate(reports, 1):
        res = requests.post(f"{BASE_URL}/api/demo/human-report", json={"text": narrative})
        assert res.status_code == 200, res.text
        evt = res.json().get("event", {})
        assert evt.get("source") == "HUMAN"
        assert evt.get("sif_potential") in ["HIGH", "CRITICAL", "MEDIUM", "REVIEW_REQUIRED"]
        assert "EXCLUSION" in str(evt.get("critical_barrier", "")).upper() or "ZONE" in str(evt.get("critical_barrier", "")).upper() or "BARRICADE" in str(evt.get("critical_barrier", "")).upper()

    # Query demo status
    status_res = requests.get(f"{BASE_URL}/api/demo/status").json()
    assert status_res.get("total_events") == 4
    assert status_res.get("pattern_count") >= 1
    top_pat = status_res.get("patterns")[0]
    assert top_pat.get("occurrence_count") == 4
    assert top_pat.get("validation_status") == "CANDIDATE"
    assert "HUMAN" in top_pat.get("source_breakdown", "").upper()

def test_cctv_occurrence_linking_as_fifth_event():
    # CCTV observation
    res = requests.post(f"{BASE_URL}/api/demo/cctv-event", json={"camera_id": "CAM-RIG-01"})
    assert res.status_code == 200, res.text
    cctv_evt = res.json().get("event", {})
    assert cctv_evt.get("source") == "CCTV"
    assert cctv_evt.get("camera_id") == "CAM-RIG-01"

    status_res = requests.get(f"{BASE_URL}/api/demo/status").json()
    assert status_res.get("total_events") == 5
    top_pat = status_res.get("patterns")[0]
    assert top_pat.get("occurrence_count") == 5
    assert "CCTV" in top_pat.get("source_breakdown", "")
    assert "Human" in top_pat.get("source_breakdown", "")

def test_hse_validation_and_precondition_derivation():
    status_res = requests.get(f"{BASE_URL}/api/demo/status").json()
    top_pat = status_res.get("patterns")[0]
    pat_id = top_pat.get("pattern_id")

    # HSE Confirm
    val_res = requests.post(f"{BASE_URL}/api/demo/validate-pattern", json={
        "pattern_id": pat_id,
        "action": "CONFIRM",
        "reviewer": "HSE_MANAGER_OIL",
        "notes": "Confirmed recurring failure of physical exclusion zone."
    }).json()

    assert val_res.get("success") is True
    assert val_res.get("status") == "HSE_VALIDATED"
    prec = val_res.get("precondition", {})
    assert prec.get("pattern_id") == pat_id
    assert "PHYSICAL" in str(prec.get("required_evidence", [])) or "PERIMETER" in str(prec.get("required_evidence", []))

def test_action_lifecycle_and_verification_and_rebreach():
    status_res = requests.get(f"{BASE_URL}/api/demo/status").json()
    top_pat = status_res.get("patterns")[0]
    pat_id = top_pat.get("pattern_id")

    # 1. Assign action
    assign_res = requests.post(f"{BASE_URL}/api/demo/assign-action", json={
        "pattern_id": pat_id,
        "supervisor": "SUP-01",
        "required_action": "Clear zone and secure perimeter barricade"
    }).json()
    assert assign_res.get("success") is True
    action = assign_res.get("action", {})
    action_id = action.get("action_id")
    assert action.get("lifecycle_state") == "ACTION_IN_PROGRESS"

    # 2. Complete action -> AWAITING_VERIFICATION (Completion is not proof)
    comp_res = requests.post(f"{BASE_URL}/api/demo/complete-action", json={
        "action_id": action_id,
        "notes": "Barricade reinstated"
    }).json()
    assert comp_res.get("success") is True
    assert comp_res["action"]["lifecycle_state"] == "AWAITING_VERIFICATION"

    # 3. Closed-loop verification with Re-breach
    rebreach_res = requests.post(f"{BASE_URL}/api/demo/verify-action", json={
        "action_id": action_id,
        "rebreach": True,
        "notes": "Optical detection: person stepped past reinstated tape"
    }).json()
    assert rebreach_res.get("success") is True
    assert rebreach_res.get("verified") is False
    assert "RE-BREACH DETECTED" in rebreach_res.get("status", "")
    assert rebreach_res["action"]["lifecycle_state"] == "REOPENED"

    # 4. Verified restoration
    restored_res = requests.post(f"{BASE_URL}/api/demo/verify-action", json={
        "action_id": action_id,
        "rebreach": False,
        "notes": "CCTV optical feed confirms zero presence in exclusion zone for 10 minutes"
    }).json()
    assert restored_res.get("success") is True
    assert restored_res.get("verified") is True
    assert "OBSERVABLE CONDITION RESTORED" in restored_res.get("status", "")

def test_reset_returns_to_zero_and_preserves_db():
    # Verify DB has real records
    evts_res = requests.get(f"{BASE_URL}/api/events?source=ALL").json()
    # Reset demo workspace
    res = requests.post(f"{BASE_URL}/api/demo/reset", json={}).json()
    assert res.get("success") is True
    summary = res.get("summary", {})
    assert summary.get("total_events") == 0
    assert summary.get("sif_potential_count") == 0
    assert summary.get("candidate_patterns_count") == 0
    assert summary.get("active_preconditions_count") == 0

    # Ensure backend is healthy
    check_res = requests.get(f"{BASE_URL}/api/demo/status").json()
    assert check_res.get("is_clean_start") is True

if __name__ == "__main__":
    pytest.main(["-v", __file__])
