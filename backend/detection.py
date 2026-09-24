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


def resolve_competing_hand_hypotheses(
    gloves_proposals: List[List[int]], 
    gloves_scores: List[float], 
    no_gloves_proposals: List[List[int]], 
    no_gloves_scores: List[float], 
    orig_w: int, 
    orig_h: int,
    iou_thresh: float = 0.35, 
    margin_thresh: float = 0.20
) -> List[Dict[str, Any]]:
    """
    Strict Mutual Exclusion Engine for Hand Detections.
    Ensures that for any physical hand region, the system reports at most ONE state:
    GLOVES, NO_GLOVES, or UNKNOWN (suppressed from output). Never both.
    
    1. Spurious filter: Discard oversized boxes (w > 0.55 * orig_w and h > 0.55 * orig_h).
    2. Overlap & Competition: For pairs with IoU >= iou_thresh:
       - If different classes (Gloves vs NO-Gloves):
         - If abs(conf_G - conf_NG) < margin_thresh: Ambiguous/close -> UNKNOWN (suppress both).
         - If conf_G >= conf_NG + margin_thresh: GLOVES wins.
         - If conf_NG >= conf_G + margin_thresh: NO_GLOVES wins.
       - If same class: The higher confidence anchor suppresses the duplicate.
    3. Intra-class NMS: Surviving winners are deduplicated so only 1 box per physical hand remains.
    """
    all_candidates = []
    max_hand_w = int(orig_w * 0.55)
    max_hand_h = int(orig_h * 0.55)

    for b, s in zip(gloves_proposals, gloves_scores):
        if b[2] <= max_hand_w and b[3] <= max_hand_h:
            all_candidates.append({
                "box": b,
                "conf": float(s),
                "type": "GLOVES",
                "is_glove": True
            })

    for b, s in zip(no_gloves_proposals, no_gloves_scores):
        if b[2] <= max_hand_w and b[3] <= max_hand_h:
            all_candidates.append({
                "box": b,
                "conf": float(s),
                "type": "NO_GLOVES",
                "is_glove": False
            })

    if not all_candidates:
        return []

    # Sort all candidates by confidence descending
    all_candidates.sort(key=lambda c: c["conf"], reverse=True)

    # Cross-class hypothesis resolution
    resolved_candidates = []
    suppressed_indices = set()

    for i in range(len(all_candidates)):
        if i in suppressed_indices:
            continue
        c_i = all_candidates[i]
        b_i = [c_i["box"][0], c_i["box"][1], c_i["box"][0] + c_i["box"][2], c_i["box"][1] + c_i["box"][3]]

        is_ambiguous = False
        winner = c_i

        for j in range(i + 1, len(all_candidates)):
            if j in suppressed_indices:
                continue
            c_j = all_candidates[j]
            b_j = [c_j["box"][0], c_j["box"][1], c_j["box"][0] + c_j["box"][2], c_j["box"][1] + c_j["box"][3]]
            
            iou = compute_box_iou(b_i, b_j)
            if iou >= iou_thresh:
                # Overlapping detections on the same physical hand region
                if c_i["type"] != c_j["type"]:
                    # Competing hypotheses: one is GLOVES, one is NO_GLOVES
                    conf_diff = abs(c_i["conf"] - c_j["conf"])
                    if conf_diff < margin_thresh:
                        # Ambiguous: e.g. 0.51 vs 0.49 -> UNKNOWN
                        is_ambiguous = True
                        suppressed_indices.add(j)
                    else:
                        # The higher confidence candidate wins (c_i since candidates are sorted)
                        suppressed_indices.add(j)
                else:
                    # Same class duplicate proposal on the same hand -> suppress lower confidence one
                    suppressed_indices.add(j)

        if not is_ambiguous:
            resolved_candidates.append(winner)
        else:
            suppressed_indices.add(i)

    return resolved_candidates


def extract_person_crop(frame: np.ndarray, box: Any, padding_pct: float = 0.10) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Extracts an individual image crop of a tracked person with natural proportions and small padding (10%).
    Guarantees natural aspect ratio without stretching, clamped cleanly to frame bounds.
    Returns (jpeg_bytes, base64_data_uri).
    """
    try:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        pad_x = int(bw * padding_pct)
        pad_y = int(bh * padding_pct)
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(w, x2 + pad_x)
        cy2 = min(h, y2 + pad_y)
        if cx2 <= cx1 or cy2 <= cy1:
            return None, None
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            return None, None
        ret, enc = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if not ret:
            return None, None
        crop_bytes = enc.tobytes()
        crop_b64 = f"data:image/jpeg;base64,{base64.b64encode(crop_bytes).decode('utf-8')}"
        return crop_bytes, crop_b64
    except Exception:
        return None, None


class PersonTrack:
    """Lightweight person tracking record across video frames with PPE (Helmet, Vest, Gloves) & Zone tracking"""
    def __init__(self, track_id: int, box: np.ndarray, now_ts: float):
        self.track_id = track_id
        self.label = f"Person #{track_id}"
        self.box = np.array(box, dtype=int)
        self.last_seen_frame = 0
        self.frames_unseen = 0
        self.first_detected_at = now_ts
        
        # Helmet detection: "HELMET", "NO_HELMET", "UNKNOWN"
        self.helmet_confirm_count = 0
        self.no_helmet_confirm_count = 0
        self.stable_status = "UNKNOWN"
        self.helmet_confidence = 0.0
        
        # Safety Vest detection: "VEST", "NO_VEST", "UNKNOWN"
        self.vest_confirm_count = 0
        self.no_vest_confirm_count = 0
        self.vest_status = "UNKNOWN"
        self.vest_confidence = 0.0
        
        # Gloves detection: "GLOVES", "NO_GLOVES", "UNKNOWN"
        self.gloves_confirm_count = 0
        self.no_gloves_confirm_count = 0
        self.gloves_status = "UNKNOWN"
        self.gloves_confidence = 0.0
        self.hand_boxes: List[Dict[str, Any]] = []
        
        # Zone tracking
        self.in_zone = False
        self.zone_score = 0.0
        self.zone_debug = None
        self.ground_point = None
        self.hip_center = None

        # Person-wise Evidence & Overall PPE Status
        self.is_head_synthesized = False
        self.overall_ppe_status = "UNKNOWN" # "OK", "VIOLATION", "UNKNOWN"
        self.best_crop_bytes: Optional[bytes] = None
        self.best_crop_base64: Optional[str] = None
        self.best_crop_conf: float = 0.0

    def clear(self):
        self.box = np.array([0, 0, 0, 0], dtype=int)
        self.stable_status = "UNKNOWN"
        self.helmet_confirm_count = 0
        self.no_helmet_confirm_count = 0
        self.helmet_confidence = 0.0
        self.vest_confirm_count = 0
        self.no_vest_confirm_count = 0
        self.vest_status = "UNKNOWN"
        self.vest_confidence = 0.0
        self.gloves_confirm_count = 0
        self.no_gloves_confirm_count = 0
        self.gloves_status = "UNKNOWN"
        self.gloves_confidence = 0.0
        self.hand_boxes = []
        self.in_zone = False
        self.zone_score = 0.0
        self.zone_debug = None
        self.ground_point = None
        self.hip_center = None
        self.is_head_synthesized = False
        self.overall_ppe_status = "UNKNOWN"
        self.best_crop_bytes = None
        self.best_crop_base64 = None
        self.best_crop_conf = 0.0


def extract_vehicle_crop(frame: np.ndarray, box: Any, padding_pct: float = 0.08) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Extracts an individual image crop of a detected vehicle with natural proportions and small padding (8%).
    Guarantees natural aspect ratio without stretching, clamped cleanly to frame bounds.
    Returns (jpeg_bytes, base64_data_uri).
    """
    try:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        pad_x = int(bw * padding_pct)
        pad_y = int(bh * padding_pct)
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(w, x2 + pad_x)
        cy2 = min(h, y2 + pad_y)
        if cx2 <= cx1 or cy2 <= cy1:
            return None, None
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            return None, None
        ret, enc = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if not ret:
            return None, None
        crop_bytes = enc.tobytes()
        crop_b64 = f"data:image/jpeg;base64,{base64.b64encode(crop_bytes).decode('utf-8')}"
        return crop_bytes, crop_b64
    except Exception:
        return None, None


class VehicleTrack:
    """Lightweight vehicle tracking record across video frames with proximity zone calculation"""
    def __init__(self, track_id: int, box: np.ndarray, class_name: str, confidence: float, now_ts: float):
        self.track_id = track_id
        self.label = f"Vehicle #{track_id}"
        self.class_name = class_name # "truck", "car", "bus", "motorcycle"
        self.box = np.array(box, dtype=int)
        self.confidence = float(confidence)
        self.last_seen_frame = 0
        self.frames_unseen = 0
        self.first_detected_at = now_ts
        self.proximity_zone: List[int] = [] # [zx1, zy1, zx2, zy2]
        self.best_crop_bytes: Optional[bytes] = None
        self.best_crop_base64: Optional[str] = None
        self.best_crop_conf: float = 0.0

    def clear(self):
        self.box = np.array([0, 0, 0, 0], dtype=int)
        self.proximity_zone = []
        self.best_crop_bytes = None
        self.best_crop_base64 = None
        self.best_crop_conf = 0.0


