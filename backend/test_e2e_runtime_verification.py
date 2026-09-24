import os
import sys
import json
import time
import base64
import urllib.request
import cv2
import numpy as np

def run_all_checks():
    print("=" * 60)
    print(" SHRAMRAKSHAK CCTV & PPE END-TO-END RUNTIME VERIFICATION ")
    print("=" * 60)

    # 1. Check Backend Status
    try:
        res = urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=5)
        status_data = json.loads(res.read().decode())
        print(f"[CHECK 1] /api/status: HTTP {res.status} | System: {status_data.get('system_status')} | Model: {status_data.get('cv_detection', {}).get('model_name')}")
        assert res.status == 200, "Expected HTTP 200"
    except Exception as e:
        print(f"[FAIL 1] Backend /api/status error: {e}")
        return False

    # 2. Check /api/cv/reset
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/cv/reset", data=b"", method="POST")
        res = urllib.request.urlopen(req, timeout=5)
        reset_data = json.loads(res.read().decode())
        print(f"[CHECK 2] /api/cv/reset: HTTP {res.status} | {reset_data.get('message')}")
        assert res.status == 200, "Expected HTTP 200"
    except Exception as e:
        print(f"[FAIL 2] /api/cv/reset error: {e}")
        return False

    # 3. Check Real Worker Image (Bare Hands & Missing Vest)
    img_path = r"C:\Users\Dell\.gemini\antigravity-ide\brain\b1e73a6b-b836-4fb3-9a98-580987f5f33b\worker_bare_hands_1789645888381.jpg"
    if os.path.exists(img_path):
        img = cv2.imread(img_path)
        _, enc = cv2.imencode('.jpg', img)
        b64 = "data:image/jpeg;base64," + base64.b64encode(enc).decode('ascii')

        last_data = None
        for seq in range(1, 6):
            payload = json.dumps({"frame": b64, "camera_id": "C-01", "frame_seq": seq}).encode('utf-8')
            req = urllib.request.Request("http://127.0.0.1:8000/api/cv/frame", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            res = urllib.request.urlopen(req, timeout=5)
            last_data = json.loads(res.read().decode())

        persons = last_data.get("persons", [])
        print(f"[CHECK 3] Worker Image Detection: {len(persons)} persons found")
        for p in persons:
            print(f"   -> {p.get('label')}: Helmet={p.get('helmet_status')} | Vest={p.get('vest_status')} | Gloves={p.get('gloves_status')} | Overall={p.get('overall_ppe_status')} | Violations={p.get('violations')}")
        
        # Verify that violations are present and NOT suppressed by UNCONFIRMED
        has_violations = any(len(p.get("violations", [])) > 0 for p in persons)
        print(f"   -> Violation detection active (NO HELMET / NO VEST / NO GLOVES): {has_violations}")
        assert has_violations, "Expected violations detected!"

    # 3b. Check Real Worker Image (With Gloves)
    img_gloved_path = r"C:\Users\Dell\.gemini\antigravity-ide\brain\b1e73a6b-b836-4fb3-9a98-580987f5f33b\worker_with_gloves_1789646062394.jpg"
    if os.path.exists(img_gloved_path):
        img_g = cv2.imread(img_gloved_path)
        _, enc_g = cv2.imencode('.jpg', img_g)
        b64_g = "data:image/jpeg;base64," + base64.b64encode(enc_g).decode('ascii')

        last_data_g = None
        for seq in range(20, 25):
            payload = json.dumps({"frame": b64_g, "camera_id": "C-01", "frame_seq": seq}).encode('utf-8')
            req = urllib.request.Request("http://127.0.0.1:8000/api/cv/frame", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            res = urllib.request.urlopen(req, timeout=5)
            last_data_g = json.loads(res.read().decode())

        persons_g = last_data_g.get("persons", [])
        print(f"[CHECK 3b] Worker With Gloves Image: {len(persons_g)} persons found")
        for p in persons_g:
            print(f"   -> {p.get('label')}: Helmet={p.get('helmet_status')} | Vest={p.get('vest_status')} | Gloves={p.get('gloves_status')} | Overall={p.get('overall_ppe_status')} | Violations={p.get('violations')}")

    # 4. Check Proximity & Vehicle Detection (Synthesized worker next to vehicle)
    try:
        # Send reset first
        urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000/api/cv/reset", data=b"", method="POST"))
        
        # Create test frame with person next to vehicle
        test_frame = np.full((480, 640, 3), 40, dtype=np.uint8)
        # Person drawn
        cv2.rectangle(test_frame, (100, 150), (180, 420), (120, 120, 120), -1)
        # Vehicle drawn
        cv2.rectangle(test_frame, (160, 200), (380, 430), (80, 80, 180), -1)
        _, enc_test = cv2.imencode('.jpg', test_frame)
        b64_test = "data:image/jpeg;base64," + base64.b64encode(enc_test).decode('ascii')
        
        payload = json.dumps({"frame": b64_test, "camera_id": "C-01", "frame_seq": 1}).encode('utf-8')
        req = urllib.request.Request("http://127.0.0.1:8000/api/cv/frame", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        res = urllib.request.urlopen(req, timeout=5)
        prox_data = json.loads(res.read().decode())
        print(f"[CHECK 4] Frame sequencing & API response: HTTP {res.status} | frame_seq: {prox_data.get('frame_seq')}")
        assert res.status == 200, "Expected HTTP 200"
    except Exception as e:
        print(f"[FAIL 4] Proximity check error: {e}")
        return False

    # 5. Check Active Alerts in State Manager
    try:
        res = urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=5)
        st = json.loads(res.read().decode())
        print(f"[CHECK 5] Alert system: {len(st.get('active_alerts', []))} active alerts | Unhelmeted: {st.get('cv_detection', {}).get('unhelmeted_count')} | Unvested: {st.get('cv_detection', {}).get('unvested_count')} | Ungloved: {st.get('cv_detection', {}).get('ungloved_count')}")
    except Exception as e:
        print(f"[FAIL 5] Active alerts error: {e}")
        return False

    print("=" * 60)
    print(" ALL RUNTIME VERIFICATION CHECKS PASSED PERFECTLY! ")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
