import sys
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from models import Alert
from state import state_manager
from nlp_engine import (
    nlp_analyzer, LSRClassifier, SIFClassifier, PrecursorExtractor, PatternMiner, ReportGenerator
)

client = TestClient(app)

def run_tests():
    print("=" * 65)
    print(" RUNNING AI + NLP SAFETY ANALYSIS TEST SUITE (SIH PS 26165)")
    print("=" * 65)

    # -------------------------------------------------------------
    # TEST 1: LSR Classifier - Multi-label IOGP Rules
    # -------------------------------------------------------------
    lsr_clf = LSRClassifier()

    # Mechanical lifting + Line of Fire
    text1 = "Person entered active lifting exclusion zone beneath suspended crane load."
    rules1 = lsr_clf.classify(text1, {"activity": "Mechanical Lifting", "hazard": "Suspended Load"})
    assert "Safe Mechanical Lifting" in rules1, f"Expected 'Safe Mechanical Lifting' in {rules1}"
    assert "Line of Fire" in rules1, f"Expected 'Line of Fire' in {rules1}"
    print("[PASS] TEST 1a: Multi-label IOGP mapping -> Safe Mechanical Lifting & Line of Fire")

    # Working at height
    text2 = "Scaffolder unclipped fall protection harness on elevated platform at 4m."
    rules2 = lsr_clf.classify(text2, {"activity": "Working at Height"})
    assert "Working at Height" in rules2, f"Expected 'Working at Height' in {rules2}"
    print("[PASS] TEST 1b: IOGP mapping -> Working at Height")

    # Bypassing safety controls
    text3 = "Interlock barrier breached and bypassed during pump maintenance."
    rules3 = lsr_clf.classify(text3)
    assert "Bypassing Safety Controls" in rules3, f"Expected 'Bypassing Safety Controls' in {rules3}"
    print("[PASS] TEST 1c: IOGP mapping -> Bypassing Safety Controls")

    # Unrelated routine text -> No rules forced
    text_none = "Office meeting regarding monthly budget review completed."
    rules_none = lsr_clf.classify(text_none)
    assert len(rules_none) == 0, f"Expected no rules, got {rules_none}"
    print("[PASS] TEST 1d: No applicable rule forced when none applies")

    # -------------------------------------------------------------
    # TEST 2: SIF Classifier - SIF Positive vs Negative
    # -------------------------------------------------------------
    sif_clf = SIFClassifier()

    # SIF Positive (High-risk mechanical lifting zone breach)
    sif_pot1, score1, lvl1, reason1, why1 = sif_clf.classify(
        "Person entered the active lifting exclusion zone while a suspended load was present.",
        {"event_type": "Restricted Zone Entry", "activity": "Mechanical Lifting", "hazard": "Suspended Load"}
    )
    assert sif_pot1 is True, "Expected SIF Potential to be True for lifting zone entry"
    assert score1 >= 60, f"Expected high risk score, got {score1}"
    assert lvl1 in ["HIGH", "CRITICAL"], f"Expected HIGH/CRITICAL, got {lvl1}"
    assert len(why1) > 0, "Expected explainability bullet points"
    print(f"[PASS] TEST 2a: SIF Positive -> Potential=YES, Score={score1}, Level={lvl1}")

    # SIF Negative (Isolated routine helmet violation)
    sif_pot2, score2, lvl2, reason2, why2 = sif_clf.classify(
        "Worker observed without required hard hat in general transit area.",
        {"event_type": "Helmet/PPE Violation", "activity": "General Site Operations"}
    )
    assert sif_pot2 is False, "Expected SIF Potential to be False for isolated helmet omission"
    assert score2 < 60, f"Expected moderate risk score for PPE, got {score2}"
    assert lvl2 == "MEDIUM", f"Expected MEDIUM level for PPE, got {lvl2}"
    assert "does not meet SIF precursor criteria" in reason2
    print(f"[PASS] TEST 2b: SIF Negative -> Potential=NO (Routine PPE), Score={score2}, Level={lvl2}")

    # -------------------------------------------------------------
    # TEST 3: Precursor & Entity Extractor
    # -------------------------------------------------------------
    extractor = PrecursorExtractor()
    extracted = extractor.extract(
        "Worker stepped into crane swing radius under suspended pipe spool in Demo Lifting Area."
    )
    assert extracted["activity"] == "Mechanical Lifting"
    assert "Demo Lifting Area" in extracted["location"]
    assert "Suspended Load" in extracted["hazard"]
    assert "barrier" in extracted["barrier_failure"].lower()
    assert "precursor" in extracted and len(extracted["precursor"]) > 5
    assert len(extracted["ai_recommendation"]) > 10
    print("[PASS] TEST 3: Precursor and barrier failure extraction verified")

    # -------------------------------------------------------------
    # TEST 4: CCTV Alert to SafetyReport Conversion
    # -------------------------------------------------------------
    rep_gen = ReportGenerator()
    test_alert = Alert(
        id="ALT-TEST-999",
        type="Restricted Zone Entry",
        location="Demo Lifting Area",
        camera="C-01",
        created_at=datetime.now().isoformat(),
        response_deadline=datetime.now().isoformat(),
        hazard="Exclusion Zone Breach",
        severity="HIGH",
        person_count=1
    )
    report = rep_gen.convert_alert_to_report(test_alert)
    assert report.report_id == "REP-TEST-999"
    assert report.source in ["CCTV_EVENT", "CCTV SAFETY OBSERVATION"]
    assert report.sif_potential is True
    assert "Safe Mechanical Lifting" in report.life_saving_rules
    assert len(report.why_flagged) > 0
    print("[PASS] TEST 4: CCTV alert successfully converted to SafetyReport with AI analysis")

    # -------------------------------------------------------------
    # TEST 5: Pattern Miner & Insufficient Data Handling
    # -------------------------------------------------------------
    miner = PatternMiner()
    
    # 5a. Insufficient data handling (< 2 reports)
    empty_patterns = miner.mine_patterns([report])
    assert len(empty_patterns) == 0, "Single report should not produce recurring pattern"
    print("[PASS] TEST 5a: Insufficient historical events handled cleanly (0 patterns)")

    # 5b. Multiple reports with repeated cluster
    report2 = rep_gen.convert_alert_to_report(test_alert)
    report2.report_id = "REP-TEST-999-B"
    patterns = miner.mine_patterns([report, report2])
    assert len(patterns) >= 1, "Expected at least 1 recurring pattern"
    assert patterns[0].occurrences >= 2
    assert "Demo Lifting Area" in patterns[0].location
    print(f"[PASS] TEST 5b: Recurring pattern detected: '{patterns[0].title}' (count={patterns[0].occurrences})")

    # 5c. Prioritization calculations
    prio = miner.calculate_prioritization([report, report2])
    assert len(prio["high_risk_locations"]) >= 1
    assert prio["high_risk_locations"][0]["location"] == "Demo Lifting Area"
    assert prio["high_risk_locations"][0]["sif_precursors"] == 2
    print("[PASS] TEST 5c: Area risk prioritization and SIF precursor density computed")

    # -------------------------------------------------------------
    # TEST 6: REST API Endpoints Verification
    # -------------------------------------------------------------
    # Reset demo to clean state
    res_reset = client.post("/api/demo/reset")
    assert res_reset.status_code == 200

    # Test raw text analysis API
    raw_payload = {
        "text": "Near-miss report: Contract rigger entered crane radius during pipe laydown without permit verification.",
        "context": {"location": "Drill Site Alpha", "activity": "Mechanical Lifting"}
    }
    res_raw = client.post("/api/reports/analyze-text", json=raw_payload)
    assert res_raw.status_code == 200
    raw_analysis = res_raw.json()
    assert raw_analysis["sif_potential"] is True
    assert "Safe Mechanical Lifting" in raw_analysis["life_saving_rules"]
    print("[PASS] TEST 6a: POST /api/reports/analyze-text processed raw incident text successfully")

    # Test dataset preset sample API
    res_sample = client.get("/api/dataset/sample?max_rows=50")
    assert res_sample.status_code == 200
    data_sample = res_sample.json()
    assert data_sample["quality_report"]["total_rows"] >= 50
    print("[PASS] TEST 6b: GET /api/dataset/sample loaded preset dataset successfully")


    print("=" * 65)
    print(" ALL 12 AI + NLP SAFETY ANALYSIS TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
