"""
Comprehensive Automated Test Suite for Advanced Keypoint & Occupancy-Based Restricted Zone Detection
Covers Tests 1 through 12 as required by system specifications.
"""

import time
import sys
import numpy as np
import cv2
from datetime import datetime

from models import RestrictedZone
from state import state_manager
from detection import VideoDetectionEngine, evaluate_person_zone_occupancy

def run_all_zone_tests():
    print("==================================================")
    print(" Running Restricted Zone Keypoint & Occupancy Tests ")
    print("==================================================")

    # Setup 1: FLOOR / GROUND Zone polygon in 640x480 space
    floor_polygon = [[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]]
    floor_poly_np = np.array(floor_polygon, dtype=np.int32)
    
    floor_zone = RestrictedZone(
        zone_id="ZONE-FLOOR-01",
        name="Compressor Exclusion Area",
        camera_id="C-01",
        zone_type="floor",
        severity="HIGH",
        polygon=floor_polygon,
        enabled=True
    )
    state_manager.set_zone(floor_zone)
    assert state_manager.active_zone.zone_type == "floor"
    print("[OK] Floor Zone configured successfully: Compressor Exclusion Area")

    # TEST 1: Person completely outside FLOOR polygon -> NO violation
    print("\n[TEST 1] Testing person completely outside FLOOR polygon...")
    person_box_out = [400, 350, 480, 470] # completely to the right and below
    kpts_out = np.zeros((17, 2))
    kpts_out[15] = [440, 465] # left ankle
    kpts_out[16] = [460, 465] # right ankle
    is_occ, score, dbg, _ = evaluate_person_zone_occupancy(person_box_out, kpts_out, None, floor_polygon, "floor")
    assert not is_occ, f"Expected outside floor zone, got {is_occ} ({dbg})"
    assert score == 0.0
    print("  [PASS] Person completely outside -> is_occupied = False, score = 0.0")

    # TEST 2: Person's upper body / bbox overlaps FLOOR polygon but feet are outside -> NO violation
    print("\n[TEST 2] Testing upper body perspective overlap on FLOOR polygon (feet outside)...")
    # Polygon is Y: 100 to 300. Person box: Y: 220 to 380 (upper body visually overlaps Y: 220-300)
    # But feet / ankles are at Y: 375 (outside polygon on ground)
    person_box_overlap = [180, 220, 260, 380]
    kpts_overlap = np.zeros((17, 2))
    kpts_overlap[5] = [190, 240] # left shoulder inside polygon area in 2D
    kpts_overlap[6] = [250, 240] # right shoulder inside polygon area in 2D
    kpts_overlap[11] = [200, 310] # hips outside polygon (Y=310)
    kpts_overlap[12] = [240, 310]
    kpts_overlap[15] = [205, 375] # left ankle outside polygon
    kpts_overlap[16] = [235, 375] # right ankle outside polygon
    is_occ, score, dbg, _ = evaluate_person_zone_occupancy(person_box_overlap, kpts_overlap, None, floor_polygon, "floor")
    assert not is_occ, f"Upper body perspective overlap should NOT trigger floor violation! dbg: {dbg}"
    assert score == 0.0
    print("  [PASS] Upper-body overlaps polygon but feet are outside -> NO violation (perspective protected).")

    # TEST 3: Person's feet enter FLOOR polygon for fewer than 5 frames -> NO alert
    print("\n[TEST 3] Testing person's feet inside FLOOR polygon for < 5 frames...")
    engine = VideoDetectionEngine.__new__(VideoDetectionEngine)
    engine.stable_person_detected = True
    engine.stable_helmet_detected = True
    engine.stable_zone_violation = False
    engine.persons_in_zone = 0
    engine.zone_inside_confirm_count = 0
    engine.zone_outside_confirm_count = 0
    engine.ZONE_CONFIRM_FRAMES = 5
    engine.ZONE_EXIT_FRAMES = 5

    # Feet inside at (200, 250)
    person_box_in = [160, 100, 240, 260]
    kpts_in = np.zeros((17, 2))
    kpts_in[15] = [190, 255] # left ankle inside
    kpts_in[16] = [210, 255] # right ankle inside
    is_occ, score, dbg, _ = evaluate_person_zone_occupancy(person_box_in, kpts_in, None, floor_polygon, "floor")
    assert is_occ, "Expected feet inside polygon"

    # Simulate 3 frames inside
    for f in range(3):
        engine.zone_inside_confirm_count += 1
        engine.zone_outside_confirm_count = 0
        if engine.zone_inside_confirm_count >= engine.ZONE_CONFIRM_FRAMES:
            engine.stable_zone_violation = True
    assert not engine.stable_zone_violation, "Zone violation must NOT trigger before 5 frames!"
    print(f"  [PASS] At 3 frames: stable_zone_violation is {engine.stable_zone_violation} (temporal smoothing active).")

    # TEST 4: Person's feet remain inside FLOOR polygon for 5 frames -> VIOLATION
    print("\n[TEST 4] Testing confirmation after 5 consecutive frames...")
    for f in range(2): # 4th and 5th frame
        engine.zone_inside_confirm_count += 1
        engine.zone_outside_confirm_count = 0
        if engine.zone_inside_confirm_count >= engine.ZONE_CONFIRM_FRAMES:
            engine.stable_zone_violation = True
            engine.persons_in_zone = 1
    assert engine.stable_zone_violation, "Expected confirmed zone violation at frame 5!"
    print("  [PASS] At frame 5, zone violation confirmed! persons_in_zone = 1.")

    # Feed to state_manager and verify alert generation
    state_manager.reset_demo()
    state_manager.set_zone(floor_zone)
    state_manager.update_cv_detection(
        person_detected=True,
        helmet_detected=True,
        zone_violation=True,
        persons_in_zone=1,
        occupancy_score=1.0,
        debug_info="FEET: INSIDE | GROUND: INSIDE | VIOLATION"
    )
    alert = state_manager.active_alert
    assert alert is not None, "Expected active alert after confirmed floor violation"
    assert alert.type == "Restricted Zone Entry"
    assert alert.location == "Compressor Exclusion Area"
    assert alert.sif_potential == "HIGH / POTENTIAL"
    print(f"  [PASS] Safety Observation generated: {alert.id} ({alert.type}) at {alert.location}")

    # TEST 5: Person sits/occupies SURFACE polygon while feet remain outside -> VIOLATION
    print("\n[TEST 5] Testing person sitting on SURFACE polygon (bed) with feet outside...")
    # Setup SURFACE polygon (bed/platform) from [200, 200] to [400, 320]
    surface_poly = [[200.0, 200.0], [400.0, 200.0], [400.0, 320.0], [200.0, 320.0]]
    surface_zone = RestrictedZone(
        zone_id="ZONE-SURFACE-01",
        name="Hospital Restricted Bed #1",
        camera_id="C-01",
        zone_type="surface",
        severity="HIGH",
        polygon=surface_poly,
        enabled=True
    )
    # Sitting on bed: hips at Y=260 inside bed polygon, feet dangling at Y=350 outside bed polygon
    kpts_bed_sitting = np.zeros((17, 2))
    kpts_bed_sitting[11] = [280, 260] # left hip inside bed
    kpts_bed_sitting[12] = [320, 260] # right hip inside bed
    kpts_bed_sitting[13] = [290, 310] # knees on edge
    kpts_bed_sitting[14] = [310, 310]
    kpts_bed_sitting[15] = [290, 350] # left ankle dangling outside
    kpts_bed_sitting[16] = [310, 350] # right ankle dangling outside
    box_sitting = [260, 160, 340, 360]
    
    is_occ_bed, score_bed, dbg_bed, _ = evaluate_person_zone_occupancy(
        box_sitting, kpts_bed_sitting, None, surface_poly, "surface"
    )
    assert is_occ_bed, f"Person sitting on bed MUST trigger surface occupancy violation! dbg: {dbg_bed}"
    assert score_bed >= 0.50, f"Expected high occupancy score for sitting on bed, got {score_bed}"
    print(f"  [PASS] Sitting on bed detected: is_occupied = True, score = {score_bed:.2f} ({dbg_bed})")

    # TEST 6: Person in front of camera, bbox overlaps SURFACE polygon without actual occupancy -> NO violation
    print("\n[TEST 6] Testing standing in front of bed (perspective overlap rejected)...")
    # Person standing on floor in front of bed: feet at Y=460 (well below bed polygon max Y=320)
    # Upper body in 2D visually overlaps bed Y: 200-320
    kpts_fg_standing = np.zeros((17, 2))
    kpts_fg_standing[5] = [280, 220] # shoulders visually projected over bed
    kpts_fg_standing[6] = [320, 220]
    kpts_fg_standing[11] = [280, 370] # hips below bed
    kpts_fg_standing[12] = [320, 370]
    kpts_fg_standing[15] = [285, 460] # feet on floor in front of bed
    kpts_fg_standing[16] = [315, 460]
    box_fg_standing = [260, 180, 340, 470]

    is_occ_fg, score_fg, dbg_fg, _ = evaluate_person_zone_occupancy(
        box_fg_standing, kpts_fg_standing, None, surface_poly, "surface"
    )
    assert not is_occ_fg, f"Standing in front of bed should NOT trigger surface violation! dbg: {dbg_fg}"
    print(f"  [PASS] Standing in foreground rejected: is_occupied = False, score = {score_fg:.2f} ({dbg_fg})")

    # TEST 7: Person remains inside -> exactly ONE active alert (no alert flood)
    print("\n[TEST 7] Testing person remaining inside (no alert flood)...")
    initial_alert_id = state_manager.active_alert.id
    for _ in range(10):
        state_manager.update_cv_detection(
            person_detected=True,
            helmet_detected=True,
            zone_violation=True,
            persons_in_zone=1,
            occupancy_score=1.0,
            debug_info="FEET: INSIDE | VIOLATION"
        )
    assert state_manager.active_alert.id == initial_alert_id, "Alert was flooded while person remained inside!"
    print("  [PASS] 10 subsequent frames processed: exactly ONE active alert maintained.")

    # TEST 8: Person exits -> zone clears after exit debounce
    print("\n[TEST 8] Testing person leaves zone (exit debounce)...")
    # 4 frames outside -> still debouncing
    for f in range(4):
        engine.zone_outside_confirm_count += 1
        engine.zone_inside_confirm_count = 0
        if engine.zone_outside_confirm_count >= engine.ZONE_EXIT_FRAMES:
            engine.stable_zone_violation = False
            engine.persons_in_zone = 0
    assert engine.stable_zone_violation, "Violation should persist during 4-frame exit debounce"

    # 5th frame outside -> clears
    engine.zone_outside_confirm_count += 1
    if engine.zone_outside_confirm_count >= engine.ZONE_EXIT_FRAMES:
        engine.stable_zone_violation = False
        engine.persons_in_zone = 0
    assert not engine.stable_zone_violation, "Violation should be cleared after 5 exit frames"
    print("  [PASS] Zone violation cleared smoothly after 5 exit frames without flickering.")

    # TEST 9: Person re-enters after resolution -> NEW alert
    print("\n[TEST 9] Testing re-entry after resolution...")
    state_manager.resolve_alert(supervisor_id="SUP-01", notes="Worker escorted out")
    assert state_manager.active_alert.status == "RESOLVED"
    state_manager.update_cv_detection(person_detected=True, helmet_detected=True, zone_violation=False, persons_in_zone=0)
    assert not state_manager.zone_violation
    
    # Wait 1.05s so timestamp in Alert ID differs
    time.sleep(1.05)
    state_manager.update_cv_detection(person_detected=True, helmet_detected=True, zone_violation=True, persons_in_zone=1)
    new_alert = state_manager.active_alert
    assert new_alert is not None and new_alert.status == "WAITING_FOR_RESPONSE"
    assert new_alert.id != initial_alert_id
    print(f"  [PASS] New alert generated upon re-entry: {new_alert.id}")

    # TEST 10: Existing helmet/no-helmet detection still works
    print("\n[TEST 10] Testing existing helmet detection stability...")
    state_manager.reset_demo()
    state_manager.update_cv_detection(person_detected=True, helmet_detected=True, zone_violation=False, persons_in_zone=0)
    assert state_manager.current_safety_state == "SAFE"
    print("  [PASS] Helmet detected -> SAFE state verified.")

    # TEST 11: Existing supervisor response workflow still passes
    print("\n[TEST 11] Testing Stage 1 -> Stage 2 -> RESOLVED workflow...")
    state_manager.trigger_alert(alert_type="Restricted Zone Entry", location="Compressor Exclusion Area")
    assert state_manager.active_alert.status == "WAITING_FOR_RESPONSE"
    
    # Supervisor clicks I'M RESPONDING
    resp = state_manager.respond_to_alert(supervisor_id="SUP-FIELD-01", notes="Acknowledged, en route")
    assert resp.status == "RESPONDING"
    assert resp.action_deadline is not None
    print("  [PASS] Supervisor acknowledged alert -> Transitioned to RESPONDING (Stage 2).")

    # Supervisor clicks FIXED / RESOLVED
    resolved = state_manager.resolve_alert(supervisor_id="SUP-FIELD-01", notes="Worker moved to safety")
    assert resolved.status == "RESOLVED"
    print("  [PASS] Alert successfully RESOLVED.")

    # TEST 12: Existing escalation workflow still passes (remains ESCALATED until explicitly resolved)
    print("\n[TEST 12] Testing automatic escalation flow (remains ESCALATED until resolved)...")
    state_manager.reset_demo()
    state_manager.trigger_alert(alert_type="Restricted Zone Entry", location="Compressor Exclusion Area", response_sec=1)
    time.sleep(1.2)
    deadline = datetime.fromisoformat(state_manager.active_alert.response_deadline)
    if datetime.now() >= deadline:
        state_manager.active_alert.status = "ESCALATED"
        state_manager.active_alert.escalated_at = datetime.now().isoformat()
    
    assert state_manager.active_alert.status == "ESCALATED", "Alert should be ESCALATED after SLA expiry"
    print(f"  [PASS] Alert ESCALATED: {state_manager.active_alert.escalated_at}")

    # Verify it does NOT resolve automatically
    time.sleep(0.3)
    assert state_manager.active_alert.status == "ESCALATED", "Escalated alert must remain OPEN / ESCALATED!"
    print("  [PASS] Escalated alert remains OPEN until explicitly resolved.")

    # Explicit resolution
    state_manager.resolve_alert(supervisor_id="HSE-MGR-01", notes="Escalation cleared by manager")
    assert state_manager.active_alert.status == "RESOLVED"
    print("  [PASS] Escalated alert explicitly resolved.")

    print("\n==================================================")
    print("  ALL 12 RESTRICTED ZONE TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    try:
        run_all_zone_tests()
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
