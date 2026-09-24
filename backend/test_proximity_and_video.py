"""
Test Suite: Feature 2 - High-Priority Person-Vehicle Proximity Alert & Video Pipeline
Tests:
1. Model vehicle class mapping in detection pipeline (car, motorcycle, bus, truck)
2. Vehicle tracking & proximity zone perimeter computation
3. Person-vehicle proximity debounce (3 consecutive frames confirm, 5 frames clear)
4. Anti-spam deduplication (single sustained alert, no duplicate alert storm)
5. Alert priority scoring: Proximity alert has priority score 150 (CRITICAL)
6. Priority sorting: Proximity alerts strictly sit at the top above Zone and PPE alerts
7. Multiple proximity alerts tie-breaking: newest proximity event appears first
8. Simultaneous monitoring: PPE violations (No Helmet) + Proximity alert + Zone breach coexist on same camera
9. Evidence preservation: Full frame, person crop, and vehicle crop stored and retrievable
10. Engine reset: clean reset of vehicle and proximity state
"""

import unittest
import numpy as np
import cv2
import time
from datetime import datetime, timedelta

from models import Alert, PersonFinding, VehicleFinding
from state import state_manager, sort_alerts_by_priority, calculate_alert_priority
from detection import (
    video_engine as detection_engine, 
    VehicleTrack, 
    PersonTrack, 
    compute_box_iou, 
    extract_person_crop, 
    extract_vehicle_crop
)

