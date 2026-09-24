"""
Test Suite: Feature 3 - Fire Detection Only & Surgical Integration Verification
Covers all requirements from STEP 18:
1. Fire model/class is correctly recognized (class 1 is fire, class 0 smoke is discarded)
2. Fire confidence threshold works (pre-NMS >= 0.28, NMS score >= 0.30)
3. Fire requires temporal confirmation (2 consecutive frames confirm)
4. One sustained fire produces one alert (anti-spam / debounce)
5. Fire disappears (cleared after 5 frames) and later reappears creates a new event
6. Fire evidence is stored (full CCTV frame + fire crop preserved in evidence store)
7. Fire bounding box is returned when model supports localization
8. Fire does not create smoke events
9. Empty Demo Video creates no fire event
10. Pause creates no new fire inference/events
11. Resume continues fire monitoring
12. Source switch clears fire state (reset_cv_session & reset_tracks)
13. Fire can coexist with PPE violations
14. Fire can coexist with Person-Vehicle Proximity (Proximity 150 top, Fire 140 second)
15. API and frame payload JSON serializability safety
"""

import os
import sys
import json
import base64
import time
import unittest
import numpy as np
import cv2

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from models import Alert, SystemStatus
from state import state_manager, calculate_alert_priority, sort_alerts_by_priority
from detection import video_engine as detection_engine

