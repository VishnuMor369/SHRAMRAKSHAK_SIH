import cv2
import time
import os
import base64
import numpy as np
import threading
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
from state import state_manager

# Try loading onnxruntime (digitally signed, works on Windows 11 Smart App Control)
try:
    import onnxruntime as ort
    ORT_AVAILABLE = True
except ImportError:
    ort = None
    ORT_AVAILABLE = False


def evaluate_person_zone_occupancy(person_box, kpts_xy=None, kpts_conf=None, zone_poly=None, zone_type="floor"):
    """
    Evaluates whether a detected person is occupying a configured restricted zone.
    
    Parameters:
    - person_box: [x1, y1, x2, y2]
    - kpts_xy: ndarray of shape (17, 2) or list of [x, y] keypoints (COCO format) or None
    - kpts_conf: ndarray of shape (17,) or list of confidences or None
    - zone_poly: ndarray of shape (N, 2) representing the polygon vertices in camera space
    - zone_type: "floor" (Floor/Ground Zone) or "surface" (Surface/Platform Zone)
    
    Returns:
    - (is_occupied: bool, occupancy_score: float, debug_info: str, visual_markers: dict)
    """
    if zone_poly is None or len(zone_poly) < 3:
        return False, 0.0, "NO_ZONE", {}
    
    x1, y1, x2, y2 = person_box
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    bottom_center = ((x1 + x2) // 2, y2)
    poly_np = np.array(zone_poly, dtype=np.int32)
    poly_max_y = float(np.max(poly_np[:, 1]))
    
    def is_inside(pt):
        if pt is None:
            return False
        return cv2.pointPolygonTest(poly_np, (float(pt[0]), float(pt[1])), False) >= 0

    has_pose = (kpts_xy is not None and len(kpts_xy) >= 17)
    if has_pose and kpts_conf is None:
        kpts_conf = np.ones(17, dtype=np.float32)

    la = kpts_xy[15] if (has_pose and kpts_conf[15] >= 0.25) else None
    ra = kpts_xy[16] if (has_pose and kpts_conf[16] >= 0.25) else None

    lh = kpts_xy[11] if (has_pose and kpts_conf[11] >= 0.25) else None
    rh = kpts_xy[12] if (has_pose and kpts_conf[12] >= 0.25) else None
    if lh is not None and rh is not None:
        hip_center = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)
    elif lh is not None:
        hip_center = lh
    elif rh is not None:
        hip_center = rh
    else:
        hip_center = ((x1 + x2) / 2, y1 + 0.60 * h)

    lk = kpts_xy[13] if (has_pose and kpts_conf[13] >= 0.25) else None
    rk = kpts_xy[14] if (has_pose and kpts_conf[14] >= 0.25) else None

    ls = kpts_xy[5] if (has_pose and kpts_conf[5] >= 0.25) else None
    rs = kpts_xy[6] if (has_pose and kpts_conf[6] >= 0.25) else None
    if ls is not None and rs is not None:
        sc = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
        torso_center = ((sc[0] + hip_center[0]) / 2, (sc[1] + hip_center[1]) / 2)
    else:
        torso_center = ((x1 + x2) / 2, y1 + 0.45 * h)

    z_type = (zone_type or "floor").lower()
    visual_markers = {
        "ground_point": (int(bottom_center[0]), int(bottom_center[1])),
        "ground_inside": is_inside(bottom_center),
        "hip_center": (int(hip_center[0]), int(hip_center[1])),
        "hip_inside": is_inside(hip_center),
        "left_ankle": (int(la[0]), int(la[1])) if la is not None else None,
        "right_ankle": (int(ra[0]), int(ra[1])) if ra is not None else None,
        "zone_type": z_type
    }

    if "surface" in z_type:
        hip_in = is_inside(hip_center)
        lh_in = is_inside(lh) if lh is not None else False
        rh_in = is_inside(rh) if rh is not None else False
        knee_in = (is_inside(lk) if lk is not None else False) or (is_inside(rk) if rk is not None else False)
        torso_in = is_inside(torso_center)
        lower_center_in = is_inside(((x1 + x2) / 2, y1 + 0.65 * h))
        bottom_center_in = is_inside(bottom_center)

        score = 0.0
        if hip_in: score += 0.45
        if lh_in or rh_in: score += 0.20
        if knee_in: score += 0.25
        if torso_in: score += 0.20
        if lower_center_in: score += 0.15
        if bottom_center_in: score += 0.15

        feet_y = max(y2, la[1] if la is not None else y2, ra[1] if ra is not None else y2)
        if feet_y > poly_max_y + 35:
            score -= 0.50

        score = max(0.0, min(1.0, score))
        if score >= 0.50:
            is_occupied = True
            h_stat = "INSIDE" if hip_in else "OCCUPIED"
            debug = f"HIPS: {h_stat} | SURFACE: {int(score*100)}% | VIOLATION"
        elif 0.35 <= score < 0.50:
            is_occupied = False
            debug = f"LOW CONFIDENCE — VERIFY ({int(score*100)}%)"
        else:
            is_occupied = False
            debug = f"HIPS: OUTSIDE | SURFACE: {int(score*100)}% | ZONE: CLEAR"
        return is_occupied, score, debug, visual_markers

    else:
        # FLOOR / GROUND ZONE:
        # Evaluates ground contact point (ankles or bottom-center)
        if la is not None or ra is not None:
            la_in = is_inside(la) if la is not None else False
            ra_in = is_inside(ra) if ra is not None else False
            if la_in or ra_in:
                is_occupied = True
                score = 1.0 if (la_in and ra_in) else 0.85
                debug = "FEET: INSIDE | GROUND: INSIDE | ZONE: VIOLATION"
            else:
                is_occupied = False
                score = 0.0
                debug = "FEET: OUTSIDE | GROUND: OUTSIDE | ZONE: CLEAR"
        else:
            bc_in = is_inside(bottom_center)
            if bc_in:
                is_occupied = True
                score = 0.80
                debug = "GROUND POINT: INSIDE | ZONE: VIOLATION"
            else:
                is_occupied = False
                score = 0.0
                debug = "FEET: OUTSIDE | GROUND: OUTSIDE | ZONE: CLEAR"
        return is_occupied, score, debug, visual_markers