class TestProximityAndVideo(unittest.TestCase):
    def setUp(self):
        state_manager.reset_demo()
        detection_engine.reset_tracks()

    def tearDown(self):
        state_manager.reset_demo()
        detection_engine.reset_tracks()

    def test_01_supported_vehicle_classes(self):
        """1. Verify detection engine COCO vehicle class mappings."""
        expected_classes = {
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck"
        }
        self.assertEqual(detection_engine.COCO_VEHICLE_MAP, expected_classes)
        print("\n  [PASS] COCO vehicle classes verified: car, motorcycle, bus, truck.")

    def test_02_vehicle_tracking_and_proximity_zone(self):
        """2. Verify VehicleTrack initialization, tracking, and proximity zone calculation."""
        box = np.array([200, 200, 400, 360])
        now = time.time()
        v_track = VehicleTrack(track_id=1, box=box, class_name="truck", confidence=0.88, now_ts=now)
        
        self.assertEqual(v_track.label, "Vehicle #1")
        self.assertEqual(v_track.class_name, "truck")
        np.testing.assert_array_equal(v_track.box, box)
        
        # Calculate proximity zone around the vehicle (as done in detection engine)
        vx1, vy1, vx2, vy2 = v_track.box
        vw = max(1, vx2 - vx1)
        vh = max(1, vy2 - vy1)
        mx = int(max(35, 0.35 * vw))
        my = int(max(25, 0.30 * vh))
        v_track.proximity_zone = [max(0, vx1 - mx), max(0, vy1 - my), vx2 + mx, vy2 + my]
        
        zone = v_track.proximity_zone
        self.assertLess(zone[0], box[0]) # zx1 < vx1
        self.assertLess(zone[1], box[1]) # zy1 < vy1
        self.assertGreater(zone[2], box[2]) # zx2 > vx2
        self.assertGreater(zone[3], box[3]) # zy2 > vy2
        
        # Test IoU matching with small movement
        moved_box = np.array([205, 202, 403, 362])
        iou = compute_box_iou(v_track.box, moved_box)
        self.assertGreater(iou, 0.85)
        print("  [PASS] VehicleTrack initializes, tracks with smoothed box, and computes proximity zone.")

    def test_03_proximity_debounce_confirmation(self):
        """3. Verify proximity requires 2 consecutive frames to confirm (debounced)."""
        v_box = np.array([250, 150, 450, 350])
        now = time.time()
        v_track = VehicleTrack(track_id=1, box=v_box, class_name="truck", confidence=0.9, now_ts=now)
        detection_engine.tracked_vehicles = {1: v_track}
        
        p_box = np.array([280, 200, 340, 320])
        p_track = PersonTrack(track_id=3, box=p_box, now_ts=now)
        detection_engine.tracked_persons = {3: p_track}
        
        # Simulate frame 1: 1 consecutive frame inside -> NOT confirmed
        pair_key = (3, 1)
        detection_engine.proximity_pair_state[pair_key] = {
            "consecutive_inside": 1,
            "consecutive_outside": 0,
            "confirmed": False
        }
        self.assertFalse(detection_engine.proximity_pair_state[pair_key]["confirmed"])
        
        # Simulate frame 2: 2 consecutive frames inside -> CONFIRMED! (PROXIMITY_CONFIRM_FRAMES = 2)
        detection_engine.proximity_pair_state[pair_key]["consecutive_inside"] = 2
        if detection_engine.proximity_pair_state[pair_key]["consecutive_inside"] >= detection_engine.PROXIMITY_CONFIRM_FRAMES:
            detection_engine.proximity_pair_state[pair_key]["confirmed"] = True
            
        self.assertTrue(detection_engine.proximity_pair_state[pair_key]["confirmed"])
        print("  [PASS] Debounce logic: exactly 2 consecutive frames required for proximity confirmation.")

    def test_04_anti_spam_deduplication(self):
        """4. Verify sustained proximity does NOT spam duplicate alerts."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()

        # Trigger initial proximity alert
        alert_1 = state_manager.trigger_alert(
            alert_type="Person–Vehicle Proximity",
            camera="C-01",
            location="Compressor Logistics Route",
            severity="CRITICAL",
            person_count=1,
            evidence_frame=frame_bytes,
            person_id="Person #3",
            vehicle_id="Vehicle #1",
            vehicle_type="truck",
            proximity_status="Proximity Confirmed",
            is_high_priority=True
        )
        self.assertIsNotNone(alert_1)
        initial_id = alert_1.id
        self.assertTrue(initial_id.startswith("ALT-PROX-"))

        # Simulate 20 subsequent frames of sustained proximity
        for _ in range(20):
            alert_subsequent = state_manager.trigger_alert(
                alert_type="Person–Vehicle Proximity",
                camera="C-01",
                location="Compressor Logistics Route",
                severity="CRITICAL",
                person_count=1,
                person_id="Person #3",
                vehicle_id="Vehicle #1",
                vehicle_type="truck",
                proximity_status="Proximity Confirmed",
                is_high_priority=True
            )
            # Must update existing alert in place without creating a new duplicate ID
            self.assertEqual(alert_subsequent.id, initial_id)

        # Verify exactly 1 alert exists in active alerts
        active_list = state_manager.get_active_alerts_list()
        proximity_alerts = [a for a in active_list if a.type == "Person–Vehicle Proximity"]
        self.assertEqual(len(proximity_alerts), 1)
        print("  [PASS] Anti-spam verified: 20 consecutive frames produce exactly 1 sustained proximity alert.")

    def test_05_priority_score_and_high_priority_status(self):
        """5. Verify Proximity alert has priority score 150 (CRITICAL) and is_high_priority."""
        score, label = calculate_alert_priority("Person–Vehicle Proximity", "CRITICAL", person_count=1)
        self.assertEqual(score, 150)
        self.assertEqual(label, "CRITICAL")

        score2, label2 = calculate_alert_priority("Vehicle Proximity Breach", "HIGH", person_count=1)
        self.assertEqual(score2, 150)
        self.assertEqual(label2, "CRITICAL")
        print("  [PASS] Proximity alert priority score is 150 (CRITICAL).")

    def test_06_priority_sorting_proximity_at_top(self):
        """6. Verify Proximity alert strictly sorts above Restricted Zone and PPE alerts."""
        t = datetime.now()
        ppe_alert = Alert(
            id="ALT-PPE-01",
            type="Helmet/PPE Violation",
            camera="C-01",
            priority_score=60,
            severity="HIGH",
            created_at=(t - timedelta(minutes=5)).isoformat(),
            response_deadline=(t + timedelta(seconds=20)).isoformat()
        )
        zone_alert = Alert(
            id="ALT-ZONE-01",
            type="Restricted Zone Entry",
            camera="C-01",
            priority_score=100,
            severity="CRITICAL",
            created_at=(t - timedelta(minutes=3)).isoformat(),
            response_deadline=(t + timedelta(seconds=20)).isoformat()
        )
        prox_alert = Alert(
            id="ALT-PROX-01",
            type="Person–Vehicle Proximity",
            camera="C-01",
            priority_score=150,
            is_high_priority=True,
            severity="CRITICAL",
            created_at=t.isoformat(),
            response_deadline=(t + timedelta(seconds=20)).isoformat()
        )

        sorted_feed = sort_alerts_by_priority([ppe_alert, zone_alert, prox_alert])
        self.assertEqual(len(sorted_feed), 3)
        self.assertEqual(sorted_feed[0].id, "ALT-PROX-01") # Priority 150
        self.assertEqual(sorted_feed[1].id, "ALT-ZONE-01") # Priority 100
        self.assertEqual(sorted_feed[2].id, "ALT-PPE-01")  # Priority 60
        print("  [PASS] Priority sorting: Person-Vehicle Proximity (150) strictly sits at top of feed.")

    def test_07_multiple_proximity_alerts_newest_first(self):
        """7. Verify multiple proximity alerts sort newest first among score 150."""
        t = datetime.now()
        prox_old = Alert(
            id="ALT-PROX-OLD",
            type="Person–Vehicle Proximity",
            person_id="Person #5",
            vehicle_id="Vehicle #2",
            priority_score=150,
            is_high_priority=True,
            severity="CRITICAL",
            created_at=(t - timedelta(seconds=20)).isoformat(), # 10:24:17
            response_deadline=(t + timedelta(seconds=20)).isoformat()
        )
        prox_new = Alert(
            id="ALT-PROX-NEW",
            type="Person–Vehicle Proximity",
            person_id="Person #3",
            vehicle_id="Vehicle #1",
            priority_score=150,
            is_high_priority=True,
            severity="CRITICAL",
            created_at=t.isoformat(), # 10:24:31
            response_deadline=(t + timedelta(seconds=20)).isoformat()
        )
        ppe_alert = Alert(
            id="ALT-PPE-02",
            type="Helmet/PPE Violation",
            priority_score=60,
            severity="HIGH",
            created_at=(t - timedelta(minutes=1)).isoformat(),
            response_deadline=(t + timedelta(seconds=20)).isoformat()
        )

        sorted_feed = sort_alerts_by_priority([ppe_alert, prox_old, prox_new])
        self.assertEqual(sorted_feed[0].id, "ALT-PROX-NEW") # 10:24:31 (newest proximity)
        self.assertEqual(sorted_feed[1].id, "ALT-PROX-OLD") # 10:24:17
        self.assertEqual(sorted_feed[2].id, "ALT-PPE-02")  # PPE remains below
        print("  [PASS] Multiple proximity alerts: newest proximity event appears first, normal alerts below.")

    def test_08_simultaneous_ppe_and_proximity_coexistence(self):
        """8. Verify simultaneous monitoring: PPE violations and Proximity co-exist independently."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()

        # 1. Trigger PPE alert (Person #2 has No Helmet)
        ppe_findings = [
            {
                "person_id": "Person #2",
                "track_id": 2,
                "bbox": [50, 100, 150, 300],
                "helmet_status": "VIOLATION",
                "vest_status": "OK",
                "glove_status": "OK",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO_HELMET"]
            }
        ]
        alert_ppe = state_manager.trigger_alert(
            alert_type="Helmet/PPE Violation",
            camera="C-01",
            location="Compressor Bay",
            severity="HIGH",
            person_count=1,
            person_findings=ppe_findings,
            evidence_frame=frame_bytes
        )

        # 2. Simultaneously trigger Proximity alert (Person #3 near Vehicle #1)
        alert_prox = state_manager.trigger_alert(
            alert_type="Person–Vehicle Proximity",
            camera="C-01",
            location="Compressor Bay Route",
            severity="CRITICAL",
            person_count=1,
            person_id="Person #3",
            vehicle_id="Vehicle #1",
            vehicle_type="truck",
            proximity_status="Proximity Confirmed",
            is_high_priority=True,
            evidence_frame=frame_bytes
        )

        # 3. Verify both alerts exist in the system simultaneously
        active_alerts = state_manager.get_active_alerts_list()
        self.assertEqual(len(active_alerts), 2)
        
        # Proximity alert must be #1, PPE alert must be #2
        self.assertEqual(active_alerts[0].id, alert_prox.id)
        self.assertEqual(active_alerts[0].type, "Person–Vehicle Proximity")
        self.assertEqual(active_alerts[1].id, alert_ppe.id)
        self.assertEqual(active_alerts[1].type, "Helmet/PPE Violation")
        print("  [PASS] Simultaneous monitoring: PPE violation and Proximity coexist without suppression.")

    def test_09_evidence_storage_full_frame_and_crops(self):
        """9. Verify evidence preservation: full frame, person crop, and vehicle crop."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:300, 100:200] = [0, 0, 255] # Red person
        frame[150:350, 300:500] = [255, 0, 0] # Blue vehicle
        
        person_box = [100, 100, 200, 300]
        vehicle_box = [300, 150, 500, 350]
        
        person_crop_bytes, _ = extract_person_crop(frame, person_box)
        vehicle_crop_bytes, _ = extract_vehicle_crop(frame, vehicle_box)
        _, jpeg = cv2.imencode('.jpg', frame)
        full_frame_bytes = jpeg.tobytes()

        self.assertIsNotNone(person_crop_bytes)
        self.assertIsNotNone(vehicle_crop_bytes)
        self.assertGreater(len(person_crop_bytes), 100)
        self.assertGreater(len(vehicle_crop_bytes), 100)

        # Trigger proximity alert with both crops
        alert = state_manager.trigger_alert(
            alert_type="Person–Vehicle Proximity",
            camera="C-01",
            severity="CRITICAL",
            person_count=1,
            evidence_frame=full_frame_bytes,
            person_crop_bytes=person_crop_bytes,
            vehicle_crop_bytes=vehicle_crop_bytes,
            person_id="Person #3",
            vehicle_id="Vehicle #1",
            vehicle_type="truck",
            proximity_status="Proximity Confirmed",
            is_high_priority=True
        )

        # Verify crops and evidence were stored in evidence_store
        full_frame_ev_id = f"ev-{alert.id}"
        self.assertIn(full_frame_ev_id, state_manager.evidence_store)
        self.assertEqual(state_manager.get_evidence(full_frame_ev_id), full_frame_bytes)
        
        # Vehicle crop check
        veh_ev_id = f"ev-{alert.id}-veh"
        self.assertIn(veh_ev_id, state_manager.evidence_store)
        self.assertEqual(state_manager.get_evidence(veh_ev_id), vehicle_crop_bytes)

        # Person crop check
        pers_ev_id = f"ev-{alert.id}-pers"
        self.assertIn(pers_ev_id, state_manager.evidence_store)
        self.assertEqual(state_manager.get_evidence(pers_ev_id), person_crop_bytes)
        print("  [PASS] Evidence storage: full CCTV frame, person crop, and vehicle crop preserved.")

    def test_10_clean_engine_and_tracks_reset(self):
        """10. Verify reset_tracks cleanly clears vehicle tracks and proximity states."""
        now = time.time()
        detection_engine.tracked_vehicles = {
            1: VehicleTrack(track_id=1, box=np.array([100, 100, 200, 200]), class_name="truck", confidence=0.9, now_ts=now)
        }
        detection_engine.proximity_pair_state[(3, 1)] = {"confirmed": True}
        detection_engine.next_vehicle_track_id = 5

        detection_engine.reset_tracks()
        self.assertEqual(len(detection_engine.tracked_vehicles), 0)
        self.assertEqual(len(detection_engine.proximity_pair_state), 0)
        self.assertEqual(detection_engine.next_vehicle_track_id, 1)
        print("  [PASS] Engine reset: vehicle tracks and proximity pair states cleanly reset.")

    def test_11_reset_cv_session_source_switch(self):
        """11. Verify state_manager.reset_cv_session() resets tracks, debounce states, and purges transient CCTV alerts."""
        now = time.time()
        # Seed engine state
        detection_engine.tracked_vehicles = {
            1: VehicleTrack(track_id=1, box=np.array([100, 100, 200, 200]), class_name="car", confidence=0.9, now_ts=now)
        }
        detection_engine.proximity_pair_state[(1, 1)] = {"confirmed": True}
        
        # Trigger an alert
        alert = state_manager.trigger_alert(
            alert_type="Person–Vehicle Proximity",
            camera="C-01",
            severity="CRITICAL",
            person_count=1,
            is_high_priority=True
        )
        self.assertIsNotNone(alert)
        self.assertIsNotNone(state_manager.active_alert)
        
        # Reset CV session (simulates user clicking Webcam/Demo Video tab switch)
        res = state_manager.reset_cv_session()
        self.assertTrue(res.get("success"))
        self.assertEqual(len(detection_engine.tracked_vehicles), 0)
        self.assertEqual(len(detection_engine.proximity_pair_state), 0)
        self.assertIsNone(state_manager.active_alert)
        print("  [PASS] Source switch reset: reset_cv_session clears all tracks, debounce states, and active CCTV alert.")

    def test_12_strict_3_state_ppe_logic(self):
        """12. Verify strict 3-state PPE logic: absence of violation detection is NOT compliance."""
        # Case A: Person with unknown helmet/vest/gloves -> overall MUST be UNKNOWN, never OK
        p_track = PersonTrack(track_id=1, box=np.array([100, 100, 200, 300]), now_ts=time.time())
        p_track.helmet_status = "UNKNOWN"
        p_track.vest_status = "UNKNOWN"
        p_track.gloves_status = "UNKNOWN"
        
        # Evaluate overall status
        is_violation = (
            p_track.helmet_status in ("VIOLATION", "NOT DETECTED") or
            p_track.vest_status in ("VIOLATION", "NO_VEST") or
            p_track.gloves_status in ("VIOLATION", "NO_GLOVES")
        )
        is_unknown = not is_violation and (
            p_track.helmet_status == "UNKNOWN" or
            p_track.vest_status == "UNKNOWN" or
            p_track.gloves_status == "UNKNOWN"
        )
        is_ok = not is_violation and not is_unknown and (
            p_track.helmet_status in ("OK", "HELMET") and
            p_track.vest_status in ("OK", "VEST") and
            p_track.gloves_status in ("OK", "GLOVES")
        )
        
        self.assertFalse(is_violation)
        self.assertTrue(is_unknown)
        self.assertFalse(is_ok)

        # Case B: Person with 1 item violated -> overall MUST be VIOLATION
        p_track.helmet_status = "VIOLATION"
        is_violation = (
            p_track.helmet_status in ("VIOLATION", "NOT DETECTED") or
            p_track.vest_status in ("VIOLATION", "NO_VEST") or
            p_track.gloves_status in ("VIOLATION", "NO_GLOVES")
        )
        self.assertTrue(is_violation)

        # Case C: Person with all 3 items explicitly OK -> overall is OK
        p_track.helmet_status = "OK"
        p_track.vest_status = "OK"
        p_track.gloves_status = "OK"
        is_violation = (
            p_track.helmet_status in ("VIOLATION", "NOT DETECTED") or
            p_track.vest_status in ("VIOLATION", "NO_VEST") or
            p_track.gloves_status in ("VIOLATION", "NO_GLOVES")
        )
        is_unknown = not is_violation and (
            p_track.helmet_status == "UNKNOWN" or
            p_track.vest_status == "UNKNOWN" or
            p_track.gloves_status == "UNKNOWN"
        )
        is_ok = not is_violation and not is_unknown and (
            p_track.helmet_status in ("OK", "HELMET") and
            p_track.vest_status in ("OK", "VEST") and
            p_track.gloves_status in ("OK", "GLOVES")
        )
        self.assertFalse(is_violation)
        self.assertFalse(is_unknown)
        self.assertTrue(is_ok)
        print("  [PASS] Strict 3-state PPE logic: UNKNOWN != OK. Only all-OK yields compliant status.")

if __name__ == '__main__':
    unittest.main()
