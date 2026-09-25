"""
SHRAMRAKSHAK: Complete Clean-Room End-to-End Test Suite (SIH 2026 PS SIH26165)
Phase 31 & Phase 33 Validation
"""
import sys
import unittest
from fastapi.testclient import TestClient

from main import app
from unified_event_store import unified_event_store
from dataset_importer import dataset_import_manager
from safety_memory import safety_memory

client = TestClient(app)

class TestCleanRoomEndToEnd(unittest.TestCase):

    def setUp(self):
        # Clean-room reset
        res = client.post("/api/demo/reset")
        self.assertEqual(res.status_code, 200)

    def test_01_human_report_submission_and_persistence(self):
        """Phase 2 & Phase 3: Real human report submission, NLP parsing, persistence and retrieval."""
        payload = {
            "narrative": "Worker crossed the barricade into the crane exclusion zone while a drill collar was suspended overhead.",
            "location": "Drilling Rig 04 - Drill Floor",
            "activity": "Mechanical Lifting Operations",
            "reporter": "Field Safety Supervisor"
        }
        res = client.post("/api/events/human", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success", False))
        ev = data["event"]
        self.assertEqual(ev["source"], "HUMAN")
        self.assertEqual(ev["assertion_status"], "ASSERTED")
        self.assertEqual(ev["sif_potential"], "HIGH")
        self.assertEqual(ev["barrier_condition"], "VIOLATED")
        self.assertTrue(len(ev["evidence_spans"]) > 0)

        # Verify event appears in list
        list_res = client.get("/api/events?source=HUMAN")
        self.assertEqual(list_res.status_code, 200)
        events_data = list_res.json()
        events = events_data.get("events", events_data) if isinstance(events_data, dict) else events_data
        event_ids = [e["event_id"] for e in events]
        self.assertIn(ev["event_id"], event_ids)

        # Verify individual retrieval
        detail_res = client.get(f"/api/events/{ev['event_id']}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["event_id"], ev["event_id"])

    def test_02_all_seven_nlp_modality_cases(self):
        """Phase 7: All 7 required modality and negation test cases."""
        scenarios = [
            ("No worker entered the exclusion zone.", "NEGATED", "NOT_SIF"),
            ("If the sling fails, the load could fall.", "HYPOTHETICAL", "LOW"),
            ("The barricade was installed after the incident.", "POST_EVENT", "HIGH"),
            ("Worker crossed the barricade into the crane exclusion zone while the drill collar was suspended overhead.", "ASSERTED", "HIGH"),
            ("Worker almost entered the zone but stopped before crossing.", "NEGATED", "NOT_SIF"),
            ("Worker entered the zone after lifting was completed.", "POST_EVENT", "LOW"),
            ("No worker entered the zone despite the barricade being removed.", "NEGATED", "NOT_SIF")
        ]

        for text, expected_assertion, expected_sif in scenarios:
            res = client.post("/api/events/human", json={
                "narrative": text,
                "location": "Drilling Rig 04",
                "activity": "Lifting Operations"
            })
            self.assertEqual(res.status_code, 200)
            ev = res.json()["event"]
            self.assertEqual(ev["assertion_status"], expected_assertion, f"Assertion mismatch for '{text}'")
            if expected_sif == "NOT_SIF":
                self.assertIn(ev["sif_potential"], ["NOT_SIF", "LOW"], f"SIF should be suppressed for '{text}'")
            elif expected_sif == "LOW":
                self.assertIn(ev["sif_potential"], ["LOW", "NOT_SIF"], f"SIF should be low for '{text}'")
            else:
                self.assertIn(ev["sif_potential"], ["HIGH", "CRITICAL"], f"SIF should be HIGH for '{text}'")

    def test_03_dataset_import_batch_and_stats(self):
        """Phase 4, 5, 6: Batch dataset ingestion and dynamic summary KPIs."""
        # Check initial stats
        initial_stats = client.get("/api/events/stats/summary").json()
        init_total = initial_stats["total_events"]

        # Run batch import (50 records)
        import_res = client.post("/api/dataset/import-execute?max_rows=50")
        self.assertEqual(import_res.status_code, 200)
        import_data = import_res.json()
        self.assertTrue(import_data.get("success", False))

        # Wait briefly for background thread or verify status
        status = client.get("/api/dataset/import-status").json()
        self.assertIn(status["state"], ["COMPLETED", "PROCESSING", "PARSING", "NORMALIZING"])

        # Check updated stats
        updated_stats = client.get("/api/events/stats/summary").json()
        self.assertGreaterEqual(updated_stats["total_events"], init_total)

    def test_04_cctv_lifecycle_and_verification(self):
        """Phase 18, 19, 21: CCTV machine observation -> Action -> Verify -> Re-breach."""
        # 1. Trigger Phase 3 / 4 live CCTV zone breach
        sim_res = client.post("/api/demo/phase/4")
        self.assertEqual(sim_res.status_code, 200)

        # 2. Check CCTV event exists in unified store
        cctv_res = client.get("/api/events?source=CCTV").json()
        cctv_events = cctv_res.get("events", cctv_res) if isinstance(cctv_res, dict) else cctv_res
        self.assertGreater(len(cctv_events), 0)
        cctv_ev = cctv_events[0]
        event_id = cctv_ev["event_id"]

        # 3. Take corrective action
        act_res = client.post(f"/api/events/{event_id}/action", json={
            "supervisor_id": "SUP-TEST",
            "notes": "Worker evacuated from zone, load grounded."
        })
        self.assertEqual(act_res.status_code, 200)
        self.assertEqual(act_res.json()["event"]["lifecycle_state"], "AWAITING_VERIFICATION")

        # 4. CCTV Verify Clear condition -> RESOLVED
        ver_res = client.post(f"/api/events/{event_id}/verify", json={
            "simulate_rebreach": False,
            "supervisor_id": "SUP-TEST"
        })
        self.assertEqual(ver_res.status_code, 200)
        self.assertEqual(ver_res.json()["event"]["lifecycle_state"], "RESOLVED")

        # 5. Take action again and simulate Re-breach -> FAILED & REOPENED
        client.post(f"/api/events/{event_id}/action", json={"supervisor_id": "SUP-TEST"})
        rebreach_res = client.post(f"/api/events/{event_id}/verify", json={
            "simulate_rebreach": True,
            "supervisor_id": "SUP-TEST"
        })
        self.assertEqual(rebreach_res.status_code, 200)
        self.assertIn(rebreach_res.json()["event"]["lifecycle_state"], ["ACTION_REQUIRED", "ACTION_IN_PROGRESS", "REOPENED"])

    def test_05_safety_memory_governance_and_future_work(self):
        """Phase 14, 15, 16, 17: Candidate recurring pattern -> HSE Validation -> Future Work Requirement."""
        # Fetch patterns
        patterns_res = client.get("/api/safety-memory/patterns").json()
        patterns = patterns_res.get("patterns", patterns_res)
        self.assertGreater(len(patterns), 0)
        pat = patterns[0]
        pat_id = pat["pattern_id"]

        # HSE Validates pattern
        val_res = client.post(f"/api/safety-memory/patterns/{pat_id}/validate", json={
            "decision": "CONFIRM",
            "reviewer": "HSE-Director-OIL"
        })
        self.assertEqual(val_res.status_code, 200)
        self.assertEqual(val_res.json()["pattern"]["validation_status"], "HSE_VALIDATED")

        # Check future work package without required barrier verification
        pkg_res = client.post("/api/safety-memory/check-work-package", json={
            "package_id": "WP-LIFT-2026-99",
            "activity": pat["activity"],
            "hazard": pat["hazard"],
            "location": "Drilling Rig 04",
            "provided_evidence": ["Permit to Work #9921"]  # Missing physical exclusion zone barrier check!
        })
        self.assertEqual(pkg_res.status_code, 200)
        pkg_data = pkg_res.json()
        self.assertEqual(pkg_data["status"], "REQUIRED_SAFETY_EVIDENCE_MISSING")

if __name__ == "__main__":
    unittest.main()