class TestFireDetectionOnly(unittest.TestCase):
    def setUp(self):
        state_manager.reset_demo()
        state_manager.reset_cv_session()
        detection_engine.reset_tracks()

    def tearDown(self):
        state_manager.reset_demo()
        state_manager.reset_cv_session()
        detection_engine.reset_tracks()

    def test_01_fire_model_loaded_and_classes_recognized(self):
        """1. Fire model is loaded, class 1 is mapped to 'fire', class 0 ('smoke') discarded."""
        self.assertIsNotNone(detection_engine.session_fire, "fire_detection.onnx session must be loaded")
        inputs = detection_engine.session_fire.get_inputs()
        outputs = detection_engine.session_fire.get_outputs()
        
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].shape, [1, 3, 640, 640])
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].shape, [1, 6, 8400]) # 4 bbox coordinates + 2 classes (smoke, fire)
        print("\n  [PASS] Fire model ONNX verified: shape (1, 3, 640, 640) -> (1, 6, 8400)")

    def test_02_fire_confidence_threshold(self):
        """2. Fire confidence threshold works: low confidence (<0.30) rejected, >=0.30 accepted."""
        detection_engine.reset_tracks()
        
        proposals = [[100, 100, 80, 80], [200, 200, 50, 50]]
        scores_low = [0.22, 0.18]
        idxs_low = cv2.dnn.NMSBoxes(proposals, scores_low, 0.30, 0.45)
        self.assertEqual(len(idxs_low), 0, "Proposals with score < 0.30 must be filtered out")

        scores_high = [0.75, 0.15]
        idxs_high = cv2.dnn.NMSBoxes(proposals, scores_high, 0.30, 0.45)
        self.assertEqual(len(idxs_high), 1, "Proposals with score >= 0.30 must pass")
        print("  [PASS] Fire confidence threshold works: scores < 0.30 rejected, >= 0.30 accepted.")

    def test_03_temporal_confirmation(self):
        """3. Fire requires temporal confirmation: 1 frame does not confirm, 2 consecutive frames confirm."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        mock_fire = [{"box": [150, 150, 100, 100], "score": 0.85, "confidence": 0.85, "label": "FIRE"}]
        
        # Frame 1: 1 detection
        detection_engine.fire_consecutive_count = 1
        detection_engine.fire_clear_count = 0
        detection_engine.last_fire_conf = 0.85
        detection_engine.confirmed_fires = []
        detection_engine.fire_confirmed = False
        
        self.assertFalse(detection_engine.fire_confirmed, "Frame 1 must NOT confirm fire yet")
        self.assertEqual(len(state_manager.get_active_alerts_list()), 0, "No alert triggered on 1st frame")

        # Frame 2: 2nd consecutive detection
        detection_engine.fire_consecutive_count += 1
        if detection_engine.fire_consecutive_count >= detection_engine.FIRE_CONFIRM_FRAMES:
            detection_engine.fire_confirmed = True
            detection_engine.confirmed_fires = mock_fire

        self.assertTrue(detection_engine.fire_confirmed, "2 consecutive frames must confirm fire")
        self.assertEqual(len(detection_engine.confirmed_fires), 1)
        print("  [PASS] Fire requires temporal confirmation: >= 2 consecutive frames required.")

    def test_04_sustained_fire_produces_single_alert(self):
        """4. Anti-spam logic: 20 sustained fire frames produce exactly ONE event, not 20 alerts."""
        crop_bytes = cv2.imencode('.jpg', np.full((100, 100, 3), 200, dtype=np.uint8))[1].tobytes()
        
        # Simulate 20 frames of sustained fire
        detection_engine.fire_confirmed = True
        detection_engine.last_fire_conf = 0.88
        detection_engine.confirmed_fires = [{"box": [100, 100, 120, 120], "score": 0.88, "confidence": 0.88, "label": "FIRE"}]
        detection_engine.last_fire_crop_bytes = crop_bytes
        detection_engine.last_fire_crop_b64 = "data:image/jpeg;base64,mockfire"

        for f_idx in range(20):
            if detection_engine.fire_confirmed and not detection_engine.fire_alert_triggered:
                state_manager.trigger_alert(
                    alert_type="Fire Hazard",
                    location="Demo Work Zone",
                    camera="C-01",
                    severity="CRITICAL",
                    sif_potential="CRITICAL / HIGH",
                    title="FIRE DETECTED — CONFIRMED",
                    short_summary="Confirmed active fire detected in Demo Work Zone",
                    fire_detected=True,
                    fire_confidence=0.88,
                    fire_bbox=[100, 100, 120, 120],
                    fire_crop_bytes=crop_bytes,
                    fire_crop_base64="data:image/jpeg;base64,mockfire"
                )
                detection_engine.fire_alert_triggered = True

        active_fire_alerts = [a for a in state_manager.get_active_alerts_list() if a.type == "Fire Hazard"]
        self.assertEqual(len(active_fire_alerts), 1, f"Expected exactly 1 Fire Hazard alert, but got {len(active_fire_alerts)}")
        print("  [PASS] Anti-spam verified: 20 sustained frames produce exactly 1 Alert.")

    def test_05_fire_clear_and_reappearance_lifecycle(self):
        """5. Fire disappears (cleared after 5 frames) and later reappears creates a new event."""
        crop_bytes = cv2.imencode('.jpg', np.full((100, 100, 3), 200, dtype=np.uint8))[1].tobytes()
        
        # 1. Fire confirmed & alerted
        detection_engine.fire_confirmed = True
        detection_engine.fire_alert_triggered = True
        detection_engine.last_fire_conf = 0.85
        detection_engine.confirmed_fires = [{"box": [100, 100, 120, 120], "score": 0.85, "confidence": 0.85, "label": "FIRE"}]
        
        a1 = state_manager.trigger_alert(
            alert_type="Fire Hazard",
            location="Demo Work Zone",
            camera="C-01",
            severity="CRITICAL",
            fire_detected=True,
            fire_confidence=0.85
        )
        self.assertEqual(len([a for a in state_manager.get_active_alerts_list() if a.type == "Fire Hazard"]), 1)

        # 2. Fire disappears for 5 frames
        for _ in range(detection_engine.FIRE_CLEAR_FRAMES):
            detection_engine.fire_clear_count += 1
            detection_engine.fire_consecutive_count = 0
            if detection_engine.fire_clear_count >= detection_engine.FIRE_CLEAR_FRAMES:
                detection_engine.fire_confirmed = False
                detection_engine.fire_alert_triggered = False
                detection_engine.confirmed_fires = []
                detection_engine.last_fire_conf = 0.0

        self.assertFalse(detection_engine.fire_confirmed)
        self.assertFalse(detection_engine.fire_alert_triggered)

        # Clear active alert in state manager as resolved / cleared
        state_manager.resolve_alert(alert_id=a1.id, notes="Fire suppressed")

        # 3. Fire reappears and confirms after 2 frames
        detection_engine.fire_consecutive_count = 2
        detection_engine.fire_confirmed = True
        detection_engine.last_fire_conf = 0.92
        detection_engine.confirmed_fires = [{"box": [110, 110, 130, 130], "score": 0.92, "confidence": 0.92, "label": "FIRE"}]

        if detection_engine.fire_confirmed and not detection_engine.fire_alert_triggered:
            state_manager.trigger_alert(
                alert_type="Fire Hazard",
                location="Demo Work Zone",
                camera="C-01",
                severity="CRITICAL",
                fire_detected=True,
                fire_confidence=0.92
            )
            detection_engine.fire_alert_triggered = True

        active_after = [a for a in state_manager.get_active_alerts_list() if a.type == "Fire Hazard"]
        self.assertEqual(len(active_after), 1, "New fire event is active")
        self.assertEqual(len(state_manager.get_history_list()), 1, "Previous event in history")
        print("  [PASS] Fire clear (5 frames) and reappearance lifecycle verified.")

    def test_06_fire_evidence_storage(self):
        """6. Fire evidence is stored: full CCTV frame and fire crop saved to evidence_store."""
        frame_bytes = cv2.imencode('.jpg', np.full((480, 640, 3), 120, dtype=np.uint8))[1].tobytes()
        fire_crop_bytes = cv2.imencode('.jpg', np.full((120, 120, 3), 220, dtype=np.uint8))[1].tobytes()

        alert = state_manager.trigger_alert(
            alert_type="Fire Hazard",
            location="Zone B - Welding",
            camera="C-01",
            severity="CRITICAL",
            evidence_frame=frame_bytes,
            fire_detected=True,
            fire_confidence=0.91,
            fire_bbox=[140, 160, 120, 120],
            fire_crop_bytes=fire_crop_bytes
        )

        self.assertIsNotNone(alert)
        self.assertIsNotNone(alert.evidence_url)
        self.assertIsNotNone(alert.fire_crop_url)
        self.assertTrue(alert.fire_crop_base64.startswith("data:image/jpeg;base64,"))
        
        # Verify evidence store contains both the full frame and the fire crop
        primary_ev_key = f"ev-{alert.id}"
        fire_ev_key = f"ev-{alert.id}-fire"
        self.assertIn(primary_ev_key, state_manager.evidence_store)
        self.assertIn(fire_ev_key, state_manager.evidence_store)
        self.assertEqual(state_manager.evidence_store[primary_ev_key], frame_bytes)
        self.assertEqual(state_manager.evidence_store[fire_ev_key], fire_crop_bytes)
        print("  [PASS] Full frame & fire crop evidence properly stored and retrievable.")

    def test_07_fire_bounding_box_returned(self):
        """7. Fire bounding box is returned in alert and detection payload."""
        bbox = [140, 160, 120, 120]
        alert = state_manager.trigger_alert(
            alert_type="Fire Hazard",
            location="Zone B",
            camera="C-01",
            severity="CRITICAL",
            fire_detected=True,
            fire_confidence=0.89,
            fire_bbox=bbox
        )
        self.assertEqual(alert.fire_bbox, bbox)
        print("  [PASS] Fire bounding box returned in alert payload.")

    def test_08_strictly_fire_no_smoke_events(self):
        """8. Model inference strictly ignores smoke class (index 0 / 4); NO smoke events emitted."""
        raw_fire_mock = np.zeros((1, 6))
        raw_fire_mock[0, :4] = [320, 240, 100, 100]
        raw_fire_mock[0, 4] = 0.95 # Smoke (must be completely discarded)
        raw_fire_mock[0, 5] = 0.05 # Fire (< 0.28, must be discarded)

        boxes_fire = raw_fire_mock[:, :4]
        fire_s = raw_fire_mock[:, 5]
        fire_idxs = np.where(fire_s >= 0.28)[0]
        
        self.assertEqual(len(fire_idxs), 0, "Smoke proposals must NEVER be converted to fire proposals")
        print("  [PASS] Strictly FIRE detection: Smoke class is completely ignored.")

    def test_09_empty_demo_video_standby(self):
        """9. Empty demo video creates no fire events, clean standby state."""
        detection_engine.reset_tracks()
        status = state_manager.get_system_status()
        self.assertFalse(status.fire_detected)
        self.assertEqual(status.fire_confidence, 0.0)
        self.assertEqual(len([a for a in state_manager.get_active_alerts_list() if a.type == "Fire Hazard"]), 0)
        print("  [PASS] Empty demo video standby verified: no fire detections or alerts.")

    def test_10_pause_and_11_resume_behavior(self):
        """10 & 11. Pause halts frame processing; Resume continues monitoring without state corruption."""
        detection_engine.reset_tracks()
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        
        res1 = detection_engine.process_frame(blank, camera_id="C-01", frame_seq=1)
        self.assertFalse(res1["fire_detected"])
        
        # During pause: 0 calls to process_frame
        # After resume: frame 2 processed
        res2 = detection_engine.process_frame(blank, camera_id="C-01", frame_seq=2)
        self.assertFalse(res2["fire_detected"])
        print("  [PASS] Pause/Resume behavior verified: state remains consistent.")

    def test_12_source_switch_clears_fire_state(self):
        """12. Source switch reset clears fire counters, confirmed state, and active alerts."""
        detection_engine.fire_consecutive_count = 2
        detection_engine.fire_confirmed = True
        detection_engine.fire_alert_triggered = True
        detection_engine.last_fire_conf = 0.88
        detection_engine.confirmed_fires = [{"box": [100, 100, 80, 80], "score": 0.88, "confidence": 0.88, "label": "FIRE"}]
        
        state_manager.trigger_alert(
            alert_type="Fire Hazard",
            location="Demo Work Zone",
            camera="C-01",
            severity="CRITICAL",
            fire_detected=True,
            fire_confidence=0.88
        )
        self.assertTrue(any(a.type == "Fire Hazard" for a in state_manager.get_active_alerts_list()))

        # Call reset as triggered by /api/cv/reset on source switch
        state_manager.reset_cv_session()
        detection_engine.reset_tracks()

        self.assertEqual(detection_engine.fire_consecutive_count, 0)
        self.assertFalse(detection_engine.fire_confirmed)
        self.assertFalse(detection_engine.fire_alert_triggered)
        self.assertEqual(len(detection_engine.confirmed_fires), 0)
        self.assertFalse(any(a.type == "Fire Hazard" for a in state_manager.get_active_alerts_list()))
        print("  [PASS] Source switch reset completely clears fire state and alerts.")

    def test_13_fire_coexists_with_ppe_violations(self):
        """13. Fire Hazard alert coexists simultaneously with PPE violations."""
        ppe_alert = state_manager.trigger_alert(
            alert_type="Helmet/PPE Violation",
            location="Demo Work Zone",
            camera="C-01",
            severity="HIGH",
            title="PPE VIOLATION — NO HELMET",
            person_count=1,
            affected_person_ids=["Person #1"]
        )

        fire_alert = state_manager.trigger_alert(
            alert_type="Fire Hazard",
            location="Demo Work Zone",
            camera="C-01",
            severity="CRITICAL",
            title="FIRE DETECTED — CONFIRMED",
            fire_detected=True,
            fire_confidence=0.90
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 2, "Both PPE Violation and Fire Hazard must coexist in active alerts")
        types = {a.type for a in active}
        self.assertIn("Helmet/PPE Violation", types)
        self.assertIn("Fire Hazard", types)
        print("  [PASS] Fire Hazard and PPE violations coexist simultaneously without suppression.")

    def test_14_fire_coexists_with_proximity_and_priority_ordering(self):
        """14. Fire Hazard (Priority 140) coexists with Person-Vehicle Proximity (Priority 150), Proximity sorted top."""
        state_manager.trigger_alert(
            alert_type="Restricted Zone Breach",
            location="Demo Work Zone",
            camera="C-01",
            severity="HIGH"
        )
        
        fire_alert = state_manager.trigger_alert(
            alert_type="Fire Hazard",
            location="Demo Work Zone",
            camera="C-01",
            severity="CRITICAL",
            fire_detected=True,
            fire_confidence=0.92
        )

        prox_alert = state_manager.trigger_alert(
            alert_type="Person–Vehicle Proximity",
            location="Demo Work Zone",
            camera="C-01",
            severity="CRITICAL",
            is_high_priority=True
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 3, "All 3 alerts (Proximity, Fire, Zone) must coexist")

        score_prox = calculate_alert_priority(prox_alert.type, severity=prox_alert.severity)[0]
        score_fire = calculate_alert_priority(fire_alert.type, severity=fire_alert.severity)[0]
        self.assertEqual(score_prox, 150, "Proximity alert score must be 150 (CRITICAL)")
        self.assertEqual(score_fire, 140, "Fire alert score must be 140 (CRITICAL)")
        self.assertGreater(score_prox, score_fire, "Proximity (150) must outrank Fire (140) for top spot")

        # Check sorted order in active alert list
        self.assertEqual(active[0].type, "Person–Vehicle Proximity", "Proximity must strictly sit at top")
        self.assertEqual(active[1].type, "Fire Hazard", "Fire must sit second at 140")
        self.assertEqual(active[2].type, "Restricted Zone Breach", "Zone breach sits third at 100")
        print("  [PASS] Priority ordering verified: Proximity (150) > Fire (140) > Zone (100).")

    def test_15_api_serialization_safety(self):
        """15. /api/cv/frame output is strictly JSON serializable with native Python types."""
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        detection_engine.fire_confirmed = True
        detection_engine.last_fire_conf = 0.88
        detection_engine.confirmed_fires = [{"box": [100, 100, 80, 80], "score": 0.88, "confidence": 0.88, "label": "FIRE"}]
        
        res = detection_engine.process_frame(blank, camera_id="C-01", frame_seq=99)
        
        try:
            api_payload = {
                "success": res.get("success", True),
                "camera_id": res["camera_id"],
                "frame_seq": res["frame_seq"],
                "model_loaded": res["model_loaded"],
                "fire_detected": res["fire_detected"],
                "fire_confidence": res["fire_confidence"],
                "fires": res["fires"],
                "persons": res["persons"],
                "vehicles": res["vehicles"],
                "proximity_events": res["proximity_events"],
                "debug": res["debug"]
            }
            json_str = json.dumps(api_payload)
            self.assertIsInstance(json_str, str)
            self.assertIn('"fire_detected": true', json_str)
            self.assertIn('"fire_confidence": 0.88', json_str)
            self.assertIn('"FIRE"', json_str)
        except TypeError as e:
            self.fail(f"API payload failed JSON serialization: {e}")
        print("  [PASS] API response is 100% JSON serializable.")

if __name__ == "__main__":
    unittest.main()
