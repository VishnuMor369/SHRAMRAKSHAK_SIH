from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any

class RestrictedZone(BaseModel):
    zone_id: str = "ZONE-001"
    name: str = "Compressor Restricted Area"
    camera_id: str = "C-01"
    zone_type: str = "floor" # "floor" (Floor/Ground) or "surface" (Surface/Platform)
    zone_category: Literal["PERMANENT", "PASSPORT_TEMPORARY"] = "PERMANENT"
    passport_id: Optional[str] = None
    duration_minutes: Optional[int] = None
    expires_at: Optional[str] = None
    status: Literal["ACTIVE", "INACTIVE", "EXPIRED"] = "ACTIVE"
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    polygon: List[List[float]] = [] # [[x1, y1], [x2, y2], ...] in 640x480 camera space
    enabled: bool = True

class PersonFinding(BaseModel):
    person_id: str = "Person #1"
    track_id: int = 1
    bbox: List[int] = [] # [x1, y1, x2, y2]
    helmet_status: Literal["OK", "VIOLATION", "UNKNOWN"] = "UNKNOWN"
    vest_status: Literal["OK", "VIOLATION", "UNKNOWN"] = "UNKNOWN"
    glove_status: Literal["OK", "VIOLATION", "UNKNOWN"] = "UNKNOWN"
    overall_ppe_status: Literal["OK", "VIOLATION", "UNKNOWN"] = "OK"
    violations: List[str] = [] # e.g. ["NO HELMET", "NO SAFETY VEST"]
    evidence_crop_url: Optional[str] = None
    evidence_crop_base64: Optional[str] = None
    helmet_confidence: float = 0.0
    vest_confidence: float = 0.0
    glove_confidence: float = 0.0
    in_zone: bool = False

class VehicleFinding(BaseModel):
    vehicle_id: str # e.g. "Vehicle #1"
    track_id: int = 1
    class_name: str = "vehicle" # e.g. "truck", "car", "bus", "motorcycle"
    bbox: List[int] = [] # [x1, y1, x2, y2]
    confidence: float = 0.0
    evidence_crop_url: Optional[str] = None
    evidence_crop_base64: Optional[str] = None
    proximity_zone: Optional[List[int]] = None # [zx1, zy1, zx2, zy2]

