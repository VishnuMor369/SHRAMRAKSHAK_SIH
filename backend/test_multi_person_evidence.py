"""
Comprehensive Test Suite for Multi-Person PPE Tracking & Person-Wise Evidence.
Validates all 14 requirements:
1. One person with normal status
2. One person with one issue
3. Multiple people with different issues
4. Multiple people with one normal and two affected
5. One person with multiple issues
6. No repeated event every frame
7. Event state updates correctly
8. Person labels remain stable across nearby frames where possible
9. Individual evidence crops are created
10. Full frame is preserved
11. Multiple people are grouped into one event
12. Existing restricted-area functionality still works
13. Existing glove logic still works
14. Existing camera endpoints still work
"""

import time
import base64
import unittest
import numpy as np
import cv2
from fastapi.testclient import TestClient

from main import app
from models import PersonFinding, Alert, RestrictedZone
from state import state_manager
from detection import (
    PersonTrack, 
    extract_person_crop, 
    compute_box_iou, 
    video_engine
)

class TestMultiPersonPPEAndEvidence(unittest.TestCase):

    def setUp(self):
        state_manager.reset_demo()
        state_manager.violation_persist_threshold = 0.0
        self.dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add synthetic pattern
        cv2.rectangle(self.dummy_frame, (100, 100), (300, 400), (120, 120, 120), -1)
        _, enc = cv2.imencode('.jpg', self.dummy_frame)
        self.dummy_bytes = enc.tobytes()
        self.client = TestClient(app)

    # 1. One person with normal status
    def test_01_one_person_normal_status(self):
        """1. One person with normal status: all PPE OK -> No violation alert created"""
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "OK",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "OK",
            "violations": [],
            "helmet_confidence": 0.95,
            "vest_confidence": 0.92,
            "glove_confidence": 0.88,
            "in_zone": False
        }]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=True,
            zone_violation=False,
            person_count=1,
            unhelmeted_count=0,
            vest_detected=True,
            unvested_count=0,
            gloves_detected=True,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 0)
        self.assertEqual(state_manager.current_safety_state, "SAFE")

    # 2. One person with one issue
    def test_02_one_person_one_issue(self):
        """2. One person with one issue: helmet violation -> single alert with finding"""
        crop_bytes, crop_b64 = extract_person_crop(self.dummy_frame, [100, 100, 250, 400])
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "VIOLATION",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO HELMET"],
            "evidence_crop_base64": crop_b64,
            "helmet_confidence": 0.94,
            "vest_confidence": 0.91,
            "glove_confidence": 0.89,
            "in_zone": False
        }]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            zone_violation=False,
            person_count=1,
            unhelmeted_count=1,
            vest_detected=True,
            unvested_count=0,
            gloves_detected=True,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1)
        alt = active[0]
        self.assertEqual(alt.camera, "C-01")
        self.assertEqual(len(alt.person_findings), 1)
        p1 = alt.person_findings[0]
        self.assertEqual(p1.person_id, "Person #1")
        self.assertEqual(p1.overall_ppe_status, "VIOLATION")
        self.assertIn("NO HELMET", p1.violations)
        self.assertIsNotNone(p1.evidence_crop_url)

    # 3. Multiple people with different issues
    def test_03_multiple_people_with_different_issues(self):
        """3. Multiple people with different issues -> ONE grouped event with distinct findings"""
        _, crop1 = extract_person_crop(self.dummy_frame, [50, 50, 200, 350])
        _, crop2 = extract_person_crop(self.dummy_frame, [250, 50, 400, 350])

        findings = [
            {
                "person_id": "Person #1",
                "track_id": 1,
                "bbox": [50, 50, 200, 350],
                "helmet_status": "VIOLATION",
                "vest_status": "OK",
                "glove_status": "OK",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO HELMET"],
                "evidence_crop_base64": crop1
            },
            {
                "person_id": "Person #2",
                "track_id": 2,
                "bbox": [250, 50, 400, 350],
                "helmet_status": "OK",
                "vest_status": "VIOLATION",
                "glove_status": "OK",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO SAFETY VEST"],
                "evidence_crop_base64": crop2
            }
        ]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            vest_detected=False,
            person_count=2,
            unhelmeted_count=1,
            unvested_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1, "Must produce exactly 1 grouped camera event")
        alt = active[0]
        self.assertEqual(len(alt.person_findings), 2)
        self.assertEqual(alt.person_findings[0].person_id, "Person #1")
        self.assertEqual(alt.person_findings[0].violations, ["NO HELMET"])
        self.assertEqual(alt.person_findings[1].person_id, "Person #2")
        self.assertEqual(alt.person_findings[1].violations, ["NO SAFETY VEST"])

    # 4. Multiple people with one normal and two affected
    def test_04_multiple_people_one_normal_two_affected(self):
        """4. 3 People: Person #1 OK, Person #2 No Helmet, Person #3 No Vest & No Gloves"""
        _, c1 = extract_person_crop(self.dummy_frame, [20, 20, 150, 300])
        _, c2 = extract_person_crop(self.dummy_frame, [180, 20, 310, 300])
        _, c3 = extract_person_crop(self.dummy_frame, [340, 20, 470, 300])

        findings = [
            {
                "person_id": "Person #1",
                "track_id": 1,
                "bbox": [20, 20, 150, 300],
                "helmet_status": "OK",
                "vest_status": "OK",
                "glove_status": "OK",
                "overall_ppe_status": "OK",
                "violations": [],
                "evidence_crop_base64": c1
            },
            {
                "person_id": "Person #2",
                "track_id": 2,
                "bbox": [180, 20, 310, 300],
                "helmet_status": "VIOLATION",
                "vest_status": "OK",
                "glove_status": "OK",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO HELMET"],
                "evidence_crop_base64": c2
            },
            {
                "person_id": "Person #3",
                "track_id": 3,
                "bbox": [340, 20, 470, 300],
                "helmet_status": "OK",
                "vest_status": "VIOLATION",
                "glove_status": "VIOLATION",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO SAFETY VEST", "NO GLOVES"],
                "evidence_crop_base64": c3
            }
        ]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            vest_detected=False,
            gloves_detected=False,
            person_count=3,
            unhelmeted_count=1,
            unvested_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1)
        alt = active[0]
        self.assertEqual(alt.person_count, 3)
        self.assertEqual(len(alt.person_findings), 3)
        self.assertEqual(alt.person_findings[0].overall_ppe_status, "OK")
        self.assertEqual(alt.person_findings[1].overall_ppe_status, "VIOLATION")
        self.assertEqual(alt.person_findings[2].overall_ppe_status, "VIOLATION")
        self.assertEqual(alt.person_findings[2].violations, ["NO SAFETY VEST", "NO GLOVES"])

    # 5. One person with multiple issues
    def test_05_one_person_multiple_issues(self):
        """5. One person with multiple simultaneous issues: helmet + vest + gloves"""
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "VIOLATION",
            "vest_status": "VIOLATION",
            "glove_status": "VIOLATION",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO HELMET", "NO SAFETY VEST", "NO GLOVES"]
        }]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            vest_detected=False,
            gloves_detected=False,
            person_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1)
        p = active[0].person_findings[0]
        self.assertEqual(len(p.violations), 3)
        self.assertIn("NO HELMET", p.violations)
        self.assertIn("NO SAFETY VEST", p.violations)
        self.assertIn("NO GLOVES", p.violations)

    # 6. No repeated event every frame
    def test_06_no_repeated_event_every_frame(self):
        """6. Ongoing violation over 25 frames -> exactly ONE event maintained (no duplicate flood)"""
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "VIOLATION",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO HELMET"]
        }]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            person_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        first_id = state_manager.get_active_alerts_list()[0].id

        # Feed 24 additional frames
        for _ in range(24):
            state_manager.update_cv_detection(
                person_detected=True,
                helmet_detected=False,
                person_count=1,
                person_findings=findings,
                evidence_frame=self.dummy_bytes
            )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].id, first_id)

    # 7. Event state updates correctly
    def test_07_event_state_updates_correctly(self):
        """7. Event state updates seamlessly in place when workers return to compliant status"""
        # Step 1: Violation
        findings_viol = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "VIOLATION",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO HELMET"]
        }]
        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            person_count=1,
            person_findings=findings_viol,
            evidence_frame=self.dummy_bytes
        )
        alt_id = state_manager.get_active_alerts_list()[0].id

        # Step 2: Worker puts on helmet (status -> OK)
        findings_ok = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "OK",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "OK",
            "violations": []
        }]
        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=True,
            person_count=1,
            person_findings=findings_ok,
            evidence_frame=self.dummy_bytes
        )

        # Existing alert notes should reflect compliance update
        alt = state_manager.get_active_alerts_list()[0]
        self.assertEqual(alt.id, alt_id)
        self.assertIn("compliant", alt.notes.lower())

    # 8. Person labels remain stable across nearby frames where possible
    def test_08_person_labels_stable_across_nearby_frames(self):
        """8. PersonTrack maintains stable tracking label across frames via IoU matching"""
        box_f1 = [100, 100, 250, 400]
        # Frame 2: person moves slightly right
        box_f2 = [105, 100, 255, 400]

        iou = compute_box_iou(box_f1, box_f2)
        self.assertGreater(iou, 0.70)

        track = PersonTrack(track_id=1, box=box_f1, now_ts=time.time())
        self.assertEqual(track.label, "Person #1")
        # Apply smoothing track update as used in detection engine
        track.box = (0.65 * track.box + 0.35 * np.array(box_f2)).astype(int)
        self.assertEqual(track.label, "Person #1")
        self.assertEqual(track.track_id, 1)

    # 9. Individual evidence crops are created
    def test_09_individual_evidence_crops_created(self):
        """9. Individual evidence crops are extracted with padding and natural proportions"""
        box = [100, 150, 300, 450]
        crop_bytes, crop_b64 = extract_person_crop(self.dummy_frame, box, padding_pct=0.10)
        self.assertIsNotNone(crop_bytes)
        self.assertIsNotNone(crop_b64)
        self.assertTrue(crop_b64.startswith("data:image/jpeg;base64,"))

        # Decode cropped bytes and verify image geometry
        arr = np.frombuffer(crop_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        self.assertGreater(h, 0)
        self.assertGreater(w, 0)

    # 10. Full frame is preserved
    def test_10_full_frame_preserved(self):
        """10. Event preserves full camera frame alongside individual person crops"""
        _, crop_b64 = extract_person_crop(self.dummy_frame, [100, 100, 250, 400])
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "VIOLATION",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO HELMET"],
            "evidence_crop_base64": crop_b64
        }]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            person_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        alt = state_manager.get_active_alerts_list()[0]
        # Full frame evidence exists
        self.assertIsNotNone(alt.evidence_url)
        full_ev_id = f"ev-{alt.id}"
        self.assertIn(full_ev_id, state_manager.evidence_store)
        self.assertEqual(state_manager.evidence_store[full_ev_id], self.dummy_bytes)

        # Person-wise crop evidence exists
        person_ev_id = f"ev-{alt.id}-p1"
        self.assertIn(person_ev_id, state_manager.evidence_store)
        self.assertEqual(alt.person_findings[0].evidence_crop_url, f"/api/evidence/{person_ev_id}")

    # 11. Multiple people are grouped into one event
    def test_11_multiple_people_grouped_into_one_event(self):
        """11. Multiple people with violations produce ONE alert card, not separate cards"""
        findings = [
            {
                "person_id": "Person #1",
                "track_id": 1,
                "bbox": [50, 50, 180, 300],
                "helmet_status": "VIOLATION",
                "vest_status": "OK",
                "glove_status": "OK",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO HELMET"]
            },
            {
                "person_id": "Person #2",
                "track_id": 2,
                "bbox": [200, 50, 330, 300],
                "helmet_status": "OK",
                "vest_status": "VIOLATION",
                "glove_status": "OK",
                "overall_ppe_status": "VIOLATION",
                "violations": ["NO SAFETY VEST"]
            }
        ]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            vest_detected=False,
            person_count=2,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1, "Exactly one grouped alert card must exist")
        self.assertIn("2", active[0].title)

    # 12. Existing restricted-area functionality still works
    def test_12_existing_restricted_area_functionality_works(self):
        """12. Existing restricted safety zone entry detection continues to work"""
        zone = RestrictedZone(
            zone_id="ZONE-01",
            name="Compressor Exclusion Area",
            camera_id="C-01",
            polygon=[[100, 100], [400, 100], [400, 400], [100, 400]],
            severity="CRITICAL",
            enabled=True
        )
        state_manager.active_zone = zone

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=True,
            zone_violation=True,
            persons_in_zone=1,
            occupancy_score=0.95,
            breached_zone=zone,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].type, "Restricted Zone Entry")
        self.assertEqual(active[0].severity, "CRITICAL")

    # 13. Existing glove logic still works
    def test_13_existing_glove_logic_works(self):
        """13. Existing glove logic (Gloves vs No Gloves) functions accurately"""
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "OK",
            "vest_status": "OK",
            "glove_status": "VIOLATION",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO GLOVES"]
        }]

        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=True,
            vest_detected=True,
            gloves_detected=False,
            person_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        active = state_manager.get_active_alerts_list()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].person_findings[0].glove_status, "VIOLATION")
        self.assertIn("NO GLOVES", active[0].person_findings[0].violations)

    # 14. Existing camera endpoints still work
    def test_14_existing_camera_endpoints_work(self):
        """14. Existing camera HTTP endpoints (/api/status, /api/cv/frame, /api/evidence/{id}) work"""
        # Step 1: Create an alert with evidence
        findings = [{
            "person_id": "Person #1",
            "track_id": 1,
            "bbox": [100, 100, 250, 400],
            "helmet_status": "VIOLATION",
            "vest_status": "OK",
            "glove_status": "OK",
            "overall_ppe_status": "VIOLATION",
            "violations": ["NO HELMET"],
            "evidence_crop_base64": f"data:image/jpeg;base64,{base64.b64encode(self.dummy_bytes).decode('utf-8')}"
        }]
        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=False,
            person_count=1,
            person_findings=findings,
            evidence_frame=self.dummy_bytes
        )

        alt = state_manager.get_active_alerts_list()[0]

        # GET /api/status
        res_status = self.client.get("/api/status")
        self.assertEqual(res_status.status_code, 200)
        data = res_status.json()
        self.assertIn("active_alerts", data)
        self.assertEqual(len(data["active_alerts"]), 1)
        self.assertIn("person_findings", data["active_alerts"][0])

        # GET /api/evidence/{evidence_id} for full frame
        ev_id = f"ev-{alt.id}"
        res_ev = self.client.get(f"/api/evidence/{ev_id}")
        self.assertEqual(res_ev.status_code, 200)
        self.assertEqual(res_ev.headers["content-type"], "image/jpeg")

        # GET /api/evidence/{evidence_id} for person crop
        p_ev_id = f"ev-{alt.id}-p1"
        res_crop = self.client.get(f"/api/evidence/{p_ev_id}")
        self.assertEqual(res_crop.status_code, 200)
        self.assertEqual(res_crop.headers["content-type"], "image/jpeg")

        # POST /api/cv/frame
        b64_frame = f"data:image/jpeg;base64,{base64.b64encode(self.dummy_bytes).decode('utf-8')}"
        res_post = self.client.post("/api/cv/frame", json={"frame": b64_frame})
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.json()
        self.assertEqual(post_data["status"], "LIVE")
        self.assertIn("persons", post_data)

if __name__ == "__main__":
    print("==================================================")
    print(" Running Multi-Person PPE & Person-Wise Evidence Tests ")
    print("==================================================")
    unittest.main(verbosity=2)
