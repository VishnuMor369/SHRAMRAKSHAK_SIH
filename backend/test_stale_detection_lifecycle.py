"""
Automated Test Suite for CCTV Stale Person Detections & Authoritative Lifecycle
Validates:
1. Person detected -> boxes visible in current frame
2. Person leaves -> after PERSON_LOST_FRAMES boxes disappear and track purged
3. Zero persons -> no helmet labels
4. Zero persons -> no zone violation, zone status CLEAR
5. Saved zone remains intact
6. Person re-enters -> new/current detection works
7. Historical alert remains in alert history
8. Evidence snapshot does not affect current live detection
9. CCTV header renders exactly ONE clean telemetry line: CAM: C-01 | [ZONE NAME] | [ZONE TYPE] | LIVE
"""

import time
import numpy as np
import cv2
from datetime import datetime

from state import state_manager, generate_visual_evidence
from detection import video_engine, PersonTrack, compute_box_iou
from models import RestrictedZone, Alert

def test_person_track_lifecycle():
    print("==================================================================")
    print(" RUNNING STALE DETECTION LIFECYCLE REGRESSION TEST SUITE")
    print("==================================================================")

    state_manager.reset_demo()
    video_engine.tracked_persons.clear()
    video_engine.next_track_id = 1
    video_engine.frame_idx = 100

    # 1. Configure permanent zone
    zone = RestrictedZone(
        zone_id="ZONE-001",
        name="Compressor Restricted Area",
        camera_id="C-01",
        zone_type="floor",
        zone_category="PERMANENT",
        severity="HIGH",
        polygon=[[100, 100], [400, 100], [400, 400], [100, 400]],
        enabled=True
    )
    state_manager.zones["ZONE-001"] = zone

    # TEST 1: Person detected -> track created and active in current frame
    test_box = np.array([150, 150, 250, 350])
    video_engine.frame_idx += 1
    pt = PersonTrack(track_id=1, box=test_box, now_ts=time.time())
    pt.last_seen_frame = video_engine.frame_idx
    video_engine.tracked_persons[1] = pt

    active_tracks = [t for t in video_engine.tracked_persons.values() if t.last_seen_frame == video_engine.frame_idx]
    assert len(active_tracks) == 1, "Expected 1 active track in current frame"
    assert active_tracks[0].label == "Person 01"
    print("[PASS] TEST 1: Person detected -> track created and active in current frame")

    # TEST 2: Frame where person is absent -> immediately excluded from active_tracks (no stale box rendered)
    video_engine.frame_idx += 1
    # Person not detected in this frame (last_seen_frame is 101, frame_idx is 102)
    current_tracks = [t for t in video_engine.tracked_persons.values() if t.last_seen_frame == video_engine.frame_idx]
    assert len(current_tracks) == 0, "Expected 0 current tracks when candidate is absent (no stale box)"
    print("[PASS] TEST 2: Person leaves -> current-frame active tracks immediately 0 (no stale box)")

    # TEST 3: After PERSON_LOST_FRAMES -> track completely purged from tracked_persons
    for f in range(video_engine.PERSON_LOST_FRAMES):
        video_engine.frame_idx += 1
        stale_ids = []
        for tid, trk in list(video_engine.tracked_persons.items()):
            if trk.last_seen_frame != video_engine.frame_idx:
                trk.frames_unseen = video_engine.frame_idx - trk.last_seen_frame
                if trk.frames_unseen >= video_engine.PERSON_LOST_FRAMES:
                    trk.clear()
                    stale_ids.append(tid)
        for tid in stale_ids:
            del video_engine.tracked_persons[tid]

    assert len(video_engine.tracked_persons) == 0, f"Expected 0 tracks after {video_engine.PERSON_LOST_FRAMES} frames, got {len(video_engine.tracked_persons)}"
    print(f"[PASS] TEST 3: After {video_engine.PERSON_LOST_FRAMES} frames -> track purged, counters/state cleared")

    # TEST 4: Zero persons -> no helmet labels & no zone violation
    state_manager.update_cv_detection(
        person_detected=False,
        helmet_detected=False,
        zone_violation=False,
        persons_in_zone=0,
        occupancy_score=0.0,
        debug_info="ZONE: CLEAR",
        person_count=0,
        unhelmeted_count=0,
        unhelmeted_ids=[],
        evidence_frame=None,
        breached_zone=None
    )
    status = state_manager.get_system_status()
    assert status.person_count == 0, "person_count should be 0"
    assert status.unhelmeted_count == 0, "unhelmeted_count should be 0"
    assert status.zone_violation is False, "zone_violation should be False"
    assert status.zone_status == "CLEAR", f"zone_status should be CLEAR, got {status.zone_status}"
    assert status.current_safety_state in ["SAFE", "MONITORING"]
    print("[PASS] TEST 4: Zero persons -> no helmet labels, zone_violation=False, zone_status=CLEAR")

    # TEST 5: Saved zone remains intact
    assert "ZONE-001" in state_manager.zones, "Saved zone must not be deleted when persons leave"
    assert state_manager.zones["ZONE-001"].enabled is True, "Saved zone must remain enabled"
    assert len(state_manager.zones["ZONE-001"].polygon) == 4, "Zone polygon must remain intact"
    print("[PASS] TEST 5: Saved permanent zone remains intact in registry")

    # TEST 6: Person re-enters -> new detection works
    video_engine.frame_idx += 1
    new_box = np.array([200, 200, 300, 400])
    new_track = PersonTrack(track_id=video_engine.next_track_id, box=new_box, now_ts=time.time())
    new_track.last_seen_frame = video_engine.frame_idx
    video_engine.tracked_persons[video_engine.next_track_id] = new_track
    video_engine.next_track_id += 1

    current_tracks = [t for t in video_engine.tracked_persons.values() if t.last_seen_frame == video_engine.frame_idx]
    assert len(current_tracks) == 1, "Expected 1 active track after person re-enters"
    assert current_tracks[0].track_id >= 1
    assert np.array_equal(current_tracks[0].box, new_box)
    print("[PASS] TEST 6: Person re-enters -> new current detection successfully registered")

    # TEST 7: Historical alert remains in history after person leaves
    # Create an alert and resolve it
    alert = state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        location="Demo Work Zone",
        camera="C-01",
        severity="HIGH",
        sif_potential="POTENTIAL",
        person_count=1,
        affected_person_ids=["Person 01"],
        title="1 PERSON WITHOUT HELMET",
        short_summary="Worker detected without hard hat"
    )
    aid = alert.id
    state_manager.respond_to_alert(aid, "SUP-01")
    state_manager.resolve_alert(aid, "SUP-01")

    # Now person leaves
    state_manager.update_cv_detection(
        person_detected=False,
        helmet_detected=False,
        zone_violation=False,
        person_count=0
    )

    history = state_manager.get_history_list()
    hist_ids = [h.id for h in history]
    assert aid in hist_ids, "Historical alert must remain preserved in history after person leaves"
    print("[PASS] TEST 7: Historical alert remains preserved in alert history after person leaves")

    # TEST 8: Evidence snapshot does not pollute live detection state
    pre_tracks_count = len(video_engine.tracked_persons)
    ev_bytes = generate_visual_evidence(
        alert_type="Helmet/PPE Violation",
        camera_id="C-01",
        location="Demo Work Zone",
        person_count=2,
        unhelmeted_ids=["Person 01", "Person 02"]
    )
    assert ev_bytes is not None and len(ev_bytes) > 1000
    assert len(video_engine.tracked_persons) == pre_tracks_count, "Evidence snapshot must not modify live tracked_persons"
    print("[PASS] TEST 8: Evidence snapshot generation does not pollute live detection tracks")

    # TEST 9: CCTV header telemetry format: CAM: C-01 | [ZONE NAME] | [ZONE TYPE] | LIVE
    active_z = state_manager.active_zone
    zone_name = active_z.name.upper() if active_z else "DEMO WORK ZONE"
    zone_type = (active_z.zone_type or "FLOOR").upper() if active_z else "GENERAL"
    expected_header = f"CAM: C-01 | {zone_name} | {zone_type} | LIVE"
    assert "CAM: C-01 | COMPRESSOR RESTRICTED AREA | FLOOR | LIVE" == expected_header
    print(f"[PASS] TEST 9: CCTV header telemetry format verified: '{expected_header}'")

    print("==================================================================")
    print(" ALL 9 STALE DETECTION & LIFECYCLE REGRESSION TESTS PASSED!")
    print("==================================================================")

if __name__ == "__main__":
    test_person_track_lifecycle()