class Alert(BaseModel):
    id: str
    incident_id: Optional[str] = None # Unique Incident ID e.g. "SR-2026-0042"
    type: str = "Helmet/PPE Violation"
    title: Optional[str] = None
    short_summary: Optional[str] = None
    location: str = "Demo Work Zone"
    camera: str = "C-01"
    camera_id: Optional[str] = "C-01"
    source: str = "AI CCTV (Camera C-01)"
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    priority_score: int = 60
    priority_label: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    status: Literal["IDLE", "WAITING_FOR_RESPONSE", "RESPONDING", "RESOLVED", "ESCALATED"] = "WAITING_FOR_RESPONSE"
    stage: Literal["RESPONSE", "ACTION", "ESCALATED", "RESOLVED"] = "RESPONSE"
    person_count: int = 1
    affected_person_ids: List[str] = []
    affected_persons: List[str] = []
    assigned_to: str = "FIELD SUPERVISOR"
    created_at: str
    response_deadline: str # Stage 1 deadline ISO timestamp
    action_deadline: Optional[str] = None # Stage 2 deadline ISO timestamp
    responded_at: Optional[str] = None
    resolved_at: Optional[str] = None
    escalated_at: Optional[str] = None
    was_escalated: bool = False
    response_duration_sec: int = 20
    action_duration_sec: int = 60
    resolved_by: Optional[str] = None
    notes: Optional[str] = None
    reason: Optional[str] = None

    # ==========================================
    # SIF PRECURSOR INTELLIGENCE & CAUSAL FIELDS
    # ==========================================
    event_id: Optional[str] = None # e.g. "EVT-2026-0042"
    activity: Optional[str] = "General Site Operations"
    hazard: Optional[str] = None
    unsafe_condition: Optional[str] = None
    sif_potential: Optional[str] = "SIF Potential" # Standardized terminology
    sif_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    sif_reason: Optional[str] = None
    sif_why: List[str] = [] # Structured bullet reasons: why SIF potential
    exposure: Optional[str] = None
    critical_barrier: Optional[str] = None
    barrier_condition: Optional[str] = None
    potential_consequence: Optional[str] = None
    life_saving_rule: Optional[str] = None

    # Event-Specific Action Recommendation Layer (Phase 3)
    immediate_action: Optional[str] = None
    consequence_if_not_addressed: Optional[str] = None

    # Corrective Action State Machine (Phase 4)
    # Lifecycle: ASSIGNED -> IN_PROGRESS -> COMPLETED
    action_status: Literal["ASSIGNED", "IN_PROGRESS", "COMPLETED"] = "ASSIGNED"
    action_taken_at: Optional[str] = None
    action_taken_by: Optional[str] = None
    action_taken_notes: Optional[str] = None

    # Verification Lifecycle: PENDING -> AWAITING_VERIFICATION -> VERIFIED / FAILED / HSE_REVIEW_REQUIRED -> HSE_CLOSED
    verification_status: Literal[
        "PENDING", 
        "AWAITING_VERIFICATION", 
        "VERIFIED", 
        "FAILED", 
        "HSE_REVIEW_REQUIRED", 
        "NOT_REQUIRED"
    ] = "PENDING"
    verification_type: Literal["CCTV_VERIFIABLE", "FIELD_HSE_VERIFICATION"] = "CCTV_VERIFIABLE"
    verification_notes: Optional[str] = None
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None

    # Enterprise Safety State Machine Lifecycle (Section 15)
    lifecycle_state: Literal[
        "DETECTED",
        "ANALYZING",
        "SIF_ASSESSED",
        "ACTION_REQUIRED",
        "ACKNOWLEDGED",
        "ACTION_IN_PROGRESS",
        "ACTION_COMPLETED",
        "AWAITING_VERIFICATION",
        "VERIFIED",
        "VERIFICATION_FAILED",
        "REOPENED",
        "RESOLVED"
    ] = "ACTION_REQUIRED"

    # Machine-Generated Safety Observation & Evidence Governance (Section 3 & 16)
    evidence_source_type: Literal["OBSERVED", "INFERRED", "HSE_VALIDATED"] = "OBSERVED"
    machine_observation: Optional[Dict[str, Any]] = None
    corroboration_status: Optional[Literal[
        "CORROBORATED",
        "CCTV_ONLY",
        "HUMAN_REPORT_ONLY",
        "EVIDENCE_CONFLICT",
        "REVIEW_REQUIRED"
    ]] = None
    recurrence_classification: Optional[Literal["DUPLICATE", "INDEPENDENT_RECURRENCE", "RELATED_BUT_DIFFERENT", "REVIEW_REQUIRED"]] = None
    recurring_pattern_title: Optional[str] = None
    independent_occurrences_count: Optional[int] = None
    evidence_spans: List[Dict[str, Any]] = []

    # Visual evidence captured from actual detection frame
    evidence_url: Optional[str] = None
    evidence_image: Optional[str] = None
    evidence_timestamp: Optional[str] = None
    # Extended PPE detection attributes
    violations: List[str] = [] # e.g. ["NO HELMET", "NO SAFETY VEST", "RESTRICTED ZONE"]
    ppe_status: Dict[str, str] = {} # e.g. {"helmet": "VIOLATION", "vest": "VIOLATION", "gloves": "UNKNOWN"}
    person_findings: List[PersonFinding] = [] # Structured findings per tracked worker

    # Person-Vehicle Proximity & Person Crop attributes
    person_id: Optional[str] = None # e.g. "Person #3"
    person_crop_url: Optional[str] = None
    person_crop_base64: Optional[str] = None
    vehicle_id: Optional[str] = None # e.g. "Vehicle #1"
    vehicle_type: Optional[str] = None # e.g. "truck", "forklift", "car"
    vehicle_crop_url: Optional[str] = None
    vehicle_crop_base64: Optional[str] = None
    proximity_status: Optional[str] = None # e.g. "Proximity Confirmed"
    is_high_priority: bool = False
    vehicle_findings: List[VehicleFinding] = []

    # Fire Detection Attributes (Feature 3)
    fire_detected: bool = False
    fire_confidence: Optional[float] = None
    fire_bbox: Optional[List[int]] = None # [x1, y1, x2, y2]
    fire_crop_url: Optional[str] = None
    fire_crop_base64: Optional[str] = None

    # ==========================================
    # HSE OBSERVATION & INCIDENT CORRELATION
    # ==========================================
    worker_identifier: Optional[str] = None # e.g. "W-104"
    hse_observation_text: Optional[str] = None
    hse_observed_hazard: Optional[str] = None
    hse_activity: Optional[str] = None
    hse_location: Optional[str] = None
    hse_notes: Optional[str] = None
    hse_timestamp: Optional[str] = None
    hse_added_by: Optional[str] = None
    
    # NLP Analysis of HSE Observation
    nlp_sif_potential: Optional[bool] = None
    nlp_risk_score: Optional[int] = None
    nlp_risk_level: Optional[str] = None
    nlp_confidence: Optional[int] = None
    nlp_activity: Optional[str] = None
    nlp_hazard: Optional[str] = None
    nlp_location: Optional[str] = None
    nlp_barrier_failure: Optional[str] = None
    nlp_life_saving_rules: List[str] = []
    nlp_precursor: Optional[str] = None
    nlp_reasoning: List[str] = []
    nlp_recommendation: Optional[str] = None

    # Historical Precursor Match against active CSV dataset in dataset_store
    has_historical_match: bool = False
    historical_pattern_title: Optional[str] = None
    historical_occurrence_count: int = 0
    historical_sif_count: int = 0
    historical_sif_density_pct: float = 0.0
    historical_related_lsr: List[str] = []
    historical_related_sites: List[str] = []

    # Incident Evidence Consistency (CCTV vs HSE claim)
    evidence_consistency_status: Literal[
        "CONSISTENT",
        "INCONSISTENCY — HSE REVIEW REQUIRED",
        "INSUFFICIENT CCTV EVIDENCE"
    ] = "INSUFFICIENT CCTV EVIDENCE"
    time_consistency: Optional[str] = None
    location_consistency: Optional[str] = None
    activity_consistency: Optional[str] = None
    worker_presence: Optional[str] = None
    coverage_status: Optional[str] = None
    consistency_details: List[str] = []

    # Chronological Incident Timeline
    incident_timeline: List[Dict[str, Any]] = []

