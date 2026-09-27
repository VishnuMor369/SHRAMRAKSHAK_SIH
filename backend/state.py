import asyncio
import threading
import time
import base64
import uuid
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Set, Dict, Union, Any
from fastapi import WebSocket
from models import (
    Alert, SystemStatus, RestrictedZone, PersonFinding, VehicleFinding,
    SafetyPassport, ControlItem, PassportEvent,
    CreatePassportRequest, VerifyControlRequest, ApprovePassportRequest, VerifyRestorationRequest
)
from utils import get_lan_ip

RESPONSE_SLA_SECONDS = 20
ACTION_SLA_SECONDS = 60

def generate_visual_evidence(
    alert_type: str,
    camera_id: str = "C-01",
    location: str = "Demo Work Zone",
    person_count: int = 1,
    unhelmeted_ids: Optional[List[str]] = None,
    zone_name: Optional[str] = None,
    zone_category: str = "PERMANENT",
    zone_polygon: Optional[List[List[float]]] = None,
    base_frame: Optional[np.ndarray] = None
) -> bytes:
    """
    Generates authentic CCTV visual evidence frame annotated with bounding boxes,
    anonymous labels ('Person 01', 'Person 02'), and restricted boundary polygons.
    """
    if base_frame is not None and isinstance(base_frame, np.ndarray) and base_frame.size > 0:
        frame = base_frame.copy()
    else:
        # Generate 640x480 dark industrial CCTV frame
        frame = np.full((480, 640, 3), 36, dtype=np.uint8)
        # Perspective floor markings & grid
        for y in range(80, 480, 50):
            cv2.line(frame, (0, y), (640, y), (48, 52, 58), 1)
        for x in range(80, 640, 80):
            cv2.line(frame, (x, 80), (x, 480), (48, 52, 58), 1)

    h, w, _ = frame.shape
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Draw zone polygon if present
    is_zone_alert = ("zone" in alert_type.lower() or "breach" in alert_type.lower() or "passport" in alert_type.lower())
    if zone_polygon and len(zone_polygon) >= 3:
        poly_pts = np.array(zone_polygon, dtype=np.int32)
        z_col = (50, 50, 230) if is_zone_alert else ((30, 150, 245) if zone_category == "PASSPORT_TEMPORARY" else (235, 150, 50))
        overlay = frame.copy()
        cv2.fillPoly(overlay, [poly_pts], z_col)
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
        cv2.polylines(frame, [poly_pts], True, z_col, 2, cv2.LINE_AA)
        
        # Zone badge
        min_x = max(10, int(np.min(poly_pts[:, 0])))
        min_y = max(55, int(np.min(poly_pts[:, 1])) - 8)
        cat_tag = "TEMPORARY PASSPORT ZONE" if zone_category == "PASSPORT_TEMPORARY" else "PERMANENT SAFETY ZONE"
        status_tag = "BREACHED" if is_zone_alert else "ACTIVE"
        badge_txt = f"{zone_name or 'RESTRICTED ZONE'} [{cat_tag}] | {status_tag}"
        (tw, th), _ = cv2.getTextSize(badge_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        cv2.rectangle(frame, (min_x - 3, min_y - th - 4), (min_x + tw + 3, min_y + 2), (24, 24, 27), -1)
        cv2.rectangle(frame, (min_x - 3, min_y - th - 4), (min_x + tw + 3, min_y + 2), z_col, 1)
        cv2.putText(frame, badge_txt, (min_x, min_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, z_col, 1, cv2.LINE_AA)

    # 2. Draw person annotations
    if "multi" in alert_type.lower():
        bx1, by1, bx2, by2 = 220, 130, 420, 430
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (60, 60, 235), 2)
        lbl = "Person 01 [MULTI-HAZARD VIOLATION]"
        (ltw, lth), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        cv2.rectangle(frame, (bx1, by1 - lth - 4), (bx1 + ltw + 6, by1 + 2), (60, 60, 235), -1)
        cv2.putText(frame, lbl, (bx1 + 3, by1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    elif "vest" in alert_type.lower():
        bx1, by1, bx2, by2 = 220, 130, 420, 430
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (60, 60, 235), 2)
        lbl = "Person 01 [NO SAFETY VEST]"
        (ltw, lth), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        cv2.rectangle(frame, (bx1, by1 - lth - 4), (bx1 + ltw + 6, by1 + 2), (60, 60, 235), -1)
        cv2.putText(frame, lbl, (bx1 + 3, by1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    elif "gloves" in alert_type.lower() or "ungloved" in alert_type.lower():
        bx1, by1, bx2, by2 = 220, 130, 420, 430
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (60, 60, 235), 2)
        lbl = "Person 01 [NO GLOVES]"
        (ltw, lth), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        cv2.rectangle(frame, (bx1, by1 - lth - 4), (bx1 + ltw + 6, by1 + 2), (60, 60, 235), -1)
        cv2.putText(frame, lbl, (bx1 + 3, by1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    elif is_zone_alert:
        # Person inside zone
        bx1, by1, bx2, by2 = 240, 140, 390, 420
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (60, 60, 235), 2)
        lbl = "Person 01 [ZONE BREACH]"
        (ltw, lth), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        cv2.rectangle(frame, (bx1, by1 - lth - 4), (bx1 + ltw + 6, by1 + 2), (60, 60, 235), -1)
        cv2.putText(frame, lbl, (bx1 + 3, by1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(frame, ((bx1 + bx2)//2, by2), 5, (60, 60, 235), -1)
    elif "helmet" in alert_type.lower() or "ppe" in alert_type.lower():
        cnt = max(1, person_count)
        boxes = []
        if cnt == 1:
            boxes = [(220, 130, 420, 430)]
        elif cnt == 2:
            boxes = [(110, 130, 280, 430), (360, 130, 530, 430)]
        else:
            step = 500 // cnt
            boxes = [(60 + i * step, 130, min(600, 60 + i * step + 150), 430) for i in range(cnt)]

        for i, (bx1, by1, bx2, by2) in enumerate(boxes):
            anon_id = f"Person {i+1:02d}"
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (60, 60, 235), 2)
            # Head circle
            head_cx = (bx1 + bx2) // 2
            head_cy = by1 + int((by2 - by1) * 0.18)
            cv2.circle(frame, (head_cx, head_cy), 25, (160, 160, 160), 2)
            # Red cross / warning on head
            cv2.line(frame, (head_cx - 12, head_cy - 12), (head_cx + 12, head_cy + 12), (60, 60, 235), 2)
            cv2.line(frame, (head_cx + 12, head_cy - 12), (head_cx - 12, head_cy + 12), (60, 60, 235), 2)
            lbl = f"{anon_id} [NO HELMET]"
            (ltw, lth), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(frame, (bx1, by1 - lth - 4), (bx1 + ltw + 6, by1 + 2), (60, 60, 235), -1)
            cv2.putText(frame, lbl, (bx1 + 3, by1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Top CCTV HUD
    cv2.rectangle(frame, (0, 0), (w, 36), (20, 20, 24), -1)
    cam_str = f"CAM: {camera_id} | {location.upper()} | EVIDENCE RECORD"
    cv2.putText(frame, cam_str, (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 225), 1, cv2.LINE_AA)
    right_str = f"{now_str} | CONFIRMED DETECTION"
    cv2.putText(frame, right_str, (w - 280, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 230, 255), 1, cv2.LINE_AA)

    _, enc = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return enc.tobytes()

def calculate_alert_priority(alert_type: str, severity: str = "HIGH", sif_potential: str = "HIGH / POTENTIAL", **kwargs) -> tuple[int, str]:
    """
    AI Recommended Response Priority:
    -1. PERSON-VEHICLE PROXIMITY (score 150, CRITICAL - HIGHEST ACTIVE FEED PRIORITY)
    0. SAFETY PASSPORT PAUSED / CRITICAL BARRIER BREACH (score 120, CRITICAL)
    1. RESTRICTED ZONE / HIGH SIF POTENTIAL (score 100, CRITICAL)
    1.5 MULTI-HAZARD CONCURRENT VIOLATION (score 95, HIGH/CRITICAL)
    2. OTHER HIGH SIF POTENTIAL SAFETY EVENTS (score 80, HIGH)
    2.5 SAFETY VEST VIOLATION (score 65, HIGH)
    3. PPE / HELMET VIOLATION (score 60, HIGH)
    3.5 GLOVES VIOLATION (score 55, HIGH)
    4. LOWER-SEVERITY OBSERVATIONS (score 40, LOW)
    """
    al_lower = alert_type.lower()
    if "proximity" in al_lower or "vehicle" in al_lower:
        return 150, "CRITICAL"
    if "fire" in al_lower:
        return 140, "CRITICAL"
    if "passport" in al_lower or "breach" in al_lower:
        return 120, "CRITICAL"
    if "zone" in al_lower or "restricted" in al_lower:
        return 100, "CRITICAL"
    if "multi" in al_lower:
        return 95, "HIGH"
    if "high" in str(sif_potential).lower() and "ppe" not in al_lower and "helmet" not in al_lower and "vest" not in al_lower and "glove" not in al_lower and "fire" not in al_lower:
        return 80, "HIGH"
    if "vest" in al_lower:
        return 65, "HIGH"
    if "ppe" in al_lower or "helmet" in al_lower:
        return 60, "HIGH"
    if "glove" in al_lower:
        return 55, "HIGH"
    if severity == "CRITICAL":
        return 90, "CRITICAL"
    if severity == "HIGH":
        return 70, "HIGH"
    if severity == "MEDIUM":
        return 50, "MEDIUM"
    return 40, "LOW"

def sort_alerts_by_priority(alerts: List[Alert]) -> List[Alert]:
    """
    Sorts alerts by AI Recommended Response Priority:
    1. Highest priority score first (e.g. Person-Vehicle Proximity at 150, Fire at 140 at top)
    2. For high-priority proximity/fire alerts (score >= 140), newest active/recent event appears first
    3. For normal SLA alerts with equal score, older unacknowledged alerts preserve FIFO response queue
    """
    def _sort_key(a: Alert):
        score = a.priority_score or 0
        ts = 0.0
        if isinstance(a.created_at, datetime):
            ts = a.created_at.timestamp()
        elif isinstance(a.created_at, str) and a.created_at:
            try:
                clean_str = a.created_at.replace("Z", "+00:00")
                ts = datetime.fromisoformat(clean_str).timestamp()
            except Exception:
                ts = 0.0
        # If critical alert (score >= 140: proximity, fire), newer timestamp sorts ahead (-ts)
        # For standard SLA alerts with equal score, older alert sorts ahead (+ts)
        secondary = -ts if score >= 140 else ts
        return (-score, secondary)

    return sorted(alerts, key=_sort_key)

def get_sif_action_recommendation(
    alert_type: str,
    location: str = "Demo Work Zone",
    hazard: Optional[str] = None,
    unsafe_condition: Optional[str] = None,
    person_count: int = 1,
    task_type: Optional[str] = None,
    zone_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Action Recommendation Layer (Phase 3 & Phase 5):
    Provides event-specific immediate action, consequence if not addressed,
    IOGP Life-Saving Rules, critical barrier condition, and causal 'Why SIF Potential' reasoning.
    Terminology strictly adheres to 'SIF Potential'.
    """
    al_low = (alert_type or "").lower()
    z_name = zone_name or location or "monitored zone"
    
    # 1. Restricted Lifting Zone / Suspended Load / Safety Passport Breach
    if "passport" in al_low or ("lifting" in al_low) or ("suspended" in str(hazard).lower()) or ("breach" in al_low and "zone" in al_low):
        return {
            "activity": task_type or "Mechanical Lifting Operations",
            "sif_potential": "SIF Potential",
            "sif_level": "HIGH",
            "sif_reason": "Worker entered active lifting exclusion perimeter with potential line-of-fire exposure to suspended load.",
            "sif_why": [
                "Person exposed to active hazardous lifting activity",
                "Critical exclusion barrier violated",
                "Potential line-of-fire / struck-by consequence"
            ],
            "exposure": f"{person_count} worker(s) inside active lifting swing radius ({z_name})",
            "critical_barrier": "Exclusion zone physical barricade & warning signage",
            "barrier_condition": "Violated",
            "potential_consequence": "Struck-by / line-of-fire from suspended/moving load",
            "life_saving_rule": "Line of Fire",
            "immediate_action": "Stop/hold lifting activity and clear the exclusion zone.",
            "consequence_if_not_addressed": "Continued exposure to suspended/moving load may result in serious injury or fatality.",
            "verification_type": "CCTV_VERIFIABLE"
        }
        
    # 2. Person–Vehicle Proximity / Mobile Equipment
    if "proximity" in al_low or "vehicle" in al_low:
        return {
            "activity": "Mobile Equipment Operations",
            "sif_potential": "SIF Potential",
            "sif_level": "CRITICAL",
            "sif_reason": "Pedestrian worker detected inside operating safety radius / blind spot of heavy mobile plant.",
            "sif_why": [
                "Pedestrian worker inside active vehicle blind spot radius",
                "Critical pedestrian segregation barrier breached",
                "Potential struck-by / run-over mobile plant consequence"
            ],
            "exposure": f"Personnel within hazardous proximity perimeter of mobile equipment ({location})",
            "critical_barrier": "Pedestrian segregation & equipment line-of-sight",
            "barrier_condition": "Violated",
            "potential_consequence": "Crushing / struck-by heavy vehicle",
            "life_saving_rule": "Line of Fire",
            "immediate_action": "Halt mobile equipment and clear personnel from vehicle operating radius.",
            "consequence_if_not_addressed": "Continued proximity creates direct struck-by or crushing danger leading to serious injury or fatality.",
            "verification_type": "CCTV_VERIFIABLE"
        }

    # 3. Fire Hazard / Thermal Ignition
    if "fire" in al_low:
        return {
            "activity": "Hydrocarbon Processing / Hot Work",
            "sif_potential": "SIF Potential",
            "sif_level": "CRITICAL",
            "sif_reason": "Visual flame confirmation in process / plant operations area requiring instant suppression.",
            "sif_why": [
                "Thermal combustion detected in process / hydrocarbon area",
                "Active ignition control barrier breached",
                "Potential rapid flame propagation or pressure explosion"
            ],
            "exposure": "Uncontrolled thermal combustion in monitored camera perimeter",
            "critical_barrier": "Ignition containment & localized fire suppression",
            "barrier_condition": "Violated",
            "potential_consequence": "Flash fire / thermal burn / hydrocarbon explosion",
            "life_saving_rule": "Hot Work",
            "immediate_action": "Sound localized alarm, isolate fuel/gas feed, and evacuate active hazard radius.",
            "consequence_if_not_addressed": "Uncontained thermal ignition creates severe burn and catastrophic explosion risk.",
            "verification_type": "FIELD_HSE_VERIFICATION"
        }

    # 4. Working at Height / Fall Hazard
    if "fall" in al_low or "height" in al_low or "harness" in al_low:
        return {
            "activity": "Working at Height",
            "sif_potential": "SIF Potential",
            "sif_level": "HIGH",
            "sif_reason": "Elevated worker observed without verified 100% tie-off fall arrest harness engagement.",
            "sif_why": [
                "Person working elevated without verified anchor point",
                "Personal fall arrest barrier not confirmed engaged",
                "Potential high-impact fall from height consequence"
            ],
            "exposure": f"{person_count} worker(s) elevated above ground level with unverified fall protection",
            "critical_barrier": "Fall arrest harness & certified anchorage lifeline",
            "barrier_condition": "Compromised / absent",
            "potential_consequence": "Fall from height resulting in fatal trauma",
            "life_saving_rule": "Work at Height",
            "immediate_action": "Stop the activity and verify fall-protection controls before work continues.",
            "consequence_if_not_addressed": "Continued work without effective fall protection may result in serious injury or fatality.",
            "verification_type": "FIELD_HSE_VERIFICATION"
        }

    # 5. Electrical Isolation / Energized Equipment
    if "electric" in al_low or "isolation" in al_low or "loto" in al_low or "energiz" in al_low:
        return {
            "activity": "Electrical Maintenance / Live Plant",
            "sif_potential": "SIF Potential",
            "sif_level": "CRITICAL",
            "sif_reason": "Work occurring adjacent to potentially energized circuits without confirmed zero-energy verification.",
            "sif_why": [
                "Worker in proximity to potentially energized industrial circuit",
                "Positive electrical isolation barrier not verified",
                "Potential high-energy arc flash / electrocution consequence"
            ],
            "exposure": "Worker in direct contact or line-of-fire of energized equipment",
            "critical_barrier": "Lockout / Tagout (LOTO) & positive electrical isolation",
            "barrier_condition": "Unverified / bypassed",
            "potential_consequence": "High-voltage electrocution / arc flash",
            "life_saving_rule": "Energy Isolation",
            "immediate_action": "Stop work and verify isolation before personnel remain exposed.",
            "consequence_if_not_addressed": "Continued exposure may result in electrical injury or fatality.",
            "verification_type": "FIELD_HSE_VERIFICATION"
        }

    # 6. Restricted Zone Entry (General / Compressor / Machinery Perimeter)
    if "zone" in al_low or "restricted" in al_low:
        return {
            "activity": "Active Plant Machinery Area",
            "sif_potential": "SIF Potential",
            "sif_level": "HIGH",
            "sif_reason": "Unauthorized worker breached restricted perimeter of operating plant equipment.",
            "sif_why": [
                "Person exposed to active hazardous plant machinery",
                "Critical exclusion barrier violated",
                "Potential line-of-fire / struck-by consequence"
            ],
            "exposure": f"{person_count} worker(s) inside configured restricted zone ({z_name})",
            "critical_barrier": "Exclusion zone physical barricade & boundary controls",
            "barrier_condition": "Violated",
            "potential_consequence": "Mechanical entanglement / struck-by rotating machinery",
            "life_saving_rule": "Bypassing Safety Controls",
            "immediate_action": "Stop/hold the hazardous activity and clear the danger zone.",
            "consequence_if_not_addressed": "Continued exposure may result in serious injury or fatality.",
            "verification_type": "CCTV_VERIFIABLE"
        }

    # 7. Multi-Hazard Safety Violation
    if "multi" in al_low:
        return {
            "activity": "Multi-Activity Industrial Zone",
            "sif_potential": "SIF Potential",
            "sif_level": "HIGH",
            "sif_reason": "Multiple concurrent barrier failures detected on worker, compounding incident likelihood.",
            "sif_why": [
                "Worker operating under multiple simultaneous barrier failures",
                "Primary physical protection and secondary PPE both degraded",
                "Compounded risk multiplier for high-consequence event"
            ],
            "exposure": f"{person_count} worker(s) missing multiple defense-in-depth safety controls",
            "critical_barrier": "Defense-in-depth PPE and operational zoning",
            "barrier_condition": "Multiple concurrent failures",
            "potential_consequence": "Multiple trauma / uncontrolled escalation",
            "life_saving_rule": "Bypassing Safety Controls",
            "immediate_action": "Halt active work immediately, withdraw personnel, and conduct on-site safety intervention.",
            "consequence_if_not_addressed": "Compounded barrier breakdown drastically escalates serious injury or fatality risk.",
            "verification_type": "CCTV_VERIFIABLE"
        }

    # 8. PPE - Helmet / Head Protection
    if "helmet" in al_low or "head" in al_low or "ppe" in al_low or "helmet" in str(hazard).lower():
        return {
            "activity": "Active Industrial Operations",
            "sif_potential": "SIF Potential",
            "sif_level": "HIGH",
            "sif_reason": "Personnel operating in industrial hazard zone without mandatory hard-hat head protection.",
            "sif_why": [
                "Worker present in active industrial zone without head protection",
                "Personal barrier against overhead dropped objects absent",
                "Potential blunt-force head trauma or fatality"
            ],
            "exposure": f"{person_count} worker(s) unequipped with impact head protection in active sector",
            "critical_barrier": "Personal protective equipment (Industrial Safety Helmet)",
            "barrier_condition": "Absent / not worn",
            "potential_consequence": "Severe blunt-force trauma from dropped object",
            "life_saving_rule": "Bypassing Safety Controls",
            "immediate_action": "Stop worker from entering hazard zone until certified industrial safety helmet / hard hat is donned.",
            "consequence_if_not_addressed": "Exposure to overhead impact or dropped objects can result in traumatic head injury or fatality.",
            "verification_type": "CCTV_VERIFIABLE"
        }

    # 9. PPE - Safety Vest
    if "vest" in al_low:
        return {
            "activity": "Logistics / Site Operations",
            "sif_potential": "SIF Potential",
            "sif_level": "MEDIUM",
            "sif_reason": "Personnel missing high-visibility safety vest in area with mobile equipment movement.",
            "sif_why": [
                "Worker lacks high-visibility identification in operational zone",
                "Operator visual awareness barrier compromised",
                "Elevated risk of undetected pedestrian movement in equipment lanes"
            ],
            "exposure": f"{person_count} worker(s) without high-visibility garments",
            "critical_barrier": "High-visibility warning garment",
            "barrier_condition": "Missing / degraded",
            "potential_consequence": "Equipment operator failure to detect pedestrian",
            "life_saving_rule": "Line of Fire",
            "immediate_action": "Direct personnel to don high-visibility vest before remaining in vehicle/machinery path.",
            "consequence_if_not_addressed": "Low visibility increases struck-by probability in mobile equipment zones.",
            "verification_type": "CCTV_VERIFIABLE"
        }

    # 10. PPE - Gloves
    if "glove" in al_low:
        return {
            "activity": "Manual Tooling & Equipment Handling",
            "sif_potential": "SIF Potential",
            "sif_level": "MEDIUM",
            "sif_reason": "Personnel handling machinery/tools without verified hand protection.",
            "sif_why": [
                "Direct bare-hand contact with industrial tooling or components",
                "Personal hand protection barrier absent",
                "Risk of pinch-point or sharp-edge trauma"
            ],
            "exposure": f"{person_count} worker(s) without protective gloves",
            "critical_barrier": "Industrial safety gloves",
            "barrier_condition": "Absent",
            "potential_consequence": "Severe hand laceration or pinch-point crush injury",
            "life_saving_rule": "Bypassing Safety Controls",
            "immediate_action": "Issue cut/chemical resistant gloves prior to manual handling.",
            "consequence_if_not_addressed": "Handling equipment without hand protection risks lacerations, chemical burns, or crush injury.",
            "verification_type": "CCTV_VERIFIABLE"
        }

    # 11. Generic Default Fallback
    return {
        "activity": "General Industrial Operations",
        "sif_potential": "SIF Potential",
        "sif_level": "MEDIUM",
        "sif_reason": "Safety condition detected requiring supervisory verification and corrective action.",
        "sif_why": [
            "Person observed under unverified safety conditions",
            "Operational barrier requires inspection",
            "Potential workplace safety compromise"
        ],
        "exposure": f"{person_count} worker(s) in monitored work area",
        "critical_barrier": "Site operational controls",
        "barrier_condition": "Unverified",
        "potential_consequence": "Uncontrolled incident / workplace injury",
        "life_saving_rule": "Bypassing Safety Controls",
        "immediate_action": "Halt task, assess site controls, and verify safe perimeter.",
        "consequence_if_not_addressed": "Uncontrolled exposure to site hazards may result in serious injury or fatality.",
        "verification_type": "CCTV_VERIFIABLE"
    }

class AlertStateManager:
    def __init__(self):
        self.lock = threading.RLock()
        self._active_alerts: Dict[str, Alert] = {}
        self.history: List[Alert] = []
        self.pattern_actions: Dict[str, Dict[str, Any]] = {}
        self.active_websockets: Set[WebSocket] = set()
        
        # Visual evidence store (evidence_id -> jpeg bytes)
        self.evidence_store: Dict[str, bytes] = {}
        
        # Dual Restricted Zone state (Permanent site zones + Passport temporary exclusion zones)
        self.zones: Dict[str, RestrictedZone] = {}
        default_perm = RestrictedZone(
            zone_id="ZONE-001",
            name="Compressor Restricted Area",
            camera_id="C-01",
            zone_type="floor",
            zone_category="PERMANENT",
            severity="HIGH",
            polygon=[[120.0, 180.0], [520.0, 180.0], [520.0, 440.0], [120.0, 440.0]],
            enabled=True,
            status="ACTIVE"
        )
        self.zones["ZONE-001"] = default_perm
        self._active_zone_override: Optional[RestrictedZone] = None
        
        # Safety Passport state
        self.passports: Dict[str, SafetyPassport] = {}
        self.active_passport_id: Optional[str] = None
        self._passport_counter: int = 0
        self._incident_counter: int = 42
        self.active_camera_id: str = "C-01"

        # Most recently resolved alert (for backwards compatibility with test_zone.py)
        self._last_resolved_alert: Optional[Alert] = None

        # Current real-time CV detection state
        self.person_detected: bool = False
        self.helmet_detected: bool = False
        self.person_count: int = 0
        self.unhelmeted_count: int = 0
        self.unhelmeted_ids: List[str] = []
        self.vest_detected: bool = False
        self.unvested_count: int = 0
        self.unvested_ids: List[str] = []
        self.gloves_detected: bool = False
        self.ungloved_count: int = 0
        self.ungloved_ids: List[str] = []
        self.person_violations: Dict[str, List[str]] = {}
        self.ppe_statuses: Dict[str, Dict[str, str]] = {}
        self.current_safety_state: str = "MONITORING" # SAFE, VIOLATION, MONITORING
        
        # Restricted Zone detection state
        self.zone_violation: bool = False
        self.zone_status: str = "CLEAR" # "CLEAR", "VIOLATION", "NO_ZONE", "LOW_CONFIDENCE"
        self.persons_in_zone: int = 0
        self.zone_occupancy_score: float = 0.0
        self.zone_debug_info: Optional[str] = None
        
        # Fire detection state (Feature 3)
        self.fire_detected: bool = False
        self.fire_confidence: float = 0.0
        
        # Debounce tracking for single violation persistence
        self.violation_start_time: Optional[float] = None
        self.vest_violation_start_time: Optional[float] = None
        self.gloves_violation_start_time: Optional[float] = None
        self.safe_start_time: Optional[float] = None
        self.violation_persist_threshold: float = 1.5 # 1.5 seconds consistent detection
        
        # Simulated override mode
        self.simulated_mode: bool = False
        self.simulated_state: Optional[str] = None # "SAFE", "VIOLATION", "ZONE_VIOLATION", "MULTI_VIOLATION", None
        
        # Network details
        self.lan_ip: str = get_lan_ip()
        self.supervisor_url: str = f"http://{self.lan_ip}:5173/supervisor"
        
        # Background worker for escalation and debouncing
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = True
        self._watcher_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watcher_thread.start()
        self._load_persisted_pattern_actions()

    def _load_persisted_pattern_actions(self):
        try:
            try:
                from backend.database import db
            except ImportError:
                from database import db
            with db.get_connection() as conn:
                cur = conn.execute("""
                    SELECT target_id, new_value FROM reviews 
                    WHERE target_type = 'PATTERN_ACTION' 
                    ORDER BY timestamp ASC
                """)
                for target_id, new_val in cur.fetchall():
                    if new_val:
                        try:
                            data = json.loads(new_val) if isinstance(new_val, str) else new_val
                            if isinstance(data, dict):
                                self.pattern_actions[target_id] = data
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Could not preload pattern actions from reviews: {e}")

    def get_next_incident_id(self) -> str:
        with self.lock:
            self._incident_counter += 1
            return f"SR-2026-{self._incident_counter:04d}"

    @property
    def active_zone(self) -> Optional[RestrictedZone]:
        """
        Backwards-compatible property returning the most relevant active zone.
        Prioritizes active temporary passport zone if one exists,
        otherwise active permanent zone, or any configured zone.
        """
        with self.lock:
            if self._active_zone_override is not None:
                return self._active_zone_override
            # 1. Check for enabled passport temporary zone
            for z in self.zones.values():
                if z.zone_category == "PASSPORT_TEMPORARY" and z.enabled and z.status != "EXPIRED":
                    return z
            # 2. Check for enabled permanent zone
            for z in self.zones.values():
                if z.zone_category == "PERMANENT" and z.enabled:
                    return z
            # 3. Check for any enabled zone
            for z in self.zones.values():
                if z.enabled:
                    return z
            # 4. Fallback to any zone in registry
            if self.zones:
                return next(iter(self.zones.values()))
            return None

    @active_zone.setter
    def active_zone(self, val: Optional[RestrictedZone]):
        with self.lock:
            if val is None:
                self._active_zone_override = None
                for z in self.zones.values():
                    z.enabled = False
            else:
                self._active_zone_override = val
                self.zones[val.zone_id] = val

    def get_evidence(self, evidence_id: str) -> Optional[bytes]:
        """Retrieves raw JPEG evidence bytes by evidence_id"""
        with self.lock:
            return self.evidence_store.get(evidence_id)

    def get_active_zones(self) -> List[RestrictedZone]:
        """Returns all currently enabled and unexpired zones (permanent + temporary)"""
        with self.lock:
            now = datetime.now()
            active = []
            for z in self.zones.values():
                if not z.enabled:
                    continue
                if z.zone_category == "PASSPORT_TEMPORARY":
                    if z.status == "EXPIRED":
                        continue
                    if z.expires_at:
                        try:
                            exp = datetime.fromisoformat(z.expires_at)
                            if now >= exp:
                                continue
                        except Exception:
                            pass
                active.append(z)
            return active

    def get_permanent_zones(self) -> List[RestrictedZone]:
        """Returns permanent safety zones"""
        with self.lock:
            return [z for z in self.zones.values() if z.zone_category == "PERMANENT"]

    def get_temporary_zones(self) -> List[RestrictedZone]:
        """Returns passport temporary exclusion zones"""
        with self.lock:
            return [z for z in self.zones.values() if z.zone_category == "PASSPORT_TEMPORARY"]

    @property
    def active_alert(self) -> Optional[Alert]:
        """
        Backwards-compatible property returning the highest-priority active alert.
        If no active alerts remain, returns the most recently resolved alert (if any)
        to maintain compatibility with existing tests that check active_alert.status == "RESOLVED".
        """
        with self.lock:
            if self._active_alerts:
                sorted_alerts = sort_alerts_by_priority(list(self._active_alerts.values()))
                return sorted_alerts[0] if sorted_alerts else None
            return self._last_resolved_alert

    @active_alert.setter
    def active_alert(self, val: Optional[Alert]):
        with self.lock:
            if val is None:
                self._active_alerts.clear()
                self._last_resolved_alert = None
            else:
                self._active_alerts[val.id] = val
                if val.status == "RESOLVED":
                    self._last_resolved_alert = val

    def get_active_alerts_list(self) -> List[Alert]:
        """Returns all active alerts sorted by AI Recommended Response Priority"""
        with self.lock:
            return sort_alerts_by_priority(list(self._active_alerts.values()))

    def get_history_list(self) -> List[Alert]:
        """Returns resolved historical alerts sorted newest first"""
        with self.lock:
            return sorted(
                list(self.history),
                key=lambda a: (a.resolved_at or a.created_at),
                reverse=True
            )

    # ==========================================
    # START WORK SAFETY PASSPORT METHODS
    # ==========================================

    @property
    def active_passport(self) -> Optional[SafetyPassport]:
        """
        Returns the currently active, paused, or pending passport for high-risk work.
        """
        with self.lock:
            if self.active_passport_id and self.active_passport_id in self.passports:
                return self.passports[self.active_passport_id]
            for p in self.passports.values():
                if p.status in ["ACTIVE", "PAUSED", "AWAITING_RESTORATION", "PENDING_APPROVAL", "PENDING_VERIFICATION"]:
                    return p
            return None

    def get_passports_list(self) -> List[SafetyPassport]:
        """Returns all passports sorted newest first"""
        with self.lock:
            return sorted(list(self.passports.values()), key=lambda p: p.created_at, reverse=True)

    def get_default_controls_for_task(self, task_type: str = "Mechanical Lifting") -> List[ControlItem]:
        """
        Pre-start safety checklist controls with honest verification sources.
        AI verifies only what CCTV can observe (PPE, zone occupancy).
        Supervisor physically verifies site and briefed workers.
        HSE verifies formal permit/authorization.
        """
        zone_active = bool(self.active_zone and self.active_zone.enabled)
        zone_clear = bool(not self.zone_violation and self.persons_in_zone == 0)
        ppe_compliant = bool(self.person_detected and self.helmet_detected and self.unhelmeted_count == 0)

        return [
            ControlItem(
                id="ctrl-1",
                name="Authorized supervisor assigned",
                verification_source="SUPERVISOR VERIFIED",
                verified=True,
                verified_by="Demo Supervisor",
                verified_at=datetime.now().isoformat()
            ),
            ControlItem(
                id="ctrl-2",
                name="Exclusion zone active",
                verification_source="SYSTEM VERIFIED",
                verified=zone_active,
                verified_by="System Vision Engine" if zone_active else None,
                verified_at=datetime.now().isoformat() if zone_active else None
            ),
            ControlItem(
                id="ctrl-3",
                name="Zone currently clear",
                verification_source="AI VERIFIED",
                verified=zone_clear,
                verified_by="YOLO-Pose Edge Vision" if zone_clear else None,
                verified_at=datetime.now().isoformat() if zone_clear else None
            ),
            ControlItem(
                id="ctrl-4",
                name="Required PPE confirmed",
                verification_source="AI + SUPERVISOR VERIFIED",
                verified=ppe_compliant,
                verified_by="AI Hard-Hat Classifier" if ppe_compliant else None,
                verified_at=datetime.now().isoformat() if ppe_compliant else None
            ),
            ControlItem(
                id="ctrl-5",
                name="Emergency response owner available",
                verification_source="SUPERVISOR VERIFIED",
                verified=False
            ),
            ControlItem(
                id="ctrl-6",
                name="Permit / authorization",
                verification_source="HSE VERIFIED",
                verified=False
            ),
        ]

    def create_passport(self, req: CreatePassportRequest) -> SafetyPassport:
        """
        Creates a new Safety Passport for a high-risk task.
        Can be requested from Supervisor or HSE.
        Initial status is PENDING_VERIFICATION.
        """
        with self.lock:
            self._passport_counter += 1
            now = datetime.now()
            pid = f"SP-{now.strftime('%Y%m%d')}-{self._passport_counter:03d}"
            
            if req.temporary_zone or req.zone_polygon:
                tz_poly = req.temporary_zone.polygon if (req.temporary_zone and req.temporary_zone.polygon) else (req.zone_polygon or [[150.0, 150.0], [490.0, 150.0], [490.0, 420.0], [150.0, 420.0]])
                tz_name = req.linked_zone_name or (req.temporary_zone.name if req.temporary_zone else "Lifting Exclusion Zone")
                tz_cam = req.camera_id or (req.temporary_zone.camera_id if req.temporary_zone else "C-01")
                tz_dur = req.zone_duration_minutes or (req.temporary_zone.duration_minutes if req.temporary_zone else req.duration_minutes)
                tz_dur = min(tz_dur, req.duration_minutes)
                tz_id = f"ZONE-TEMP-{self._passport_counter:03d}"
                temp_zone = RestrictedZone(
                    zone_id=tz_id,
                    name=tz_name,
                    camera_id=tz_cam,
                    zone_type="floor",
                    zone_category="PASSPORT_TEMPORARY",
                    passport_id=pid,
                    duration_minutes=tz_dur,
                    expires_at=(now + timedelta(minutes=tz_dur)).isoformat(),
                    status="ACTIVE",
                    severity="HIGH",
                    polygon=tz_poly,
                    enabled=True
                )
                self.zones[tz_id] = temp_zone
                linked_z_id = tz_id
                linked_z_name = tz_name
            else:
                linked_z_id = req.linked_zone_id or (self.active_zone.zone_id if self.active_zone else "ZONE-001")
                linked_z_name = req.linked_zone_name or (self.active_zone.name if self.active_zone else "Lifting Exclusion Zone")
            
            controls = self.get_default_controls_for_task(req.task_type)
            
            created_event = PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="created",
                actor=req.created_by or "Demo Supervisor",
                description=f"Safety Passport created for {req.task_type} at {req.location} (Permit Ref: {req.permit_reference or 'N/A'})"
            )
            
            passport = SafetyPassport(
                id=pid,
                task_type=req.task_type,
                location=req.location,
                supervisor=req.supervisor,
                camera_id=req.camera_id,
                linked_zone_id=linked_z_id,
                linked_zone_name=linked_z_name,
                duration_minutes=req.duration_minutes,
                permit_reference=req.permit_reference,
                status="PENDING_VERIFICATION",
                created_by=req.created_by or "Demo Supervisor",
                created_at=now.isoformat(),
                controls=controls,
                events=[created_event]
            )
            
            self.passports[pid] = passport
            self.active_passport_id = pid
            
        self.notify_clients()
        return passport

    def verify_control(self, passport_id: str, control_id: str, verified: bool = True, verified_by: str = "Demo Supervisor", notes: Optional[str] = None, user_role: str = "supervisor") -> SafetyPassport:
        """
        Verifies or un-verifies a specific pre-start control.
        Enforces strict role separation: HSE verification (ctrl-6) requires HSE role.
        """
        with self.lock:
            p = self.passports.get(passport_id)
            if not p:
                raise ValueError(f"Passport {passport_id} not found")
                
            ctrl = next((c for c in p.controls if c.id == control_id), None)
            if not ctrl:
                raise ValueError(f"Control {control_id} not found in passport {passport_id}")
                
            # Strict role check: Permit / Authorization or HSE verified controls require HSE role
            if (ctrl.id == "ctrl-6" or "HSE" in (ctrl.verification_source or "").upper()) and str(user_role).lower() != "hse":
                raise PermissionError("Forbidden: HSE verification is an HSE-only responsibility. Supervisor cannot verify permit authorization.")
                
            now = datetime.now()
            ctrl.verified = verified
            ctrl.verified_by = verified_by if verified else None
            ctrl.verified_at = now.isoformat() if verified else None
            if notes:
                ctrl.notes = notes
                
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="control_verified",
                actor=verified_by,
                description=f"Control '{ctrl.name}' marked {'VERIFIED' if verified else 'UNVERIFIED'} ({ctrl.verification_source})"
            ))
            
            all_verified = all(c.verified for c in p.controls)
            if all_verified and p.status == "PENDING_VERIFICATION":
                p.status = "PENDING_APPROVAL"
                p.events.append(PassportEvent(
                    id=f"evt-{int(now.timestamp()*1000)+1}",
                    timestamp=now.isoformat(),
                    event_type="submitted",
                    actor=verified_by,
                    description="All 6/6 pre-start controls verified. Ready for HSE clearance."
                ))
            elif not all_verified and p.status == "PENDING_APPROVAL":
                p.status = "PENDING_VERIFICATION"
                
        self.notify_clients()
        return p

    def approve_passport(self, passport_id: str, approved_by: str = "HSE Manager", notes: Optional[str] = None, user_role: str = "hse") -> SafetyPassport:
        """
        Formal HSE authorization for the Safety Passport.
        Requires HSE role authorization.
        """
        if str(user_role).lower() != "hse":
            raise PermissionError("Forbidden: Safety Passport formal approval requires HSE role authorization.")

        with self.lock:
            p = self.passports.get(passport_id)
            if not p:
                raise ValueError(f"Passport {passport_id} not found")
                
            now = datetime.now()
            p.approved_by = approved_by
            p.approved_at = now.isoformat()
            
            # Ensure permit control is marked verified by HSE
            permit_ctrl = next((c for c in p.controls if "permit" in c.name.lower() or "authorization" in c.name.lower()), None)
            if permit_ctrl:
                permit_ctrl.verified = True
                permit_ctrl.verified_by = approved_by
                permit_ctrl.verified_at = now.isoformat()
                
            all_verified = all(c.verified for c in p.controls)
            if all_verified:
                p.status = "PENDING_APPROVAL"
                
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="approved",
                actor=approved_by,
                description=f"Formal HSE work authorization granted by {approved_by}"
            ))
            
        self.notify_clients()
        return p

    def activate_passport(self, passport_id: str, user_role: str = "hse") -> tuple[bool, str, Optional[SafetyPassport]]:
        """
        Activates the Safety Passport.
        Requires all mandatory controls to be verified.
        Requires HSE role authorization.
        Sets time-bound validity.
        """
        if str(user_role).lower() != "hse":
            raise PermissionError("Forbidden: Safety Passport activation requires HSE role authorization.")
        with self.lock:
            p = self.passports.get(passport_id)
            if not p:
                return False, f"Passport {passport_id} not found", None
                
            # Re-evaluate live AI / System controls to ensure honesty
            if self.active_zone and self.active_zone.enabled:
                z_ctrl = next((c for c in p.controls if c.id == "ctrl-2"), None)
                if z_ctrl:
                    z_ctrl.verified = True
                    z_ctrl.verified_by = "System Vision Engine"
                    z_ctrl.verified_at = datetime.now().isoformat()
                    
            if not self.zone_violation and self.persons_in_zone == 0:
                c_ctrl = next((c for c in p.controls if c.id == "ctrl-3"), None)
                if c_ctrl:
                    c_ctrl.verified = True
                    c_ctrl.verified_by = "YOLO-Pose Edge Vision"
                    c_ctrl.verified_at = datetime.now().isoformat()
                    
            missing = [c.name for c in p.controls if not c.verified]
            if missing:
                verified_count = len(p.controls) - len(missing)
                reason = f"SAFETY PASSPORT BLOCKED: {verified_count} / {len(p.controls)} controls verified. Missing: {', '.join(missing)}"
                return False, reason, p
                
            now = datetime.now()
            p.status = "ACTIVE"
            p.activated_at = now.isoformat()
            p.expires_at = (now + timedelta(minutes=p.duration_minutes)).isoformat()
            
            # Align linked temporary zone with passport activation and expiry
            if p.linked_zone_id and p.linked_zone_id in self.zones:
                tz = self.zones[p.linked_zone_id]
                if tz.zone_category == "PASSPORT_TEMPORARY":
                    tz.enabled = True
                    tz.status = "ACTIVE"
                    tz.passport_id = p.id
                    tz_dur = min(tz.duration_minutes or p.duration_minutes, p.duration_minutes)
                    tz.duration_minutes = tz_dur
                    tz.expires_at = (now + timedelta(minutes=tz_dur)).isoformat()
            
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="activated",
                actor=p.approved_by or "HSE Manager",
                description=f"Safety Passport ACTIVE. Valid for {p.duration_minutes} minutes until {p.expires_at}."
            ))
            self.active_passport_id = p.id
            
        self.notify_clients()
        return True, "Safety Passport successfully activated", p

    def pause_passport_due_to_breach(self, breach_reason: str = "Lifting exclusion zone breached", evidence_frame: Optional[bytes] = None) -> Optional[Alert]:
        """
        Triggered when a linked critical barrier (exclusion zone) is breached while passport is ACTIVE.
        Pauses the passport and generates a priority CRITICAL safety alert.
        """
        alert = None
        trigger_alert_needed = False
        with self.lock:
            p = self.active_passport
            if not p or p.status != "ACTIVE":
                return None
                
            now = datetime.now()
            p.status = "PAUSED"
            p.paused_at = now.isoformat()
            p.breach_reason = breach_reason
            
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="paused",
                actor="AI CCTV Vision",
                description=f"CRITICAL BARRIER BREACH: {breach_reason}. High-risk work PAUSED."
            ))
            
            # Check if breach alert already exists
            existing_breach = None
            for a in self._active_alerts.values():
                if a.type == "SAFETY PASSPORT BREACH" or a.id == p.active_breach_alert_id:
                    existing_breach = a
                    break
                    
            if not existing_breach:
                trigger_alert_needed = True
            else:
                alert = existing_breach

        if trigger_alert_needed and p:
            alert = self.trigger_alert(
                alert_type="SAFETY PASSPORT BREACH",
                location=p.location,
                camera=p.camera_id,
                severity="CRITICAL",
                sif_potential="HIGH / POTENTIAL",
                person_count=max(1, self.persons_in_zone),
                title="SAFETY PASSPORT PAUSED: Restricted Zone Breach",
                short_summary=f"Restricted Zone Breach — Lifting exclusion zone entered during {p.task_type}",
                hazard="Line of Fire / Exclusion Zone Intrusion during High-Risk Activity",
                unsafe_condition=f"Person detected occupying {p.linked_zone_name} during active {p.task_type}",
                notes="Automated SIF Prevention Alert: High-risk passport paused due to critical barrier breach. Line of Fire → Struck-by / Crushing Potential.",
                evidence_frame=evidence_frame
            )
            with self.lock:
                p.active_breach_alert_id = alert.id
                p.events.append(PassportEvent(
                    id=f"evt-{int(now.timestamp()*1000)+1}",
                    timestamp=now.isoformat(),
                    event_type="alerted",
                    actor="Alert Watchdog",
                    description=f"CRITICAL ALERT {alert.id} generated. 20s Supervisor Response Window initiated."
                ))
                
        self.notify_clients()
        return alert

    def verify_barrier_restored(self, passport_id: str, supervisor_id: str = "Demo Supervisor", notes: Optional[str] = None) -> tuple[bool, str, Optional[SafetyPassport]]:
        """
        Supervisor explicitly verifies that the critical barrier has been physically restored.
        Reactivates passport and resolves the linked breach alert.
        """
        alert_to_resolve = None
        with self.lock:
            p = self.passports.get(passport_id)
            if not p:
                return False, f"Passport {passport_id} not found", None
                
            if p.status not in ["PAUSED", "AWAITING_RESTORATION"]:
                return False, f"Passport is in state '{p.status}', not awaiting restoration", p
                
            now = datetime.now()
            p.status = "ACTIVE"
            p.reactivated_at = now.isoformat()
            p.breach_reason = None
            
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="restoration_verified",
                actor=supervisor_id,
                description=f"Barrier restoration physically verified by {supervisor_id}. {notes or 'Exclusion zone clear and secured.'}"
            ))
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)+1}",
                timestamp=now.isoformat(),
                event_type="reactivated",
                actor=supervisor_id,
                description="Safety Passport REACTIVATED. High-risk work cleared to continue."
            ))
            
            alert_id = p.active_breach_alert_id
            p.active_breach_alert_id = None
            
        if alert_id:
            self.resolve_alert(
                supervisor_id=supervisor_id, 
                notes=f"Barrier restoration verified on-site: {notes or 'Exclusion zone cleared'}", 
                alert_id=alert_id
            )
            
        self.notify_clients()
        return True, "Barrier restoration verified and passport reactivated", p

    def close_passport(self, passport_id: str) -> SafetyPassport:
        """
        Closes the Safety Passport upon task completion.
        Immediately deactivates linked temporary zone.
        """
        with self.lock:
            p = self.passports.get(passport_id)
            if not p:
                raise ValueError(f"Passport {passport_id} not found")
            now = datetime.now()
            p.status = "CLOSED"
            p.closed_at = now.isoformat()
            # CHANGE 6 & 7: linked temporary zone must immediately deactivate
            if p.linked_zone_id and p.linked_zone_id in self.zones:
                tz = self.zones[p.linked_zone_id]
                if tz.zone_category == "PASSPORT_TEMPORARY":
                    tz.enabled = False
                    tz.status = "INACTIVE"
            p.events.append(PassportEvent(
                id=f"evt-{int(now.timestamp()*1000)}",
                timestamp=now.isoformat(),
                event_type="closed",
                actor="Demo Supervisor",
                description="Safety Passport formally closed upon task completion."
            ))
            if self.active_passport_id == passport_id:
                self.active_passport_id = None
        self.notify_clients()
        return p

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def register_websocket(self, ws: WebSocket):
        with self.lock:
            self.active_websockets.add(ws)

    def unregister_websocket(self, ws: WebSocket):
        with self.lock:
            self.active_websockets.discard(ws)

    def set_zone(self, zone: RestrictedZone) -> RestrictedZone:
        with self.lock:
            # Handle zone_category normalization
            if getattr(zone, 'zone_category', None) is None:
                if str(zone.zone_type).upper() in ["PERMANENT", "PASSPORT_TEMPORARY"]:
                    zone.zone_category = str(zone.zone_type).upper()
                    zone.zone_type = "floor"
                else:
                    zone.zone_category = "PERMANENT"
            
            if zone.zone_category == "PASSPORT_TEMPORARY":
                if not zone.expires_at and zone.duration_minutes:
                    zone.expires_at = (datetime.now() + timedelta(minutes=zone.duration_minutes)).isoformat()

            self.zones[zone.zone_id] = zone
            self._active_zone_override = zone
            self.zone_violation = False
            self.zone_status = "CLEAR" if zone.enabled else "NO_ZONE"
            self.persons_in_zone = 0
        self.notify_clients()
        return zone

    def delete_zone(self, zone_id: Optional[str] = None):
        with self.lock:
            if zone_id and zone_id in self.zones:
                del self.zones[zone_id]
            else:
                cur = self.active_zone
                if cur and cur.zone_id in self.zones:
                    del self.zones[cur.zone_id]
                else:
                    self.zones.clear()
            self._active_zone_override = None
            
            has_enabled = any(z.enabled for z in self.zones.values())
            if not has_enabled:
                self.zone_violation = False
                self.zone_status = "NO_ZONE"
                self.persons_in_zone = 0
                self.zone_occupancy_score = 0.0
                self.zone_debug_info = None
                # Immediately remove any active Restricted Zone Entry alerts
                to_remove = [aid for aid, a in self._active_alerts.items() if a.type == "Restricted Zone Entry"]
                for aid in to_remove:
                    del self._active_alerts[aid]
                if not self._active_alerts:
                    self.current_safety_state = "SAFE"
        self.notify_clients()

    def toggle_zone(self, zone_id: Optional[str] = None) -> Optional[RestrictedZone]:
        with self.lock:
            target = None
            if zone_id and zone_id in self.zones:
                target = self.zones[zone_id]
            else:
                target = self.active_zone
                
            # If no zone exists and toggle was requested, restore default permanent zone
            if not target and (not zone_id or zone_id == "ZONE-001"):
                target = RestrictedZone(
                    zone_id="ZONE-001",
                    name="Compressor Restricted Area",
                    camera_id="C-01",
                    zone_type="floor",
                    zone_category="PERMANENT",
                    severity="HIGH",
                    polygon=[[120.0, 180.0], [520.0, 180.0], [520.0, 440.0], [120.0, 440.0]],
                    enabled=True,
                    status="ACTIVE"
                )
                self.zones["ZONE-001"] = target
                self.zone_status = "CLEAR"
                self.notify_clients()
                return target

            if target:
                target.enabled = not target.enabled
                self.zone_status = "CLEAR" if target.enabled else "NO_ZONE"
                if not target.enabled:
                    self.zone_violation = False
                    self.persons_in_zone = 0
                    self.zone_occupancy_score = 0.0
                    self.zone_debug_info = None
                    has_enabled = any(z.enabled for z in self.zones.values())
                    if not has_enabled:
                        to_remove = [aid for aid, a in self._active_alerts.items() if a.type == "Restricted Zone Entry"]
                        for aid in to_remove:
                            del self._active_alerts[aid]
                        if not self._active_alerts:
                            self.current_safety_state = "SAFE"
        self.notify_clients()
        return target

    def restore_default_zone(self) -> RestrictedZone:
        with self.lock:
            perm = RestrictedZone(
                zone_id="ZONE-001",
                name="Compressor Restricted Area",
                camera_id="C-01",
                zone_type="floor",
                zone_category="PERMANENT",
                severity="HIGH",
                polygon=[[120.0, 180.0], [520.0, 180.0], [520.0, 440.0], [120.0, 440.0]],
                enabled=True,
                status="ACTIVE"
            )
            self.zones["ZONE-001"] = perm
            self._active_zone_override = None
            self.zone_status = "CLEAR"
            self.zone_violation = False
            self.persons_in_zone = 0
            self.zone_occupancy_score = 0.0
            self.zone_debug_info = None
        self.notify_clients()
        return perm

    def get_system_status(self) -> SystemStatus:
        with self.lock:
            alerts_sorted = sort_alerts_by_priority(list(self._active_alerts.values()))
            highest_priority_alert = alerts_sorted[0] if alerts_sorted else None
            active_p = self.active_passport
            active_z = self.active_zone

            # Clean Dashboard KPI calculations (Phase 6)
            sif_pot_cnt = sum(
                1 for a in alerts_sorted 
                if getattr(a, 'sif_level', '') in ("CRITICAL", "HIGH") or "SIF" in str(getattr(a, 'sif_potential', ''))
            )
            open_act_cnt = sum(
                1 for a in alerts_sorted 
                if getattr(a, 'action_status', '') in ("ASSIGNED", "IN_PROGRESS") or getattr(a, 'status', '') in ("WAITING_FOR_RESPONSE", "RESPONDING", "ESCALATED")
            )
            await_ver_cnt = sum(
                1 for a in alerts_sorted 
                if getattr(a, 'verification_status', '') == "AWAITING_VERIFICATION"
            )
            verified_cnt = sum(
                1 for a in self.history 
                if getattr(a, 'verification_status', '') == "VERIFIED" or getattr(a, 'status', '') == "RESOLVED"
            )
            if verified_cnt == 0 and len(self.history) > 0:
                verified_cnt = len(self.history)

            return SystemStatus(
                system_status="ONLINE",
                active_alerts=alerts_sorted,
                active_alert=highest_priority_alert,
                person_detected=self.person_detected,
                helmet_detected=self.helmet_detected,
                person_count=self.person_count,
                unhelmeted_count=self.unhelmeted_count,
                vest_detected=getattr(self, 'vest_detected', False),
                unvested_count=getattr(self, 'unvested_count', 0),
                gloves_detected=getattr(self, 'gloves_detected', False),
                ungloved_count=getattr(self, 'ungloved_count', 0),
                fire_detected=getattr(self, 'fire_detected', False),
                fire_confidence=getattr(self, 'fire_confidence', 0.0),
                current_safety_state=self.current_safety_state,
                active_zone=active_z,
                permanent_zones=self.get_permanent_zones(),
                temporary_zones=self.get_temporary_zones(),
                active_zones=self.get_active_zones(),
                zone_violation=self.zone_violation,
                zone_status=self.zone_status,
                persons_in_zone=self.persons_in_zone,
                zone_occupancy_score=self.zone_occupancy_score,
                zone_debug_info=self.zone_debug_info,
                lan_ip=self.lan_ip,
                supervisor_url=self.supervisor_url,
                camera_active=True,
                camera_name="C-01 (Laptop Webcam)",
                timestamp=datetime.now().isoformat(),
                active_passport=active_p,
                passport_status=active_p.status if active_p else "NO_PASSPORT",
                sif_potential_count=sif_pot_cnt,
                open_actions_count=open_act_cnt,
                awaiting_verification_count=await_ver_cnt,
                verified_count=verified_cnt
            )

    def _process_person_findings(self, raw_findings: Optional[List[Union[PersonFinding, Dict[str, Any]]]], alert_id: str) -> List[PersonFinding]:
        """
        Processes person findings: stores individual crops in evidence_store under ev-{alert_id}-p{idx+1},
        constructs PersonFinding models, and attaches evidence_crop_url and base64.
        """
        if not raw_findings:
            return []
        processed: List[PersonFinding] = []
        for idx, item in enumerate(raw_findings):
            if isinstance(item, PersonFinding):
                processed.append(item)
                continue
            if isinstance(item, dict):
                crop_bytes = item.get("crop_bytes") or item.get("evidence_crop_bytes")
                crop_b64 = item.get("evidence_crop_base64") or item.get("evidence_crop")
                p_id = item.get("person_id") or f"Person #{idx+1}"
                
                p_ev_id = f"ev-{alert_id}-p{idx+1}"
                if crop_bytes:
                    self.evidence_store[p_ev_id] = crop_bytes
                    ev_url = f"/api/evidence/{p_ev_id}"
                elif crop_b64:
                    try:
                        raw_b64 = crop_b64.split(",", 1)[1] if "," in crop_b64 else crop_b64
                        self.evidence_store[p_ev_id] = base64.b64decode(raw_b64)
                        ev_url = f"/api/evidence/{p_ev_id}"
                    except Exception:
                        ev_url = item.get("evidence_crop_url")
                else:
                    ev_url = item.get("evidence_crop_url")
                
                pf = PersonFinding(
                    person_id=p_id,
                    track_id=item.get("track_id", idx+1),
                    bbox=item.get("bbox", []),
                    helmet_status=item.get("helmet_status", "UNKNOWN"),
                    vest_status=item.get("vest_status", "UNKNOWN"),
                    glove_status=item.get("glove_status", "UNKNOWN"),
                    overall_ppe_status=item.get("overall_ppe_status", "OK"),
                    violations=item.get("violations", []),
                    evidence_crop_url=ev_url,
                    evidence_crop_base64=crop_b64,
                    helmet_confidence=float(item.get("helmet_confidence", 0.0)),
                    vest_confidence=float(item.get("vest_confidence", 0.0)),
                    glove_confidence=float(item.get("glove_confidence", 0.0)),
                    in_zone=bool(item.get("in_zone", False))
                )
                processed.append(pf)
        return processed

    def _process_vehicle_findings(self, raw_findings: Optional[List[Union[VehicleFinding, Dict[str, Any]]]], alert_id: str) -> List[VehicleFinding]:
        """
        Processes vehicle findings: stores individual vehicle crops in evidence_store under ev-{alert_id}-veh{idx+1},
        constructs VehicleFinding models, and attaches evidence_crop_url and base64.
        """
        if not raw_findings:
            return []
        processed: List[VehicleFinding] = []
        for idx, item in enumerate(raw_findings):
            if isinstance(item, VehicleFinding):
                processed.append(item)
                continue
            if isinstance(item, dict):
                crop_bytes = item.get("crop_bytes") or item.get("evidence_crop_bytes")
                crop_b64 = item.get("evidence_crop_base64") or item.get("evidence_crop")
                v_id = item.get("vehicle_id") or f"Vehicle #{idx+1}"
                
                v_ev_id = f"ev-{alert_id}-veh{idx+1}"
                if crop_bytes:
                    self.evidence_store[v_ev_id] = crop_bytes
                    ev_url = f"/api/evidence/{v_ev_id}"
                elif crop_b64:
                    try:
                        raw_b64 = crop_b64.split(",", 1)[1] if "," in crop_b64 else crop_b64
                        self.evidence_store[v_ev_id] = base64.b64decode(raw_b64)
                        ev_url = f"/api/evidence/{v_ev_id}"
                    except Exception:
                        ev_url = item.get("evidence_crop_url")
                else:
                    ev_url = item.get("evidence_crop_url")
                
                vf = VehicleFinding(
                    vehicle_id=v_id,
                    track_id=item.get("track_id", idx+1),
                    class_name=item.get("class_name", "vehicle"),
                    bbox=item.get("bbox", []),
                    confidence=float(item.get("confidence", 0.0)),
                    evidence_crop_url=ev_url,
                    evidence_crop_base64=crop_b64,
                    proximity_zone=item.get("proximity_zone", [])
                )
                processed.append(vf)
        return processed

    def trigger_alert(self, alert_type: str = "Helmet/PPE Violation", 
                      location: str = "Demo Work Zone", 
                      camera: str = "C-01",
                      severity: str = "HIGH",
                      response_sec: int = RESPONSE_SLA_SECONDS,
                      action_sec: int = ACTION_SLA_SECONDS,
                      sif_potential: str = "HIGH / POTENTIAL",
                      hazard: Optional[str] = None,
                      unsafe_condition: Optional[str] = None,
                      notes: Optional[str] = None,
                      person_count: int = 1,
                      affected_person_ids: Optional[List[str]] = None,
                      title: Optional[str] = None,
                      short_summary: Optional[str] = None,
                      evidence_frame: Optional[bytes] = None,
                      violations: Optional[List[str]] = None,
                      ppe_status: Optional[Dict[str, str]] = None,
                      person_findings: Optional[List[Union[PersonFinding, Dict[str, Any]]]] = None,
                      person_id: Optional[str] = None,
                      person_crop_bytes: Optional[bytes] = None,
                      person_crop_base64: Optional[str] = None,
                      vehicle_id: Optional[str] = None,
                      vehicle_type: Optional[str] = None,
                      vehicle_crop_bytes: Optional[bytes] = None,
                      vehicle_crop_base64: Optional[str] = None,
                      proximity_status: Optional[str] = None,
                      is_high_priority: bool = False,
                      vehicle_findings: Optional[List[Union[VehicleFinding, Dict[str, Any]]]] = None,
                      fire_detected: bool = False,
                      fire_confidence: Optional[float] = None,
                      fire_bbox: Optional[List[int]] = None,
                      fire_crop_bytes: Optional[bytes] = None,
                      fire_crop_base64: Optional[str] = None,
                      activity: Optional[str] = None,
                      source: Optional[str] = None) -> Optional[Alert]:
        """
        Triggers or updates an alert with verified CCTV visual evidence.
        Same-type alerts are grouped and updated (deduplication).
        When person_findings are provided, all camera violations are grouped into ONE camera event.
        Different-type alerts (e.g. Restricted Zone vs Helmet vs Person-Vehicle Proximity vs Fire Hazard) coexist independently.
        """
        now = datetime.now()
        affected_ids = affected_person_ids or [f"Person #{i+1}" for i in range(person_count)]
        priority_score, priority_label = calculate_alert_priority(alert_type, severity, sif_potential)

        with self.lock:
            # Check if an alert of this SAME type is already active, OR if person_findings are provided, on this camera
            existing_alert = None
            for a in self._active_alerts.values():
                if a.status in ["WAITING_FOR_RESPONSE", "RESPONDING", "ESCALATED"]:
                    if "fire" in alert_type.lower():
                        if "fire" in a.type.lower() and (a.camera_id == camera or a.camera == camera):
                            existing_alert = a
                            break
                    elif alert_type == "Person–Vehicle Proximity":
                        if a.type == "Person–Vehicle Proximity" and (a.camera_id == camera or a.camera == camera):
                            if vehicle_id and a.vehicle_id and a.vehicle_id == vehicle_id:
                                existing_alert = a
                                break
                            elif not vehicle_id:
                                existing_alert = a
                                break
                    elif "fire" not in a.type.lower() and a.type != "Person–Vehicle Proximity":
                        if a.type == alert_type or (person_findings and (a.camera_id == camera or a.camera == camera)):
                            existing_alert = a
                            break

            if existing_alert:
                # Update existing alert without resetting timer
                existing_alert.person_count = max(1, person_count)
                existing_alert.affected_person_ids = affected_ids
                existing_alert.affected_persons = affected_ids
                if vehicle_id:
                    existing_alert.vehicle_id = vehicle_id
                if person_id:
                    existing_alert.person_id = person_id
                if vehicle_type:
                    existing_alert.vehicle_type = vehicle_type
                if proximity_status:
                    existing_alert.proximity_status = proximity_status
                if is_high_priority or alert_type == "Person–Vehicle Proximity":
                    existing_alert.is_high_priority = True
                if person_crop_bytes:
                    p_ev_id = f"ev-{existing_alert.id}-pers"
                    self.evidence_store[p_ev_id] = person_crop_bytes
                    existing_alert.person_crop_url = f"/api/evidence/{p_ev_id}"
                    existing_alert.person_crop_base64 = f"data:image/jpeg;base64,{base64.b64encode(person_crop_bytes).decode('utf-8')}"
                elif person_crop_base64:
                    try:
                        raw_b64 = person_crop_base64.split(",", 1)[1] if "," in person_crop_base64 else person_crop_base64
                        p_ev_id = f"ev-{existing_alert.id}-pers"
                        self.evidence_store[p_ev_id] = base64.b64decode(raw_b64)
                        existing_alert.person_crop_url = f"/api/evidence/{p_ev_id}"
                        existing_alert.person_crop_base64 = person_crop_base64
                    except Exception:
                        existing_alert.person_crop_base64 = person_crop_base64
                if vehicle_crop_bytes:
                    v_ev_id = f"ev-{existing_alert.id}-veh"
                    self.evidence_store[v_ev_id] = vehicle_crop_bytes
                    existing_alert.vehicle_crop_url = f"/api/evidence/{v_ev_id}"
                    existing_alert.vehicle_crop_base64 = f"data:image/jpeg;base64,{base64.b64encode(vehicle_crop_bytes).decode('utf-8')}"
                elif vehicle_crop_base64:
                    try:
                        raw_b64 = vehicle_crop_base64.split(",", 1)[1] if "," in vehicle_crop_base64 else vehicle_crop_base64
                        v_ev_id = f"ev-{existing_alert.id}-veh"
                        self.evidence_store[v_ev_id] = base64.b64decode(raw_b64)
                        existing_alert.vehicle_crop_url = f"/api/evidence/{v_ev_id}"
                        existing_alert.vehicle_crop_base64 = vehicle_crop_base64
                    except Exception:
                        existing_alert.vehicle_crop_base64 = vehicle_crop_base64
                if vehicle_findings:
                    existing_alert.vehicle_findings = self._process_vehicle_findings(vehicle_findings, existing_alert.id)
                if fire_detected or "fire" in alert_type.lower():
                    existing_alert.fire_detected = True
                    if fire_confidence is not None:
                        existing_alert.fire_confidence = fire_confidence
                    if fire_bbox is not None:
                        existing_alert.fire_bbox = fire_bbox
                    if fire_crop_bytes:
                        f_ev_id = f"ev-{existing_alert.id}-fire"
                        self.evidence_store[f_ev_id] = fire_crop_bytes
                        existing_alert.fire_crop_url = f"/api/evidence/{f_ev_id}"
                        existing_alert.fire_crop_base64 = f"data:image/jpeg;base64,{base64.b64encode(fire_crop_bytes).decode('utf-8')}"
                    elif fire_crop_base64:
                        existing_alert.fire_crop_base64 = fire_crop_base64
                if violations:
                    existing_alert.violations = list(dict.fromkeys(existing_alert.violations + violations))
                if ppe_status:
                    existing_alert.ppe_status.update(ppe_status)
                if person_findings:
                    existing_alert.person_findings = self._process_person_findings(person_findings, existing_alert.id)
                if evidence_frame:
                    ev_id = f"ev-{existing_alert.id}"
                    self.evidence_store[ev_id] = evidence_frame
                    existing_alert.evidence_url = f"/api/evidence/{ev_id}"
                    b64 = base64.b64encode(evidence_frame).decode('utf-8')
                    existing_alert.evidence_image = f"data:image/jpeg;base64,{b64}"
                    existing_alert.evidence_timestamp = now.isoformat()

                if title:
                    existing_alert.title = title
                elif alert_type == "Helmet/PPE Violation":
                    p_word = "PEOPLE" if person_count > 1 else "PERSON"
                    existing_alert.title = f"{person_count} {p_word} WITHOUT HELMETS"
                    existing_alert.short_summary = f"{person_count} unequipped workers detected in active area"
                    existing_alert.unsafe_condition = f"{person_count} workers present without hard hat in active zone"
                elif alert_type == "Restricted Zone Entry":
                    p_word = "PEOPLE" if person_count > 1 else "PERSON"
                    existing_alert.title = f"RESTRICTED ZONE ENTRY ({person_count} {p_word})"
                    existing_alert.short_summary = f"{person_count} {p_word} detected occupying restricted perimeter ({location})"
                elif "multi" in alert_type.lower():
                    v_str = ', '.join(existing_alert.violations) if existing_alert.violations else "Multiple Violations"
                    existing_alert.title = title or f"MULTI-HAZARD SAFETY VIOLATION ({', '.join(affected_ids)})"
                    existing_alert.short_summary = f"Worker detected with concurrent safety violations: {v_str}"
                elif "fall" in alert_type.lower():
                    existing_alert.title = title or "FALL DETECTED — WORKER DOWN"
                    existing_alert.short_summary = "Worker horizontal / fallen posture confirmed across multiple video frames"
                elif "vest" in alert_type.lower():
                    p_word = "PEOPLE" if person_count > 1 else "PERSON"
                    existing_alert.title = f"{person_count} {p_word} WITHOUT SAFETY VEST"
                    existing_alert.short_summary = f"{person_count} unequipped workers detected without high-visibility vest"

                if short_summary:
                    existing_alert.short_summary = short_summary

                self.current_safety_state = "VIOLATION"
                self.notify_clients()
                return existing_alert

            # No existing alert of this type: create new independent alert
            deadline = now + timedelta(seconds=response_sec)
            al_low = alert_type.lower()
            alert_prefix = "FIRE" if "fire" in al_low else ("PROX" if ("proximity" in al_low or "vehicle" in al_low) else ("FALL" if "fall" in al_low else ("MULTI" if "multi" in al_low else ("ZONE" if "zone" in al_low else ("PASS" if "passport" in al_low else "PPE")))))
            ms = int(now.microsecond / 1000)
            alert_id = f"ALT-{alert_prefix}-{now.strftime('%Y%m%d-%H%M%S')}-{ms:03d}"
            suffix = 1
            base_id = alert_id
            while alert_id in self._active_alerts:
                alert_id = f"{base_id}-{suffix}"
                suffix += 1

            default_notes = "Automated SIF Prevention Alert"
            if "fire" in al_low:
                title = title or "FIRE DETECTED — CONFIRMED"
                short_summary = short_summary or "Active fire detected in monitored area"
                default_notes = "Automated SIF Alert: Visual fire confirmation in CCTV feed. Immediate response required."
                hazard = hazard or "Active Fire Hazard / Thermal Ignition"
                unsafe_condition = unsafe_condition or "Confirmed open fire in monitored camera perimeter"
            elif "proximity" in al_low or "vehicle" in al_low:
                title = title or "HIGH PRIORITY — PERSON–VEHICLE PROXIMITY"
                short_summary = short_summary or "Worker detected in vehicle proximity zone"
                default_notes = "Automated SIF Prevention Alert: High-priority proximity event detected between personnel and mobile vehicle."
                hazard = hazard or "Heavy Equipment / Vehicle Proximity & Struck-By Hazard"
                unsafe_condition = unsafe_condition or "Worker present in active proximity perimeter of mobile equipment"
            elif "fall" in al_low:
                title = title or "FALL DETECTED — WORKER DOWN"
                short_summary = short_summary or "Worker horizontal / fallen posture confirmed across multiple video frames"
                default_notes = "Automated SIF Alert: Critical fall event requiring immediate supervisor and first-aid response."
                hazard = hazard or "Slip, Trip or Fall from Same Level / Height"
                unsafe_condition = unsafe_condition or "Worker down in active zone"
            elif "multi" in al_low:
                v_str = ', '.join(violations) if violations else "Multiple Violations"
                title = title or f"MULTI-HAZARD SAFETY VIOLATION ({', '.join(affected_ids)})"
                short_summary = short_summary or f"Worker detected with concurrent safety violations: {v_str}"
                default_notes = f"Automated SIF Prevention Alert: Multiple simultaneous barrier failures ({v_str})."
                hazard = hazard or "Multiple Concurrent Safety Barrier Failures"
                unsafe_condition = unsafe_condition or f"Concurrent safety violations: {v_str}"
            elif "vest" in al_low:
                p_word = "PEOPLE" if person_count > 1 else "PERSON"
                title = title or f"{person_count} {p_word} WITHOUT SAFETY VEST"
                short_summary = short_summary or f"{person_count} unequipped workers detected without high-visibility vest"
                hazard = hazard or "Lack of required PPE (High-Visibility Safety Vest)"
                unsafe_condition = unsafe_condition or f"{person_count} workers present without safety vest in active zone"
            elif "harness" in al_low or "height" in al_low:
                title = title or "WORKING AT HEIGHT VIOLATION (NO HARNESS)"
                short_summary = short_summary or "Worker detected in working-at-height zone without required fall arrest harness"
                hazard = hazard or "Working at Height without Fall Protection / Harness"
                unsafe_condition = unsafe_condition or "Worker present in height zone without verified safety harness"
            elif alert_type == "Restricted Zone Entry":
                p_word = "PEOPLE" if person_count > 1 else "PERSON"
                title = title or f"RESTRICTED ZONE ENTRY"
                short_summary = short_summary or f"{person_count} {p_word} detected occupying restricted perimeter ({location})"
                default_notes = f"Automated SIF Observation: {person_count} person detected inside an HSE-defined restricted area."
                hazard = hazard or "Unauthorized / Unsafe Restricted Zone Entry"
                unsafe_condition = unsafe_condition or f"Person detected occupying configured restricted zone ({location})"
            elif alert_type == "SAFETY PASSPORT BREACH":
                title = title or "SAFETY PASSPORT PAUSED: Restricted Zone Breach"
                short_summary = short_summary or f"Restricted Zone Breach — Lifting exclusion zone entered"
                default_notes = "Automated SIF Prevention Alert: High-risk passport paused due to critical barrier breach."
                hazard = hazard or "Line of Fire / Exclusion Zone Intrusion during High-Risk Activity"
                unsafe_condition = unsafe_condition or "Person detected occupying linked exclusion zone during active task"
            else:
                p_word = "PEOPLE" if person_count > 1 else "PERSON"
                title = title or f"{person_count} {p_word} WITHOUT HELMETS"
                short_summary = short_summary or f"{person_count} unequipped workers detected without head protection"
                hazard = hazard or "Lack of required PPE (Head Protection)"
                unsafe_condition = unsafe_condition or f"{person_count} workers present without hard hat in active zone"

            # Generate visual evidence if not provided
            if not evidence_frame:
                cur_z = self.active_zone
                evidence_frame = generate_visual_evidence(
                    alert_type=alert_type,
                    camera_id=camera,
                    location=location,
                    person_count=person_count,
                    unhelmeted_ids=affected_ids,
                    zone_name=cur_z.name if cur_z else None,
                    zone_category=cur_z.zone_category if cur_z else "PERMANENT",
                    zone_polygon=cur_z.polygon if cur_z else None
                )

            ev_id = f"ev-{alert_id}"
            self.evidence_store[ev_id] = evidence_frame
            ev_url = f"/api/evidence/{ev_id}"
            b64_img = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
            ev_time = now.isoformat()

            inc_id = self.get_next_incident_id()

            init_timeline = [
                {
                    "timestamp": now.isoformat(),
                    "event_type": "CCTV_DETECTION",
                    "title": f"CCTV Alert Detected: {title or alert_type}",
                    "actor": f"AI CCTV ({camera})",
                    "details": f"Visual safety event detected at {location} on camera {camera}."
                }
            ]

            new_person_findings = self._process_person_findings(person_findings, alert_id)

            # Process person crop if passed directly
            p_ev_url = None
            p_ev_b64 = None
            if person_crop_bytes:
                p_ev_id = f"ev-{alert_id}-pers"
                self.evidence_store[p_ev_id] = person_crop_bytes
                p_ev_url = f"/api/evidence/{p_ev_id}"
                p_ev_b64 = f"data:image/jpeg;base64,{base64.b64encode(person_crop_bytes).decode('utf-8')}"
            elif person_crop_base64:
                try:
                    raw_b64 = person_crop_base64.split(",", 1)[1] if "," in person_crop_base64 else person_crop_base64
                    p_ev_id = f"ev-{alert_id}-pers"
                    self.evidence_store[p_ev_id] = base64.b64decode(raw_b64)
                    p_ev_url = f"/api/evidence/{p_ev_id}"
                    p_ev_b64 = person_crop_base64
                except Exception:
                    p_ev_b64 = person_crop_base64

            # Process vehicle crop if passed directly
            v_ev_url = None
            v_ev_b64 = None
            if vehicle_crop_bytes:
                v_ev_id = f"ev-{alert_id}-veh"
                self.evidence_store[v_ev_id] = vehicle_crop_bytes
                v_ev_url = f"/api/evidence/{v_ev_id}"
                v_ev_b64 = f"data:image/jpeg;base64,{base64.b64encode(vehicle_crop_bytes).decode('utf-8')}"
            elif vehicle_crop_base64:
                try:
                    raw_b64 = vehicle_crop_base64.split(",", 1)[1] if "," in vehicle_crop_base64 else vehicle_crop_base64
                    v_ev_id = f"ev-{alert_id}-veh"
                    self.evidence_store[v_ev_id] = base64.b64decode(raw_b64)
                    v_ev_url = f"/api/evidence/{v_ev_id}"
                    v_ev_b64 = vehicle_crop_base64
                except Exception:
                    v_ev_b64 = vehicle_crop_base64

            new_vehicle_findings = self._process_vehicle_findings(vehicle_findings, alert_id)
            if not v_ev_url and new_vehicle_findings and new_vehicle_findings[0].evidence_crop_url:
                v_ev_url = new_vehicle_findings[0].evidence_crop_url
            if not v_ev_b64 and new_vehicle_findings and new_vehicle_findings[0].evidence_crop_base64:
                v_ev_b64 = new_vehicle_findings[0].evidence_crop_base64

            # Process fire crop if passed directly
            f_ev_url = None
            f_ev_b64 = None
            if fire_crop_bytes:
                f_ev_id = f"ev-{alert_id}-fire"
                self.evidence_store[f_ev_id] = fire_crop_bytes
                f_ev_url = f"/api/evidence/{f_ev_id}"
                f_ev_b64 = f"data:image/jpeg;base64,{base64.b64encode(fire_crop_bytes).decode('utf-8')}"
            elif fire_crop_base64:
                try:
                    raw_b64 = fire_crop_base64.split(",", 1)[1] if "," in fire_crop_base64 else fire_crop_base64
                    f_ev_id = f"ev-{alert_id}-fire"
                    self.evidence_store[f_ev_id] = base64.b64decode(raw_b64)
                    f_ev_url = f"/api/evidence/{f_ev_id}"
                    f_ev_b64 = fire_crop_base64
                except Exception:
                    f_ev_b64 = fire_crop_base64

            cur_p = self.active_passport
            cur_z = self.active_zone
            sif_rec = get_sif_action_recommendation(
                alert_type=alert_type,
                location=location,
                hazard=hazard,
                unsafe_condition=unsafe_condition,
                person_count=person_count,
                task_type=activity or (cur_p.task_type if cur_p else None),
                zone_name=cur_z.name if cur_z else None
            )

            new_alert = Alert(
                id=alert_id,
                event_id=f"EVT-{now.strftime('%Y%m%d')}-{self._incident_counter:04d}",
                incident_id=inc_id,
                type=alert_type,
                title=title,
                short_summary=short_summary,
                location=location,
                camera=camera,
                camera_id=camera,
                source=source or f"AI CCTV (Camera {camera})",
                severity=severity,
                priority_score=priority_score,
                priority_label=priority_label,
                status="WAITING_FOR_RESPONSE",
                stage="RESPONSE",
                person_count=max(1, person_count),
                affected_person_ids=affected_ids,
                affected_persons=affected_ids,
                assigned_to="FIELD SUPERVISOR",
                created_at=now.isoformat(),
                response_deadline=deadline.isoformat(),
                action_deadline=None,
                response_duration_sec=response_sec,
                action_duration_sec=action_sec,
                notes=notes or default_notes,
                # Structured SIF intelligence & causal fields (Phases 2, 3, 5, 8)
                activity=sif_rec["activity"],
                hazard=hazard or sif_rec.get("critical_barrier"),
                unsafe_condition=unsafe_condition,
                sif_potential="SIF Potential", # Strictly 'SIF Potential' terminology
                sif_level=sif_rec["sif_level"],
                sif_reason=sif_rec["sif_reason"],
                sif_why=sif_rec["sif_why"],
                exposure=sif_rec["exposure"],
                critical_barrier=sif_rec["critical_barrier"],
                barrier_condition=sif_rec["barrier_condition"],
                potential_consequence=sif_rec["potential_consequence"],
                life_saving_rule=sif_rec["life_saving_rule"],
                immediate_action=sif_rec["immediate_action"],
                consequence_if_not_addressed=sif_rec["consequence_if_not_addressed"],
                # Corrective Action State Machine (Phase 4): ASSIGNED -> IN_PROGRESS -> COMPLETED
                action_status="ASSIGNED",
                verification_status="PENDING",
                verification_type=sif_rec["verification_type"],
                evidence_url=ev_url,
                evidence_image=b64_img,
                evidence_timestamp=ev_time,
                incident_timeline=init_timeline,
                violations=violations or [],
                ppe_status=ppe_status or {},
                person_findings=new_person_findings,
                person_id=person_id or (affected_ids[0] if affected_ids else None),
                person_crop_url=p_ev_url,
                person_crop_base64=p_ev_b64,
                vehicle_id=vehicle_id,
                vehicle_type=vehicle_type,
                vehicle_crop_url=v_ev_url,
                vehicle_crop_base64=v_ev_b64,
                proximity_status=proximity_status or ("Proximity Confirmed" if alert_type == "Person–Vehicle Proximity" else None),
                is_high_priority=bool(is_high_priority or alert_type == "Person–Vehicle Proximity"),
                vehicle_findings=new_vehicle_findings,
                fire_detected=bool(fire_detected or "fire" in alert_type.lower()),
                fire_confidence=fire_confidence,
                fire_bbox=fire_bbox,
                fire_crop_url=f_ev_url,
                fire_crop_base64=f_ev_b64
            )

            # Record machine-generated safety observation in Safety Memory (Sections 3A & 16)
            try:
                from safety_memory import safety_memory, SafetyEvent, AssertionStatus
                mach_obs = {
                    "source": "CCTV",
                    "camera_id": camera,
                    "timestamp": now.strftime("%H:%M:%S"),
                    "location": location,
                    "observed_event": f"Person entered defined restricted zone ({location})",
                    "activity": sif_rec["activity"],
                    "observable_exposure": sif_rec["exposure"],
                    "observable_barrier": sif_rec["critical_barrier"],
                    "barrier_state": (sif_rec.get("barrier_condition") or "VIOLATED").upper(),
                    "evidence_url": ev_url,
                    "pipeline_stage": "OBSERVATION_SENT_TO_SIF_INTELLIGENCE"
                }
                new_alert.machine_observation = mach_obs
                new_alert.evidence_source_type = "OBSERVED"
                new_alert.corroboration_status = "CCTV_ONLY"
                new_alert.lifecycle_state = "ACTION_REQUIRED"

                se = SafetyEvent(
                    event_id=new_alert.event_id or f"EVT-{now.strftime('%Y%m%d')}-{self._incident_counter:04d}",
                    incident_id=inc_id,
                    source="CCTV",
                    evidence_source_type="OBSERVED",
                    timestamp=now.isoformat(),
                    camera_id=camera,
                    location=location,
                    activity=sif_rec["activity"],
                    hazard=hazard or sif_rec.get("critical_barrier"),
                    energy_source="Mechanical / Gravitational Potential Energy",
                    exposure=sif_rec["exposure"],
                    exposure_assertion=AssertionStatus.OBSERVED_FACT,
                    critical_barrier=sif_rec["critical_barrier"],
                    barrier_state=(sif_rec.get("barrier_condition") or "VIOLATED").upper(),
                    potential_consequence=sif_rec["potential_consequence"],
                    consequence_type="POTENTIAL",
                    sif_potential="HIGH" if sif_rec.get("sif_level") in ["HIGH", "CRITICAL"] else "MEDIUM",
                    life_saving_rule=sif_rec.get("life_saving_rule"),
                    assertion_status=AssertionStatus.OBSERVED_FACT,
                    temporal_status="DURING_EVENT",
                    evidence_url=ev_url,
                    raw_narrative=f"CCTV Safety Observation: {person_count} person(s) entered restricted zone ({location}) during {sif_rec['activity']}.",
                    underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
                )
                rec_res = safety_memory.record_safety_event(se)
                new_alert.recurrence_classification = rec_res["classification"]
                if rec_res.get("pattern"):
                    new_alert.recurring_pattern_title = rec_res["pattern"].title
                    new_alert.independent_occurrences_count = rec_res["pattern"].independent_occurrences_count
            except Exception as e:
                print(f"[State] Safety Memory record notice: {e}")

            # Also register into canonical Unified Event Store (Phase 1 & 19)
            try:
                from unified_event_store import unified_event_store, SafetyEvent as CanonicalSafetyEvent
                canonical_event = CanonicalSafetyEvent(
                    event_id=new_alert.event_id or f"EVT-CCTV-{now.strftime('%Y%m%d-%H%M%S')}",
                    source="CCTV",
                    timestamp=now.isoformat(),
                    location=location,
                    activity=sif_rec["activity"],
                    narrative=f"Machine-Generated Safety Observation: {person_count} person(s) detected inside restricted {location} on camera {camera}.",
                    hazard=hazard or sif_rec.get("critical_barrier"),
                    exposure=sif_rec["exposure"],
                    critical_barrier=sif_rec["critical_barrier"],
                    barrier_condition=(sif_rec.get("barrier_condition") or "VIOLATED").upper(),
                    consequence=sif_rec["potential_consequence"],
                    sif_potential="HIGH" if sif_rec.get("sif_level") in ["HIGH", "CRITICAL"] else "MEDIUM",
                    lsr=sif_rec.get("life_saving_rule"),
                    assertion_status="ASSERTED",
                    temporal_status="CURRENT",
                    evidence_sources=["CCTV"],
                    recurrence_classification=new_alert.recurrence_classification or "INDEPENDENT_RECURRENCE",
                    corroboration_status="CCTV_ONLY",
                    lifecycle_state="ACTION_REQUIRED",
                    machine_observation=True,
                    camera_id=camera
                )
                unified_event_store.add_event(canonical_event)
            except Exception as ue_err:
                print(f"[State] Unified event store record notice: {ue_err}")

            self._active_alerts[alert_id] = new_alert
            self._last_resolved_alert = None
            self.current_safety_state = "VIOLATION"

        self.notify_clients()
        return new_alert

    def respond_to_alert(self, supervisor_id: str = "SUP-01", notes: Optional[str] = None, alert_id: Optional[str] = None) -> Optional[Alert]:
        """
        Supervisor acknowledges response (Stage 1 -> Stage 2).
        If alert_id is not specified, acknowledges the highest-priority WAITING_FOR_RESPONSE alert.
        Updates action_status to IN_PROGRESS.
        """
        with self.lock:
            target = None
            if alert_id:
                target = self._active_alerts.get(alert_id)
            else:
                # Find highest priority alert waiting for response
                sorted_alerts = sort_alerts_by_priority(list(self._active_alerts.values()))
                for a in sorted_alerts:
                    if a.status == "WAITING_FOR_RESPONSE":
                        target = a
                        break

            if not target:
                return None
            if target.status != "WAITING_FOR_RESPONSE":
                return target

            now = datetime.now()
            action_deadline = now + timedelta(seconds=target.action_duration_sec)
            target.status = "RESPONDING"
            target.stage = "ACTION"
            target.action_status = "IN_PROGRESS"
            target.responded_at = now.isoformat()
            target.action_deadline = action_deadline.isoformat()
            target.lifecycle_state = "ACTION_IN_PROGRESS"
            target.resolved_by = supervisor_id
            if notes:
                target.notes = notes

            target.incident_timeline.append({
                "timestamp": now.isoformat(),
                "event_type": "SUPERVISOR_RESPONDED",
                "title": f"Response Acknowledged by {supervisor_id}",
                "actor": supervisor_id,
                "details": f"Supervisor acknowledged incident. Action SLA timer initialized ({target.action_duration_sec}s)."
            })

        self.notify_clients()
        return target

    def mark_action_taken(self, alert_id: Optional[str] = None, supervisor_id: str = "SUP-01", notes: Optional[str] = None, action_taken: Optional[str] = None) -> Optional[Alert]:
        """
        Supervisor marks corrective action completed (Phase 4).
        Sets action_status='COMPLETED' and verification_status='AWAITING_VERIFICATION'.
        Does NOT equate manager completion with verified fixed.
        """
        with self.lock:
            target = None
            if alert_id:
                target = self._active_alerts.get(alert_id)
            else:
                sorted_alerts = sort_alerts_by_priority(list(self._active_alerts.values()))
                for a in sorted_alerts:
                    if a.action_status in ["ASSIGNED", "IN_PROGRESS"]:
                        target = a
                        break

            if not target:
                return None

            now = datetime.now()
            target.action_status = "COMPLETED"
            target.verification_status = "AWAITING_VERIFICATION"
            target.lifecycle_state = "AWAITING_VERIFICATION"
            target.status = "AWAITING_VERIFICATION"
            target.action_taken_at = now.isoformat()
            target.action_taken_by = supervisor_id
            target.action_taken_notes = notes or action_taken or "Corrective action executed on-site"
            target.stage = "ACTION"

            target.incident_timeline.append({
                "timestamp": now.isoformat(),
                "event_type": "ACTION_COMPLETED",
                "title": f"Corrective Action Completed by {supervisor_id}",
                "actor": supervisor_id,
                "details": target.action_taken_notes
            })

            if getattr(target, "pattern_id", None) and target.pattern_id in self.pattern_actions:
                self.pattern_actions[target.pattern_id]["operational_status"] = "AWAITING_VERIFICATION"
                self.pattern_actions[target.pattern_id]["action_completed_at"] = now.isoformat()
                self.pattern_actions[target.pattern_id]["action_taken_by"] = supervisor_id
                self.pattern_actions[target.pattern_id]["action_notes"] = target.action_taken_notes

        self.notify_clients()
        return target

    def verify_alert(self, alert_id: Optional[str] = None, supervisor_id: str = "SUP-01", decision: str = "VERIFIED", verification_method: str = "CCTV_VERIFIED", notes: Optional[str] = None) -> Optional[Alert]:
        """
        Executes formal safety verification step (Phase 4).
        Separates physical/objective verification from action completion.
        - If decision == "VERIFIED": sets verification_status="VERIFIED", status="RESOLVED", moves to history.
        - If decision == "FAILED": sets verification_status="FAILED", action_status="IN_PROGRESS" (reopen required).
        - If decision == "HSE_REVIEW_REQUIRED": sets verification_status="HSE_REVIEW_REQUIRED", assigned_to="HSE CONTROL DESK".
        """
        with self.lock:
            target = None
            if alert_id:
                target = self._active_alerts.get(alert_id)
                if not target:
                    # Check history if already resolved
                    for h in self.history:
                        if h.id == alert_id:
                            target = h
                            break
            else:
                sorted_alerts = sort_alerts_by_priority(list(self._active_alerts.values()))
                for a in sorted_alerts:
                    if a.verification_status == "AWAITING_VERIFICATION" or a.action_status == "COMPLETED":
                        target = a
                        break
                if not target and sorted_alerts:
                    target = sorted_alerts[0]

            if not target:
                return None

            now = datetime.now()
            clean_decision = str(decision).upper()

            if clean_decision == "VERIFIED":
                target.action_status = "COMPLETED"
                target.verification_status = "VERIFIED"
                target.lifecycle_state = "VERIFIED"
                target.verified_at = now.isoformat()
                target.verified_by = supervisor_id
                target.verification_notes = notes or f"Barrier restoration verified ({verification_method})"
                target.status = "RESOLVED"
                target.stage = "RESOLVED"
                target.resolved_at = now.isoformat()
                target.resolved_by = supervisor_id
                if target.escalated_at:
                    target.was_escalated = True

                target.incident_timeline.append({
                    "timestamp": now.isoformat(),
                    "event_type": "VERIFIED_AND_RESOLVED",
                    "title": f"Safety Verification Passed ({verification_method})",
                    "actor": supervisor_id,
                    "details": target.verification_notes
                })

                if target.id in self._active_alerts:
                    del self._active_alerts[target.id]
                self._last_resolved_alert = target
                self.history.append(target)

                # Reactivate passport if breach alert
                p = self.active_passport
                if p and (target.type == "SAFETY PASSPORT BREACH" or p.active_breach_alert_id == target.id):
                    if p.status in ["PAUSED", "AWAITING_RESTORATION"]:
                        p.status = "ACTIVE"
                        p.reactivated_at = now.isoformat()
                        p.breach_reason = None
                        p.events.append(PassportEvent(
                            id=f"evt-{int(now.timestamp()*1000)}",
                            timestamp=now.isoformat(),
                            event_type="reactivated",
                            actor=supervisor_id,
                            description="Safety verification passed. Safety Passport REACTIVATED."
                        ))
                        p.active_breach_alert_id = None

                if not self._active_alerts:
                    has_helmet_violation = (self.person_detected and not self.helmet_detected)
                    if not has_helmet_violation and not self.zone_violation:
                        self.current_safety_state = "SAFE" if self.person_detected else "MONITORING"

            elif clean_decision == "FAILED":
                target.verification_status = "FAILED"
                target.action_status = "IN_PROGRESS"
                target.status = "WAITING_FOR_RESPONSE"
                target.stage = "RESPONSE"
                target.lifecycle_state = "REOPENED"
                target.verification_notes = notes or "Verification failed: Safety barrier or PPE remains compromised. Reopen required."
                target.incident_timeline.append({
                    "timestamp": now.isoformat(),
                    "event_type": "VERIFICATION_FAILED",
                    "title": "Safety Verification Failed — Reopen Required",
                    "actor": supervisor_id,
                    "details": target.verification_notes
                })
                # Reinsert into active alerts
                self._active_alerts[target.id] = target
                self.history = [h for h in self.history if h.id != target.id]

            elif clean_decision == "HSE_REVIEW_REQUIRED":
                target.verification_status = "HSE_REVIEW_REQUIRED"
                target.assigned_to = "HSE CONTROL DESK"
                target.verification_notes = notes or "Action completed on-site; formal HSE review and documentation audit required."
                target.incident_timeline.append({
                    "timestamp": now.isoformat(),
                    "event_type": "HSE_REVIEW_REQUIRED",
                    "title": "HSE Verification Review Required",
                    "actor": supervisor_id,
                    "details": target.verification_notes
                })

        self.notify_clients()
        return target

    def verify_cctv_condition(self, alert_id: Optional[str] = None, supervisor_id: str = "SUP-01", simulate_rebreach: bool = False) -> Dict[str, Any]:
        """
        Executes CCTV-based verification of observable site conditions ("Completion is not proof").
        - If simulate_rebreach is True or zone_violation is currently active:
          Returns VERIFICATION_FAILED — RE-BREACH DETECTED, and reopens the alert!
        - If zone is clear and no violation:
          Returns VERIFIED — OBSERVABLE CONDITION RESTORED, and resolves the alert.
        """
        with self.lock:
            target = None
            if alert_id:
                target = self._active_alerts.get(alert_id)
                if not target:
                    for a in self._active_alerts.values():
                        if getattr(a, "pattern_id", None) == alert_id:
                            target = a
                            break
            else:
                for a in self._active_alerts.values():
                    if a.verification_status == "AWAITING_VERIFICATION" or a.action_status == "COMPLETED":
                        target = a
                        break

            if not target and alert_id in self.pattern_actions:
                # Direct pattern verification without active alert object
                pat_id = alert_id
                is_breached = simulate_rebreach or (self.zone_violation and self.persons_in_zone > 0)
                now = datetime.now()
                if is_breached:
                    self.pattern_actions[pat_id]["operational_status"] = "REOPENED"
                    self.pattern_actions[pat_id]["verification_status"] = "FAILED"
                    self.pattern_actions[pat_id]["last_rebreach_at"] = now.isoformat()
                    try:
                        try:
                            from backend.database import db
                        except ImportError:
                            from database import db
                        db.save_verification(
                            verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
                            event_id=self.pattern_actions[pat_id].get("action_id"),
                            source="CCTV",
                            status="FAILED",
                            details={
                                "type": "RE-BREACH DETECTED",
                                "message": "Personnel observed inside restricted zone during verification window",
                                "pattern_id": pat_id,
                                "supervisor": supervisor_id
                            }
                        )
                    except Exception:
                        pass
                    try:
                        from models_canonical import SafetyEvent, SIFStatus
                        try:
                            from backend.database import db
                        except ImportError:
                            from database import db
                        new_ev_id = f"EVT-CCTV-REBREACH-{uuid.uuid4().hex[:6].upper()}"
                        loc = self.pattern_actions[pat_id].get("location") or "Lifting Zone 03"
                        rebreach_ev = SafetyEvent(
                            event_id=new_ev_id,
                            source="CCTV",
                            timestamp=now.isoformat(),
                            location=loc,
                            activity="Mechanical Lifting",
                            energy="Suspended Load",
                            exposure="Person inside restricted perimeter during active operations",
                            barrier=["EXCLUSION_ZONE"],
                            barrier_state=["BYPASSED"],
                            consequence="Struck-by / line-of-fire from suspended/moving load",
                            sif_status=SIFStatus.SIF_POTENTIAL,
                            lsr=["Line of Fire"],
                            pattern_id=pat_id,
                            machine_observation=True,
                            narrative=f"CCTV automated verification detected personnel re-entry into {loc} following corrective action sign-off."
                        )
                        db.save_event(rebreach_ev)
                        try:
                            from backend.nlp_engine.semantic_memory import semantic_memory
                            semantic_memory.add_event(rebreach_ev)
                        except Exception:
                            pass
                        db.add_pattern_member(pat_id, new_ev_id, "INDEPENDENT_RECURRENCE", 0.95, "CCTV Re-breach during verification window")
                        cur_pat = db.get_pattern(pat_id)
                        if cur_pat:
                            new_cnt = (cur_pat.occurrence_count or 1) + 1
                            with db.get_connection() as conn:
                                conn.execute("UPDATE patterns SET occurrence_count = ?, updated_at = ? WHERE pattern_id = ?",
                                             (new_cnt, now.isoformat(), pat_id))
                    except Exception:
                        pass

                    self.notify_clients()
                    return {
                        "verified": False,
                        "decision": "FAILED",
                        "status": "VERIFICATION_FAILED_REBREACH",
                        "verification_notes": "VERIFICATION FAILED — RE-BREACH DETECTED. Personnel re-entered restricted zone.",
                        "message": "✕ VERIFICATION FAILED — RE-BREACH DETECTED. Action reopened.",
                        "pattern_id": pat_id
                    }
                else:
                    self.pattern_actions[pat_id]["operational_status"] = "VERIFIED"
                    self.pattern_actions[pat_id]["verification_status"] = "VERIFIED"
                    self.pattern_actions[pat_id]["verified_at"] = now.isoformat()
                    try:
                        try:
                            from backend.database import db
                        except ImportError:
                            from database import db
                        db.save_verification(
                            verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
                            event_id=self.pattern_actions[pat_id].get("action_id"),
                            source="CCTV",
                            status="VERIFIED",
                            details={
                                "type": "OBSERVABLE CONDITION RESTORED",
                                "message": "Restricted zone verified clear by AI vision stream",
                                "pattern_id": pat_id,
                                "supervisor": supervisor_id
                            }
                        )
                    except Exception:
                        pass
                    self.notify_clients()
                    return {
                        "verified": True,
                        "decision": "VERIFIED",
                        "status": "VERIFIED",
                        "verification_notes": "VERIFIED — OBSERVABLE CONDITION RESTORED. Area clear.",
                        "message": "✓ VERIFIED — OBSERVABLE CONDITION RESTORED.",
                        "pattern_id": pat_id
                    }

            if not target:
                for h in self.history:
                    if h.id == alert_id or getattr(h, "pattern_id", None) == alert_id:
                        return {
                            "verified": True,
                            "decision": "VERIFIED",
                            "status": "VERIFIED",
                            "alert": h,
                            "verification_notes": h.verification_notes or "Already verified",
                            "message": "Alert is already verified and resolved"
                        }
                return {
                    "verified": False,
                    "decision": "NONE",
                    "status": "NO_ALERT_FOUND",
                    "message": "No alert awaiting verification"
                }

            is_breached = simulate_rebreach or (self.zone_violation and self.persons_in_zone > 0)
            now = datetime.now()

            if is_breached:
                target.verification_status = "FAILED"
                target.action_status = "IN_PROGRESS"
                target.status = "WAITING_FOR_RESPONSE"
                target.stage = "RESPONSE"
                target.lifecycle_state = "REOPENED"
                target.verification_notes = "VERIFICATION FAILED — RE-BREACH DETECTED. Personnel re-entered restricted zone. Corrective action reopened."
                target.incident_timeline.append({
                    "timestamp": now.isoformat(),
                    "event_type": "VERIFICATION_FAILED_REBREACH",
                    "title": "CCTV Verification Failed (Re-Breach Detected)",
                    "actor": f"AI CCTV ({target.camera or 'C-01'})",
                    "details": target.verification_notes
                })
                # Reinsert into active alerts
                self._active_alerts[target.id] = target
                self.history = [h for h in self.history if h.id != target.id]

                if getattr(target, "pattern_id", None):
                    pat_id = target.pattern_id
                    if pat_id in self.pattern_actions:
                        self.pattern_actions[pat_id]["operational_status"] = "REOPENED"
                        self.pattern_actions[pat_id]["verification_status"] = "FAILED"
                        self.pattern_actions[pat_id]["last_rebreach_at"] = now.isoformat()
                    try:
                        try:
                            from backend.database import db
                        except ImportError:
                            from database import db
                        db.save_verification(
                            verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
                            event_id=target.event_id,
                            source="CCTV",
                            status="FAILED",
                            details={
                                "type": "RE-BREACH DETECTED",
                                "message": "Personnel observed inside restricted zone during verification window",
                                "pattern_id": pat_id,
                                "supervisor": supervisor_id
                            }
                        )
                    except Exception:
                        pass
                    try:
                        from models_canonical import SafetyEvent, SIFStatus
                        try:
                            from backend.database import db
                        except ImportError:
                            from database import db
                        new_ev_id = f"EVT-CCTV-REBREACH-{uuid.uuid4().hex[:6].upper()}"
                        loc = target.location or "Lifting Zone 03"
                        rebreach_ev = SafetyEvent(
                            event_id=new_ev_id,
                            source="CCTV",
                            timestamp=now.isoformat(),
                            location=loc,
                            activity=target.activity or "Mechanical Lifting",
                            energy=target.hazard or "Suspended Load",
                            exposure="Person inside restricted perimeter during active operations",
                            barrier=["EXCLUSION_ZONE"],
                            barrier_state=["BYPASSED"],
                            consequence="Struck-by / line-of-fire from suspended/moving load",
                            sif_status=SIFStatus.SIF_POTENTIAL,
                            lsr=[target.life_saving_rule or "Line of Fire"],
                            pattern_id=pat_id,
                            machine_observation=True,
                            narrative=f"CCTV automated verification detected personnel re-entry into {loc} following corrective action sign-off."
                        )
                        db.save_event(rebreach_ev)
                        try:
                            from backend.nlp_engine.semantic_memory import semantic_memory
                            semantic_memory.add_event(rebreach_ev)
                        except Exception:
                            pass
                        db.add_pattern_member(pat_id, new_ev_id, "INDEPENDENT_RECURRENCE", 0.95, "CCTV Re-breach during verification window")
                        cur_pat = db.get_pattern(pat_id)
                        if cur_pat:
                            new_cnt = (cur_pat.occurrence_count or 1) + 1
                            with db.get_connection() as conn:
                                conn.execute("UPDATE patterns SET occurrence_count = ?, updated_at = ? WHERE pattern_id = ?",
                                             (new_cnt, now.isoformat(), pat_id))
                    except Exception as e:
                        print("EXCEPTION IN REBREACH:", e)

                self.notify_clients()
                return {
                    "verified": False,
                    "decision": "FAILED",
                    "status": "VERIFICATION_FAILED_REBREACH",
                    "verification_notes": target.verification_notes,
                    "message": "✕ VERIFICATION FAILED — RE-BREACH DETECTED. Action reopened.",
                    "alert": target
                }
            else:
                target.verification_status = "VERIFIED"
                target.action_status = "COMPLETED"
                target.status = "RESOLVED"
                target.stage = "RESOLVED"
                target.lifecycle_state = "VERIFIED"
                target.resolved_at = now.isoformat()
                target.verified_at = now.isoformat()
                target.verified_by = f"AI CCTV ({target.camera or 'C-01'}) + {supervisor_id}"
                target.verification_notes = "✓ CCTV VERIFIED: Camera confirmed restricted zone is clear of personnel. Observable condition restored."
                target.incident_timeline.append({
                    "timestamp": now.isoformat(),
                    "event_type": "CCTV_VERIFIED_RESTORED",
                    "title": "CCTV Verification Passed (Observable Condition Restored)",
                    "actor": f"AI CCTV ({target.camera or 'C-01'})",
                    "details": target.verification_notes
                })
                if target.id in self._active_alerts:
                    del self._active_alerts[target.id]
                self._last_resolved_alert = target
                self.history.append(target)

                if getattr(target, "pattern_id", None):
                    pat_id = target.pattern_id
                    if pat_id in self.pattern_actions:
                        self.pattern_actions[pat_id]["operational_status"] = "VERIFIED"
                        self.pattern_actions[pat_id]["verification_status"] = "VERIFIED"
                        self.pattern_actions[pat_id]["verified_at"] = now.isoformat()
                        self.pattern_actions[pat_id]["verified_by"] = supervisor_id
                    try:
                        try:
                            from backend.database import db
                        except ImportError:
                            from database import db
                        db.save_verification(
                            verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
                            event_id=target.event_id,
                            source="CCTV",
                            status="VERIFIED",
                            details={
                                "type": "OBSERVABLE CONDITION RESTORED",
                                "message": "Camera confirmed restricted zone is clear of personnel.",
                                "pattern_id": pat_id,
                                "supervisor": supervisor_id
                            }
                        )
                    except Exception:
                        pass

                self.notify_clients()
                return {
                    "verified": True,
                    "decision": "VERIFIED",
                    "status": "VERIFIED",
                    "verification_notes": target.verification_notes,
                    "message": "✓ VERIFIED — OBSERVABLE CONDITION RESTORED. Alert resolved.",
                    "alert": target
                }

    def assign_pattern_action(
        self,
        pattern_id: str,
        supervisor_id: str = "SUP-01",
        supervisor_name: str = "Rajesh Kumar (Field Lead)",
        required_action: str = "Clear unauthorized personnel and secure the restricted zone.",
        location: str = "Lifting Zone 03",
        priority: str = "HIGH",
        verification_method: str = "CCTV_VERIFIABLE",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        HSE assigns corrective action for a recurring pattern (Class 2: PATTERN_ACTION).
        Generates distinct PATTERN_ACTION alert for supervisor notification.
        """
        with self.lock:
            now = datetime.now()
            try:
                from backend.database import db
            except ImportError:
                from database import db
            pat = db.get_pattern(pattern_id)
            pat_title = pat.title if pat else f"Recurring Pattern {pattern_id}"
            pat_occ = pat.occurrence_count if pat else 1
            pat_act = pat.activity if pat else "General Site Operations"
            pat_bar = pat.barrier if pat else "Critical Safety Barrier"
            pat_energy = pat.energy if pat else "Gravitational / Kinetic Energy"

            alert_id = f"ACT-PAT-{uuid.uuid4().hex[:6].upper()}"
            action_alert = Alert(
                id=alert_id,
                alert_class="PATTERN_ACTION",
                pattern_id=pattern_id,
                pattern_title=pat_title,
                pattern_occurrence_count=pat_occ,
                assigned_by="HSE Control Desk",
                type="PATTERN CORRECTIVE ACTION",
                title=f"PATTERN ACTION: {pat_title}",
                short_summary=f"Recurring control breach at {location} ({pat_occ} independent occurrences). Action: {required_action}",
                location=location,
                camera=self.active_camera_id or "C-01",
                camera_id=self.active_camera_id or "C-01",
                source="HSE Safety Memory Governance",
                severity=priority if priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "HIGH",
                priority_label=priority if priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "HIGH",
                priority_score=95,
                status="WAITING_FOR_RESPONSE",
                stage="ACTION",
                assigned_to=f"{supervisor_id} ({supervisor_name})",
                created_at=now.isoformat(),
                response_deadline=(now + timedelta(seconds=RESPONSE_SLA_SECONDS)).isoformat(),
                action_deadline=(now + timedelta(seconds=ACTION_SLA_SECONDS)).isoformat(),
                activity=pat_act,
                hazard=pat_energy,
                sif_potential="SIF Potential",
                sif_level=priority if priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "HIGH",
                sif_reason=f"Recurring control breach of {pat_bar} requires field supervisor intervention.",
                critical_barrier=pat_bar,
                barrier_condition="Compromised",
                immediate_action=required_action,
                action_status="ASSIGNED",
                verification_type=verification_method if verification_method in ["CCTV_VERIFIABLE", "FIELD_HSE_VERIFICATION"] else "CCTV_VERIFIABLE",
                lifecycle_state="ACTION_REQUIRED",
                recurring_pattern_title=pat_title,
                independent_occurrences_count=pat_occ,
                notes=notes or f"Assigned by HSE to {supervisor_name}"
            )

            self._active_alerts[alert_id] = action_alert

            record = {
                "pattern_id": pattern_id,
                "alert_id": alert_id,
                "operational_status": "ACTION_REQUIRED",
                "supervisor_id": supervisor_id,
                "supervisor_name": supervisor_name,
                "required_action": required_action,
                "location": location,
                "priority": priority,
                "verification_method": verification_method,
                "assigned_at": now.isoformat(),
                "action_completed_at": None,
                "action_taken_by": None,
                "action_notes": None,
                "verification_status": "PENDING",
                "verification_notes": None,
                "verified_at": None,
                "closed_at": None,
            }
            self.pattern_actions[pattern_id] = record

            # Durably persist to SQLite reviews table
            try:
                rev_id = f"REV-{uuid.uuid4().hex[:8].upper()}"
                db.log_review(
                    review_id=rev_id,
                    target_type="PATTERN_ACTION",
                    target_id=pattern_id,
                    reviewer_role="HSE_DESK",
                    action="ASSIGN_ACTION",
                    previous_value=None,
                    new_value=record,
                    reason=f"Action assigned to {supervisor_name}: {required_action}"
                )
            except Exception as e:
                logger.warning(f"Failed to persist pattern action review: {e}")

            return {
                "success": True,
                "alert_id": alert_id,
                "pattern_action": record,
                "alert": action_alert.model_dump() if hasattr(action_alert, "model_dump") else action_alert.dict()
            }

    def get_pattern_action(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.pattern_actions.get(pattern_id)

    def get_pattern_operational_status(self, pattern_id: str, validation_status: str = "CANDIDATE") -> str:
        with self.lock:
            act = self.pattern_actions.get(pattern_id)
            if act:
                return act.get("operational_status", "ACTIVE")
            if str(validation_status) == "HSE_VALIDATED":
                return "ACTION_REQUIRED"
            return "ACTIVE"

    def close_pattern_action(self, pattern_id: str, closed_by: str = "Chief HSE Officer (OIL)", notes: str = "", closure_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        HSE closes verified pattern and moves it to CLOSED / HISTORY.
        Pattern remains accessible in historical records.
        """
        with self.lock:
            now = datetime.now().isoformat()
            actual_notes = closure_notes if closure_notes is not None else notes
            if pattern_id not in self.pattern_actions:
                self.pattern_actions[pattern_id] = {
                    "pattern_id": pattern_id,
                    "operational_status": "CLOSED_HISTORY",
                    "verification_status": "VERIFIED"
                }

            act = self.pattern_actions[pattern_id]
            act["operational_status"] = "CLOSED_HISTORY"
            act["closed_at"] = now
            act["closed_by"] = closed_by
            act["closure_notes"] = actual_notes or "Pattern verified and formally closed by HSE authority."
            act["success"] = True

            try:
                try:
                    from backend.database import db
                except ImportError:
                    from database import db
                db.log_review(
                    review_id=f"REV-CLOSE-{uuid.uuid4().hex[:8].upper()}",
                    target_type="PATTERN",
                    target_id=pattern_id,
                    reviewer_role=closed_by,
                    action="CLOSE_PATTERN",
                    previous_value={"operational_status": "VERIFIED"},
                    new_value={"operational_status": "CLOSED_HISTORY"},
                    reason=act["closure_notes"]
                )
            except Exception:
                pass

            self.notify_clients()
            return act

    def resolve_alert(self, supervisor_id: str = "SUP-01", notes: Optional[str] = None, alert_id: Optional[str] = None) -> Optional[Alert]:
        """
        Supervisor marks alert fixed/resolved.
        Fulfills both action completion and verified resolution for full backwards compatibility.
        """
        with self.lock:
            target = None
            if alert_id:
                target = self._active_alerts.get(alert_id)
            else:
                sorted_alerts = sort_alerts_by_priority(list(self._active_alerts.values()))
                target = sorted_alerts[0] if sorted_alerts else None

            if not target:
                return None

            now = datetime.now()
            target.action_status = "COMPLETED"
            target.verification_status = "VERIFIED"
            target.status = "RESOLVED"
            target.stage = "RESOLVED"
            target.resolved_at = now.isoformat()
            target.verified_at = now.isoformat()
            target.verified_by = supervisor_id
            if target.escalated_at:
                target.was_escalated = True
            if supervisor_id:
                target.resolved_by = supervisor_id
            if notes:
                target.notes = notes

            target.incident_timeline.append({
                "timestamp": now.isoformat(),
                "event_type": "DIRECT_HUMAN_RESOLUTION",
                "title": f"Direct Human Resolution by {supervisor_id}",
                "actor": supervisor_id,
                "details": notes or "Direct Human Resolution authorized by Supervisor on site"
            })

            # Remove only this specific alert from active alerts
            if target.id in self._active_alerts:
                del self._active_alerts[target.id]

            self._last_resolved_alert = target
            self.history.append(target)

            # Check if resolving a Safety Passport breach alert
            p = self.active_passport
            if p and (target.type == "SAFETY PASSPORT BREACH" or p.active_breach_alert_id == target.id):
                if p.status == "PAUSED":
                    p.status = "AWAITING_RESTORATION"
                    p.events.append(PassportEvent(
                        id=f"evt-{int(now.timestamp()*1000)}",
                        timestamp=now.isoformat(),
                        event_type="alert_resolved",
                        actor=supervisor_id or "Supervisor",
                        description=f"Breach alert {target.id} acknowledged/resolved. Physical barrier restoration verification required before passport reactivation."
                    ))

            # Check remaining active alerts
            if not self._active_alerts:
                has_helmet_violation = (self.person_detected and not self.helmet_detected)
                if not has_helmet_violation and not self.zone_violation:
                    self.current_safety_state = "SAFE" if self.person_detected else "MONITORING"

        self.notify_clients()
        return target

    def reset_demo(self):
        with self.lock:
            self._active_alerts.clear()
            self._last_resolved_alert = None
            self.history.clear()
            self.violation_start_time = None
            self.safe_start_time = None
            self.simulated_mode = False
            self.simulated_state = None
            self.zone_violation = False
            self.persons_in_zone = 0
            self.zone_occupancy_score = 0.0
            self.zone_debug_info = None
            self.current_safety_state = "SAFE" if getattr(self, 'helmet_detected', False) else "MONITORING"
            self.person_count = 0
            self.unhelmeted_count = 0
            self.unhelmeted_ids = []
            self.vest_detected = False
            self.unvested_count = 0
            self.unvested_ids = []
            self.gloves_detected = False
            self.ungloved_count = 0
            self.ungloved_ids = []
            self.person_violations = {}
            self.ppe_statuses = {}
            self.vest_violation_start_time = None
            self.gloves_violation_start_time = None
            self.passports.clear()
            self.active_passport_id = None
            self._passport_counter = 0

            # Reset Safety Memory (governance, patterns, events)
            try:
                from safety_memory import safety_memory
                safety_memory.reset()
            except Exception as e:
                print(f"[State] Safety Memory reset notice: {e}")

            # Reset Unified Event Store & Dataset Importer
            try:
                from unified_event_store import unified_event_store
                from dataset_importer import dataset_import_manager
                unified_event_store.reset()
                dataset_import_manager.reset()
            except Exception as e:
                print(f"[State] Unified store reset notice: {e}")

            # CHANGE 15: Remove temporary Passport zones only!
            temp_ids = [zid for zid, z in self.zones.items() if z.zone_category == "PASSPORT_TEMPORARY"]
            for zid in temp_ids:
                del self.zones[zid]

            # Preserve permanent site zones; if none exists, restore default
            if not any(z.zone_category == "PERMANENT" for z in self.zones.values()):
                self.zones["ZONE-001"] = RestrictedZone(
                    zone_id="ZONE-001",
                    name="Compressor Restricted Area",
                    camera_id="C-01",
                    zone_type="floor",
                    zone_category="PERMANENT",
                    severity="HIGH",
                    polygon=[[120.0, 180.0], [520.0, 180.0], [520.0, 440.0], [120.0, 440.0]],
                    enabled=True,
                    status="ACTIVE"
                )
            else:
                for z in self.zones.values():
                    if z.zone_category == "PERMANENT":
                        z.enabled = True
                        z.status = "ACTIVE"

            self._active_zone_override = None
            self.zone_status = "CLEAR" if (self.active_zone and self.active_zone.enabled) else "NO_ZONE"

        self.notify_clients()


    def simulate_no_helmet(self, count: int = 2):
        with self.lock:
            self.simulated_mode = True
            self.simulated_state = "VIOLATION"
            self.person_detected = True
            self.helmet_detected = False
            self.person_count = count
            self.unhelmeted_count = count
            self.unhelmeted_ids = [f"Person {i+1:02d}" for i in range(count)]
            self.current_safety_state = "VIOLATION"

        p_word = "PEOPLE" if count > 1 else "PERSON"
        ev_frame = generate_visual_evidence(
            alert_type="Helmet/PPE Violation",
            camera_id="C-01",
            location="Demo Work Zone",
            person_count=count,
            unhelmeted_ids=[f"Person {i+1:02d}" for i in range(count)]
        )
        return self.trigger_alert(
            alert_type="Helmet/PPE Violation",
            location="Demo Work Zone",
            camera="C-01",
            severity="HIGH",
            sif_potential="HIGH / POTENTIAL",
            person_count=count,
            affected_person_ids=[f"Person {i+1:02d}" for i in range(count)],
            title=f"{count} {p_word} WITHOUT HELMETS",
            short_summary=f"{count} workers detected without hard hat protection",
            hazard="Lack of required PPE (Head Protection)",
            unsafe_condition=f"{count} workers present without hard hat in active zone",
            notes=f"Automated SIF Prevention Alert: {count} unequipped workers.",
            evidence_frame=ev_frame
        )

    def simulate_safe(self):
        with self.lock:
            self.simulated_mode = False
            self.simulated_state = "SAFE"
            self.person_detected = False
            self.helmet_detected = False
            self.person_count = 0
            self.unhelmeted_count = 0
            self.unhelmeted_ids = []
            self.zone_violation = False
            self.persons_in_zone = 0
            self.zone_occupancy_score = 0.0
            self.zone_debug_info = None
            if self.active_zone and self.active_zone.enabled:
                self.zone_status = "CLEAR"
            self.current_safety_state = "SAFE"

        self.notify_clients()

    def simulate_zone_entry(self):
        with self.lock:
            self.simulated_mode = True
            self.simulated_state = "ZONE_VIOLATION"
            self.person_detected = True
            self.zone_violation = True
            self.zone_status = "VIOLATION"
            self.persons_in_zone = 1
            self.zone_occupancy_score = 0.92
            self.current_safety_state = "VIOLATION"
            active_z = self.active_zone
            loc = active_z.name if active_z else "Compressor Restricted Area"
            cam = active_z.camera_id if active_z else "C-01"
            sev = active_z.severity if active_z else "HIGH"
            z_cat = active_z.zone_category if active_z else "PERMANENT"
            z_poly = active_z.polygon if active_z else None
            z_type = (active_z.zone_type or "floor").lower() if active_z else "floor"
            type_label = "Surface / Platform" if "surface" in z_type else "Floor / Ground"
            self.zone_debug_info = f"SIMULATED | {type_label.upper()} OCCUPIED | VIOLATION"

        ev_frame = generate_visual_evidence(
            alert_type="Restricted Zone Entry",
            camera_id=cam,
            location=loc,
            person_count=1,
            zone_name=loc,
            zone_category=z_cat,
            zone_polygon=z_poly
        )

        # Check if active passport exists and pause it (produce only ONE canonical critical breach alert)
        p = self.active_passport
        if p and p.status in ["ACTIVE", "PAUSED"]:
            if p.status == "ACTIVE":
                return self.pause_passport_due_to_breach("Lifting exclusion zone breached", evidence_frame=ev_frame)
            if p.active_breach_alert_id and p.active_breach_alert_id in self._active_alerts:
                return self._active_alerts[p.active_breach_alert_id]
            return None

        return self.trigger_alert(
            alert_type="Restricted Zone Entry",
            location=loc,
            camera=cam,
            severity=sev,
            sif_potential="HIGH / POTENTIAL",
            person_count=1,
            affected_person_ids=["Person 01"],
            title="RESTRICTED ZONE ENTRY",
            short_summary=f"1 person detected occupying restricted perimeter ({loc})",
            hazard=f"Unauthorized / Unsafe Occupancy of {type_label} Zone",
            unsafe_condition=f"Person detected occupying {type_label} restricted perimeter ({loc})",
            notes="Automated SIF Observation: Person detected inside an HSE-defined restricted area.",
            evidence_frame=ev_frame
        )

    def simulate_multi_violation(self):
        """
        Simultaneous Demo Scenario (Part 11):
        Camera sees 3 people:
        - Person 01 & 02: NO HELMET
        - Person 03: inside restricted zone
        Triggers BOTH alerts simultaneously with visual evidence!
        """
        with self.lock:
            self.simulated_mode = True
            self.simulated_state = "MULTI_VIOLATION"
            self.person_detected = True
            self.helmet_detected = False
            self.person_count = 3
            self.unhelmeted_count = 2
            self.unhelmeted_ids = ["Person 01", "Person 02"]
            self.zone_violation = True
            self.zone_status = "VIOLATION"
            self.persons_in_zone = 1
            self.zone_occupancy_score = 0.95
            self.current_safety_state = "VIOLATION"
            active_z = self.active_zone
            loc = active_z.name if active_z else "Compressor Restricted Area"
            cam = active_z.camera_id if active_z else "C-01"
            z_cat = active_z.zone_category if active_z else "PERMANENT"
            z_poly = active_z.polygon if active_z else None
            self.zone_debug_info = "SIMULATED | MULTI-HAZARD (ZONE + 2 NO-HELMET)"

        zone_ev = generate_visual_evidence(
            alert_type="Restricted Zone Entry",
            camera_id=cam,
            location=loc,
            person_count=1,
            zone_name=loc,
            zone_category=z_cat,
            zone_polygon=z_poly
        )

        ppe_ev = generate_visual_evidence(
            alert_type="Helmet/PPE Violation",
            camera_id="C-01",
            location="Demo Work Zone",
            person_count=2,
            unhelmeted_ids=["Person 01", "Person 02"]
        )

        # 1. Check if active passport exists and pause it (produce only ONE canonical breach alert for zone)
        p = self.active_passport
        if p and p.status in ["ACTIVE", "PAUSED"]:
            if p.status == "ACTIVE":
                self.pause_passport_due_to_breach("Lifting exclusion zone breached", evidence_frame=zone_ev)
        else:
            self.trigger_alert(
                alert_type="Restricted Zone Entry",
                location=loc,
                camera=cam,
                severity="HIGH",
                sif_potential="HIGH / POTENTIAL",
                person_count=1,
                affected_person_ids=["Person 03"],
                title="RESTRICTED ZONE ENTRY",
                short_summary=f"1 person detected inside restricted area ({loc})",
                hazard="Unauthorized Restricted Zone Entry",
                unsafe_condition=f"Worker present within high-risk restricted perimeter ({loc})",
                notes="Automated SIF Observation: Unauthorized worker detected inside restricted zone.",
                evidence_frame=zone_ev
            )

        # 2. Trigger Grouped PPE alert (Priority: HIGH)
        self.trigger_alert(
            alert_type="Helmet/PPE Violation",
            location="Demo Work Zone",
            camera="C-01",
            severity="HIGH",
            sif_potential="HIGH / POTENTIAL",
            person_count=2,
            affected_person_ids=["Person 01", "Person 02"],
            title="2 PEOPLE WITHOUT HELMETS",
            short_summary="2 unequipped workers detected without head protection",
            hazard="Lack of required PPE (Head Protection)",
            unsafe_condition="2 workers present without hard hat in active zone",
            notes="Automated SIF Prevention Alert: 2 unequipped workers.",
            evidence_frame=ppe_ev
        )

        return self.get_active_alerts_list()

    def update_cv_detection(self, person_detected: bool, helmet_detected: bool, 
                            zone_violation: bool = False, persons_in_zone: int = 0,
                            occupancy_score: float = 0.0, debug_info: Optional[str] = None,
                            person_count: int = 0, unhelmeted_count: int = 0,
                            unhelmeted_ids: Optional[List[str]] = None,
                            evidence_frame: Optional[bytes] = None,
                            breached_zone: Optional[RestrictedZone] = None,
                            vest_detected: bool = False,
                            unvested_count: int = 0,
                            unvested_ids: Optional[List[str]] = None,
                            gloves_detected: bool = False,
                            ungloved_count: int = 0,
                            ungloved_ids: Optional[List[str]] = None,
                            person_violations: Optional[Dict[str, List[str]]] = None,
                            ppe_statuses: Optional[Dict[str, Dict[str, str]]] = None,
                            person_findings: Optional[List[Dict[str, Any]]] = None,
                            fire_detected: bool = False,
                            fire_confidence: float = 0.0,
                            **kwargs):
        """
        Called by detection loop for each frame.
        Applies debounce logic for violations and notifies clients on state transitions.
        Unifies multiple simultaneous violations across people into ONE camera incident.
        Supports person detection, helmet, safety vest, gloves, and restricted zones with authentic visual evidence!
        """
        state_changed = False
        trigger_helmet_alert = False
        trigger_vest_alert = False
        trigger_gloves_alert = False
        trigger_multi_alert = False
        trigger_zone_alert = False
        trigger_passport_breach = False
        trigger_grouped_camera_alert = False
        grouped_alert_args = {}
        multi_violations_list = []
        multi_affected_ids = []
        
        with self.lock:
            if self.simulated_mode:
                if person_count > 0:
                    self.simulated_mode = False
                else:
                    return # In simulated mode without real person, preserve simulated baseline
            
            prev_person = self.person_detected
            prev_helmet = self.helmet_detected
            prev_vest = self.vest_detected
            prev_gloves = getattr(self, 'gloves_detected', False)
            prev_fire = getattr(self, 'fire_detected', False)
            prev_person_count = self.person_count
            prev_unhelmeted_count = self.unhelmeted_count
            prev_unvested_count = self.unvested_count
            prev_ungloved_count = getattr(self, 'ungloved_count', 0)
            prev_safety = self.current_safety_state
            prev_zone_violation = self.zone_violation
            prev_persons_in_zone = self.persons_in_zone
            prev_zone_status = self.zone_status
            prev_occupancy_score = self.zone_occupancy_score
            prev_debug_info = self.zone_debug_info
            
            self.person_detected = person_detected
            self.helmet_detected = helmet_detected
            self.vest_detected = vest_detected
            self.gloves_detected = gloves_detected
            self.fire_detected = fire_detected
            self.fire_confidence = fire_confidence
            self.person_count = person_count
            self.unhelmeted_count = unhelmeted_count
            self.unhelmeted_ids = unhelmeted_ids or []
            self.unvested_count = unvested_count
            self.unvested_ids = unvested_ids or []
            self.ungloved_count = ungloved_count
            self.ungloved_ids = ungloved_ids or []
            self.person_violations = person_violations or {}
            self.ppe_statuses = ppe_statuses or {}
            self.zone_occupancy_score = occupancy_score
            self.zone_debug_info = debug_info
            
            # Zone tracking
            active_z = breached_zone or self.active_zone
            if active_z and active_z.enabled:
                self.zone_violation = zone_violation
                self.persons_in_zone = persons_in_zone
                self.zone_status = "VIOLATION" if zone_violation else "CLEAR"
            else:
                self.zone_violation = False
                self.persons_in_zone = 0
                self.zone_status = "NO_ZONE"
                
            now_ts = time.time()

            if person_findings is not None:
                self.person_findings = person_findings
                target_z = breached_zone or self.active_zone
                cam_id = (target_z.camera_id if target_z else self.active_camera_id) or "C-01"
                loc = target_z.name if target_z else "Demo Work Zone"
                total_people = max(person_count, len(person_findings))
                
                # Identify people with confirmed issues
                people_with_issues = [pf for pf in person_findings if len(pf.get("violations", [])) > 0]
                all_viols = []
                for pf in people_with_issues:
                    for v in pf.get("violations", []):
                        if v not in all_viols:
                            all_viols.append(v)
                            
                p_aff = [pf.get("person_id") for pf in people_with_issues]

                # Check if camera already has an active ongoing alert
                active_cam_alert = None
                for a in self._active_alerts.values():
                    if (a.camera_id == cam_id or a.camera == cam_id) and a.status in ["WAITING_FOR_RESPONSE", "RESPONDING", "ESCALATED"]:
                        active_cam_alert = a
                        break

                if people_with_issues:
                    self.current_safety_state = "VIOLATION"
                    self.safe_start_time = None
                    
                    if active_cam_alert:
                        active_cam_alert.person_count = total_people
                        active_cam_alert.affected_person_ids = p_aff
                        active_cam_alert.affected_persons = p_aff
                        active_cam_alert.violations = all_viols
                        active_cam_alert.person_findings = self._process_person_findings(person_findings, active_cam_alert.id)
                        if len(people_with_issues) > 1:
                            active_cam_alert.title = f"CAMERA EVENT — {len(people_with_issues)} People With Issues"
                            active_cam_alert.short_summary = f"{total_people} People Detected • {len(people_with_issues)} with issues ({', '.join(all_viols)})"
                        else:
                            active_cam_alert.title = f"CAMERA EVENT — {p_aff[0]}: {', '.join(all_viols)}"
                            active_cam_alert.short_summary = f"{total_people} People Detected • 1 with issues: {', '.join(all_viols)}"
                        if evidence_frame:
                            ev_id = f"ev-{active_cam_alert.id}"
                            self.evidence_store[ev_id] = evidence_frame
                            active_cam_alert.evidence_url = f"/api/evidence/{ev_id}"
                            active_cam_alert.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                        state_changed = True
                    else:
                        if self.violation_start_time is None:
                            self.violation_start_time = now_ts
                        elapsed = now_ts - self.violation_start_time
                        if elapsed >= self.violation_persist_threshold:
                            is_multi = (len(people_with_issues) > 1 or len(all_viols) > 1)
                            if len(people_with_issues) > 1:
                                al_type = "Multi-Hazard Safety Violation"
                                title = f"CAMERA EVENT — {len(people_with_issues)} People With Issues"
                            elif len(all_viols) > 1:
                                al_type = "Multi-Hazard Safety Violation"
                                title = f"CAMERA EVENT — {p_aff[0]}: {', '.join(all_viols)}"
                            elif "RESTRICTED ZONE" in all_viols:
                                al_type = "Restricted Zone Entry"
                                title = "RESTRICTED ZONE ENTRY"
                            elif "NO HELMET" in all_viols:
                                al_type = "Helmet/PPE Violation"
                                title = f"{p_aff[0]} WITHOUT HELMET"
                            elif "NO SAFETY VEST" in all_viols:
                                al_type = "Safety Vest Violation"
                                title = f"{p_aff[0]} WITHOUT SAFETY VEST"
                            elif "NO GLOVES" in all_viols:
                                al_type = "Gloves Violation"
                                title = f"{p_aff[0]} WITHOUT GLOVES"
                            else:
                                al_type = "Helmet/PPE Violation"
                                title = f"CAMERA EVENT ({cam_id})"

                            sev = "CRITICAL" if any("ZONE" in v for v in all_viols) else "HIGH"
                            grouped_alert_args = {
                                "alert_type": al_type,
                                "location": loc,
                                "camera": cam_id,
                                "severity": sev,
                                "sif_potential": "CRITICAL / HIGH" if sev == "CRITICAL" else "HIGH / POTENTIAL",
                                "person_count": total_people,
                                "affected_person_ids": p_aff,
                                "title": title,
                                "short_summary": f"{total_people} People Detected • {len(people_with_issues)} with issues: {', '.join(all_viols)}",
                                "hazard": "Multiple Concurrent Safety Barrier Failures" if is_multi else f"Lack of required PPE ({', '.join(all_viols)})",
                                "unsafe_condition": f"Workers detected with safety violations: {', '.join(all_viols)}",
                                "notes": f"Automated SIF Alert: {total_people} detected, {len(people_with_issues)} affected.",
                                "evidence_frame": evidence_frame,
                                "violations": all_viols,
                                "person_findings": person_findings
                            }
                            trigger_grouped_camera_alert = True

                    if any("ZONE" in v for v in all_viols):
                        p = self.active_passport
                        is_passport_zone = bool(active_z and (active_z.zone_category == "PASSPORT_TEMPORARY" or (p and p.linked_zone_id == active_z.zone_id)))
                        if p and p.status in ["ACTIVE", "PAUSED"] and is_passport_zone:
                            if p.status == "ACTIVE":
                                trigger_passport_breach = True
                else:
                    # All people are normal (no issues)
                    self.violation_start_time = None
                    if self.safe_start_time is None:
                        self.safe_start_time = now_ts
                    if active_cam_alert:
                        active_cam_alert.notes = "All detected workers have returned to normal compliant PPE status."
                        active_cam_alert.person_findings = self._process_person_findings(person_findings, active_cam_alert.id)
                        state_changed = True
                    if not self._active_alerts:
                        self.current_safety_state = "SAFE" if total_people > 0 else "MONITORING"

            else:
                # Fallback path when person_findings is not provided
                # Identify workers with multiple simultaneous violations
                multi_viol_persons = {pid: vlist for pid, vlist in self.person_violations.items() if len(vlist) > 1}
                if multi_viol_persons:
                    multi_affected_ids = list(multi_viol_persons.keys())
                    combined_v = []
                    for vlist in multi_viol_persons.values():
                        for v in vlist:
                            if v not in combined_v:
                                combined_v.append(v)
                    multi_violations_list = combined_v
                    self.current_safety_state = "VIOLATION"
                    
                    # Deduplication: check if Multi-Hazard alert is already active
                    has_active_multi = any(a.type == "Multi-Hazard Safety Violation" for a in self._active_alerts.values())
                    if not has_active_multi:
                        trigger_multi_alert = True
                    else:
                        for a in self._active_alerts.values():
                            if a.type == "Multi-Hazard Safety Violation":
                                a.person_count = max(1, len(multi_affected_ids))
                                a.affected_person_ids = multi_affected_ids
                                a.affected_persons = multi_affected_ids
                                a.violations = list(dict.fromkeys(a.violations + multi_violations_list))
                                if evidence_frame:
                                    ev_id = f"ev-{a.id}"
                                    self.evidence_store[ev_id] = evidence_frame
                                    a.evidence_url = f"/api/evidence/{ev_id}"
                                    a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                state_changed = True
                                break

                    if any("ZONE" in v for v in multi_violations_list):
                        p = self.active_passport
                        is_passport_zone = bool(active_z and (active_z.zone_category == "PASSPORT_TEMPORARY" or (p and p.linked_zone_id == active_z.zone_id)))
                        if p and p.status in ["ACTIVE", "PAUSED"] and is_passport_zone:
                            if p.status == "ACTIVE":
                                trigger_passport_breach = True

                # Single-violation paths (no person has multiple concurrent violations)
                # 1. Check Zone Violation & Passport Breach
                if not multi_viol_persons and self.zone_violation and active_z and active_z.enabled:
                    self.current_safety_state = "VIOLATION"
                    p = self.active_passport
                    is_passport_zone = (active_z.zone_category == "PASSPORT_TEMPORARY" or (p and p.linked_zone_id == active_z.zone_id))
                    if p and p.status in ["ACTIVE", "PAUSED"] and is_passport_zone:
                        if p.status == "ACTIVE":
                            trigger_passport_breach = True
                    else:
                        has_active_zone_alert = any(a.type == "Restricted Zone Entry" for a in self._active_alerts.values())
                        if not has_active_zone_alert:
                            trigger_zone_alert = True
                        else:
                            for a in self._active_alerts.values():
                                if a.type == "Restricted Zone Entry":
                                    a.person_count = max(1, self.persons_in_zone)
                                    if evidence_frame:
                                        ev_id = f"ev-{a.id}"
                                        self.evidence_store[ev_id] = evidence_frame
                                        a.evidence_url = f"/api/evidence/{ev_id}"
                                        a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                    break
                elif not multi_viol_persons:
                    # Zone is clear
                    p = self.active_passport
                    if p and p.status == "PAUSED":
                        p.status = "AWAITING_RESTORATION"
                        p.events.append(PassportEvent(
                            id=f"evt-{int(now_ts*1000)}",
                            timestamp=datetime.now().isoformat(),
                            event_type="barrier_clear",
                            actor="AI CCTV Vision",
                            description="AI indicates exclusion zone is now clear. Human verification required before reactivation."
                        ))
                        state_changed = True

                # 2. Check Helmet Violation
                if not multi_viol_persons and unhelmeted_count > 0:
                    self.safe_start_time = None
                    if self.violation_start_time is None:
                        self.violation_start_time = now_ts
                    
                    elapsed = now_ts - self.violation_start_time
                    if elapsed >= self.violation_persist_threshold:
                        self.current_safety_state = "VIOLATION"
                        has_active_ppe_alert = any(a.type == "Helmet/PPE Violation" for a in self._active_alerts.values())
                        if not has_active_ppe_alert:
                            trigger_helmet_alert = True
                        else:
                            for a in self._active_alerts.values():
                                if a.type == "Helmet/PPE Violation":
                                    a.person_count = unhelmeted_count
                                    a.affected_person_ids = self.unhelmeted_ids
                                    a.affected_persons = self.unhelmeted_ids
                                    combined_viols = ["NO HELMET"]
                                    if self.unvested_count > 0 and "NO SAFETY VEST" not in combined_viols:
                                        combined_viols.append("NO SAFETY VEST")
                                    if getattr(self, 'ungloved_count', 0) > 0 and "NO GLOVES" not in combined_viols:
                                        combined_viols.append("NO GLOVES")
                                    a.title = " + ".join(combined_viols)
                                    a.violations = combined_viols
                                    a.short_summary = f"{unhelmeted_count} unequipped workers detected missing: {', '.join(combined_viols)}"
                                    if evidence_frame:
                                        ev_id = f"ev-{a.id}"
                                        self.evidence_store[ev_id] = evidence_frame
                                        a.evidence_url = f"/api/evidence/{ev_id}"
                                        a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                    state_changed = True
                                    break
                elif not multi_viol_persons:
                    self.violation_start_time = None

                # 3. Check Safety Vest Violation (Single violation)
                if not multi_viol_persons and unvested_count > 0 and unhelmeted_count == 0:
                    self.safe_start_time = None
                    if self.vest_violation_start_time is None:
                        self.vest_violation_start_time = now_ts
                    
                    elapsed = now_ts - self.vest_violation_start_time
                    if elapsed >= self.violation_persist_threshold:
                        self.current_safety_state = "VIOLATION"
                        has_active_vest = any(a.type == "Safety Vest Violation" for a in self._active_alerts.values())
                        if not has_active_vest:
                            trigger_vest_alert = True
                        else:
                            for a in self._active_alerts.values():
                                if a.type == "Safety Vest Violation":
                                    if a.person_count != unvested_count or evidence_frame:
                                        a.person_count = unvested_count
                                        a.affected_person_ids = self.unvested_ids
                                        a.affected_persons = self.unvested_ids
                                        p_word = "PEOPLE" if unvested_count > 1 else "PERSON"
                                        a.title = f"{unvested_count} {p_word} WITHOUT SAFETY VEST"
                                        a.short_summary = f"{unvested_count} unequipped workers detected without high-visibility vest"
                                        if evidence_frame:
                                            ev_id = f"ev-{a.id}"
                                            self.evidence_store[ev_id] = evidence_frame
                                            a.evidence_url = f"/api/evidence/{ev_id}"
                                            a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                        state_changed = True
                                    break
                elif not multi_viol_persons:
                    self.vest_violation_start_time = None

                # 4. Check Gloves Violation (Single violation)
                if not multi_viol_persons and ungloved_count > 0 and unhelmeted_count == 0 and unvested_count == 0:
                    self.safe_start_time = None
                    if self.gloves_violation_start_time is None:
                        self.gloves_violation_start_time = now_ts
                    
                    elapsed = now_ts - self.gloves_violation_start_time
                    if elapsed >= self.violation_persist_threshold:
                        self.current_safety_state = "VIOLATION"
                        has_active_gloves = any("glove" in a.type.lower() for a in self._active_alerts.values())
                        if not has_active_gloves:
                            trigger_gloves_alert = True
                        else:
                            for a in self._active_alerts.values():
                                if "glove" in a.type.lower():
                                    if a.person_count != ungloved_count or evidence_frame:
                                        a.person_count = ungloved_count
                                        a.affected_person_ids = self.ungloved_ids
                                        a.affected_persons = self.ungloved_ids
                                        p_word = "PEOPLE" if ungloved_count > 1 else "PERSON"
                                        a.title = f"{ungloved_count} {p_word} WITHOUT SAFETY GLOVES"
                                        a.short_summary = f"{ungloved_count} unequipped workers detected without safety gloves"
                                        if evidence_frame:
                                            ev_id = f"ev-{a.id}"
                                            self.evidence_store[ev_id] = evidence_frame
                                            a.evidence_url = f"/api/evidence/{ev_id}"
                                            a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                        state_changed = True
                                    break
                else:
                    self.gloves_violation_start_time = None

                # 5. Check Safe State
                if (person_detected and helmet_detected and vest_detected and not self.zone_violation and 
                    unhelmeted_count == 0 and unvested_count == 0 and ungloved_count == 0):
                    self.violation_start_time = None
                    self.vest_violation_start_time = None
                    self.gloves_violation_start_time = None
                    if self.safe_start_time is None:
                        self.safe_start_time = now_ts
                    if not self._active_alerts:
                        self.current_safety_state = "SAFE"
                elif not person_detected and not self.zone_violation:
                    self.violation_start_time = None
                    self.vest_violation_start_time = None
                    self.gloves_violation_start_time = None
                    self.safe_start_time = None
                    if not self._active_alerts:
                        self.current_safety_state = "MONITORING"

            if (self.person_detected != prev_person or 
                self.helmet_detected != prev_helmet or 
                self.vest_detected != prev_vest or
                getattr(self, 'gloves_detected', False) != prev_gloves or
                getattr(self, 'fire_detected', False) != prev_fire or
                self.person_count != prev_person_count or
                self.unhelmeted_count != prev_unhelmeted_count or
                self.unvested_count != prev_unvested_count or
                getattr(self, 'ungloved_count', 0) != prev_ungloved_count or
                self.current_safety_state != prev_safety or
                self.zone_violation != prev_zone_violation or
                self.persons_in_zone != prev_persons_in_zone or
                self.zone_status != prev_zone_status or
                abs(self.zone_occupancy_score - prev_occupancy_score) > 0.05 or
                self.zone_debug_info != prev_debug_info):
                state_changed = True

        # Alert dispatches outside lock
        target_z = breached_zone or self.active_zone
        loc = target_z.name if target_z else "Demo Work Zone"
        cam = target_z.camera_id if target_z else "C-01"

        if trigger_grouped_camera_alert and grouped_alert_args:
            self.trigger_alert(**grouped_alert_args)

        if trigger_passport_breach:
            b_name = (breached_zone.name if breached_zone else (self.active_passport.linked_zone_name if self.active_passport else "Lifting exclusion zone"))
            self.pause_passport_due_to_breach(f"{b_name} breached", evidence_frame=evidence_frame)

        if trigger_multi_alert:
            v_str = " + ".join(multi_violations_list)
            p_str = ", ".join(multi_affected_ids)
            self.trigger_alert(
                alert_type="Multi-Hazard Safety Violation",
                location=loc,
                camera=cam,
                severity="CRITICAL" if any("ZONE" in v for v in multi_violations_list) else "HIGH",
                sif_potential="CRITICAL / HIGH",
                person_count=max(1, len(multi_affected_ids)),
                affected_person_ids=multi_affected_ids,
                title=f"MULTI-HAZARD SAFETY VIOLATION ({p_str})",
                short_summary=f"{p_str} detected with concurrent violations: {v_str}",
                hazard="Multiple Concurrent Safety Barrier Failures",
                unsafe_condition=f"Worker present with multiple simultaneous safety violations: {v_str}",
                notes=f"Automated SIF Alert: {p_str} multiple concurrent violations ({v_str}).",
                evidence_frame=evidence_frame,
                violations=multi_violations_list
            )

        if trigger_zone_alert:
            sev = target_z.severity if target_z else "HIGH"
            z_type = (target_z.zone_type or "floor").lower() if target_z else "floor"
            type_label = "Surface / Platform" if "surface" in z_type else "Floor / Ground"
            self.trigger_alert(
                alert_type="Restricted Zone Entry",
                location=loc,
                camera=cam,
                severity=sev,
                sif_potential="HIGH / POTENTIAL",
                person_count=max(1, self.persons_in_zone),
                hazard=f"Unauthorized / Unsafe Occupancy of {type_label} Zone",
                unsafe_condition=f"Person detected occupying {type_label} restricted perimeter ({loc})",
                notes="Automated SIF Observation: Person detected inside an HSE-defined restricted area.",
                evidence_frame=evidence_frame,
                violations=["RESTRICTED ZONE"]
            )
        
        if trigger_helmet_alert:
            cnt = max(1, self.unhelmeted_count)
            p_word = "PEOPLE" if cnt > 1 else "PERSON"
            combined_viols = ["NO HELMET"]
            if self.unvested_count > 0 and "NO SAFETY VEST" not in combined_viols:
                combined_viols.append("NO SAFETY VEST")
            if getattr(self, 'ungloved_count', 0) > 0 and "NO GLOVES" not in combined_viols:
                combined_viols.append("NO GLOVES")
            alert_title = " + ".join(combined_viols)

            self.trigger_alert(
                alert_type="Helmet/PPE Violation",
                location="Demo Work Zone",
                camera="C-01",
                severity="HIGH",
                sif_potential="HIGH / POTENTIAL",
                person_count=cnt,
                affected_person_ids=self.unhelmeted_ids,
                title=alert_title,
                short_summary=f"{cnt} unequipped workers detected missing: {', '.join(combined_viols)}",
                hazard=f"Lack of required PPE ({', '.join(combined_viols)})",
                unsafe_condition=f"{cnt} workers present missing required PPE ({' + '.join(combined_viols)}) in active zone",
                notes=f"Automated SIF Prevention Alert: {cnt} workers.",
                evidence_frame=evidence_frame,
                violations=combined_viols
            )

        if trigger_vest_alert:
            cnt = max(1, self.unvested_count)
            p_word = "PEOPLE" if cnt > 1 else "PERSON"
            combined_viols = ["NO SAFETY VEST"]
            if getattr(self, 'ungloved_count', 0) > 0 and "NO GLOVES" not in combined_viols:
                combined_viols.append("NO GLOVES")
            alert_title = " + ".join(combined_viols)

            self.trigger_alert(
                alert_type="Safety Vest Violation",
                location="Demo Work Zone",
                camera="C-01",
                severity="HIGH",
                sif_potential="HIGH / POTENTIAL",
                person_count=cnt,
                affected_person_ids=self.unvested_ids,
                title=alert_title,
                short_summary=f"{cnt} unequipped workers detected missing: {', '.join(combined_viols)}",
                hazard=f"Lack of required PPE ({', '.join(combined_viols)})",
                unsafe_condition=f"{cnt} workers present missing required PPE ({' + '.join(combined_viols)}) in active zone",
                notes=f"Automated SIF Prevention Alert: {cnt} workers.",
                evidence_frame=evidence_frame,
                violations=combined_viols
            )

        if trigger_gloves_alert:
            cnt = max(1, self.ungloved_count)
            p_word = "PEOPLE" if cnt > 1 else "PERSON"
            self.trigger_alert(
                alert_type="Gloves Violation",
                location="Demo Work Zone",
                camera="C-01",
                severity="HIGH",
                sif_potential="HIGH / POTENTIAL",
                person_count=cnt,
                affected_person_ids=self.ungloved_ids,
                title=f"{cnt} {p_word} WITHOUT SAFETY GLOVES",
                short_summary=f"{cnt} unequipped workers detected without hand protection",
                hazard="Lack of required PPE (Safety Hand Protection / Gloves)",
                unsafe_condition=f"{cnt} workers present without safety gloves in active zone",
                notes=f"Automated SIF Prevention Alert: {cnt} workers.",
                evidence_frame=evidence_frame,
                violations=["NO GLOVES"]
            )

        if state_changed and not (trigger_grouped_camera_alert or trigger_zone_alert or trigger_helmet_alert or trigger_vest_alert or 
                                  trigger_gloves_alert or trigger_multi_alert or trigger_passport_breach):
            self.notify_clients()

    def _watchdog_loop(self):
        """
        Runs continuously in background.
        Checks every active alert in WAITING_FOR_RESPONSE for 20s SLA escalation.
        Checks temporary exclusion zones for expiry (pausing linked passport).
        Checks active passports for expiry (deactivating linked temporary zones).
        """
        while self._running:
            time.sleep(0.2)
            should_notify = False
            now = datetime.now()
            with self.lock:
                for alert in list(self._active_alerts.values()):
                    if alert.status == "WAITING_FOR_RESPONSE":
                        try:
                            deadline = datetime.fromisoformat(alert.response_deadline)
                            if now >= deadline:
                                alert.status = "ESCALATED"
                                alert.stage = "ESCALATED"
                                alert.was_escalated = True
                                alert.assigned_to = "HSE CONTROL DESK"
                                alert.escalated_at = now.isoformat()
                                alert.reason = "Supervisor response was not received within 20 seconds."
                                should_notify = True
                        except Exception as e:
                            print(f"Error checking deadline for alert {alert.id}: {e}")

                # Check temporary exclusion zones expiry (CHANGE 3 & CHANGE 14)
                for tz in list(self.zones.values()):
                    if tz.zone_category == "PASSPORT_TEMPORARY" and tz.enabled and tz.status == "ACTIVE" and tz.expires_at:
                        try:
                            exp_z = datetime.fromisoformat(tz.expires_at)
                            if now >= exp_z:
                                tz.status = "EXPIRED"
                                tz.enabled = False
                                should_notify = True
                                # If linked passport is still ACTIVE, transition to PAUSED:
                                lp = None
                                if tz.passport_id and tz.passport_id in self.passports:
                                    lp = self.passports[tz.passport_id]
                                elif self.active_passport and self.active_passport.linked_zone_id == tz.zone_id:
                                    lp = self.active_passport
                                
                                if lp and lp.status == "ACTIVE":
                                    lp.status = "PAUSED"
                                    lp.paused_at = now.isoformat()
                                    lp.breach_reason = "Temporary exclusion zone expired"
                                    lp.events.append(PassportEvent(
                                        id=f"evt-{int(now.timestamp()*1000)}",
                                        timestamp=now.isoformat(),
                                        event_type="paused",
                                        actor="Zone Watchdog",
                                        description="SAFETY PASSPORT PAUSED / BLOCKED: Temporary exclusion zone expired."
                                    ))
                                    self.trigger_alert(
                                        alert_type="SAFETY PASSPORT BREACH",
                                        location=lp.location,
                                        camera=lp.camera_id,
                                        severity="CRITICAL",
                                        sif_potential="HIGH / POTENTIAL",
                                        person_count=1,
                                        title="SAFETY PASSPORT PAUSED: Temporary Zone Expired",
                                        short_summary=f"Safety Passport PAUSED — Temporary exclusion zone expired for {lp.task_type}",
                                        hazard="Exclusion Barrier Expired during High-Risk Activity",
                                        unsafe_condition=f"Temporary exclusion zone expired while task {lp.task_type} in progress",
                                        notes="High-risk work clearance blocked: Temporary exclusion zone time window expired."
                                    )
                        except Exception:
                            pass

                # Check active passport expiry (CHANGE 5 & CHANGE 7)
                for p in list(self.passports.values()):
                    if p.status in ["ACTIVE", "PAUSED", "AWAITING_RESTORATION"] and p.expires_at:
                        try:
                            exp = datetime.fromisoformat(p.expires_at)
                            if now >= exp:
                                p.status = "EXPIRED"
                                # Deactivate linked temporary zone
                                if p.linked_zone_id and p.linked_zone_id in self.zones:
                                    tz = self.zones[p.linked_zone_id]
                                    if tz.zone_category == "PASSPORT_TEMPORARY":
                                        tz.enabled = False
                                        tz.status = "EXPIRED"
                                p.events.append(PassportEvent(
                                    id=f"evt-{int(now.timestamp()*1000)}",
                                    timestamp=now.isoformat(),
                                    event_type="expired",
                                    actor="Passport Watchdog",
                                    description="Work clearance time window has EXPIRED."
                                ))
                                if self.active_passport_id == p.id:
                                    self.active_passport_id = None
                                should_notify = True
                        except Exception:
                            pass
            
            if should_notify:
                self.notify_clients()

    def reset_cv_session(self):
        """
        Clears transient CV live tracking state when switching camera sources or videos.
        Resets active_alert if it is a CV-generated alert, resets detection counters, and clears tracking state.
        Returns a dict with success=True.
        """
        with self.lock:
            # Reset live transient CV counters
            self.person_detected = False
            self.person_count = 0
            self.unhelmeted_count = 0
            self.unvested_count = 0
            self.ungloved_count = 0
            self.unhelmeted_ids = []
            self.unvested_ids = []
            self.ungloved_ids = []
            self.helmet_detected = False
            self.vest_detected = False
            self.gloves_detected = False
            self.fire_detected = False
            self.fire_confidence = 0.0
            self.zone_violation = False
            self.camera_consecutive_violation_count = 0
            self.camera_consecutive_safe_count = 0
            self.camera_active_alert_id = None
            self.current_safety_state = "MONITORING"

            # Clear active CV alert if present
            if self.active_alert:
                if (
                    self.active_alert.type in ("Person–Vehicle Proximity", "Helmet/PPE Violation", "Restricted Area Breach", "Zone Breach", "CCTV Safety Violation", "Safety Vest Violation", "Gloves Violation", "Fire Hazard", "Fire Detection") or
                    "fire" in self.active_alert.type.lower() or
                    getattr(self.active_alert, "source", "") in ("CCTV_CV", "CV_DETECTION", "CCTV") or
                    self.active_alert.id.startswith("ALT-PROX-") or
                    self.active_alert.id.startswith("ALT-FIRE-") or
                    self.active_alert.id.startswith("ALT-CV-")
                ):
                    self.active_alert = None
            
            # Reset detection engine tracks if available
            try:
                from detection import video_engine
                video_engine.reset_tracks()
            except Exception:
                pass
                
        self.notify_clients()
        return {"success": True, "message": "CV session cleanly reset"}

    def notify_clients(self):
        """
        Sends the updated SystemStatus via WebSocket to all active dashboards and mobile clients.
        """
        if not getattr(self, '_loop', None) or not self.active_websockets:
            return
        
        status_data = self.get_system_status().model_dump_json()
        
        async def _broadcast():
            to_remove = set()
            for ws in list(self.active_websockets):
                try:
                    await ws.send_text(status_data)
                except Exception:
                    to_remove.add(ws)
            with self.lock:
                self.active_websockets.difference_update(to_remove)

        asyncio.run_coroutine_threadsafe(_broadcast(), self._loop)

# Singleton state manager instance
state_manager = AlertStateManager()