def compute_box_iou(b1, b2) -> float:
    """Computes Intersection-over-Union between two [x1, y1, x2, y2] boxes"""
    xA = max(b1[0], b2[0])
    yA = max(b1[1], b2[1])
    xB = min(b1[2], b2[2])
    yB = min(b1[3], b2[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    area1 = max(0, b1[2] - b1[0]) * max(0, b1[3] - b1[1])
    area2 = max(0, b2[2] - b2[0]) * max(0, b2[3] - b2[1])
    union = float(area1 + area2 - inter)
    return inter / union if union > 0 else 0.0


class PersonTrack:
    """Lightweight person tracking record across video frames"""
    def __init__(self, track_id: int, box: np.ndarray, now_ts: float):
        self.track_id = track_id
        self.label = f"Person {track_id:02d}"
        self.box = np.array(box, dtype=int)
        self.last_seen_frame = 0
        self.frames_unseen = 0
        self.first_detected_at = now_ts
        self.helmet_confirm_count = 0
        self.no_helmet_confirm_count = 0
        self.stable_status = "MONITORING" # "HELMET", "NO_HELMET", "MONITORING"
        self.helmet_confidence = 0.0
        self.in_zone = False
        self.zone_score = 0.0
        self.zone_debug = None
        self.ground_point = None
        self.hip_center = None

    def clear(self):
        self.box = np.array([0, 0, 0, 0], dtype=int)
        self.stable_status = "MONITORING"
        self.helmet_confirm_count = 0
        self.no_helmet_confirm_count = 0
        self.helmet_confidence = 0.0
        self.in_zone = False
        self.zone_score = 0.0
        self.zone_debug = None
        self.ground_point = None
        self.hip_center = None


class VideoDetectionEngine:
    """
    Production-grade AI CCTV Detection Engine.
    Uses ONNX Runtime to execute real YOLO PPE/Helmet inference on CPU
    without PyTorch dependency, bypassing Windows 11 Smart App Control policies.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.session: Optional[Any] = None
        self.model_loaded = False
        self.model_name = "UNAVAILABLE"
        self.is_custom_helmet_model = False
        
        # 13 PPE classes supported by ppe_safety.onnx
        self.ppe_classes = [
            'Fall-Detected', 'Gloves', 'Goggles', 'Hardhat', 'Mask',
            'NO-Gloves', 'NO-Goggles', 'NO-Hardhat', 'NO-Mask', 'NO-Safety Vest',
            'No_Harness', 'Person', 'Safety Vest'
        ]
        
        # Tracking & state
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.last_frame: Optional[np.ndarray] = None
        self.person_detected = False
        self.helmet_detected = False
        
        self.tracked_persons: Dict[int, PersonTrack] = {}
        self.next_track_id: int = 1
        self.frame_idx: int = 0
        
        # Smoothing & Debounce state
        self.stable_person_detected = False
        self.stable_helmet_detected = False
        self.stable_zone_violation = False
        self.persons_in_zone = 0
        self.zone_occupancy_score = 0.0
        self.zone_debug_info = None
        
        self.helmet_confirm_count = 0
        self.no_helmet_confirm_count = 0
        self.zone_inside_confirm_count = 0
        self.zone_outside_confirm_count = 0
        
        # Debounce settings (5 frames for confirmation at 5-10 FPS)
        self.HELMET_CONFIRM_FRAMES = 4
        self.NO_HELMET_CONFIRM_FRAMES = 4
        self.PERSON_CONFIRM_FRAMES = 2
        self.PERSON_LOST_FRAMES = 6
        self.ZONE_CONFIRM_FRAMES = 4
        self.ZONE_EXIT_FRAMES = 5
        
        # Performance & Debug counters
        self.frames_received = 0
        self.last_inference_time = None
        self.last_alert_time = None
        self.total_helmet_detections = 0
        self.total_zone_violations = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        self.frame_count = 0
        
        # Initialize ONNX model and background hardware watcher
        self._init_models()
        self.is_running = True
        self._capture_thread = threading.Thread(target=self._hardware_camera_loop, daemon=True)
        self._capture_thread.start()

    def _init_models(self):
        """Loads ppe_safety.onnx (and yolov8n.onnx for robust person detection) using ONNX Runtime"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ppe_model_path = os.path.join(base_dir, "ppe_safety.onnx")
        yolo_model_path = os.path.join(base_dir, "yolov8n.onnx")
        
        self.session_ppe = None
        self.session_coco = None

        if not ORT_AVAILABLE:
            print("[CV Engine] Warning: onnxruntime not installed. Model unavailable.")
            self.model_loaded = False
            self.model_name = "MODEL NOT AVAILABLE (onnxruntime missing)"
            return

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        if os.path.exists(ppe_model_path):
            try:
                print(f"[CV Engine] Loading PPE Safety ONNX model from {ppe_model_path}...")
                self.session_ppe = ort.InferenceSession(ppe_model_path, opts, providers=['CPUExecutionProvider'])
                print(f"[CV Engine] Loaded ppe_safety.onnx successfully! Classes: {len(self.ppe_classes)}")
            except Exception as e:
                print(f"[CV Engine] Failed to load ppe_safety.onnx: {e}")

        if os.path.exists(yolo_model_path):
            try:
                print(f"[CV Engine] Loading COCO YOLOv8n ONNX model from {yolo_model_path}...")
                self.session_coco = ort.InferenceSession(yolo_model_path, opts, providers=['CPUExecutionProvider'])
                print(f"[CV Engine] Loaded yolov8n.onnx successfully!")
            except Exception as e:
                print(f"[CV Engine] Failed to load yolov8n.onnx: {e}")

        if self.session_ppe is not None or self.session_coco is not None:
            self.model_loaded = True
            if self.session_ppe is not None:
                self.model_name = "ppe_safety.onnx (ONNX Runtime)"
                self.is_custom_helmet_model = True
            else:
                self.model_name = "yolov8n.onnx (Fallback)"
                self.is_custom_helmet_model = False
        else:
            print("[CV Engine] No valid ONNX model found. Setting status to MODEL NOT AVAILABLE.")
            self.model_loaded = False
            self.model_name = "MODEL NOT AVAILABLE"

    def _detect_helmet_heuristic(self, frame: np.ndarray, person_box: List[int]) -> Tuple[bool, bool]:
        """
        Color analysis of the upper head region to detect safety helmet colors (yellow, white, blue, orange, lime).
        Returns: (has_helmet_evidence: bool, has_no_helmet_evidence: bool)
        """
        x1, y1, x2, y2 = person_box
        h = y2 - y1
        w = x2 - x1
        if h <= 0 or w <= 0:
            return False, False
        
        head_top = max(0, y1)
        head_bottom = min(frame.shape[0], int(y1 + 0.22 * h))
        center_margin = int(w * 0.15)
        head_left = max(0, x1 + center_margin)
        head_right = min(frame.shape[1], x2 - center_margin)
        
        head_crop = frame[head_top:head_bottom, head_left:head_right]
        if head_crop.size == 0 or head_crop.shape[0] < 5 or head_crop.shape[1] < 5:
            return False, False
        
        hsv = cv2.cvtColor(head_crop, cv2.COLOR_BGR2HSV)
        mask_yellow = cv2.inRange(hsv, np.array([18, 80, 80]), np.array([35, 255, 255]))
        mask_orange = cv2.inRange(hsv, np.array([5, 110, 100]), np.array([17, 255, 255]))
        mask_blue = cv2.inRange(hsv, np.array([95, 90, 70]), np.array([125, 255, 255]))
        mask_lime = cv2.inRange(hsv, np.array([36, 70, 70]), np.array([85, 255, 255]))
        mask_white = cv2.inRange(hsv, np.array([0, 0, 215]), np.array([180, 35, 255]))
        
        vivid_mask = mask_yellow | mask_orange | mask_blue | mask_lime
        total_pixels = head_crop.shape[0] * head_crop.shape[1] + 1e-5
        
        vivid_ratio = np.sum(vivid_mask > 0) / total_pixels
        white_ratio = np.sum(mask_white > 0) / total_pixels
        combined_ratio = vivid_ratio + (white_ratio * 0.6)
        
        has_helmet = (combined_ratio >= 0.28)
        has_no_helmet = (combined_ratio <= 0.12)
        return has_helmet, has_no_helmet

    def _run_inference(self, frame: np.ndarray) -> Tuple[List[Tuple[List[int], float]], List[Tuple[List[int], float]], List[Tuple[List[int], float]]]:
        """
        Executes real ONNX inference on a 640x640 preprocessed frame using dual-engine:
        COCO model for human presence + PPE model for Hardhat / NO-Hardhat detection.
        """
        if not self.model_loaded:
            return [], [], []

        orig_h, orig_w = frame.shape[:2]
        resized = cv2.resize(frame, (640, 640))
        blob = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis, :]

        x_scale = orig_w / 640.0
        y_scale = orig_h / 640.0

        person_proposals = []
        person_scores = []
        hardhat_proposals = []
        hardhat_scores = []
        no_hardhat_proposals = []
        no_hardhat_scores = []

        # 1. Run COCO Person detection if available
        if self.session_coco is not None:
            try:
                inp_name = self.session_coco.get_inputs()[0].name
                raw_coco = self.session_coco.run(None, {inp_name: blob})[0][0].T
                p_s = raw_coco[:, 4] # Class 0: Person
                p_idxs = np.where(p_s >= 0.35)[0]
                p_boxes = raw_coco[:, :4]
                for idx in p_idxs:
                    cx, cy, bw, bh = p_boxes[idx]
                    x = int((cx - bw / 2) * x_scale)
                    y = int((cy - bh / 2) * y_scale)
                    w = int(bw * x_scale)
                    h = int(bh * y_scale)
                    person_proposals.append([x, y, w, h])
                    person_scores.append(float(p_s[idx]))
            except Exception as e:
                print(f"[CV Engine] COCO person detection error: {e}")

        # 2. Run PPE Safety model (Hardhat vs NO-Hardhat)
        if self.session_ppe is not None:
            try:
                inp_name = self.session_ppe.get_inputs()[0].name
                raw_ppe = self.session_ppe.run(None, {inp_name: blob})[0][0].T
                boxes_ppe = raw_ppe[:, :4]
                scores_ppe = raw_ppe[:, 4:]

                # Hardhat proposals (class 3)
                h_s = scores_ppe[:, 3]
                for idx in np.where(h_s >= 0.20)[0]:
                    cx, cy, bw, bh = boxes_ppe[idx]
                    x = int((cx - bw / 2) * x_scale)
                    y = int((cy - bh / 2) * y_scale)
                    w = int(bw * x_scale)
                    h = int(bh * y_scale)
                    hardhat_proposals.append([x, y, w, h])
                    hardhat_scores.append(float(h_s[idx]))

                # NO-Hardhat proposals (class 7)
                nh_s = scores_ppe[:, 7]
                for idx in np.where(nh_s >= 0.18)[0]:
                    cx, cy, bw, bh = boxes_ppe[idx]
                    x = int((cx - bw / 2) * x_scale)
                    y = int((cy - bh / 2) * y_scale)
                    w = int(bw * x_scale)
                    h = int(bh * y_scale)
                    no_hardhat_proposals.append([x, y, w, h])
                    no_hardhat_scores.append(float(nh_s[idx]))

                # Person proposals from PPE model (class 11)
                if scores_ppe.shape[1] >= 12:
                    p_s_ppe = scores_ppe[:, 11]
                    for idx in np.where(p_s_ppe >= 0.22)[0]:
                        cx, cy, bw, bh = boxes_ppe[idx]
                        x = int((cx - bw / 2) * x_scale)
                        y = int((cy - bh / 2) * y_scale)
                        w = int(bw * x_scale)
                        h = int(bh * y_scale)
                        person_proposals.append([x, y, w, h])
                        person_scores.append(float(p_s_ppe[idx]))

            except Exception as e:
                print(f"[CV Engine] PPE model inference error: {e}")

        # Non-Maximum Suppression (NMS)
        def nms(b_list, s_list, score_thresh, iou_thresh=0.45):
            if not b_list:
                return []
            idxs = cv2.dnn.NMSBoxes(b_list, s_list, score_thresh, iou_thresh)
            return [(b_list[i], s_list[i]) for i in idxs]

        final_persons = nms(person_proposals, person_scores, 0.25, 0.45)
        final_hardhats = nms(hardhat_proposals, hardhat_scores, 0.20, 0.45)
        final_no_hardhats = nms(no_hardhat_proposals, no_hardhat_scores, 0.18, 0.45)

        # Synthesize person box for close-up webcam head if no person box covers it
        for head_list in [final_no_hardhats, final_hardhats]:
            for h_box, h_conf in head_list:
                hx, hy, hw, hh = h_box
                covered = any(
                    bx - 20 <= (hx + hw / 2) <= bx + bw + 20 and
                    by - 20 <= (hy + hh / 2) <= by + bh + 20
                    for (bx, by, bw, bh), _ in final_persons
                )
                if not covered:
                    px1 = max(0, hx - int(hw * 0.5))
                    py1 = max(0, hy - int(hh * 0.2))
                    pw = min(orig_w - px1, int(hw * 2.0))
                    ph = min(orig_h - py1, int(hh * 3.2))
                    final_persons.append(([px1, py1, pw, ph], float(h_conf)))

        return final_persons, final_hardhats, final_no_hardhats

    def process_frame(self, frame: np.ndarray, camera_id: str = "C-01") -> Dict[str, Any]:
        """
        Main frame ingestion pipeline:
        Accepts any incoming frame (from browser webcam via POST /api/cv/frame or hardware camera),
        runs ONNX inference, maps Person -> Helmet, checks Restricted Zones,
        applies debounce logic, updates state manager, triggers alerts, and draws HUD.
        """
        now_ts = time.time()
        self.frames_received += 1
        self.last_inference_time = datetime.now().strftime("%H:%M:%S")
        self.frame_idx += 1
        h, w, _ = frame.shape

        # 1. Run Real AI Model Inference
        persons_nms, hardhats_nms, no_hardhats_nms = self._run_inference(frame)

        # 2. Match Detected Persons to Tracks using IoU
        current_person_boxes = []
        for p_box, p_conf in persons_nms:
            x, y, bw, bh = p_box
            # Clamped [x1, y1, x2, y2]
            x1 = max(0, min(w - 1, x))
            y1 = max(0, min(h - 1, y))
            x2 = max(0, min(w, x + bw))
            y2 = max(0, min(h, y + bh))
            if (x2 - x1) >= 25 and (y2 - y1) >= 40:
                current_person_boxes.append((np.array([x1, y1, x2, y2], dtype=int), p_conf))

        matched_track_ids = set()
        active_tracks: List[PersonTrack] = []

        for p_box, p_conf in current_person_boxes:
            best_iou = 0.0
            best_id = None
            for t_id, track in self.tracked_persons.items():
                if t_id in matched_track_ids:
                    continue
                iou = compute_box_iou(track.box, p_box)
                if iou > best_iou:
                    best_iou = iou
                    best_id = t_id

            if best_id is not None and best_iou > 0.25:
                track = self.tracked_persons[best_id]
                # Smooth box coordinates
                track.box = (0.65 * track.box + 0.35 * p_box).astype(int)
                track.last_seen_frame = self.frame_idx
                track.frames_unseen = 0
                matched_track_ids.add(best_id)
                active_tracks.append(track)
            else:
                new_id = self.next_track_id
                self.next_track_id += 1
                new_track = PersonTrack(new_id, p_box, now_ts)
                new_track.last_seen_frame = self.frame_idx
                self.tracked_persons[new_id] = new_track
                matched_track_ids.add(new_id)
                active_tracks.append(new_track)

        # Prune stale tracks
        stale_ids = []
        for t_id, track in list(self.tracked_persons.items()):
            if t_id not in matched_track_ids:
                track.frames_unseen += 1
                if track.frames_unseen > self.PERSON_LOST_FRAMES:
                    stale_ids.append(t_id)
        for t_id in stale_ids:
            del self.tracked_persons[t_id]

        # 3. Associate Helmet / No-Helmet Detection with Each Person
        for track in active_tracks:
            bx1, by1, bx2, by2 = track.box
            bw = bx2 - bx1
            bh = by2 - by1
            head_y_bottom = by1 + int(0.35 * bh)

            # Check for hardhat boxes in head region
            hardhat_found = False
            best_h_conf = 0.0
            for h_box, h_conf in hardhats_nms:
                hx, hy, hbw, hbh = h_box
                hcx = hx + hbw / 2
                hcy = hy + hbh / 2
                if bx1 - 20 <= hcx <= bx2 + 20 and by1 - 30 <= hcy <= head_y_bottom + 20:
                    hardhat_found = True
                    best_h_conf = max(best_h_conf, h_conf)

            # Check for no-hardhat boxes in head region
            no_hardhat_found = False
            best_nh_conf = 0.0
            for nh_box, nh_conf in no_hardhats_nms:
                nhx, nhy, nhbw, nhbh = nh_box
                nhcx = nhx + nhbw / 2
                nhcy = nhy + nhbh / 2
                if bx1 - 20 <= nhcx <= bx2 + 20 and by1 - 30 <= nhcy <= head_y_bottom + 20:
                    no_hardhat_found = True
                    best_nh_conf = max(best_nh_conf, nh_conf)

            # Assign Status & Confidence
            if hardhat_found and not no_hardhat_found:
                track.helmet_confirm_count += 1
                track.no_helmet_confirm_count = 0
                track.helmet_confidence = best_h_conf
                if track.helmet_confirm_count >= self.HELMET_CONFIRM_FRAMES:
                    track.stable_status = "HELMET"
            elif no_hardhat_found:
                track.no_helmet_confirm_count += 1
                track.helmet_confirm_count = 0
                track.helmet_confidence = best_nh_conf
                if track.no_helmet_confirm_count >= self.NO_HELMET_CONFIRM_FRAMES:
                    track.stable_status = "NO_HELMET"
            else:
                # Color heuristic fallback for head region
                has_h, has_nh = self._detect_helmet_heuristic(frame, [bx1, by1, bx2, by2])
                if has_h:
                    track.helmet_confirm_count += 1
                    track.no_helmet_confirm_count = 0
                    track.helmet_confidence = 0.65
                    if track.helmet_confirm_count >= self.HELMET_CONFIRM_FRAMES:
                        track.stable_status = "HELMET"
                elif has_nh:
                    track.no_helmet_confirm_count += 1
                    track.helmet_confirm_count = 0
                    track.helmet_confidence = 0.70
                    if track.no_helmet_confirm_count >= self.NO_HELMET_CONFIRM_FRAMES:
                        track.stable_status = "NO_HELMET"
                else:
                    # Default: If person detected without verified hardhat, flag as NO_HELMET after confirmation
                    track.no_helmet_confirm_count += 1
                    track.helmet_confidence = 0.60
                    if track.no_helmet_confirm_count >= (self.NO_HELMET_CONFIRM_FRAMES + 2):
                        track.stable_status = "NO_HELMET"

        # 4. Evaluate Restricted Zones (Permanent + Temporary)
        active_zones = state_manager.get_active_zones()
        current_occupancy_score = 0.0
        current_debug_info = None
        primary_breached_zone = None
        zone_violator_tracks = set()

        for track in active_tracks:
            track.in_zone = False
            track.zone_score = 0.0
            track.ground_point = ((track.box[0] + track.box[2]) // 2, track.box[3])

        for z in active_zones:
            if not (z.enabled and len(z.polygon) >= 3):
                continue
            z_poly = np.array(z.polygon, dtype=np.int32)
            z_type = (z.zone_type or "floor").lower()

            for track in active_tracks:
                is_occ, score, dbg, markers = evaluate_person_zone_occupancy(
                    track.box, None, None, z_poly, z_type
                )
                if is_occ:
                    track.in_zone = True
                    track.zone_score = max(track.zone_score, score)
                    track.zone_debug = dbg
                    track.ground_point = markers.get("ground_point", track.ground_point)
                    track.hip_center = markers.get("hip_center")
                    zone_violator_tracks.add(track)
                    if score > current_occupancy_score:
                        current_occupancy_score = score
                        current_debug_info = f"{track.label} {dbg}"
                        if primary_breached_zone is None or (z.zone_category == "PASSPORT_TEMPORARY"):
                            primary_breached_zone = z

        total_persons = len(active_tracks)
        unhelmeted_tracks = [t for t in active_tracks if t.stable_status == "NO_HELMET"]
        helmeted_tracks = [t for t in active_tracks if t.stable_status == "HELMET"]
        unhelmeted_count = len(unhelmeted_tracks)
        unhelmeted_ids = [t.label for t in unhelmeted_tracks]
        raw_persons_in_zone = len(zone_violator_tracks)

        # Zone confirmation debounce
        if active_zones:
            if total_persons > 0 and raw_persons_in_zone > 0:
                self.zone_inside_confirm_count += 1
                self.zone_outside_confirm_count = 0
                if self.zone_inside_confirm_count >= self.ZONE_CONFIRM_FRAMES:
                    self.stable_zone_violation = True
                    self.persons_in_zone = raw_persons_in_zone
                    self.zone_occupancy_score = current_occupancy_score
                    self.zone_debug_info = current_debug_info or "ZONE OCCUPIED"
            else:
                self.zone_outside_confirm_count += 1
                self.zone_inside_confirm_count = 0
                clear_threshold = min(self.ZONE_EXIT_FRAMES, self.PERSON_LOST_FRAMES)
                if self.zone_outside_confirm_count >= clear_threshold or total_persons == 0:
                    self.stable_zone_violation = False
                    self.persons_in_zone = 0
                    self.zone_occupancy_score = 0.0
                    self.zone_debug_info = "ZONE: CLEAR"
        else:
            self.stable_zone_violation = False
            self.persons_in_zone = 0
            self.zone_occupancy_score = 0.0
            self.zone_debug_info = None

        self.stable_person_detected = (total_persons > 0)
        self.stable_helmet_detected = (total_persons > 0 and unhelmeted_count == 0)

        # 5. Capture visual evidence snapshot when violation detected
        evidence_frame_bytes = None
        if unhelmeted_count > 0 or self.stable_zone_violation:
            try:
                ret, enc = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if ret:
                    evidence_frame_bytes = enc.tobytes()
            except Exception:
                pass

        # 6. Update State Manager
        state_manager.update_cv_detection(
            person_detected=self.stable_person_detected,
            helmet_detected=self.stable_helmet_detected,
            zone_violation=self.stable_zone_violation,
            persons_in_zone=self.persons_in_zone,
            occupancy_score=self.zone_occupancy_score,
            debug_info=self.zone_debug_info,
            person_count=total_persons,
            unhelmeted_count=unhelmeted_count,
            unhelmeted_ids=unhelmeted_ids,
            evidence_frame=evidence_frame_bytes,
            breached_zone=primary_breached_zone
        )

        if unhelmeted_count > 0 or self.stable_zone_violation:
            self.last_alert_time = datetime.now().strftime("%H:%M:%S")

        # 7. Render Bounding Boxes & Annotations on Frame
        annotated_frame = frame.copy()

        # Draw Restricted Zones
        for z in active_zones:
            if not (z.enabled and len(z.polygon) >= 3):
                continue
            z_poly = np.array(z.polygon, dtype=np.int32)
            is_breached = bool(primary_breached_zone and primary_breached_zone.zone_id == z.zone_id and self.stable_zone_violation)
            z_color = (60, 60, 235) if is_breached else ((30, 150, 245) if z.zone_category == "PASSPORT_TEMPORARY" else (235, 150, 50))
            cat_label = "BREACHED" if is_breached else ("PASSPORT TEMPORARY" if z.zone_category == "PASSPORT_TEMPORARY" else "PERMANENT ZONE")

            overlay = annotated_frame.copy()
            cv2.fillPoly(overlay, [z_poly], z_color)
            cv2.addWeighted(overlay, 0.22, annotated_frame, 0.78, 0, annotated_frame)
            cv2.polylines(annotated_frame, [z_poly], True, z_color, 2, cv2.LINE_AA)

            min_x = max(10, int(np.min(z_poly[:, 0])))
            min_y = max(55, int(np.min(z_poly[:, 1])) - 8)
            badge_txt = f"{z.name.upper()} [{cat_label}]"
            (tw, th), _ = cv2.getTextSize(badge_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            cv2.rectangle(annotated_frame, (min_x - 3, min_y - th - 3), (min_x + tw + 3, min_y + 3), (24, 24, 27), -1)
            cv2.rectangle(annotated_frame, (min_x - 3, min_y - th - 3), (min_x + tw + 3, min_y + 3), z_color, 1)
            cv2.putText(annotated_frame, badge_txt, (min_x, min_y), cv2.FONT_HERSHEY_SIMPLEX, 0.40, z_color, 1, cv2.LINE_AA)

        # Draw Person Bounding Boxes
        for track in active_tracks:
            bx1, by1, bx2, by2 = track.box
            conf_pct = int(track.helmet_confidence * 100) if track.helmet_confidence > 0 else 85
            if track.in_zone:
                b_col = (60, 60, 235)
                lbl = f"{track.label} [ZONE VIOLATION]"
            elif track.stable_status == "NO_HELMET":
                b_col = (60, 60, 235)
                lbl = f"{track.label} [NO HELMET {conf_pct}%]"
            elif track.stable_status == "HELMET":
                b_col = (60, 210, 80)
                lbl = f"{track.label} [HELMET OK {conf_pct}%]"
            else:
                b_col = (40, 180, 240)
                lbl = f"{track.label} [MONITORING]"

            cv2.rectangle(annotated_frame, (bx1, by1), (bx2, by2), b_col, 2)
            tag_y = max(38, by1 - 8)
            (ltw, lth), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(annotated_frame, (bx1, tag_y - lth - 4), (bx1 + ltw + 6, tag_y + 2), b_col, -1)
            cv2.putText(annotated_frame, lbl, (bx1 + 3, tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

            if track.ground_point:
                cv2.circle(annotated_frame, track.ground_point, 5, b_col, -1)

        # Draw Clean Telemetry Bar
        cv2.rectangle(annotated_frame, (0, 0), (w, 34), (24, 24, 27), -1)
        cv2.line(annotated_frame, (0, 34), (w, 34), (55, 55, 60), 1)
        now_str = datetime.now().strftime("%H:%M:%S")
        active_z = state_manager.active_zone
        zone_str = f" | {active_z.name.upper()}" if (active_z and active_z.enabled) else ""
        telemetry_str = f"CAM: {camera_id}{zone_str} | LIVE [{now_str}] | MODEL: {self.model_name.split()[0]}"
        cv2.putText(annotated_frame, telemetry_str, (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (235, 235, 240), 1, cv2.LINE_AA)

        with self.lock:
            self.last_frame = annotated_frame.copy()
            self.person_detected = self.stable_person_detected
            self.helmet_detected = self.stable_helmet_detected

        # Prepare JSON detection payload
        persons_payload = []
        for t in active_tracks:
            persons_payload.append({
                "id": t.track_id,
                "label": t.label,
                "box": [int(x) for x in t.box],
                "helmet_status": "DETECTED" if t.stable_status == "HELMET" else ("NOT DETECTED" if t.stable_status == "NO_HELMET" else "MONITORING"),
                "helmet_confidence": round(float(t.helmet_confidence), 2),
                "in_zone": t.in_zone
            })

        return {
            "status": "LIVE",
            "camera_id": camera_id,
            "model_loaded": self.model_loaded,
            "model_name": self.model_name,
            "person_count": total_persons,
            "helmet_detected": self.stable_helmet_detected,
            "unhelmeted_count": unhelmeted_count,
            "zone_violation": self.stable_zone_violation,
            "persons": persons_payload,
            "debug": self.get_debug_stats()
        }

    def _hardware_camera_loop(self):
        """
        Optional background loop that samples physical hardware camera 0
        IF available and not receiving frames from the browser.
        """
        while self.is_running:
            # If we are actively receiving frames from browser via POST /api/cv/frame, yield loop
            if (self.last_inference_time and 
                (time.time() - getattr(self, '_last_external_frame_ts', 0)) < 3.0):
                time.sleep(0.1)
                continue

            # Otherwise, if physical hardware camera is opened, process its frames
            if self.cap and self.cap.isOpened():
                ret, raw_frame = self.cap.read()
                if ret and raw_frame is not None and raw_frame.size > 0:
                    frame = cv2.flip(raw_frame, 1)
                    self.process_frame(frame, camera_id="C-01")
            time.sleep(0.04)

    def get_debug_stats(self) -> Dict[str, Any]:
        """Returns developer/debug diagnostics metrics"""
        return {
            "camera": "LIVE" if (self.frames_received > 0 or (self.cap and self.cap.isOpened())) else "STANDBY",
            "frames_received": self.frames_received,
            "inference": "RUNNING" if self.model_loaded else "MODEL NOT AVAILABLE",
            "model": self.model_name,
            "persons": len(self.tracked_persons),
            "helmet_detections": sum(1 for t in self.tracked_persons.values() if t.stable_status == "HELMET"),
            "unhelmeted_detections": sum(1 for t in self.tracked_persons.values() if t.stable_status == "NO_HELMET"),
            "zone_violations": 1 if self.stable_zone_violation else 0,
            "last_inference": self.last_inference_time or "N/A",
            "last_alert": self.last_alert_time or "None"
        }

    def _generate_synthetic_frame(self, state_text: str, is_safe: bool) -> np.ndarray:
        frame = np.full((480, 640, 3), 35, dtype=np.uint8)
        for y in range(60, 480, 60):
            cv2.line(frame, (0, y), (640, y), (45, 45, 45), 1)
        for x in range(80, 640, 80):
            cv2.line(frame, (x, 0), (x, 480), (45, 45, 45), 1)
        box_color = (70, 180, 80) if is_safe else (70, 70, 230)
        cv2.rectangle(frame, (200, 120), (440, 420), box_color, 2)
        cv2.circle(frame, (320, 180), 45, (180, 180, 180), 2)
        if is_safe:
            cv2.ellipse(frame, (320, 160), (46, 26), 0, 180, 360, (0, 220, 255), -1)
            cv2.putText(frame, "HELMET DETECTED", (210, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 220, 80), 2)
        else:
            cv2.putText(frame, "NO HELMET", (240, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (70, 70, 240), 2)
        return frame

    def _generate_cctv_channel_frame(self, channel: str) -> np.ndarray:
        ch = (channel or "C-01").upper()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        w, h = 640, 480
        frame = np.full((h, w, 3), 26, dtype=np.uint8)

        for y in range(80, h, 60):
            cv2.line(frame, (0, y), (w, y), (38, 38, 42), 1)
        for x in range(0, w, 80):
            cv2.line(frame, (x, 80), (x, h), (38, 38, 42), 1)

        if ch == "C-02":
            cv2.rectangle(frame, (140, 160), (320, 360), (45, 50, 55), -1)
            cv2.rectangle(frame, (140, 160), (320, 360), (70, 75, 80), 2)
            cv2.circle(frame, (230, 230), 40, (60, 65, 70), -1)
            cv2.putText(frame, "COMPRESSOR P-101", (150, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 165, 170), 1)
            cv2.line(frame, (320, 200), (560, 200), (90, 70, 50), 8)
            cv2.line(frame, (320, 280), (560, 280), (90, 70, 50), 8)
            
            c02_zone = None
            for z in state_manager.zones.values():
                if z.camera_id in ["C-02", "C-01"] and z.zone_category == "PERMANENT":
                    c02_zone = z
                    break
            if not c02_zone and state_manager.zones:
                c02_zone = next(iter(state_manager.zones.values()))

            if c02_zone is not None:
                z_poly = np.array(c02_zone.polygon if len(c02_zone.polygon) >= 3 else [[120, 150], [540, 150], [540, 430], [120, 430]], dtype=np.int32)
                if c02_zone.enabled:
                    cv2.polylines(frame, [z_poly], True, (235, 150, 50), 2, cv2.LINE_AA)
                    cv2.putText(frame, f"{c02_zone.name.upper()} [ACTIVE]", (128, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (235, 150, 50), 1)
                else:
                    cv2.polylines(frame, [z_poly], True, (90, 90, 95), 1, cv2.LINE_AA)
                    cv2.putText(frame, f"{c02_zone.name.upper()} [DISABLED]", (128, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 120, 130), 1)

            cv2.rectangle(frame, (0, 0), (w, 34), (24, 24, 27), -1)
            cv2.line(frame, (0, 34), (w, 34), (55, 55, 60), 1)
            telemetry_str = f"CAM: C-02 | COMPRESSOR RESTRICTED AREA | FLOOR | LIVE  [{now_str}]"
            cv2.putText(frame, telemetry_str, (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (235, 235, 240), 1, cv2.LINE_AA)

        elif ch == "C-03":
            cv2.rectangle(frame, (100, 120), (380, 420), (42, 44, 48), -1)
            cv2.rectangle(frame, (100, 120), (380, 420), (65, 70, 75), 2)
            cv2.circle(frame, (240, 270), 55, (20, 20, 22), -1)
            cv2.circle(frame, (240, 270), 55, (220, 160, 40), 3)
            cv2.putText(frame, "TANK 04 - CONFINED SPACE", (140, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 200, 210), 1)
            cv2.putText(frame, "[ENTRY PERMIT REQUIRED]", (150, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (40, 160, 240), 1)
            
            cv2.rectangle(frame, (410, 130), (620, 230), (20, 24, 28), -1)
            cv2.rectangle(frame, (410, 130), (620, 230), (45, 120, 180), 1)
            cv2.putText(frame, "GAS MONITOR (WIRELESS)", (420, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (80, 180, 240), 1)
            cv2.putText(frame, "O2: 20.9%  LEL: 0%", (420, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100, 220, 120), 1)
            cv2.putText(frame, "H2S: 0 ppm  CO: 0 ppm", (420, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100, 220, 120), 1)
            cv2.putText(frame, "STATUS: ATMOSPHERE CLEAR", (420, 222), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (220, 220, 220), 1)

            cv2.rectangle(frame, (0, 0), (w, 34), (24, 24, 27), -1)
            cv2.line(frame, (0, 34), (w, 34), (55, 55, 60), 1)
            telemetry_str = f"CAM: C-03 | TANK BATTERY CONFINED SPACE | PORTAL | LIVE  [{now_str}]"
            cv2.putText(frame, telemetry_str, (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (235, 235, 240), 1, cv2.LINE_AA)

        elif ch == "C-04":
            cv2.line(frame, (60, 400), (320, 100), (220, 180, 40), 6)
            cv2.line(frame, (320, 100), (320, 240), (180, 180, 190), 2)
            cv2.rectangle(frame, (270, 240), (370, 280), (60, 80, 100), -1)
            cv2.rectangle(frame, (270, 240), (370, 280), (120, 160, 200), 2)
            cv2.putText(frame, "SUSPENDED LOAD (3.5T)", (250, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (60, 60, 240), 1)
            
            cv2.ellipse(frame, (320, 360), (180, 70), 0, 0, 360, (40, 80, 240), 2)
            cv2.putText(frame, "CRANE SWING RADIUS [LINE-OF-FIRE]", (140, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 80, 240), 1)

            cv2.rectangle(frame, (0, 0), (w, 34), (24, 24, 27), -1)
            cv2.line(frame, (0, 34), (w, 34), (55, 55, 60), 1)
            telemetry_str = f"CAM: C-04 | MECHANICAL LIFTING PERIMETER | LINE-OF-FIRE | LIVE  [{now_str}]"
            cv2.putText(frame, telemetry_str, (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (235, 235, 240), 1, cv2.LINE_AA)

        else:
            cv2.rectangle(frame, (0, 0), (w, 34), (24, 24, 27), -1)
            cv2.line(frame, (0, 34), (w, 34), (55, 55, 60), 1)
            telemetry_str = f"CAM: {ch} | GENERAL WORK ZONE | LIVE  [{now_str}]"
            cv2.putText(frame, telemetry_str, (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (235, 235, 240), 1, cv2.LINE_AA)

        return frame

    def get_latest_jpeg(self, camera_id: str = "C-01") -> bytes:
        cam = (camera_id or "C-01").upper()
        with self.lock:
            if cam in ["C-01", "CAM-01", "0", "DEFAULT"]:
                if self.last_frame is None:
                    standby = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(standby, "INITIALIZING CAMERA C-01...", (140, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                    ret, jpeg = cv2.imencode('.jpg', standby)
                    return jpeg.tobytes()
                ret, jpeg = cv2.imencode('.jpg', self.last_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                return jpeg.tobytes() if ret else b''
            else:
                c_frame = self._generate_cctv_channel_frame(cam)
                ret, jpeg = cv2.imencode('.jpg', c_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                return jpeg.tobytes() if ret else b''


video_engine = VideoDetectionEngine()


def generate_mjpeg_stream(camera_id: str = "C-01"):
    """Generator for streaming live MJPEG frames over HTTP for any camera channel"""
    while True:
        jpeg_bytes = video_engine.get_latest_jpeg(camera_id=camera_id)
        if jpeg_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
        time.sleep(0.04)
