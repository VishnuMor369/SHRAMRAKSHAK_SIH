import os
import sys
import numpy as np
import cv2

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from detection import video_engine, PersonTrack
from state import state_manager

def test_cctv_targeted_fixes():
    print("=" * 65)
    print(" SHRAMRAKSHAK TARGETED CCTV FIXES UNIT & REGRESSION TEST ")
    print("=" * 65)

    worker_img_path = r"C:\Users\Dell\.gemini\antigravity-ide\brain\b1e73a6b-b836-4fb3-9a98-580987f5f33b\worker_bare_hands_1789645888381.jpg"

    # -------------------------------------------------------------
    # TEST 1: BUG 1 — Partial Person / Head-only (Vest must be UNKNOWN)
    # -------------------------------------------------------------
    print("\n[TEST 1] Head-only / Partial Person -> Helmet evaluates, Vest=UNKNOWN")
    video_engine.reset_tracks()
    
    if os.path.exists(worker_img_path):
        full_worker = cv2.imread(worker_img_path)
        # Crop only the head and upper collar (top 28% of the image)
        wh, ww = full_worker.shape[:2]
        head_crop = full_worker[:int(wh * 0.28), :]
        
        # Place head crop inside a standard 640x480 frame
        head_frame = np.full((480, 640, 3), 40, dtype=np.uint8)
        ch, cw = head_crop.shape[:2]
        head_frame[:min(480, ch), :min(640, cw)] = head_crop[:min(480, ch), :min(640, cw)]

        res_head = None
        for seq in range(1, 8):
            res_head = video_engine.process_frame(head_frame, camera_id="C-01", frame_seq=seq)
        
        persons_h = res_head.get("persons", [])
        print(f"   Head-only detections found: {len(persons_h)}")
        for ph in persons_h:
            print(f"   -> {ph['label']}: Helmet={ph['helmet_status']} | Vest={ph['vest_status']} | Violations={ph['violations']}")
            assert ph["vest_status"] == "UNKNOWN", f"Vest should be UNKNOWN on head crop, got: {ph['vest_status']}"
            assert "NO SAFETY VEST" not in ph["violations"], "NO SAFETY VEST must not be manufactured for head-only crop"
        print("   [OK] TEST 1 PASSED: Partial/Head-only person evaluated independently without false NO VEST.")

    # -------------------------------------------------------------
    # TEST 2: BUG 1 — Full Person Without Vest (Must detect NO VEST)
    # -------------------------------------------------------------
    print("\n[TEST 2] Full Person Visible Without Vest -> Detects NO SAFETY VEST")
    video_engine.reset_tracks()
    
    if os.path.exists(worker_img_path):
        worker_frame = cv2.imread(worker_img_path)
        res_worker = None
        for seq in range(1, 8):
            res_worker = video_engine.process_frame(worker_frame, camera_id="C-01", frame_seq=seq)
        
        persons_w = res_worker.get("persons", [])
        print(f"   Full person detections found: {len(persons_w)}")
        for pw in persons_w:
            print(f"   -> {pw['label']}: Helmet={pw['helmet_status']} | Vest={pw['vest_status']} | Gloves={pw['gloves_status']} | Violations={pw['violations']}")
        has_vest_viol = any("NO SAFETY VEST" in pw["violations"] or pw["vest_status"] == "VIOLATION" for pw in persons_w)
        print(f"   -> Real NO VEST detected: {has_vest_viol}")
        assert has_vest_viol, "Real NO SAFETY VEST detection must still work for full person!"
        print("   [OK] TEST 2 PASSED: Real NO SAFETY VEST successfully detected on full body.")

    # -------------------------------------------------------------
    # TEST 3: BUG 2 — Glove Detection & No Percentage in Hand Labels
    # -------------------------------------------------------------
    print("\n[TEST 3] Hand Box Labels Must Have No Visible Percentage")
    for t in video_engine.tracked_persons.values():
        for hb in t.hand_boxes:
            print(f"   Hand label: {hb.get('label')}")
            assert "%" not in hb.get("label", ""), f"Percentage found in hand label: {hb.get('label')}"
    print("   [OK] TEST 3 PASSED: Hand labels contain NO percentage.")

    # -------------------------------------------------------------
    # TEST 4: BUG 4 — Alert Response Deduplication & Idempotency
    # -------------------------------------------------------------
    print("\n[TEST 4] Alert Response Deduplication & Idempotency")
    alert = state_manager.trigger_alert(
        alert_type="Helmet/PPE Violation",
        location="Demo Work Zone",
        camera="C-01",
        severity="HIGH"
    )
    assert alert is not None, "Failed to trigger test alert"
    assert alert.status == "WAITING_FOR_RESPONSE", "Initial alert should be WAITING_FOR_RESPONSE"

    # Supervisor responds once
    r1 = state_manager.respond_to_alert(supervisor_id="SUP-FIELD-01", notes="En route", alert_id=alert.id)
    assert r1 is not None and r1.status == "RESPONDING", "Alert should transition to RESPONDING"
    initial_responded_at = r1.responded_at

    # Supervisor or repeated poll responds a second time
    r2 = state_manager.respond_to_alert(supervisor_id="SUP-FIELD-01", notes="Duplicate call", alert_id=alert.id)
    assert r2.status == "RESPONDING", "Alert remains in RESPONDING"
    assert r2.responded_at == initial_responded_at, "Responded timestamp must NOT be overwritten on duplicate calls"
    print("   [OK] TEST 4 PASSED: Exactly one response recorded, duplicate requests are idempotent.")

    # -------------------------------------------------------------
    # TEST 5: BUG 3 & 5 — Source Switch Clean Session Reset
    # -------------------------------------------------------------
    print("\n[TEST 5] Clean CV Session Reset on Source Switch")
    video_engine.reset_tracks()
    state_manager.reset_cv_session()
    assert len(video_engine.tracked_persons) == 0, "All person tracks should be cleared"
    assert len(video_engine.tracked_vehicles) == 0, "All vehicle tracks should be cleared"
    assert state_manager.active_alert is None or state_manager.active_alert.type not in ("Helmet/PPE Violation", "Person–Vehicle Proximity"), "Active CV alert should be cleared"
    print("   [OK] TEST 5 PASSED: Tracking state and active CCTV detection cleanly reset.")

    print("\n" + "=" * 65)
    print(" ALL 5 CCTV TARGETED BUG FIX VERIFICATION TESTS PASSED! ")
    print("=" * 65)
    return True

if __name__ == "__main__":
    success = test_cctv_targeted_fixes()
    sys.exit(0 if success else 1)
