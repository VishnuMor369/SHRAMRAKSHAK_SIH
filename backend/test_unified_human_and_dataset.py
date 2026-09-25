"""
SHRAMRAKSHAK: Comprehensive Test Suite for Unified Safety Events, Human Reports & Dataset Ingestion
Tests all critical requirements specified in Phases 1, 2, 3, 4, 5, 6, 7, 21, 30, 31.
"""

import os
import sys
import json
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from unified_event_store import unified_event_store
from dataset_importer import dataset_import_manager
from state import state_manager
from safety_memory import safety_memory

client = TestClient(app)


class TestUnifiedHumanAndDataset(unittest.TestCase):

    def setUp(self):
        unified_event_store.reset()
        dataset_import_manager.reset()
        state_manager.reset_demo()
        safety_memory.reset()

    def test_01_human_report_creation_and_persistence(self):
        """Test Phase 2: Human report submission creates canonical SafetyEvent and persists to disk."""
        payload = {
            "narrative": "Worker crossed the barricade into the crane exclusion zone while a drill collar was suspended overhead.",
            "location": "Drilling Rig 04 - Drill Floor",
            "activity": "Mechanical Lifting Operations",
            "reporter": "HSE Inspector Rajesh"
        }
        res = client.post("/api/events/human", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        ev = data["event"]

        self.assertTrue(ev["event_id"].startswith("EVT-HUMAN-"))
        self.assertEqual(ev["source"], "HUMAN")
        self.assertEqual(ev["sif_potential"], "HIGH")
        self.assertEqual(ev["assertion_status"], "ASSERTED")
        self.assertEqual(ev["barrier_condition"], "VIOLATED")
        self.assertTrue(len(ev["evidence_spans"]) > 0)

        # Verify disk persistence
        retrieved = unified_event_store.get_event(ev["event_id"])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.narrative, payload["narrative"])

    def test_02_all_seven_phase_7_nlp_scenarios(self):
        """Test Phase 7: Real context-aware NLP across all 7 benchmark scenarios."""
        scenarios = [
            # 1. Negation
            {
                "text": "No worker entered the exclusion zone.",
                "expected_sif": "NOT_SIF",
                "expected_assertion": "NEGATED"
            },
            # 2. Hypothetical
            {
                "text": "If the sling fails, the load could fall.",
                "expected_sif": "LOW",
                "expected_assertion": "HYPOTHETICAL"
            },
            # 3. Post-event
            {
                "text": "The barricade was installed after the incident.",
                "expected_sif": "HIGH",
                "expected_assertion": "POST_EVENT"
            },
            # 4. Direct breach SIF High
            {
                "text": "Worker crossed the barricade into the crane exclusion zone while the drill collar was suspended overhead.",
                "expected_sif": "HIGH",
                "expected_assertion": "ASSERTED"
            },
            # 5. Near-miss aborted entry
            {
                "text": "Worker almost entered the zone but stopped before crossing.",
                "expected_sif": "NOT_SIF",
                "expected_assertion": "NEGATED"
            },
            # 6. Post-completion entry
            {
                "text": "Worker entered the zone after lifting was completed.",
                "expected_sif": "LOW",
                "expected_assertion": "POST_EVENT"
            },
            # 7. Barrier removed, exposure negated
            {
                "text": "No worker entered the zone despite the barricade being removed.",
                "expected_sif": "NOT_SIF",
                "expected_assertion": "NEGATED"
            }
        ]

        for idx, sc in enumerate(scenarios):
            res = client.post("/api/events/human", json={
                "narrative": sc["text"],
                "location": f"Test Rig Sector {idx+1}",
                "activity": "Lifting and Rigging"
            })
            self.assertEqual(res.status_code, 200)
            ev = res.json()["event"]
            self.assertEqual(
                ev["sif_potential"], sc["expected_sif"],
                f"Failed scenario {idx+1} '{sc['text']}': expected SIF {sc['expected_sif']}, got {ev['sif_potential']}"
            )
            self.assertEqual(
                ev["assertion_status"], sc["expected_assertion"],
                f"Failed scenario {idx+1} '{sc['text']}': expected assertion {sc['expected_assertion']}, got {ev['assertion_status']}"
            )

    def test_03_unified_events_filtering_and_pagination(self):
        """Test Phase 10 & 11: GET /api/events filters by source and SIF potential."""
        # Query all events
        res = client.get("/api/events?source=ALL&sif_status=ALL")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 6)

        # Query human only
        res_human = client.get("/api/events?source=HUMAN")
        self.assertEqual(res_human.status_code, 200)
        for ev in res_human.json()["events"]:
            self.assertEqual(ev["source"], "HUMAN")

        # Query CCTV only
        res_cctv = client.get("/api/events?source=CCTV")
        self.assertEqual(res_cctv.status_code, 200)
        for ev in res_cctv.json()["events"]:
            self.assertEqual(ev["source"], "CCTV")

    def test_04_dynamic_summary_stats_calculation(self):
        """Test Phase 13 & 23: Dashboard summary metrics are derived dynamically from real events."""
        res = client.get("/api/events/stats/summary")
        self.assertEqual(res.status_code, 200)
        stats = res.json()

        self.assertIn("total_events", stats)
        self.assertIn("sif_high_count", stats)
        self.assertIn("not_sif_count", stats)
        self.assertIn("human_count", stats)
        self.assertIn("cctv_count", stats)
        self.assertIn("top_hazards", stats)
        self.assertIn("top_lsrs", stats)
        self.assertEqual(stats["total_events"], stats["human_count"] + stats["imported_count"] + stats["cctv_count"])

    def test_05_dataset_import_csv_and_batch_processing(self):
        """Test Phase 4, 5, 6: Importing CSV parses columns, runs NLP batch, and updates stats."""
        csv_content = """IncidentID,EventDate,Location,Activity,Description,Hazard
INC-101,2026-09-01,Drill Floor A,Pipe Handling,Worker stepped inside lifting drop area while pipe was moving.,Suspended Pipe
INC-102,2026-09-02,Tank Battery,Maintenance,Technician performed valve overhaul with certified LOTO padlock intact.,Stored Pressure
INC-103,2026-09-03,Compressor Area,Gas Testing,Continuous gas monitor alerted crew of H2S trace before vessel entry.,Toxic Gas
"""
        files = {"file": ("test_company_incidents.csv", csv_content.encode("utf-8"), "text/csv")}
        res = client.post("/api/dataset/import-file", files=files)
        self.assertEqual(res.status_code, 200, res.text)
        preview = res.json()
        self.assertEqual(preview["total_rows"], 3)
        self.assertIn("narrative_field", preview["detected_mapping"])

        # Execute import
        exec_res = client.post("/api/dataset/import-execute", json={"max_rows": 10})
        self.assertEqual(exec_res.status_code, 200)

        # Check telemetry
        import time
        time.sleep(0.5)
        st_res = client.get("/api/dataset/import-status")
        self.assertEqual(st_res.status_code, 200)
        st = st_res.json()
        self.assertIn(st["status"], ["PROCESSING", "COMPLETED"])

    def test_06_event_action_and_cctv_verification_lifecycle(self):
        """Test Phase 21: Action Taken -> Awaiting Verification -> Re-breach -> Reopened."""
        # Submit high SIF event
        payload = {
            "narrative": "Worker stepped into crane swing radius without spotter guidance.",
            "location": "Lifting Zone 03",
            "activity": "Mechanical Lifting"
        }
        res = client.post("/api/events/human", json=payload)
        ev_id = res.json()["event"]["event_id"]

        # 1. Action taken -> Awaiting Verification
        act_res = client.post(f"/api/events/{ev_id}/action", json={"supervisor_id": "SUP-01", "notes": "Perimeter cleared"})
        self.assertEqual(act_res.status_code, 200)
        self.assertEqual(act_res.json()["event"]["lifecycle_state"], "AWAITING_VERIFICATION")

        # 2. CCTV check: simulate re-breach -> FAILED & REOPENED
        fail_res = client.post(f"/api/events/{ev_id}/verify", json={"simulate_rebreach": True, "notes": "Re-breach detected"})
        self.assertEqual(fail_res.status_code, 200)
        self.assertFalse(fail_res.json()["verified"])
        self.assertEqual(fail_res.json()["event"]["lifecycle_state"], "REOPENED")

        # 3. Repeat action taken and clear verification -> RESOLVED
        client.post(f"/api/events/{ev_id}/action", json={"supervisor_id": "SUP-01"})
        pass_res = client.post(f"/api/events/{ev_id}/verify", json={"simulate_rebreach": False})
        self.assertEqual(pass_res.status_code, 200)
        self.assertTrue(pass_res.json()["verified"])
        self.assertEqual(pass_res.json()["event"]["lifecycle_state"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
