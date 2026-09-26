"""
SHRAMRAKSHAK: Phase 5 Website & API Contract Regression Test Suite
SIH 2026 Problem Statement: SIH26165

Verifies frontend/backend API contracts across all 8 enterprise views:
1. OverviewView: /api/safety-memory/summary, /api/events/stats/summary
2. ReportsView: /api/events, /api/events/human
3. SafetyIntelligenceView: /api/events/stats/summary, /api/events
4. SafetyMemoryView: /api/safety-memory/patterns, /api/safety-memory/validate-pattern, /api/safety-memory/check-work-package
5. LiveSafetyView: /api/corroboration/scenarios, /api/corroboration/evaluate, /api/alerts
6. ActionsVerificationView: /api/alerts, /api/alerts/{id}/respond, /api/alerts/{id}/action, /api/alerts/{id}/verify, /api/alerts/{id}/cctv-verify
7. ImportDataView: /api/dataset/import-status
8. SettingsDemoView: /api/status, /api/analyze-raw, /api/qr
"""

import os
import sys
import unittest
from datetime import datetime

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
from fastapi.testclient import TestClient
from backend.main import app
from backend.models_canonical import (
    SafetyPattern,
    ReviewStatus,
    SafetyEvent,
    SIFStatus,
    BarrierState
)