class HSEObservationRequest(BaseModel):
    worker_identifier: Optional[str] = None
    activity: Optional[str] = "Maintenance"
    location: Optional[str] = "Compressor Area"
    hazard: Optional[str] = None
    observation: str
    notes: Optional[str] = None
    reviewer_role: Optional[str] = "HSE Officer"
    linked_alert_id: Optional[str] = None


# ==========================================
# START WORK SAFETY PASSPORT MODELS
# ==========================================

class ControlItem(BaseModel):
    id: str # e.g. "ctrl-1"
    name: str # e.g. "Authorized supervisor assigned"
    verification_source: str # "SUPERVISOR VERIFIED", "SYSTEM VERIFIED", "AI VERIFIED", "AI + SUPERVISOR VERIFIED", "HSE VERIFIED"
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    notes: Optional[str] = None

class PassportEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str # "created", "submitted", "control_verified", "approved", "activated", "paused", "responded", "barrier_clear", "restoration_verified", "reactivated", "escalated", "expired", "closed"
    actor: str # e.g. "Demo Supervisor", "HSE Manager", "AI System"
    description: str

class SafetyPassport(BaseModel):
    id: str # e.g. "SP-20260909-001"
    task_type: str = "Mechanical Lifting"
    location: str = "Demo Lifting Area"
    supervisor: str = "Demo Supervisor"
    camera_id: str = "C-01"
    linked_zone_id: Optional[str] = "ZONE-001"
    linked_zone_name: Optional[str] = "Lifting Exclusion Zone"
    duration_minutes: int = 15
    permit_reference: Optional[str] = "PTW-OIL-2026-8841"
    status: Literal[
        "NOT_CLEARED",
        "PENDING_VERIFICATION",
        "PENDING_APPROVAL",
        "ACTIVE",
        "PAUSED",
        "AWAITING_RESTORATION",
        "EXPIRED",
        "CLOSED"
    ] = "PENDING_VERIFICATION"
    created_by: str = "Demo Supervisor"
    created_at: str
    activated_at: Optional[str] = None
    paused_at: Optional[str] = None
    expires_at: Optional[str] = None
    closed_at: Optional[str] = None
    reactivated_at: Optional[str] = None
    controls: List[ControlItem] = []
    events: List[PassportEvent] = []
    breach_reason: Optional[str] = None
    active_breach_alert_id: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