class VideoDetectionEngine:
    """
    Production-grade AI CCTV Detection Engine.
    Uses ONNX Runtime to execute real YOLO PPE/Helmet inference on CPU
    without PyTorch dependency, bypassing Windows 11 Smart App Control policies.
    """
    # Supported vehicle classes in COCO yolov8n.onnx
    COCO_VEHICLE_MAP = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

    def __init__(self):
        self.lock = threading.Lock()
        self.session: Optional[Any] = None
        self.model_loaded = False
        self.model_name = "UNAVAILABLE"
        self.is_custom_helmet_model = False
        self.COCO_VEHICLE_MAP = VideoDetectionEngine.COCO_VEHICLE_MAP
        
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
        self.vest_detected = False
        self.gloves_detected = False
        
        self.tracked_persons: Dict[int, PersonTrack] = {}
        self.next_track_id: int = 1
        self.tracked_vehicles: Dict[int, VehicleTrack] = {}
        self.next_vehicle_track_id: int = 1
        self.frame_idx: int = 0
        
        # Smoothing & Debounce state
        self.stable_person_detected = False
        self.stable_helmet_detected = False
        self.stable_vest_detected = False
        self.stable_gloves_detected = False
        self.stable_zone_violation = False
        self.persons_in_zone = 0
        self.zone_occupancy_score = 0.0
        self.zone_debug_info = None
        
        self.helmet_confirm_count = 0
        self.no_helmet_confirm_count = 0
        self.vest_confirm_count = 0
        self.no_vest_confirm_count = 0
        self.zone_inside_confirm_count = 0
        self.zone_outside_confirm_count = 0
        
        # Debounce settings (tuned for fast, responsive 10-12 FPS operation)
        self.HELMET_CONFIRM_FRAMES = 2
        self.NO_HELMET_CONFIRM_FRAMES = 2
        self.VEST_CONFIRM_FRAMES = 2
        self.NO_VEST_CONFIRM_FRAMES = 2
        self.FALL_CONFIRM_FRAMES = 5
        self.FALL_CLEAR_FRAMES = 4
        self.PERSON_CONFIRM_FRAMES = 1
        self.PERSON_LOST_FRAMES = 8
        self.ZONE_CONFIRM_FRAMES = 3
        self.ZONE_EXIT_FRAMES = 4
        self.VEHICLE_LOST_FRAMES = 10
        self.PROXIMITY_CONFIRM_FRAMES = 2
        self.PROXIMITY_CLEAR_FRAMES = 4
        self.proximity_pair_state: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        # Feature 3: Fire Detection debounce & state
        self.FIRE_CONFIRM_FRAMES = 2
        self.FIRE_CLEAR_FRAMES = 5
        self.fire_consecutive_count = 0
        self.fire_clear_count = 0
        self.fire_confirmed = False
        self.fire_alert_triggered = False
        self.confirmed_fires: List[Dict[str, Any]] = []
        self.last_fire_crop_bytes: Optional[bytes] = None
        self.last_fire_crop_b64: Optional[str] = None
        self.last_fire_conf: float = 0.0
        
        # Performance & Debug counters
        self.frames_received = 0
        self.last_inference_time = None
        self.last_alert_time = None
        self.total_helmet_detections = 0
        self.total_zone_violations = 0
        self.total_fall_detections = 0
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
        fire_model_path = os.path.join(base_dir, "fire_detection.onnx")
        
        self.session_ppe = None
        self.session_coco = None
        self.session_fire = None

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

        if os.path.exists(fire_model_path):
            try:
                print(f"[CV Engine] Loading Fire Detection ONNX model from {fire_model_path}...")
                self.session_fire = ort.InferenceSession(fire_model_path, opts, providers=['CPUExecutionProvider'])
                print(f"[CV Engine] Loaded fire_detection.onnx successfully! (Class 1: Fire, Class 0 Smoke discarded)")
            except Exception as e:
                print(f"[CV Engine] Failed to load fire_detection.onnx: {e}")

        if self.session_ppe is not None or self.session_coco is not None or self.session_fire is not None:
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

    def _detect_vest_heuristic(self, frame: np.ndarray, person_box: List[int]) -> Tuple[bool, bool]:
        """
        Color analysis of the torso region to detect high-vis safety vest colors (fluorescent yellow, neon orange, lime).
        Returns: (has_vest_evidence: bool, has_no_vest_evidence: bool)
        """
        x1, y1, x2, y2 = person_box
        h = y2 - y1
        w = x2 - x1
        if h <= 0 or w <= 0:
            return False, False
        
        # Guard: If torso is not sufficiently visible or cropped, do not produce vest evidence or absence
        frame_h = frame.shape[0]
        aspect = h / max(1, w)
        is_bottom_cropped = (y2 >= frame_h - 12) and (h < 240 or aspect < 1.45)
        if h < 140 or w < 35 or is_bottom_cropped or (aspect < 1.35 and h < 220):
            return False, False
        
        torso_top = min(frame.shape[0], int(y1 + 0.18 * h))
        torso_bottom = min(frame.shape[0], int(y1 + 0.70 * h))
        center_margin = int(w * 0.12)
        torso_left = max(0, x1 + center_margin)
        torso_right = min(frame.shape[1], x2 - center_margin)
        
        torso_crop = frame[torso_top:torso_bottom, torso_left:torso_right]
        if torso_crop.size == 0 or torso_crop.shape[0] < 15 or torso_crop.shape[1] < 15:
            return False, False
        
        hsv = cv2.cvtColor(torso_crop, cv2.COLOR_BGR2HSV)
        mask_yellow = cv2.inRange(hsv, np.array([24, 70, 70]), np.array([40, 255, 255]))
        mask_orange = cv2.inRange(hsv, np.array([5, 100, 90]), np.array([22, 255, 255]))
        mask_lime = cv2.inRange(hsv, np.array([36, 60, 60]), np.array([85, 255, 255]))
        
        hi_vis_mask = mask_yellow | mask_orange | mask_lime
        total_pixels = torso_crop.shape[0] * torso_crop.shape[1] + 1e-5
        ratio = np.sum(hi_vis_mask > 0) / total_pixels
        
        has_vest = (ratio >= 0.20)
        has_no_vest = (ratio <= 0.08)
        return has_vest, has_no_vest

    def _run_inference(self, frame: np.ndarray, model_mode: str = "both") -> Dict[str, Any]:
        """
        Executes real ONNX inference on a 640x640 preprocessed frame.
        Supports interleaved model execution for 10-12 FPS performance:
        - "coco": runs YOLOv8n COCO for Person and Vehicle detection (car, motorcycle, bus, truck)
        - "ppe": runs PPE safety model for Person, Hardhat, Vest, Gloves
        - "both": runs both models (used on initial frame 1 and when isolated)
        """
        empty_res = {
            "persons": [], "hardhats": [], "no_hardhats": [],
            "vests": [], "no_vests": [], "gloves": [], "no_gloves": [],
            "goggles": [], "no_goggles": [], "no_harness": [], "falls": [],
            "vehicles": [], "fires": []
        }
        if not self.model_loaded:
            return empty_res

        orig_h, orig_w = frame.shape[:2]
        resized = cv2.resize(frame, (640, 640))
        blob = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis, :]

        x_scale = orig_w / 640.0
        y_scale = orig_h / 640.0

        person_proposals, person_scores = [], []
        vehicle_proposals, vehicle_scores, vehicle_classes = [], [], []
        # COCO vehicle classes: 2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'
        COCO_VEHICLE_MAP = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
        hardhat_proposals, hardhat_scores = [], []
        no_hardhat_proposals, no_hardhat_scores = [], []
        vest_proposals, vest_scores = [], []
        no_vest_proposals, no_vest_scores = [], []
        gloves_proposals, gloves_scores = [], []
        no_gloves_proposals, no_gloves_scores = [], []
        fire_proposals, fire_scores = [], []

        # 1. Run COCO Person and Vehicle detection if available and scheduled
        run_coco = (self.session_coco is not None) and (model_mode in ("both", "coco") or self.session_ppe is None)
        if run_coco:
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

                # Extract vehicle proposals (car, motorcycle, bus, truck)
                for c_idx, c_name in COCO_VEHICLE_MAP.items():
                    v_s = raw_coco[:, 4 + c_idx]
                    v_idxs = np.where(v_s >= 0.28)[0]
                    for idx in v_idxs:
                        cx, cy, bw, bh = p_boxes[idx]
                        x = int((cx - bw / 2) * x_scale)
                        y = int((cy - bh / 2) * y_scale)
                        w = int(bw * x_scale)
                        h = int(bh * y_scale)
                        vehicle_proposals.append([x, y, w, h])
                        vehicle_scores.append(float(v_s[idx]))
                        vehicle_classes.append(c_name)
            except Exception as e:
                print(f"[CV Engine] COCO person/vehicle detection error: {e}")

        # 2. Run PPE Safety model for Person, Hardhat, Vest, and Gloves
        run_ppe = (self.session_ppe is not None) and (model_mode in ("both", "ppe") or self.session_coco is None)
        if run_ppe:
            try:
                inp_name = self.session_ppe.get_inputs()[0].name
                raw_ppe = self.session_ppe.run(None, {inp_name: blob})[0][0].T
                boxes_ppe = raw_ppe[:, :4]
                scores_ppe = raw_ppe[:, 4:]
                num_classes = scores_ppe.shape[1]

                def _extract_proposals(class_idx: int, thresh: float, p_list: list, s_list: list):
                    if class_idx < num_classes:
                        s_vec = scores_ppe[:, class_idx]
                        for idx in np.where(s_vec >= thresh)[0]:
                            cx, cy, bw, bh = boxes_ppe[idx]
                            x = int((cx - bw / 2) * x_scale)
                            y = int((cy - bh / 2) * y_scale)
                            w = int(bw * x_scale)
                            h = int(bh * y_scale)
                            p_list.append([x, y, w, h])
                            s_list.append(float(s_vec[idx]))

                # Class 1: Gloves (raw candidate threshold 0.18)
                _extract_proposals(1, 0.18, gloves_proposals, gloves_scores)
                # Class 3: Hardhat
                _extract_proposals(3, 0.18, hardhat_proposals, hardhat_scores)
                # Class 5: NO-Gloves (raw candidate threshold 0.18)
                _extract_proposals(5, 0.18, no_gloves_proposals, no_gloves_scores)
                # Class 7: NO-Hardhat (tuned to 0.16 for responsive small-head detection)
                _extract_proposals(7, 0.16, no_hardhat_proposals, no_hardhat_scores)
                # Class 9: NO-Safety Vest
                _extract_proposals(9, 0.18, no_vest_proposals, no_vest_scores)
                # Class 11: Person (from PPE model)
                _extract_proposals(11, 0.22, person_proposals, person_scores)
                # Class 12: Safety Vest
                _extract_proposals(12, 0.18, vest_proposals, vest_scores)

            except Exception as e:
                print(f"[CV Engine] PPE model inference error: {e}")

        # 3. Run Fire Detection model if available and scheduled
        run_fire = (self.session_fire is not None) and (model_mode in ("both", "fire", "all"))
        if run_fire:
            try:
                inp_name = self.session_fire.get_inputs()[0].name
                raw_fire = self.session_fire.run(None, {inp_name: blob})[0][0].T
                boxes_fire = raw_fire[:, :4]
                # Index 4 is smoke (DISCARD COMPLETELY), Index 5 is fire (USE THIS ONLY)
                fire_s = raw_fire[:, 5]
                fire_idxs = np.where(fire_s >= 0.28)[0]
                for idx in fire_idxs:
                    cx, cy, bw, bh = boxes_fire[idx]
                    x = int((cx - bw / 2) * x_scale)
                    y = int((cy - bh / 2) * y_scale)
                    w = int(bw * x_scale)
                    h = int(bh * y_scale)
                    fire_proposals.append([x, y, w, h])
                    fire_scores.append(float(fire_s[idx]))
            except Exception as e:
                print(f"[CV Engine] Fire model inference error: {e}")

        # Non-Maximum Suppression (NMS) for Person, Helmet, and Vest
        def nms(b_list, s_list, score_thresh, iou_thresh=0.45):
            if not b_list:
                return []
            idxs = cv2.dnn.NMSBoxes(b_list, s_list, score_thresh, iou_thresh)
            return [(b_list[i], s_list[i]) for i in idxs]

        final_persons = nms(person_proposals, person_scores, 0.25, 0.45)
        final_hardhats = nms(hardhat_proposals, hardhat_scores, 0.18, 0.45)
        final_no_hardhats = nms(no_hardhat_proposals, no_hardhat_scores, 0.16, 0.45)
        final_vests = nms(vest_proposals, vest_scores, 0.18, 0.45)
        final_no_vests = nms(no_vest_proposals, no_vest_scores, 0.18, 0.45)

        # Non-Maximum Suppression (NMS) for Vehicles (car, motorcycle, bus, truck)
        final_vehicles = []
        if vehicle_proposals:
            v_idxs = cv2.dnn.NMSBoxes(vehicle_proposals, vehicle_scores, 0.28, 0.45)
            for i in v_idxs:
                final_vehicles.append({
                    "box": vehicle_proposals[i],
                    "score": float(vehicle_scores[i]),
                    "class_name": vehicle_classes[i]
                })

        # Non-Maximum Suppression (NMS) for Fire (class 1 'fire' only)
        final_fires = []
        if fire_proposals:
            f_idxs = cv2.dnn.NMSBoxes(fire_proposals, fire_scores, 0.30, 0.45)
            for i in f_idxs:
                final_fires.append({
                    "box": fire_proposals[i],
                    "score": float(fire_scores[i]),
                    "label": "FIRE"
                })

        # Strictly Mutually Exclusive Hand Hypothesis Resolution
        resolved_hands = []
        final_gloves = []
        final_no_gloves = []
        if run_ppe and (gloves_proposals or no_gloves_proposals):
            resolved_hands = resolve_competing_hand_hypotheses(
                gloves_proposals, gloves_scores,
                no_gloves_proposals, no_gloves_scores,
                orig_w=orig_w, orig_h=orig_h,
                iou_thresh=0.35, margin_thresh=0.20
            )
            final_gloves = [(h["box"], h["conf"]) for h in resolved_hands if h["type"] == "GLOVES"]
            final_no_gloves = [(h["box"], h["conf"]) for h in resolved_hands if h["type"] == "NO_GLOVES"]

        # Synthesize person box for close-up webcam head if no person box covers it
        synthesized_boxes = []
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
                    synthesized_boxes.append([px1, py1, pw, ph])

        return {
            "persons": final_persons,
            "synthesized_boxes": synthesized_boxes,
            "hardhats": final_hardhats,
            "no_hardhats": final_no_hardhats,
            "vests": final_vests,
            "no_vests": final_no_vests,
            "resolved_hands": resolved_hands,
            "gloves": final_gloves,
            "no_gloves": final_no_gloves,
            "vehicles": final_vehicles,
            "fires": final_fires
        }

    def process_frame(self, frame: np.ndarray, camera_id: str = "C-01", frame_seq: int = 0) -> Dict[str, Any]:
        """
        Main frame ingestion pipeline:
        Accepts any incoming frame (from browser webcam via POST /api/cv/frame, demo video, or hardware camera),
        runs high-efficiency ONNX inference (10-12 FPS with interleaved scheduling),
        maps Person -> (Helmet, Safety Vest, Gloves, Goggles, Harness, Fall),
        tracks vehicles and computes proximity perimeters via ground-contact point,
        checks Restricted & Working-at-Height Zones, applies debounce logic,
        updates state manager, triggers alerts, and draws HUD.
        """
        now_ts = time.time()
        self.frames_received += 1
        self.last_inference_time = datetime.now().strftime("%H:%M:%S")
        self.frame_idx += 1
        h, w, _ = frame.shape

        # Determine interleaved model execution mode for high FPS (10-12 FPS)
        if self.session_coco is not None and self.session_ppe is not None:
            if self.frame_idx <= 1:
                model_mode = "both"
            elif self.session_fire is not None:
                mod = self.frame_idx % 4
                if mod == 0:
                    model_mode = "coco"
                elif mod == 1:
                    model_mode = "ppe"
                elif mod == 2:
                    model_mode = "fire"
                else:
                    model_mode = "ppe"
            elif self.frame_idx % 2 == 0:
                model_mode = "coco"
            else:
                model_mode = "ppe"
        else:
            model_mode = "both"

        # 1. Run Real AI Model Inference across scheduled model mode
        inf_res = self._run_inference(frame, model_mode=model_mode)
        persons_nms = inf_res.get("persons", [])
        synthesized_boxes = inf_res.get("synthesized_boxes", [])
        vehicles_nms = inf_res.get("vehicles", [])
        raw_fires_nms = inf_res.get("fires", [])
        hardhats_nms = inf_res.get("hardhats", [])
        no_hardhats_nms = inf_res.get("no_hardhats", [])
        vests_nms = inf_res.get("vests", [])
        no_vests_nms = inf_res.get("no_vests", [])
        gloves_nms = inf_res.get("gloves", [])
        no_gloves_nms = inf_res.get("no_gloves", [])
        goggles_nms = inf_res.get("goggles", [])
        no_goggles_nms = inf_res.get("no_goggles", [])
        no_harness_nms = inf_res.get("no_harness", [])
        falls_nms = inf_res.get("falls", [])

        # 2. Match Detected Persons to Tracks using IoU
        current_person_boxes = []
        for p_box, p_conf in persons_nms:
            x, y, bw, bh = p_box
            # Clamped [x1, y1, x2, y2]
            x1 = max(0, min(w - 1, x))
            y1 = max(0, min(h - 1, y))
            x2 = max(0, min(w, x + bw))
            y2 = max(0, min(h, y + bh))
            if (x2 - x1) >= 20 and (y2 - y1) >= 30:
                is_synth = any(compute_box_iou([x1, y1, x2, y2], [sb[0], sb[1], sb[0]+sb[2], sb[1]+sb[3]]) > 0.80 for sb in synthesized_boxes)
                current_person_boxes.append((np.array([x1, y1, x2, y2], dtype=int), p_conf, is_synth))

        matched_track_ids = set()
        active_tracks: List[PersonTrack] = []

        if model_mode in ("both", "coco", "ppe"):
            for p_box, p_conf, is_synth in current_person_boxes:
                best_iou = 0.0
                best_id = None
                for t_id, track in self.tracked_persons.items():
                    if t_id in matched_track_ids:
                        continue
                    iou = compute_box_iou(track.box, p_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_id = t_id

                if best_id is not None and best_iou > 0.20:
                    track = self.tracked_persons[best_id]
                    # Smooth box coordinates
                    track.box = (0.65 * track.box + 0.35 * p_box).astype(int)
                    track.is_head_synthesized = is_synth
                    track.last_seen_frame = self.frame_idx
                    track.frames_unseen = 0
                    matched_track_ids.add(best_id)
                    active_tracks.append(track)
                else:
                    new_id = self.next_track_id
                    self.next_track_id += 1
                    new_track = PersonTrack(new_id, p_box, now_ts)
                    new_track.is_head_synthesized = is_synth
                    new_track.last_seen_frame = self.frame_idx
                    self.tracked_persons[new_id] = new_track
                    matched_track_ids.add(new_id)
                    active_tracks.append(new_track)

            # Prune stale person tracks
            stale_ids = []
            for t_id, track in list(self.tracked_persons.items()):
                if t_id not in matched_track_ids:
                    track.frames_unseen += 1
                    if track.frames_unseen > self.PERSON_LOST_FRAMES:
                        stale_ids.append(t_id)
            for t_id in stale_ids:
                del self.tracked_persons[t_id]
        else:
            # On fire-only frames, preserve active person tracks without incrementing frames_unseen
            active_tracks = [t for t in self.tracked_persons.values() if t.frames_unseen <= self.PERSON_LOST_FRAMES]

        # 2b. Match Detected Vehicles to Tracks using IoU
        if model_mode in ("both", "coco"):
            current_vehicle_detections = []
            for v in vehicles_nms:
                vx, vy, vbw, vbh = v["box"]
                vx1 = max(0, min(w - 1, vx))
                vy1 = max(0, min(h - 1, vy))
                vx2 = max(0, min(w, vx + vbw))
                vy2 = max(0, min(h, vy + vbh))
                if (vx2 - vx1) >= 30 and (vy2 - vy1) >= 25:
                    current_vehicle_detections.append({
                        "box": np.array([vx1, vy1, vx2, vy2], dtype=int),
                        "score": v["score"],
                        "class_name": v["class_name"]
                    })

            matched_vehicle_track_ids = set()
            active_vehicles: List[VehicleTrack] = []

            for v_det in current_vehicle_detections:
                v_box = v_det["box"]
                best_iou = 0.0
                best_id = None
                for vt_id, v_track in self.tracked_vehicles.items():
                    if vt_id in matched_vehicle_track_ids:
                        continue
                    iou = compute_box_iou(v_track.box, v_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_id = vt_id
                
                if best_id is not None and best_iou >= 0.25:
                    v_track = self.tracked_vehicles[best_id]
                    v_track.box = (0.70 * v_track.box + 0.30 * v_box).astype(int)
                    v_track.confidence = v_det["score"]
                    v_track.class_name = v_det["class_name"]
                    v_track.last_seen_frame = self.frame_idx
                    v_track.frames_unseen = 0
                    matched_vehicle_track_ids.add(best_id)
                    active_vehicles.append(v_track)
                else:
                    new_vid = self.next_vehicle_track_id
                    self.next_vehicle_track_id += 1
                    new_vtrack = VehicleTrack(new_vid, v_box, v_det["class_name"], v_det["score"], now_ts)
                    new_vtrack.last_seen_frame = self.frame_idx
                    self.tracked_vehicles[new_vid] = new_vtrack
                    matched_vehicle_track_ids.add(new_vid)
                    active_vehicles.append(new_vtrack)

            # Update unseen vehicle tracks and prune stale tracks
            stale_vehicle_ids = []
            for vt_id, v_track in list(self.tracked_vehicles.items()):
                if vt_id not in matched_vehicle_track_ids:
                    v_track.frames_unseen += 1
                    if v_track.frames_unseen > self.VEHICLE_LOST_FRAMES:
                        stale_vehicle_ids.append(vt_id)
            for vt_id in stale_vehicle_ids:
                del self.tracked_vehicles[vt_id]
        else:
            # On PPE-only frames, preserve active vehicle tracks without incrementing frames_unseen
            active_vehicles: List[VehicleTrack] = [
                v for v in self.tracked_vehicles.values() if v.frames_unseen <= self.VEHICLE_LOST_FRAMES
            ]

        # Calculate proximity zone and best crops for each active vehicle
        vehicle_findings = []
        for v_track in active_vehicles:
            vx1, vy1, vx2, vy2 = v_track.box
            vw = max(1, vx2 - vx1)
            vh = max(1, vy2 - vy1)
            mx = max(35, int(0.35 * vw))
            my = max(25, int(0.30 * vh))
            zx1 = max(0, vx1 - mx)
            zy1 = max(0, vy1 - my)
            zx2 = min(w, vx2 + mx)
            zy2 = min(h, vy2 + my)
            v_track.proximity_zone = [int(zx1), int(zy1), int(zx2), int(zy2)]

            cur_v_crop_bytes, cur_v_crop_b64 = extract_vehicle_crop(frame, v_track.box)
            if cur_v_crop_bytes and (v_track.best_crop_bytes is None or v_track.confidence >= v_track.best_crop_conf):
                v_track.best_crop_bytes = cur_v_crop_bytes
                v_track.best_crop_base64 = cur_v_crop_b64
                v_track.best_crop_conf = v_track.confidence

            vehicle_findings.append({
                "vehicle_id": v_track.label,
                "track_id": v_track.track_id,
                "class_name": v_track.class_name,
                "bbox": [int(x) for x in v_track.box],
                "confidence": round(float(v_track.confidence), 2),
                "proximity_zone": v_track.proximity_zone,
                "evidence_crop_base64": v_track.best_crop_base64 or cur_v_crop_b64,
                "evidence_crop_bytes": v_track.best_crop_bytes or cur_v_crop_bytes
            })

        # 2c. Person-Vehicle Proximity Evaluation with Consecutive-Frame Debounce
        confirmed_proximity_events = []
        active_pair_keys = set()

        for p_track in active_tracks:
            px1, py1, px2, py2 = p_track.box
            p_cx = (px1 + px2) // 2
            p_cy = (py1 + py2) // 2
            p_bottom = py2

            for v_track in active_vehicles:
                pair_key = (p_track.track_id, v_track.track_id)
                active_pair_keys.add(pair_key)
                if pair_key not in self.proximity_pair_state:
                    self.proximity_pair_state[pair_key] = {
                        "consecutive_inside_count": 0,
                        "consecutive_outside_count": 0,
                        "is_confirmed": False,
                        "alert_triggered": False,
                        "last_seen_frame": self.frame_idx
                    }
                p_state = self.proximity_pair_state[pair_key]
                p_state["last_seen_frame"] = self.frame_idx

                zx1, zy1, zx2, zy2 = v_track.proximity_zone
                is_inside = (
                    (zx1 <= p_cx <= zx2 and zy1 <= p_bottom <= zy2) or
                    (zx1 <= p_cx <= zx2 and zy1 <= p_cy <= zy2) or
                    compute_box_iou(p_track.box, v_track.proximity_zone) > 0.05
                )

                if is_inside:
                    p_state["consecutive_inside_count"] += 1
                    p_state["consecutive_outside_count"] = 0
                    if p_state["consecutive_inside_count"] >= self.PROXIMITY_CONFIRM_FRAMES:
                        p_state["is_confirmed"] = True
                else:
                    p_state["consecutive_outside_count"] += 1
                    if p_state["consecutive_outside_count"] >= self.PROXIMITY_CLEAR_FRAMES:
                        p_state["is_confirmed"] = False
                        p_state["alert_triggered"] = False
                        p_state["consecutive_inside_count"] = 0

                if p_state["is_confirmed"]:
                    confirmed_proximity_events.append({
                        "person_id": p_track.label,
                        "vehicle_id": v_track.label,
                        "person_track_id": p_track.track_id,
                        "vehicle_track_id": v_track.track_id,
                        "vehicle_type": v_track.class_name,
                        "proximity_status": "Proximity Confirmed",
                        "person_crop_bytes": p_track.best_crop_bytes,
                        "person_crop_base64": p_track.best_crop_base64,
                        "vehicle_crop_bytes": v_track.best_crop_bytes,
                        "vehicle_crop_base64": v_track.best_crop_base64,
                        "alert_triggered": p_state["alert_triggered"]
                    })

        # Cleanup pairs unseen for multiple frames
        for pair_key in list(self.proximity_pair_state.keys()):
            if pair_key not in active_pair_keys:
                self.proximity_pair_state[pair_key]["consecutive_outside_count"] += 1
                if self.proximity_pair_state[pair_key]["consecutive_outside_count"] >= self.PROXIMITY_CLEAR_FRAMES:
                    del self.proximity_pair_state[pair_key]

        # 2d. Fire Evaluation & Temporal Confirmation Debounce (Feature 3)
        if model_mode in ("both", "fire"):
            if raw_fires_nms:
                self.fire_consecutive_count += 1
                self.fire_clear_count = 0
                best_f = max(raw_fires_nms, key=lambda f: f["score"])
                self.last_fire_conf = float(best_f["score"])
                
                # Extract fire crop for evidence
                fx, fy, fbw, fbh = best_f["box"]
                fx1 = max(0, min(w - 1, fx))
                fy1 = max(0, min(h - 1, fy))
                fx2 = max(0, min(w, fx + fbw))
                fy2 = max(0, min(h, fy + fbh))
                if (fx2 - fx1) >= 10 and (fy2 - fy1) >= 10:
                    fcrop = frame[fy1:fy2, fx1:fx2]
                    if fcrop.size > 0:
                        try:
                            ret, enc = cv2.imencode('.jpg', fcrop, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                            if ret:
                                self.last_fire_crop_bytes = enc.tobytes()
                                self.last_fire_crop_b64 = f"data:image/jpeg;base64,{base64.b64encode(self.last_fire_crop_bytes).decode('utf-8')}"
                        except Exception:
                            pass
                
                # Requires >= 2 consecutive confirming frames
                if self.fire_consecutive_count >= self.FIRE_CONFIRM_FRAMES:
                    self.fire_confirmed = True
                    self.confirmed_fires = [
                        {
                            "box": [max(0, f["box"][0]), max(0, f["box"][1]), min(w, f["box"][0] + f["box"][2]), min(h, f["box"][1] + f["box"][3])],
                            "confidence": round(float(f["score"]), 2),
                            "label": "FIRE"
                        }
                        for f in raw_fires_nms
                    ]
            else:
                self.fire_clear_count += 1
                self.fire_consecutive_count = 0
                if self.fire_clear_count >= self.FIRE_CLEAR_FRAMES:
                    self.fire_confirmed = False
                    self.fire_alert_triggered = False
                    self.confirmed_fires = []
                    self.last_fire_conf = 0.0

        # 3. Evaluate Restricted Zones (Permanent + Temporary) FIRST so zone context is available
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

        # 4. Associate Helmet, Vest, Gloves, Goggles, Harness, and Fall with each Person
        if model_mode in ("both", "ppe"):
            for track in active_tracks:
                bx1, by1, bx2, by2 = track.box
                bw = max(1, bx2 - bx1)
                bh = max(1, by2 - by1)
                head_y_bottom = by1 + int(0.40 * bh)
                torso_y_top = by1 + int(0.18 * bh)
                torso_y_bottom = by1 + int(0.75 * bh)
                head_margin_x = max(20, int(0.25 * bw))
                head_margin_y = max(20, int(0.20 * bh))

                # --- A. HELMET DETECTION ---
                hardhat_found = False
                best_h_conf = 0.0
                for h_box, h_conf in hardhats_nms:
                    hx, hy, hbw, hbh = h_box
                    hcx = hx + hbw / 2
                    hcy = hy + hbh / 2
                    in_region = (bx1 - head_margin_x <= hcx <= bx2 + head_margin_x and by1 - head_margin_y <= hcy <= head_y_bottom + 15)
                    h_box_xyxy = [hx, hy, hx + hbw, hy + hbh]
                    head_region_xyxy = [bx1, by1, bx2, head_y_bottom]
                    has_overlap = compute_box_iou(h_box_xyxy, head_region_xyxy) > 0.08
                    if in_region or has_overlap:
                        hardhat_found = True
                        best_h_conf = max(best_h_conf, h_conf)

                no_hardhat_found = False
                best_nh_conf = 0.0
                for nh_box, nh_conf in no_hardhats_nms:
                    nhx, nhy, nhbw, nhbh = nh_box
                    nhcx = nhx + nhbw / 2
                    nhcy = nhy + nhbh / 2
                    in_region = (bx1 - head_margin_x <= nhcx <= bx2 + head_margin_x and by1 - head_margin_y <= nhcy <= head_y_bottom + 15)
                    nh_box_xyxy = [nhx, nhy, nhx + nhbw, nhy + nhbh]
                    head_region_xyxy = [bx1, by1, bx2, head_y_bottom]
                    has_overlap = compute_box_iou(nh_box_xyxy, head_region_xyxy) > 0.08
                    if in_region or has_overlap:
                        no_hardhat_found = True
                        best_nh_conf = max(best_nh_conf, nh_conf)

                # Evaluate head visibility independently
                head_clipped_top = (by1 <= 3) and not (hardhat_found or no_hardhat_found)
                head_is_visible = not head_clipped_top and (bh >= 50 and bw >= 25)

                if not head_is_visible:
                    track.helmet_confirm_count = 0
                    track.no_helmet_confirm_count = 0
                    track.stable_status = "UNKNOWN"
                    track.helmet_confidence = 0.0
                elif no_hardhat_found and (best_nh_conf >= best_h_conf):
                    track.no_helmet_confirm_count += 1
                    track.helmet_confirm_count = 0
                    track.helmet_confidence = best_nh_conf
                    if track.no_helmet_confirm_count >= self.NO_HELMET_CONFIRM_FRAMES:
                        track.stable_status = "NO_HELMET"
                elif hardhat_found and (best_h_conf > best_nh_conf + 0.10):
                    track.helmet_confirm_count += 1
                    track.no_helmet_confirm_count = 0
                    track.helmet_confidence = best_h_conf
                    if track.helmet_confirm_count >= self.HELMET_CONFIRM_FRAMES:
                        track.stable_status = "HELMET"
                else:
                    has_h, has_nh = self._detect_helmet_heuristic(frame, [bx1, by1, bx2, by2])
                    if has_nh:
                        track.no_helmet_confirm_count += 1
                        track.helmet_confirm_count = 0
                        track.helmet_confidence = 0.70
                        if track.no_helmet_confirm_count >= self.NO_HELMET_CONFIRM_FRAMES:
                            track.stable_status = "NO_HELMET"
                    elif has_h:
                        track.helmet_confirm_count += 1
                        track.no_helmet_confirm_count = 0
                        track.helmet_confidence = 0.65
                        if track.helmet_confirm_count >= self.HELMET_CONFIRM_FRAMES:
                            track.stable_status = "HELMET"
                    elif head_is_visible and by1 > 5 and bh >= 80:
                        # Fallback: Person detected with visible head region without hardhat
                        track.no_helmet_confirm_count += 1
                        track.helmet_confidence = 0.60
                        if track.no_helmet_confirm_count >= (self.NO_HELMET_CONFIRM_FRAMES + 1):
                            track.stable_status = "NO_HELMET"
                    else:
                        track.helmet_confirm_count = 0
                        track.no_helmet_confirm_count = 0
                        track.stable_status = "UNKNOWN"
                        track.helmet_confidence = 0.0

                # --- B. SAFETY VEST DETECTION ---
                vest_found = False
                best_v_conf = 0.0
                for v_box, v_conf in vests_nms:
                    vx, vy, vbw, vbh = v_box
                    vcx = vx + vbw / 2
                    vcy = vy + vbh / 2
                    if bx1 - 30 <= vcx <= bx2 + 30 and torso_y_top - 20 <= vcy <= torso_y_bottom + 30:
                        vest_found = True
                        best_v_conf = max(best_v_conf, v_conf)

                no_vest_found = False
                best_nv_conf = 0.0
                for nv_box, nv_conf in no_vests_nms:
                    nvx, nvy, nvbw, nvbh = nv_box
                    nvcx = nvx + nvbw / 2
                    nvcy = nvy + nvbh / 2
                    if bx1 - 30 <= nvcx <= bx2 + 30 and torso_y_top - 20 <= nvcy <= torso_y_bottom + 30:
                        no_vest_found = True
                        best_nv_conf = max(best_nv_conf, nv_conf)

                # Check sufficient torso visibility for vest evaluation:
                # If only head/upper neck is visible, cropped close, or truncated at bottom border:
                # Vest = UNKNOWN (do NOT manufacture NO VEST)
                detected_head_h = 0
                head_lowest_y = by1 + int(0.35 * bh)
                for h_b, _ in (hardhats_nms + no_hardhats_nms):
                    hx, hy, hbw, hbh = h_b
                    hcx = hx + hbw / 2
                    hcy = hy + hbh / 2
                    if (bx1 - 25 <= hcx <= bx2 + 25) and (by1 - 25 <= hcy <= by1 + int(0.50 * bh) + 20):
                        head_lowest_y = max(head_lowest_y, hy + hbh)
                        detected_head_h = max(detected_head_h, hbh)

                clearance_below_head = by2 - head_lowest_y
                aspect_ratio = bh / max(1, bw)

                is_bottom_cropped = (by2 >= h - 12) and (clearance_below_head < 140 or bh < 240 or aspect_ratio < 1.45)
                is_top_cropped = (by1 <= 3) and (bh < 160 or clearance_below_head < 100)
                is_synthesized = getattr(track, 'is_head_synthesized', False)

                if is_synthesized or is_bottom_cropped or is_top_cropped:
                    has_sufficient_torso = False
                elif detected_head_h > 0:
                    # When head is detected, visible torso below head must exceed head height
                    min_torso_clearance = max(90, int(detected_head_h * 1.05))
                    has_sufficient_torso = (
                        clearance_below_head >= min_torso_clearance and
                        bh >= 140 and
                        bw >= 35 and
                        (bh >= 220 or aspect_ratio >= 1.35)
                    )
                else:
                    # No head proposal detected: check full box dimensions
                    has_sufficient_torso = (
                        bh >= 140 and
                        bw >= 35 and
                        clearance_below_head >= 85 and
                        (bh >= 240 or aspect_ratio >= 1.40)
                    )

                if vest_found and not no_vest_found and best_v_conf >= 0.22:
                    track.vest_confirm_count += 1
                    track.no_vest_confirm_count = 0
                    track.vest_confidence = best_v_conf
                    if track.vest_confirm_count >= self.VEST_CONFIRM_FRAMES:
                        track.vest_status = "VEST"
                elif has_sufficient_torso:
                    if no_vest_found and best_nv_conf >= 0.35:
                        track.no_vest_confirm_count += 1
                        track.vest_confirm_count = 0
                        track.vest_confidence = best_nv_conf
                        if track.no_vest_confirm_count >= self.NO_VEST_CONFIRM_FRAMES:
                            track.vest_status = "NO_VEST"
                    else:
                        has_v, has_nv = self._detect_vest_heuristic(frame, [bx1, by1, bx2, by2])
                        if has_v:
                            track.vest_confirm_count += 1
                            track.no_vest_confirm_count = 0
                            track.vest_confidence = 0.65
                            if track.vest_confirm_count >= self.VEST_CONFIRM_FRAMES:
                                track.vest_status = "VEST"
                        elif has_nv:
                            track.no_vest_confirm_count += 1
                            track.vest_confirm_count = 0
                            track.vest_confidence = 0.65
                            if track.no_vest_confirm_count >= self.NO_VEST_CONFIRM_FRAMES:
                                track.vest_status = "NO_VEST"
                        else:
                            # Fallback: Sufficient torso visible, confirmed absence of compliant vest
                            track.no_vest_confirm_count += 1
                            track.vest_confidence = 0.60
                            if track.no_vest_confirm_count >= (self.NO_VEST_CONFIRM_FRAMES + 1):
                                track.vest_status = "NO_VEST"
                else:
                    # Insufficient torso visibility -> Vest MUST be UNKNOWN
                    track.vest_confirm_count = 0
                    track.no_vest_confirm_count = 0
                    track.vest_status = "UNKNOWN"
                    track.vest_confidence = 0.0

            # 4B. Spatial Association of Real ONNX Hand / Glove Bounding Boxes to Persons
            # Only run during PPE inference frames so COCO frames do not wipe hand associations
            for track in active_tracks:
                track.hand_boxes = []

            # Retrieve strictly mutually exclusive resolved hand detections
            resolved_hands = inf_res.get("resolved_hands", [])

            # Associate hand detections with person tracks spatially
            if len(active_tracks) == 1:
                track = active_tracks[0]
                bx1, by1, bx2, by2 = track.box
                bw = max(1, bx2 - bx1)
                bh = max(1, by2 - by1)
                reach_x = max(120, int(0.75 * bw))
                reach_y_top = max(0, by1 - int(0.20 * bh))
                reach_y_bottom = min(h, by2 + int(0.25 * bh))
                for rh in resolved_hands:
                    gx, gy, gbw, gbh = rh["box"]
                    gcx = gx + gbw / 2
                    gcy = gy + gbh / 2
                    if (bx1 - reach_x <= gcx <= bx2 + reach_x) and (reach_y_top <= gcy <= reach_y_bottom):
                        is_glove = rh["is_glove"]
                        hand_label = f"HAND {track.track_id:02d} — {'GLOVES' if is_glove else 'NO GLOVES'}"
                        track.hand_boxes.append({
                            "box": [int(gx), int(gy), int(gx + gbw), int(gy + gbh)],
                            "type": rh["type"],
                            "confidence": round(float(rh["conf"]), 2),
                            "label": hand_label
                        })
            elif len(active_tracks) > 1:
                for rh in resolved_hands:
                    gx, gy, gbw, gbh = rh["box"]
                    gcx = gx + gbw / 2
                    gcy = gy + gbh / 2
                    best_track = None
                    best_score = float('inf')
                    for track in active_tracks:
                        bx1, by1, bx2, by2 = track.box
                        bw = max(1, bx2 - bx1)
                        bh = max(1, by2 - by1)
                        reach_x = max(90, int(0.55 * bw))
                        reach_y_top = max(0, by1 - int(0.15 * bh))
                        reach_y_bottom = min(h, by2 + int(0.20 * bh))
                        if (bx1 - reach_x <= gcx <= bx2 + reach_x) and (reach_y_top <= gcy <= reach_y_bottom):
                            # Distance from hand center to person bounding box (0 if inside person box)
                            dx = max(0, bx1 - gcx, gcx - bx2)
                            dy = max(0, by1 - gcy, gcy - by2)
                            box_dist = (dx * dx + dy * dy) ** 0.5
                            center_x = (bx1 + bx2) / 2
                            center_y = (by1 + by2) / 2
                            center_dist = ((gcx - center_x) ** 2 + (gcy - center_y) ** 2) ** 0.5
                            score = box_dist * 10.0 + center_dist
                            if score < best_score:
                                best_score = score
                                best_track = track
                    if best_track is not None:
                        is_glove = rh["is_glove"]
                        hand_label = f"HAND {best_track.track_id:02d} — {'GLOVES' if is_glove else 'NO GLOVES'}"
                        best_track.hand_boxes.append({
                            "box": [int(gx), int(gy), int(gx + gbw), int(gy + gbh)],
                            "type": rh["type"],
                            "confidence": round(float(rh["conf"]), 2),
                            "label": hand_label
                        })

            # Determine each person's gloves_status from associated hand evidence
            for track in active_tracks:
                has_no_gloves = any(hb["type"] == "NO_GLOVES" for hb in track.hand_boxes)
                has_gloves = any(hb["type"] == "GLOVES" for hb in track.hand_boxes)

                if has_no_gloves and has_gloves:
                    # If competing detections exist across different hands, resolve by higher confidence
                    max_ng = max((hb["confidence"] for hb in track.hand_boxes if hb["type"] == "NO_GLOVES"), default=0.0)
                    max_g = max((hb["confidence"] for hb in track.hand_boxes if hb["type"] == "GLOVES"), default=0.0)
                    if abs(max_ng - max_g) < 0.20:
                        track.gloves_status = "UNKNOWN"
                        track.gloves_confidence = 0.0
                        track.gloves_confirm_count = 0
                        track.no_gloves_confirm_count = 0
                    elif max_ng > max_g:
                        track.no_gloves_confirm_count = min(6, track.no_gloves_confirm_count + 2)
                        track.gloves_confirm_count = 0
                        track.gloves_status = "NO_GLOVES"
                        track.gloves_confidence = max_ng
                    else:
                        track.gloves_confirm_count = min(6, track.gloves_confirm_count + 2)
                        track.no_gloves_confirm_count = 0
                        track.gloves_status = "GLOVES"
                        track.gloves_confidence = max_g
                elif has_no_gloves:
                    track.no_gloves_confirm_count = min(6, track.no_gloves_confirm_count + 2)
                    track.gloves_confirm_count = 0
                    track.gloves_status = "NO_GLOVES"
                    track.gloves_confidence = max(hb["confidence"] for hb in track.hand_boxes if hb["type"] == "NO_GLOVES")
                elif has_gloves:
                    track.gloves_confirm_count = min(6, track.gloves_confirm_count + 2)
                    track.no_gloves_confirm_count = 0
                    track.gloves_status = "GLOVES"
                    track.gloves_confidence = max(hb["confidence"] for hb in track.hand_boxes if hb["type"] == "GLOVES")
                else:
                    # Gradual decay only on PPE frames when no hand was detected
                    if track.gloves_confirm_count > 0:
                        track.gloves_confirm_count -= 1
                    if track.no_gloves_confirm_count > 0:
                        track.no_gloves_confirm_count -= 1
                    if track.gloves_confirm_count <= 0 and track.no_gloves_confirm_count <= 0:
                        track.gloves_status = "UNKNOWN"
                        track.gloves_confidence = 0.0

        # 5. Zone confirmation debounce
        total_persons = len(active_tracks)
        raw_persons_in_zone = len(zone_violator_tracks)

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

        # 6. Aggregate Counts and Per-Person PPE Status & Findings
        unhelmeted_tracks = [t for t in active_tracks if t.stable_status == "NO_HELMET"]
        unhelmeted_count = len(unhelmeted_tracks)
        unhelmeted_ids = [t.label for t in unhelmeted_tracks]

        unvested_tracks = [t for t in active_tracks if t.vest_status == "NO_VEST"]
        unvested_count = len(unvested_tracks)
        unvested_ids = [t.label for t in unvested_tracks]

        ungloved_tracks = [t for t in active_tracks if t.gloves_status == "NO_GLOVES"]
        ungloved_count = len(ungloved_tracks)
        ungloved_ids = [t.label for t in ungloved_tracks]

        person_violations: Dict[str, List[str]] = {}
        person_ppe_statuses: Dict[str, Dict[str, str]] = {}
        person_findings: List[Dict[str, Any]] = []

        for t in active_tracks:
            h_stat = "OK" if t.stable_status == "HELMET" else ("VIOLATION" if t.stable_status == "NO_HELMET" else "UNKNOWN")
            v_stat = "OK" if t.vest_status == "VEST" else ("VIOLATION" if t.vest_status == "NO_VEST" else "UNKNOWN")
            g_stat = "OK" if t.gloves_status == "GLOVES" else ("VIOLATION" if t.gloves_status == "NO_GLOVES" else "UNKNOWN")

            viols = []
            if h_stat == "VIOLATION":
                viols.append("NO HELMET")
            if v_stat == "VIOLATION":
                viols.append("NO SAFETY VEST")
            if g_stat == "VIOLATION":
                viols.append("NO GLOVES")
            if t.in_zone:
                viols.append("RESTRICTED ZONE")

            # Evaluate overall PPE status per person
            if len(viols) > 0:
                overall_ppe = "VIOLATION"
            elif h_stat == "OK" and v_stat == "OK":
                overall_ppe = "OK"
            elif h_stat == "UNKNOWN" or v_stat == "UNKNOWN":
                overall_ppe = "UNKNOWN"
            else:
                overall_ppe = "OK"
            t.overall_ppe_status = overall_ppe

            # Extract individual person crop with 10% padding
            cur_crop_bytes, cur_crop_b64 = extract_person_crop(frame, t.box, padding_pct=0.10)
            person_conf = max(t.helmet_confidence, t.vest_confidence, t.gloves_confidence, 0.5)
            if cur_crop_bytes is not None:
                if t.best_crop_bytes is None or person_conf >= t.best_crop_conf or (overall_ppe == "VIOLATION" and len(viols) > 0):
                    t.best_crop_bytes = cur_crop_bytes
                    t.best_crop_base64 = cur_crop_b64
                    t.best_crop_conf = person_conf

            person_violations[t.label] = viols
            person_ppe_statuses[t.label] = {
                "helmet": h_stat,
                "vest": v_stat,
                "gloves": g_stat,
                "overall": overall_ppe
            }

            person_findings.append({
                "person_id": t.label,
                "track_id": t.track_id,
                "bbox": [int(x) for x in t.box],
                "helmet_status": h_stat,
                "vest_status": v_stat,
                "glove_status": g_stat,
                "overall_ppe_status": overall_ppe,
                "violations": viols,
                "evidence_crop_base64": t.best_crop_base64 or cur_crop_b64,
                "helmet_confidence": round(float(t.helmet_confidence), 2),
                "vest_confidence": round(float(t.vest_confidence), 2),
                "glove_confidence": round(float(t.gloves_confidence), 2),
                "in_zone": t.in_zone
            })

        self.stable_person_detected = (total_persons > 0)
        self.stable_helmet_detected = (total_persons > 0 and unhelmeted_count == 0 and any(t.stable_status == "HELMET" for t in active_tracks))
        self.stable_vest_detected = (total_persons > 0 and unvested_count == 0 and any(t.vest_status == "VEST" for t in active_tracks))
        self.stable_gloves_detected = (total_persons > 0 and ungloved_count == 0 and any(t.gloves_status == "GLOVES" for t in active_tracks))

        # 7. Capture visual evidence snapshot when any violation detected
        evidence_frame_bytes = None
        has_any_violation = (unhelmeted_count > 0 or self.stable_zone_violation or unvested_count > 0 or ungloved_count > 0 or len(confirmed_proximity_events) > 0 or self.fire_confirmed)
        if has_any_violation:
            try:
                ret, enc = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if ret:
                    evidence_frame_bytes = enc.tobytes()
            except Exception:
                pass

        # 8. Update State Manager with grouped multi-person findings
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
            breached_zone=primary_breached_zone,
            vest_detected=self.stable_vest_detected,
            unvested_count=unvested_count,
            unvested_ids=unvested_ids,
            gloves_detected=self.stable_gloves_detected,
            ungloved_count=ungloved_count,
            ungloved_ids=ungloved_ids,
            person_violations=person_violations,
            ppe_statuses=person_ppe_statuses,
            person_findings=person_findings,
            fire_detected=self.fire_confirmed,
            fire_confidence=round(float(self.last_fire_conf), 2)
        )

        # 8b. Dispatch or update High-Priority Person-Vehicle Proximity Alerts
        for pe in confirmed_proximity_events:
            pair_key = (pe["person_track_id"], pe["vehicle_track_id"])
            p_state = self.proximity_pair_state.get(pair_key)
            if p_state and not p_state.get("alert_triggered"):
                target_z = primary_breached_zone or (active_zones[0] if active_zones else state_manager.active_zone)
                loc = target_z.name if target_z else "Demo Work Zone"
                state_manager.trigger_alert(
                    alert_type="Person–Vehicle Proximity",
                    location=loc,
                    camera=camera_id,
                    severity="CRITICAL",
                    sif_potential="CRITICAL / HIGH",
                    person_count=1,
                    affected_person_ids=[pe["person_id"]],
                    title="HIGH PRIORITY — PERSON–VEHICLE PROXIMITY",
                    short_summary=f"{pe['person_id']} ↔ {pe['vehicle_id']} ({pe['vehicle_type'].capitalize()}) • Proximity Zone Entered",
                    hazard="Heavy Equipment / Vehicle Proximity & Struck-By Hazard",
                    unsafe_condition=f"Worker detected occupying active proximity perimeter of {pe['vehicle_type']} ({pe['vehicle_id']})",
                    notes=f"Automated SIF Alert: {pe['person_id']} entered proximity perimeter of {pe['vehicle_id']}.",
                    evidence_frame=evidence_frame_bytes,
                    vehicle_id=pe["vehicle_id"],
                    vehicle_type=pe["vehicle_type"],
                    vehicle_crop_bytes=pe.get("vehicle_crop_bytes"),
                    vehicle_crop_base64=pe.get("vehicle_crop_base64"),
                    proximity_status="Proximity Confirmed",
                    is_high_priority=True,
                    vehicle_findings=vehicle_findings,
                    person_findings=[pf for pf in person_findings if pf.get("person_id") == pe["person_id"]]
                )
                p_state["alert_triggered"] = True

        # 8c. Dispatch or update Fire Hazard Alert (Priority 140, CRITICAL, Orange)
        if self.fire_confirmed and not self.fire_alert_triggered:
            target_z = primary_breached_zone or (active_zones[0] if active_zones else state_manager.active_zone)
            loc = target_z.name if target_z else "Demo Work Zone"
            state_manager.trigger_alert(
                alert_type="Fire Hazard",
                location=loc,
                camera=camera_id,
                severity="CRITICAL",
                sif_potential="CRITICAL / HIGH",
                person_count=total_persons,
                title="FIRE DETECTED — CONFIRMED",
                short_summary=f"Confirmed active fire detected ({int(self.last_fire_conf*100)}% conf) in {loc}",
                hazard="Active Fire Hazard / Thermal Ignition",
                unsafe_condition=f"Confirmed open flame detected in monitored CCTV sector ({camera_id})",
                notes="Automated SIF Alert: Visual fire confirmation in CCTV feed. Immediate response required.",
                evidence_frame=evidence_frame_bytes,
                fire_detected=True,
                fire_confidence=round(float(self.last_fire_conf), 2),
                fire_bbox=self.confirmed_fires[0]["box"] if self.confirmed_fires else None,
                fire_crop_bytes=self.last_fire_crop_bytes,
                fire_crop_base64=self.last_fire_crop_b64
            )
            self.fire_alert_triggered = True

        if has_any_violation:
            self.last_alert_time = datetime.now().strftime("%H:%M:%S")

        # 9. Render Bounding Boxes & Annotations on Frame
        annotated_frame = frame.copy()

        # Draw Restricted Zones
        for z in active_zones:
            if not (z.enabled and len(z.polygon) >= 3):
                continue
            z_poly = np.array(z.polygon, dtype=np.int32)
            is_breached = bool(primary_breached_zone and primary_breached_zone.zone_id == z.zone_id and self.stable_zone_violation)
            
            if is_breached:
                z_color = (60, 60, 235)
                cat_label = "BREACHED"
            elif z.zone_category == "PASSPORT_TEMPORARY":
                z_color = (30, 150, 245)
                cat_label = "PASSPORT TEMPORARY"
            else:
                z_color = (235, 150, 50)
                cat_label = "RESTRICTED ZONE"

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

        # Draw Person Bounding Boxes & Clean Multi-Person HUD
        for track in active_tracks:
            bx1, by1, bx2, by2 = track.box
            p_viols = person_violations.get(track.label, [])
            
            if len(p_viols) > 0:
                b_col = (60, 60, 235) # Red for violation
                lbl = f"{track.label} [{', '.join(p_viols[:2])}]"
            elif track.overall_ppe_status == "OK":
                b_col = (60, 210, 80) # Green for PPE OK
                lbl = f"{track.label} [PPE OK]"
            elif track.stable_status == "HELMET":
                b_col = (60, 210, 80)
                lbl = f"{track.label} [HELMET OK]"
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

            # Draw Hand Bounding Boxes (small separate bounding boxes around hands/gloves)
            for hb in track.hand_boxes:
                hx1, hy1, hx2, hy2 = hb["box"]
                h_col = (60, 210, 80) if hb["type"] == "GLOVES" else (60, 60, 235)
                cv2.rectangle(annotated_frame, (hx1, hy1), (hx2, hy2), h_col, 2)
                h_tag_y = max(18, hy1 - 6)
                (htw, hth), _ = cv2.getTextSize(hb["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                cv2.rectangle(annotated_frame, (hx1, h_tag_y - hth - 3), (hx1 + htw + 4, h_tag_y + 2), h_col, -1)
                cv2.putText(annotated_frame, hb["label"], (hx1 + 2, h_tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw Vehicle Bounding Boxes & Proximity Zones
        for v_track in active_vehicles:
            vx1, vy1, vx2, vy2 = v_track.box
            v_col = (235, 160, 40) # Bright Amber/Orange for Vehicle
            cv2.rectangle(annotated_frame, (vx1, vy1), (vx2, vy2), v_col, 2)
            
            v_lbl = f"{v_track.label} [{v_track.class_name.upper()}]"
            v_tag_y = max(38, vy1 - 8)
            (vtw, vth), _ = cv2.getTextSize(v_lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(annotated_frame, (vx1, v_tag_y - vth - 4), (vx1 + vtw + 6, v_tag_y + 2), v_col, -1)
            cv2.putText(annotated_frame, v_lbl, (vx1 + 3, v_tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 20, 24), 1, cv2.LINE_AA)

            if v_track.proximity_zone:
                zx1, zy1, zx2, zy2 = v_track.proximity_zone
                has_prox_conflict = any(pe["vehicle_track_id"] == v_track.track_id for pe in confirmed_proximity_events)
                pz_col = (60, 60, 235) if has_prox_conflict else (200, 180, 50)
                z_overlay = annotated_frame.copy()
                cv2.rectangle(z_overlay, (zx1, zy1), (zx2, zy2), pz_col, -1)
                cv2.addWeighted(z_overlay, 0.12, annotated_frame, 0.88, 0, annotated_frame)
                cv2.rectangle(annotated_frame, (zx1, zy1), (zx2, zy2), pz_col, 1)
                
                pz_txt = "PROXIMITY ZONE" if not has_prox_conflict else "PROXIMITY CONFLICT"
                cv2.putText(annotated_frame, pz_txt, (zx1 + 4, zy1 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, pz_col, 1, cv2.LINE_AA)

        # Draw Warning Lines & Labels for Confirmed Proximity Events
        for pe in confirmed_proximity_events:
            p_id = pe["person_track_id"]
            v_id = pe["vehicle_track_id"]
            p_trk = self.tracked_persons.get(p_id)
            v_trk = self.tracked_vehicles.get(v_id)
            if p_trk and v_trk:
                p_pt = ((p_trk.box[0] + p_trk.box[2]) // 2, (p_trk.box[1] + p_trk.box[3]) // 2)
                v_pt = ((v_trk.box[0] + v_trk.box[2]) // 2, (v_trk.box[1] + v_trk.box[3]) // 2)
                cv2.line(annotated_frame, p_pt, v_pt, (60, 60, 235), 2, cv2.LINE_AA)
                mid_pt = ((p_pt[0] + v_pt[0]) // 2, (p_pt[1] + v_pt[1]) // 2)
                warn_lbl = f"{p_trk.label} <-> {v_trk.label} [PROXIMITY]"
                (wtw, wth), _ = cv2.getTextSize(warn_lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                cv2.rectangle(annotated_frame, (mid_pt[0] - 4, mid_pt[1] - wth - 4), (mid_pt[0] + wtw + 4, mid_pt[1] + 2), (60, 60, 235), -1)
                cv2.putText(annotated_frame, warn_lbl, (mid_pt[0], mid_pt[1] - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw Fire Bounding Boxes & Distinctive ORANGE Visual Treatment (Feature 3)
        if self.fire_confirmed and self.confirmed_fires:
            for f in self.confirmed_fires:
                fx1, fy1, fx2, fy2 = f["box"]
                f_col = (30, 130, 245) # Distinctive vibrant orange in BGR
                # Semi-transparent orange fill
                f_overlay = annotated_frame.copy()
                cv2.rectangle(f_overlay, (fx1, fy1), (fx2, fy2), f_col, -1)
                cv2.addWeighted(f_overlay, 0.20, annotated_frame, 0.80, 0, annotated_frame)
                cv2.rectangle(annotated_frame, (fx1, fy1), (fx2, fy2), f_col, 3)
                
                f_conf_pct = int(f.get("confidence", self.last_fire_conf) * 100)
                f_lbl = f"FIRE DETECTED [{f_conf_pct}%]" if f_conf_pct > 0 else "FIRE DETECTED"
                f_tag_y = max(38, fy1 - 8)
                (ftw, fth), _ = cv2.getTextSize(f_lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
                cv2.rectangle(annotated_frame, (fx1, f_tag_y - fth - 4), (fx1 + ftw + 6, f_tag_y + 2), f_col, -1)
                cv2.putText(annotated_frame, f_lbl, (fx1 + 3, f_tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

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
            self.vest_detected = self.stable_vest_detected
            self.gloves_detected = self.stable_gloves_detected

        # Prepare JSON detection payload
        persons_payload = []
        all_hand_boxes = []
        for t in active_tracks:
            all_hand_boxes.extend(t.hand_boxes)
            persons_payload.append({
                "id": t.track_id,
                "label": t.label,
                "box": [int(x) for x in t.box],
                "helmet_status": "OK" if t.stable_status == "HELMET" else ("VIOLATION" if t.stable_status == "NO_HELMET" else "UNKNOWN"),
                "helmet_confidence": round(float(t.helmet_confidence), 2),
                "vest_status": "OK" if t.vest_status == "VEST" else ("VIOLATION" if t.vest_status == "NO_VEST" else "UNKNOWN"),
                "vest_confidence": round(float(t.vest_confidence), 2),
                "gloves_status": "OK" if t.gloves_status == "GLOVES" else ("VIOLATION" if t.gloves_status == "NO_GLOVES" else "UNKNOWN"),
                "gloves_confidence": round(float(t.gloves_confidence), 2),
                "overall_ppe_status": t.overall_ppe_status,
                "evidence_crop": t.best_crop_base64,
                "hands": t.hand_boxes,
                "in_zone": t.in_zone,
                "violations": person_violations.get(t.label, [])
            })

        vehicle_payload = []
        for v in active_vehicles:
            vehicle_payload.append({
                "id": int(v.track_id),
                "label": str(v.label),
                "class_name": str(v.class_name),
                "box": [int(x) for x in v.box],
                "confidence": round(float(v.confidence), 2),
                "proximity_zone": [int(x) for x in v.proximity_zone] if v.proximity_zone else None,
                "evidence_crop": v.best_crop_base64
            })

        json_proximity_events = []
        for pe in confirmed_proximity_events:
            json_proximity_events.append({
                "person_id": str(pe["person_id"]),
                "vehicle_id": str(pe["vehicle_id"]),
                "person_track_id": int(pe["person_track_id"]),
                "vehicle_track_id": int(pe["vehicle_track_id"]),
                "vehicle_type": str(pe["vehicle_type"]),
                "proximity_status": str(pe["proximity_status"]),
                "person_crop_base64": pe.get("person_crop_base64"),
                "vehicle_crop_base64": pe.get("vehicle_crop_base64"),
                "alert_triggered": bool(pe.get("alert_triggered", False))
            })

        return {
            "status": "LIVE",
            "camera_id": camera_id,
            "frame_seq": frame_seq,
            "model_loaded": self.model_loaded,
            "model_name": self.model_name,
            "person_count": total_persons,
            "helmet_detected": self.stable_helmet_detected,
            "unhelmeted_count": unhelmeted_count,
            "vest_detected": self.stable_vest_detected,
            "unvested_count": unvested_count,
            "gloves_detected": self.stable_gloves_detected,
            "ungloved_count": ungloved_count,
            "zone_violation": self.stable_zone_violation,
            "fire_detected": self.fire_confirmed,
            "fire_confidence": round(float(self.last_fire_conf), 2) if self.fire_confirmed else 0.0,
            "fires": [
                {
                    "box": [int(b) for b in f["box"]],
                    "confidence": round(float(f.get("confidence", f.get("score", self.last_fire_conf))), 2),
                    "label": "FIRE"
                }
                for f in self.confirmed_fires
            ] if self.fire_confirmed else [],
            "persons": persons_payload,
            "person_findings": person_findings,
            "vehicles": vehicle_payload,
            "proximity_events": json_proximity_events,
            "hands": all_hand_boxes,
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
            "vehicles": len(self.tracked_vehicles),
            "proximity_events": sum(1 for p in self.proximity_pair_state.values() if p.get("is_confirmed")),
            "helmet_detections": sum(1 for t in self.tracked_persons.values() if t.stable_status == "HELMET"),
            "unhelmeted_detections": sum(1 for t in self.tracked_persons.values() if t.stable_status == "NO_HELMET"),
            "vest_detections": sum(1 for t in self.tracked_persons.values() if t.vest_status == "VEST"),
            "unvested_detections": sum(1 for t in self.tracked_persons.values() if t.vest_status == "NO_VEST"),
            "gloves_detections": sum(1 for t in self.tracked_persons.values() if t.gloves_status == "GLOVES"),
            "ungloved_detections": sum(1 for t in self.tracked_persons.values() if t.gloves_status == "NO_GLOVES"),
            "zone_violations": 1 if self.stable_zone_violation else 0,
            "fire_detected": self.fire_confirmed,
            "fire_confidence": round(float(self.last_fire_conf), 2) if self.fire_confirmed else 0.0,
            "last_inference": self.last_inference_time or "N/A",
            "last_alert": self.last_alert_time or "None"
        }

    def reset_tracks(self):
        """Cleans all tracked person and vehicle records, proximity states, debounce counts, and resets IDs"""
        with self.lock:
            self.tracked_persons.clear()
            self.next_track_id = 1
            self.tracked_vehicles.clear()
            self.next_vehicle_track_id = 1
            self.proximity_pair_state.clear()
            self.frame_idx = 0
            self.person_detected = False
            self.helmet_detected = False
            self.vest_detected = False
            self.gloves_detected = False
            self.stable_person_detected = False
            self.stable_helmet_detected = False
            self.stable_vest_detected = False
            self.stable_gloves_detected = False
            self.stable_zone_violation = False
            self.persons_in_zone = 0
            self.zone_occupancy_score = 0.0
            self.zone_debug_info = None
            self.zone_inside_confirm_count = 0
            self.zone_outside_confirm_count = 0
            self.helmet_confirm_count = 0
            self.no_helmet_confirm_count = 0
            self.vest_confirm_count = 0
            self.no_vest_confirm_count = 0
            self.fire_consecutive_count = 0
            self.fire_clear_count = 0
            self.fire_confirmed = False
            self.fire_alert_triggered = False
            self.confirmed_fires.clear()
            self.last_fire_crop_bytes = None
            self.last_fire_crop_b64 = None
            self.last_fire_conf = 0.0

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