class TestPhase5WebsiteRegression(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_view_1_overview_contract(self):
        """View 1: OverviewView API Contracts"""
        with isolated_test_environment(prefix="p5_overview_"):
            # GET /api/safety-memory/summary
            res_sm = self.client.get("/api/safety-memory/summary")
            self.assertEqual(res_sm.status_code, 200)
            data_sm = res_sm.json()
            self.assertIn("total_events", data_sm)
            self.assertIn("sif_events_count", data_sm)
            self.assertIn("pattern_count", data_sm)
            self.assertIn("patterns", data_sm)

            # GET /api/events/stats/summary
            res_ev = self.client.get("/api/events/stats/summary")
            self.assertEqual(res_ev.status_code, 200)
            data_ev = res_ev.json()
            self.assertIn("total_events", data_ev)
            self.assertIn("sif_potential_count", data_ev)
            self.assertIn("top_hazards", data_ev)

    def test_view_2_reports_contract(self):
        """View 2: ReportsView API Contracts"""
        with isolated_test_environment(prefix="p5_reports_"):
            # POST /api/events/human
            payload = {
                "narrative": "Worker stepped into the lifting zone without hard hat while crane was hoisting pipe.",
                "reporter_id": "REP-OIL-101",
                "site": "OIL Duliajan",
                "location": "Drilling Rig 04"
            }
            res_post = self.client.post("/api/events/human", json=payload)
            self.assertEqual(res_post.status_code, 200)
            data_post = res_post.json()
            self.assertTrue(data_post.get("success"))
            event_data = data_post["event"]
            self.assertIn("event_id", event_data)
            self.assertIn("assertion", event_data)
            self.assertIn("sif_status", event_data)
            self.assertIn("barrier", event_data)

            # GET /api/events
            res_get = self.client.get("/api/events?limit=20")
            self.assertEqual(res_get.status_code, 200)
            data_get = res_get.json()
            self.assertIn("events", data_get)
            self.assertIn("total", data_get)
            self.assertGreaterEqual(len(data_get["events"]), 1)

    def test_view_3_safety_intelligence_contract(self):
        """View 3: SafetyIntelligenceView API Contracts"""
        with isolated_test_environment(prefix="p5_intelligence_") as env:
            test_db = env["db"]
            # Seed an event
            evt = SafetyEvent(
                event_id="EVT-INTEL-01",
                activity="Mechanical Lifting Operations",
                energy="Gravitational Energy",
                exposure="Personnel under load",
                barrier=["EXCLUSION_ZONE"],
                barrier_state=[BarrierState.BYPASSED],
                sif_status=SIFStatus.SIF_POTENTIAL,
                narrative="Crane operator hoisted casing while rigger was inside."
            )
            test_db.save_event(evt)

            # GET /api/events/stats/summary
            res_stats = self.client.get("/api/events/stats/summary")
            self.assertEqual(res_stats.status_code, 200)
            data_stats = res_stats.json()
            self.assertIn("total_events", data_stats)
            self.assertIn("sif_potential_count", data_stats)
            self.assertIn("top_hazards", data_stats)
            self.assertIn("top_barriers", data_stats)

            # GET /api/events with filters
            res_filter = self.client.get("/api/events?sif_potential=SIF_POTENTIAL")
            self.assertEqual(res_filter.status_code, 200)
            data_filter = res_filter.json()
            self.assertIn("events", data_filter)

    def test_view_4_safety_memory_contract(self):
        """View 4: SafetyMemoryView API Contracts"""
        with isolated_test_environment(prefix="p5_memory_") as env:
            test_db = env["db"]
            # Seed pattern
            pattern_id = "PAT-MEM-DEMO-01"
            pat = SafetyPattern(
                pattern_id=pattern_id,
                title="Recurring Exclusion Zone Breach",
                activity="Mechanical Lifting Operations",
                energy="Gravitational Energy",
                exposure="Personnel in perimeter",
                barrier="EXCLUSION_ZONE",
                occurrence_count=3,
                duplicate_count=0,
                validation_status=ReviewStatus.CANDIDATE,
                operational_status="ACTIVE"
            )
            test_db.save_pattern(pat)

            # GET /api/safety-memory/patterns
            res_pats = self.client.get("/api/safety-memory/patterns")
            self.assertEqual(res_pats.status_code, 200)
            data_pats = res_pats.json()
            self.assertIn("patterns", data_pats)
            self.assertTrue(any(p["pattern_id"] == pattern_id for p in data_pats["patterns"]))

            # POST /api/safety-memory/validate-pattern
            val_payload = {
                "pattern_id": pattern_id,
                "decision": "CONFIRM",
                "reviewer": "HSE Lead (OIL)",
                "notes": "Validated recurring control breach"
            }
            res_val = self.client.post("/api/safety-memory/validate-pattern", json=val_payload)
            self.assertEqual(res_val.status_code, 200)
            data_val = res_val.json()
            self.assertEqual(data_val["pattern"]["validation_status"], "HSE_VALIDATED")

            # POST /api/safety-memory/check-work-package
            wp_payload = {
                "package_id": "WP-TEST-P5-01",
                "activity": "Mechanical Lifting Operations",
                "location": "Lifting Zone 03",
                "evidence": {
                    "PHYSICAL_PERIMETER_DEMARCATION": "Barricade tape installed",
                    "AUTHORIZED_ENTRANTS_PASSPORT": "Pass #1234",
                    "OBSERVABLE_CCTV_CLEAR_ZONE": True
                }
            }
            res_wp = self.client.post("/api/safety-memory/check-work-package", json=wp_payload)
            self.assertEqual(res_wp.status_code, 200)
            data_wp = res_wp.json()
            self.assertIn("status", data_wp)
            self.assertIn("findings", data_wp)

    def test_view_5_live_safety_contract(self):
        """View 5: LiveSafetyView API Contracts"""
        with isolated_test_environment(prefix="p5_live_"):
            # GET /api/corroboration/scenarios
            res_scen = self.client.get("/api/corroboration/scenarios")
            self.assertEqual(res_scen.status_code, 200)
            data_scen = res_scen.json()
            self.assertIn("scenarios", data_scen)
            self.assertGreaterEqual(len(data_scen["scenarios"]), 1)

            # POST /api/corroboration/evaluate with scenario_key
            res_eval = self.client.post("/api/corroboration/evaluate", json={"scenario_key": "lifting_exclusion_corroborated"})
            self.assertEqual(res_eval.status_code, 200)
            data_eval = res_eval.json()
            self.assertIn("status", data_eval)
            self.assertEqual(data_eval["status"], "CORROBORATED")

            # GET /api/alerts
            res_alerts = self.client.get("/api/alerts")
            self.assertEqual(res_alerts.status_code, 200)

    def test_view_6_actions_verification_contract(self):
        """View 6: ActionsVerificationView API Contracts"""
        with isolated_test_environment(prefix="p5_actions_"):
            # Trigger alert
            res_trigger = self.client.post("/api/alert/trigger", json={
                "type": "Restricted Zone Entry",
                "location": "Lifting Zone 03",
                "camera": "C-01",
                "severity": "CRITICAL"
            })
            self.assertEqual(res_trigger.status_code, 200)
            alert_id = res_trigger.json()["alert"]["id"]

            # POST /api/alerts/{id}/respond
            res_resp = self.client.post(f"/api/alerts/{alert_id}/respond", json={
                "supervisor_id": "SUP-OIL-01",
                "notes": "Responding to hold crane"
            })
            self.assertEqual(res_resp.status_code, 200)
            self.assertEqual(res_resp.json()["alert"]["status"], "RESPONDING")

            # POST /api/alerts/{id}/action
            res_act = self.client.post(f"/api/alerts/{alert_id}/action", json={
                "supervisor_id": "SUP-OIL-01",
                "action_taken": "Perimeter secured with barricades"
            })
            self.assertEqual(res_act.status_code, 200)
            self.assertEqual(res_act.json()["alert"]["verification_status"], "AWAITING_VERIFICATION")

            # POST /api/alerts/{id}/cctv-verify
            res_cctv = self.client.post(f"/api/alerts/{alert_id}/cctv-verify", json={
                "supervisor_id": "SUP-OIL-01",
                "simulate_rebreach": False
            })
            self.assertEqual(res_cctv.status_code, 200)
            self.assertTrue(res_cctv.json()["verified"])

    def test_view_7_import_data_contract(self):
        """View 7: ImportDataView API Contracts"""
        with isolated_test_environment(prefix="p5_import_"):
            # GET /api/dataset/import-status
            res_status = self.client.get("/api/dataset/import-status")
            self.assertEqual(res_status.status_code, 200)
            data_status = res_status.json()
            self.assertIn("status", data_status)
            self.assertIn("total_records", data_status)

    def test_view_8_settings_demo_contract(self):
        """View 8: SettingsDemoView API Contracts"""
        with isolated_test_environment(prefix="p5_settings_"):
            # GET /api/status
            res_stat = self.client.get("/api/status")
            self.assertEqual(res_stat.status_code, 200)
            data_stat = res_stat.json()
            self.assertIn("system_status", data_stat)

            # POST /api/analyze-raw
            res_raw = self.client.post("/api/analyze-raw", json={
                "text": "Worker slipped on mud near pump house without handrail."
            })
            self.assertEqual(res_raw.status_code, 200)
            data_raw = res_raw.json()
            self.assertIn("assertion_status", data_raw)
            self.assertIn("sif_potential", data_raw)

            # GET /api/qr
            res_qr = self.client.get("/api/qr")
            self.assertEqual(res_qr.status_code, 200)
            self.assertIn("qr_base64", res_qr.json())


if __name__ == "__main__":
    unittest.main()