class CreatePassportRequest(BaseModel):
    task_type: str = "Mechanical Lifting"
    location: str = "Demo Lifting Area"
    supervisor: str = "Demo Supervisor"
    camera_id: str = "C-01"
    linked_zone_id: Optional[str] = "ZONE-001"
    linked_zone_name: Optional[str] = "Lifting Exclusion Zone"
    duration_minutes: int = 15
    permit_reference: Optional[str] = "PTW-OIL-2026-8841"
    created_by: Optional[str] = "Demo Supervisor"
    # Optional temporary zone created directly inside passport creation flow
    temporary_zone: Optional[RestrictedZone] = None
    zone_polygon: Optional[List[List[float]]] = None
    zone_duration_minutes: Optional[int] = None

class VerifyControlRequest(BaseModel):
    control_id: str
    verified: bool = True
    verified_by: Optional[str] = "Demo Supervisor"
    user_role: Optional[str] = "supervisor" # "supervisor" | "hse"
    notes: Optional[str] = None

class ApprovePassportRequest(BaseModel):
    approved_by: Optional[str] = "HSE Manager"
    user_role: Optional[str] = "hse" # "supervisor" | "hse"
    notes: Optional[str] = None

class VerifyRestorationRequest(BaseModel):
    supervisor_id: Optional[str] = "Demo Supervisor"
    user_role: Optional[str] = "supervisor" # "supervisor" | "hse"
    notes: Optional[str] = None

class SystemStatus(BaseModel):
    system_status: str = "ONLINE"
    active_alerts: List[Alert] = []
    active_alert: Optional[Alert] = None
    person_detected: bool = False
    helmet_detected: bool = False
    person_count: int = 0
    unhelmeted_count: int = 0
    vest_detected: bool = False
    unvested_count: int = 0
    gloves_detected: bool = False
    ungloved_count: int = 0
    fire_detected: bool = False
    fire_confidence: float = 0.0
    current_safety_state: Literal["SAFE", "VIOLATION", "MONITORING"] = "MONITORING"
    active_zone: Optional[RestrictedZone] = None
    permanent_zones: List[RestrictedZone] = []
    temporary_zones: List[RestrictedZone] = []
    active_zones: List[RestrictedZone] = []
    zone_violation: bool = False
    zone_status: str = "NO_ZONE" # "CLEAR", "VIOLATION", "NO_ZONE", "LOW_CONFIDENCE"
    persons_in_zone: int = 0
    zone_occupancy_score: float = 0.0
    zone_debug_info: Optional[str] = None
    lan_ip: str = "127.0.0.1"
    supervisor_url: str = "http://127.0.0.1:5173/supervisor"
    camera_active: bool = True
    camera_name: str = "C-01 (Laptop Webcam)"
    timestamp: str
    # Safety Passport integration
    active_passport: Optional[SafetyPassport] = None
    passport_status: Optional[str] = None
    # KPI counts for Clean Dashboard (Phase 6)
    sif_potential_count: int = 0
    open_actions_count: int = 0
    awaiting_verification_count: int = 0
    verified_count: int = 0

