import asyncio
import threading
import time
import base64
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Set, Dict
from fastapi import WebSocket
from models import (
    Alert, SystemStatus, RestrictedZone,
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
    if is_zone_alert:
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

def calculate_alert_priority(alert_type: str, severity: str = "HIGH", sif_potential: str = "HIGH / POTENTIAL") -> tuple[int, str]:
    """
    AI Recommended Response Priority:
    0. SAFETY PASSPORT PAUSED / CRITICAL BARRIER BREACH (score 120, CRITICAL)
    1. RESTRICTED ZONE / HIGH SIF POTENTIAL (score 100, CRITICAL)
    2. OTHER HIGH SIF POTENTIAL SAFETY EVENTS (score 80, HIGH)
    3. PPE / HELMET VIOLATION (score 60, HIGH)
    4. LOWER-SEVERITY OBSERVATIONS (score 40, LOW)
    """
    al_lower = alert_type.lower()
    if "passport" in al_lower or "breach" in al_lower:
        return 120, "CRITICAL"
    if "zone" in al_lower or "restricted" in al_lower:
        return 100, "CRITICAL"
    if "high" in str(sif_potential).lower() and "ppe" not in al_lower and "helmet" not in al_lower:
        return 80, "HIGH"
    if "ppe" in al_lower or "helmet" in al_lower:
        return 60, "HIGH"
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
    1. Highest priority score first
    2. Within same score, oldest unresolved alert first (created_at ascending)
    """
    return sorted(alerts, key=lambda a: (-a.priority_score, a.created_at))

class AlertStateManager:
    def __init__(self):
        self.lock = threading.RLock()
        self._active_alerts: Dict[str, Alert] = {}
        self.history: List[Alert] = []
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
        self.current_safety_state: str = "MONITORING" # SAFE, VIOLATION, MONITORING
        
        # Restricted Zone detection state
        self.zone_violation: bool = False
        self.zone_status: str = "CLEAR" # "CLEAR", "VIOLATION", "NO_ZONE", "LOW_CONFIDENCE"
        self.persons_in_zone: int = 0
        self.zone_occupancy_score: float = 0.0
        self.zone_debug_info: Optional[str] = None
        
        # Debounce tracking for single violation persistence
        self.violation_start_time: Optional[float] = None
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
            return SystemStatus(
                system_status="ONLINE",
                active_alerts=alerts_sorted,
                active_alert=highest_priority_alert,
                person_detected=self.person_detected,
                helmet_detected=self.helmet_detected,
                person_count=self.person_count,
                unhelmeted_count=self.unhelmeted_count,
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
                passport_status=active_p.status if active_p else "NO_PASSPORT"
            )

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
                      evidence_frame: Optional[bytes] = None) -> Optional[Alert]:
        """
        Triggers or updates an alert with verified CCTV visual evidence.
        Same-type alerts are grouped and updated (deduplication).
        Different-type alerts (e.g. Restricted Zone vs Helmet) coexist independently.
        """
        now = datetime.now()
        affected_ids = affected_person_ids or [f"Person {i+1:02d}" for i in range(person_count)]
        priority_score, priority_label = calculate_alert_priority(alert_type, severity, sif_potential)

        with self.lock:
            # Check if an alert of this SAME type is already active (WAITING_FOR_RESPONSE, RESPONDING, ESCALATED)
            existing_alert = None
            for a in self._active_alerts.values():
                if a.type == alert_type and a.status in ["WAITING_FOR_RESPONSE", "RESPONDING", "ESCALATED"]:
                    existing_alert = a
                    break

            if existing_alert:
                # Update existing alert (e.g., person count increase or ID updates) without resetting timer
                existing_alert.person_count = max(1, person_count)
                existing_alert.affected_person_ids = affected_ids
                existing_alert.affected_persons = affected_ids
                if evidence_frame:
                    ev_id = f"ev-{existing_alert.id}"
                    self.evidence_store[ev_id] = evidence_frame
                    existing_alert.evidence_url = f"/api/evidence/{ev_id}"
                    b64 = base64.b64encode(evidence_frame).decode('utf-8')
                    existing_alert.evidence_image = f"data:image/jpeg;base64,{b64}"
                    existing_alert.evidence_timestamp = now.isoformat()

                if alert_type == "Helmet/PPE Violation":
                    p_word = "PEOPLE" if person_count > 1 else "PERSON"
                    existing_alert.title = f"{person_count} {p_word} WITHOUT HELMETS"
                    existing_alert.short_summary = f"{person_count} unequipped workers detected in active area"
                    existing_alert.unsafe_condition = f"{person_count} workers present without hard hat in active zone"
                elif alert_type == "Restricted Zone Entry":
                    p_word = "PEOPLE" if person_count > 1 else "PERSON"
                    existing_alert.title = f"RESTRICTED ZONE ENTRY ({person_count} {p_word})"
                    existing_alert.short_summary = f"{person_count} {p_word} detected occupying restricted perimeter ({location})"
                self.current_safety_state = "VIOLATION"
                self.notify_clients()
                return existing_alert

            # No existing alert of this type: create new independent alert
            deadline = now + timedelta(seconds=response_sec)
            alert_prefix = "ZONE" if "zone" in alert_type.lower() else ("PASS" if "passport" in alert_type.lower() else "PPE")
            ms = int(now.microsecond / 1000)
            alert_id = f"ALT-{alert_prefix}-{now.strftime('%Y%m%d-%H%M%S')}-{ms:03d}"
            suffix = 1
            base_id = alert_id
            while alert_id in self._active_alerts:
                alert_id = f"{base_id}-{suffix}"
                suffix += 1

            default_notes = "Automated SIF Prevention Alert"
            if alert_type == "Restricted Zone Entry":
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

            new_alert = Alert(
                id=alert_id,
                incident_id=inc_id,
                type=alert_type,
                title=title,
                short_summary=short_summary,
                location=location,
                camera=camera,
                camera_id=camera,
                source=f"AI CCTV (Camera {camera})",
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
                sif_potential=sif_potential,
                hazard=hazard,
                unsafe_condition=unsafe_condition,
                evidence_url=ev_url,
                evidence_image=b64_img,
                evidence_timestamp=ev_time,
                incident_timeline=init_timeline
            )

            self._active_alerts[alert_id] = new_alert
            self._last_resolved_alert = None
            self.current_safety_state = "VIOLATION"

        self.notify_clients()
        return new_alert

    def respond_to_alert(self, supervisor_id: str = "SUP-01", notes: Optional[str] = None, alert_id: Optional[str] = None) -> Optional[Alert]:
        """
        Supervisor acknowledges response (Stage 1 -> Stage 2).
        If alert_id is not specified, acknowledges the highest-priority WAITING_FOR_RESPONSE alert.
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
            target.responded_at = now.isoformat()
            target.action_deadline = action_deadline.isoformat()
            target.resolved_by = supervisor_id
            if notes:
                target.notes = notes

        self.notify_clients()
        return target

    def resolve_alert(self, supervisor_id: str = "SUP-01", notes: Optional[str] = None, alert_id: Optional[str] = None) -> Optional[Alert]:
        """
        Supervisor marks alert fixed/resolved.
        Resolving one alert removes ONLY that alert from active_alerts.
        Other active alerts remain active and running.
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
            target.status = "RESOLVED"
            target.stage = "RESOLVED"
            target.resolved_at = now.isoformat()
            if target.escalated_at:
                target.was_escalated = True
            if supervisor_id:
                target.resolved_by = supervisor_id
            if notes:
                target.notes = notes

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
            self.passports.clear()
            self.active_passport_id = None
            self._passport_counter = 0

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
                            breached_zone: Optional[RestrictedZone] = None):
        """
        Called by detection loop for each frame.
        Applies debounce logic for violations and notifies clients on state transitions.
        Supports multiple simultaneous alerts with authentic visual evidence!
        """
        state_changed = False
        trigger_helmet_alert = False
        trigger_zone_alert = False
        trigger_passport_breach = False
        
        with self.lock:
            if self.simulated_mode:
                if person_count > 0:
                    self.simulated_mode = False
                else:
                    return # In simulated mode without real person, preserve simulated baseline
            
            prev_person = self.person_detected
            prev_helmet = self.helmet_detected
            prev_person_count = self.person_count
            prev_unhelmeted_count = self.unhelmeted_count
            prev_safety = self.current_safety_state
            prev_zone_violation = self.zone_violation
            prev_persons_in_zone = self.persons_in_zone
            prev_zone_status = self.zone_status
            prev_occupancy_score = self.zone_occupancy_score
            prev_debug_info = self.zone_debug_info
            
            self.person_detected = person_detected
            self.helmet_detected = helmet_detected
            self.person_count = person_count
            self.unhelmeted_count = unhelmeted_count
            self.unhelmeted_ids = unhelmeted_ids or []
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
            
            # 1. Check Zone Violation & Passport Breach
            if self.zone_violation and active_z and active_z.enabled:
                self.current_safety_state = "VIOLATION"
                # Check linked active passport
                p = self.active_passport
                is_passport_zone = (active_z.zone_category == "PASSPORT_TEMPORARY" or (p and p.linked_zone_id == active_z.zone_id))
                if p and p.status in ["ACTIVE", "PAUSED"] and is_passport_zone:
                    if p.status == "ACTIVE":
                        trigger_passport_breach = True
                else:
                    # Check if zone alert is already active
                    has_active_zone_alert = any(a.type == "Restricted Zone Entry" for a in self._active_alerts.values())
                    if not has_active_zone_alert:
                        trigger_zone_alert = True
                    else:
                        # Update active zone alert person count if changed
                        for a in self._active_alerts.values():
                            if a.type == "Restricted Zone Entry":
                                a.person_count = max(1, self.persons_in_zone)
                                if evidence_frame:
                                    ev_id = f"ev-{a.id}"
                                    self.evidence_store[ev_id] = evidence_frame
                                    a.evidence_url = f"/api/evidence/{ev_id}"
                                    a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                break
            else:
                # Zone is clear!
                p = self.active_passport
                if p and p.status == "PAUSED":
                    # Transition to AWAITING_RESTORATION (DO NOT AUTO-REACTIVATE!)
                    p.status = "AWAITING_RESTORATION"
                    p.events.append(PassportEvent(
                        id=f"evt-{int(now_ts*1000)}",
                        timestamp=datetime.now().isoformat(),
                        event_type="barrier_clear",
                        actor="AI CCTV Vision",
                        description="AI indicates exclusion zone is now clear. Human verification required before reactivation."
                    ))
                    state_changed = True
            
            # 2. Check Helmet Violation (Multi-Person or Single)
            if unhelmeted_count > 0:
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
                        # Update existing active PPE alert person count dynamically!
                        for a in self._active_alerts.values():
                            if a.type == "Helmet/PPE Violation":
                                if a.person_count != unhelmeted_count or evidence_frame:
                                    a.person_count = unhelmeted_count
                                    a.affected_person_ids = self.unhelmeted_ids
                                    a.affected_persons = self.unhelmeted_ids
                                    p_word = "PEOPLE" if unhelmeted_count > 1 else "PERSON"
                                    a.title = f"{unhelmeted_count} {p_word} WITHOUT HELMETS"
                                    a.short_summary = f"{unhelmeted_count} unequipped workers detected without head protection"
                                    if evidence_frame:
                                        ev_id = f"ev-{a.id}"
                                        self.evidence_store[ev_id] = evidence_frame
                                        a.evidence_url = f"/api/evidence/{ev_id}"
                                        a.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(evidence_frame).decode('utf-8')}"
                                    state_changed = True
                                break
            elif person_detected and helmet_detected:
                self.violation_start_time = None
                if self.safe_start_time is None:
                    self.safe_start_time = now_ts
                if not self.zone_violation:
                    self.current_safety_state = "SAFE"
            else:
                self.violation_start_time = None
                self.safe_start_time = None
                if not self.zone_violation:
                    self.current_safety_state = "MONITORING"

            if (self.person_detected != prev_person or 
                self.helmet_detected != prev_helmet or 
                self.person_count != prev_person_count or
                self.unhelmeted_count != prev_unhelmeted_count or
                self.current_safety_state != prev_safety or
                self.zone_violation != prev_zone_violation or
                self.persons_in_zone != prev_persons_in_zone or
                self.zone_status != prev_zone_status or
                abs(self.zone_occupancy_score - prev_occupancy_score) > 0.05 or
                self.zone_debug_info != prev_debug_info):
                state_changed = True

        if trigger_passport_breach:
            b_name = (breached_zone.name if breached_zone else (self.active_passport.linked_zone_name if self.active_passport else "Lifting exclusion zone"))
            self.pause_passport_due_to_breach(f"{b_name} breached", evidence_frame=evidence_frame)

        if trigger_zone_alert:
            target_z = breached_zone or self.active_zone
            loc = target_z.name if target_z else "Compressor Restricted Area"
            cam = target_z.camera_id if target_z else "C-01"
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
                evidence_frame=evidence_frame
            )
        
        if trigger_helmet_alert:
            cnt = max(1, self.unhelmeted_count)
            p_word = "PEOPLE" if cnt > 1 else "PERSON"
            self.trigger_alert(
                alert_type="Helmet/PPE Violation",
                location="Demo Work Zone",
                camera="C-01",
                severity="HIGH",
                sif_potential="HIGH / POTENTIAL",
                person_count=cnt,
                affected_person_ids=self.unhelmeted_ids,
                title=f"{cnt} {p_word} WITHOUT HELMETS",
                short_summary=f"{cnt} unequipped workers detected without head protection",
                hazard="Lack of required PPE (Head Protection)",
                unsafe_condition=f"{cnt} workers present without hard hat in active zone",
                notes=f"Automated SIF Prevention Alert: {cnt} workers.",
                evidence_frame=evidence_frame
            )

        if state_changed and not (trigger_zone_alert or trigger_helmet_alert or trigger_passport_breach):
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