class AlertActionRequest(BaseModel):
    alert_id: Optional[str] = None
    supervisor_id: Optional[str] = "SUP-01"
    notes: Optional[str] = None
    action_taken: Optional[str] = None

class AlertVerificationRequest(BaseModel):
    alert_id: Optional[str] = None
    supervisor_id: Optional[str] = "SUP-01"
    decision: Literal["VERIFIED", "FAILED", "HSE_REVIEW_REQUIRED"] = "VERIFIED"
    verification_method: Literal["CCTV_VERIFIED", "PHYSICAL_INSPECTION", "DOCUMENTATION"] = "CCTV_VERIFIED"
    notes: Optional[str] = None

# ==========================================
# AI + NLP SAFETY ANALYSIS MODELS (SIH PS 26165)
# ==========================================

class SafetyReport(BaseModel):
    report_id: str
    alert_id: Optional[str] = None
    source: str = "CCTV SAFETY OBSERVATION"
    event_type: str = "RESTRICTED_ZONE" # RESTRICTED_ZONE, HELMET_VIOLATION, PASSPORT_BREACH
    timestamp: str
    camera_id: str = "C-01"
    location: str = "Demo Work Zone"
    activity: str = "General Operations"
    description: str
    hazard: Optional[str] = None
    energy_source: Optional[str] = None
    exposure: Optional[str] = None
    barrier: Optional[str] = None
    unsafe_act: Optional[str] = None
    unsafe_condition: Optional[str] = None
    barrier_failure: Optional[str] = None
    potential_consequence: Optional[str] = None
    sif_pathway: Optional[str] = None
    sif_potential: bool = False
    risk_score: int = 50 # 0-100 Prototype Priority Score
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    confidence: int = 80 # 0-100
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
    evidence_strength: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
    needs_hse_review: bool = False
    life_saving_rules: List[str] = []
    lsr_evidence: List[Dict[str, Any]] = []
    precursor: Optional[str] = None
    reason: Optional[str] = None
    why_flagged: List[str] = []
    ai_recommendation: Optional[str] = None
    recommended_action: Optional[Dict[str, Any]] = None
    score_breakdown: Optional[Dict[str, int]] = None
    evidence_url: Optional[str] = None
    evidence_image: Optional[str] = None
    is_demo_sample: bool = False
    hse_review: Optional[Dict[str, Any]] = None
    model_version: str = "Hybrid Safety Reasoning v1"
    rule_version: str = "SIF Rules v1"
    validation_note: Optional[str] = "Prototype SIF risk model. Requires validation and calibration against HSE-labelled OIL data before operational use."

class HSEReviewRequest(BaseModel):
    decision: Literal["CONFIRM", "CORRECT", "REJECT"] = "CONFIRM"
    corrected_sif: Optional[bool] = None
    corrected_risk: Optional[int] = None
    corrected_barrier: Optional[str] = None
    corrected_lsr: Optional[str] = None
    corrected_consequence: Optional[str] = None
    reviewer_role: Optional[str] = "HSE Officer"
    notes: Optional[str] = None

class RecurringPattern(BaseModel):
    pattern_id: str
    title: str
    occurrences: int
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    related_lsr: List[str] = []
    related_precursor: str
    location: str
    locations: List[str] = []
    activity: str
    sif_potential_count: int = 0

class AnalysisSummary(BaseModel):
    reports_analyzed: int = 0
    sif_potential_count: int = 0
    sif_percentage: float = 0.0
    risk_distribution: dict = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    top_life_saving_rules: List[dict] = []
    recurring_patterns: List[RecurringPattern] = []
    high_risk_locations: List[dict] = []
    high_risk_activities: List[dict] = []
    data_source_disclaimer: str = (
        "Prototype analysis uses CCTV-generated safety observations. "
        "The same AI/NLP engine is designed to process OIL UA/UC, Near-Miss and Incident reports "
        "when connected to the HSSE data source."
    )

