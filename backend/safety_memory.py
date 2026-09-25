"""
SHRAMRAKSHAK: Safety Memory & Recurring Safety-Control Intelligence
SIH 2026 Problem Statement: SIH26165

CORE STORY:
UNDERSTAND -> REMEMBER -> LEARN -> PREVENT -> VERIFY

Safety Memory is the organizational intelligence layer that transforms individual
safety observations into persistent, reusable safety intelligence.

Key differentiators:
1. Rejection of superficial similarity scores (e.g. avoids "Similarity = 87%")
2. Classification of safety observations into:
   - DUPLICATE (same event; does NOT inflate recurrence count)
   - INDEPENDENT RECURRENCE (independent failure of same underlying control mechanism)
   - RELATED BUT DIFFERENT (shared domain/location, different control mechanism)
   - REVIEW REQUIRED (ambiguous correlation)
3. Formal Governance:
   - System proposes: CANDIDATE RECURRING PATTERN
   - HSE confirms: HSE VALIDATED SAFETY PATTERN
4. Future-Work Safety Learning:
   - Validated patterns become requirements / preconditions for future work packages
   - Flags "REQUIRED SAFETY EVIDENCE MISSING" when critical evidence is absent.
"""

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field


class AssertionStatus(str, Enum):
    ASSERTED = "ASSERTED"
    OBSERVED_FACT = "ASSERTED"
    NEGATED = "NEGATED"
    HYPOTHETICAL = "HYPOTHETICAL"
    POST_EVENT = "POST_EVENT"


class RecurrenceClassification(str, Enum):
    DUPLICATE = "DUPLICATE"
    INDEPENDENT_RECURRENCE = "INDEPENDENT_RECURRENCE"
    RELATED_BUT_DIFFERENT = "RELATED_BUT_DIFFERENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class HSEValidationStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    HSE_VALIDATED = "HSE_VALIDATED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"


class EvidenceSpan(BaseModel):
    text: str
    category: str  # "hazard", "exposure", "barrier", "consequence", "lsr", "assertion"
    start: int
    end: int
    note: Optional[str] = None


class SafetyEvent(BaseModel):
    event_id: str
    incident_id: Optional[str] = None
    source: str = "HUMAN_REPORT"  # "HUMAN_REPORT", "CCTV", "HYBRID"
    evidence_source_type: str = "OBSERVED"  # "OBSERVED", "INFERRED", "HSE_VALIDATED"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    camera_id: Optional[str] = None
    location: str = "General Site Area"
    activity: str = "General Operations"
    hazard: str = "Unspecified Hazard"
    energy_source: str = "Mechanical / Gravitational Energy"
    exposure: str = "Personnel in proximity"
    exposure_assertion: AssertionStatus = AssertionStatus.OBSERVED_FACT
    critical_barrier: str = "Physical Exclusion Barrier"
    barrier_state: str = "VIOLATED"  # "VIOLATED", "COMPROMISED", "ABSENT", "MAINTAINED", "POST_INSTALLATION"
    potential_consequence: str = "Struck-by / Crushing injury"
    consequence_type: str = "POTENTIAL"  # "POTENTIAL", "OBSERVED", "HYPOTHETICAL"
    sif_potential: str = "HIGH"  # "HIGH", "MEDIUM", "LOW", "NOT_SIF"
    life_saving_rule: Optional[str] = "Safe Mechanical Lifting"
    evidence_spans: List[EvidenceSpan] = []
    assertion_status: AssertionStatus = AssertionStatus.OBSERVED_FACT
    temporal_status: str = "DURING_EVENT"  # "DURING_EVENT", "POST_EVENT", "PRE_EVENT"
    confidence: int = 85
    validation_status: HSEValidationStatus = HSEValidationStatus.CANDIDATE
    corroboration_status: Optional[str] = None  # "CORROBORATED", "CCTV_ONLY", "HUMAN_REPORT_ONLY", "EVIDENCE_CONFLICT"
    evidence_url: Optional[str] = None
    evidence_image: Optional[str] = None
    raw_narrative: str = ""
    underlying_control_mechanism: str = "Personnel Segregation / Exclusion-Zone Control"
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None


class RecurringPattern(BaseModel):
    pattern_id: str
    title: str
    underlying_control_mechanism: str
    activity: str
    hazard: str
    critical_barrier: str
    independent_occurrences_count: int = 0
    duplicate_count: int = 0
    event_ids: List[str] = []
    duplicate_event_ids: List[str] = []
    locations: List[str] = []
    top_life_saving_rules: List[str] = []
    validation_status: HSEValidationStatus = HSEValidationStatus.CANDIDATE
    hse_validated_at: Optional[str] = None
    hse_validated_by: Optional[str] = None
    hse_notes: Optional[str] = None
    future_work_precondition: Optional[str] = None
    required_evidence_type: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FutureWorkRequirement(BaseModel):
    requirement_id: str
    derived_from_pattern_id: str
    pattern_title: str
    activity: str
    mandatory_control_precondition: str
    required_safety_evidence: str
    verification_method: str  # "CCTV_CLEARANCE", "PHYSICAL_ZERO_ENERGY", "INDEPENDENT_VERIFICATION"
    hse_validated_date: str
    enforcement_status: str = "ACTIVE_MANDATORY"


class WorkPackageEvaluation(BaseModel):
    package_id: str
    activity: str
    location: str
    planned_time: str
    has_isolation_record: bool = True
    has_physical_verification_evidence: bool = False
    has_exclusion_zone_evidence: bool = False
    status: str = "REQUIRED_SAFETY_EVIDENCE_MISSING"
    missing_evidence_details: List[str] = []
    authorization_review_required: bool = True
    linked_pattern_title: Optional[str] = None


class SafetyMemoryStore:
    """
    In-memory Safety Intelligence & Memory Store.
    Manages historical safety events, classifies recurrence,
    maintains candidate vs validated patterns, and enforces future learning.
    """

    def __init__(self):
        self.events: Dict[str, SafetyEvent] = {}
        self.patterns: Dict[str, RecurringPattern] = {}
        self.future_requirements: Dict[str, FutureWorkRequirement] = {}
        self._seed_baseline_memory()

    def _seed_baseline_memory(self):
        """
        Seeds realistic historical safety memory with OIL-style baseline data.
        Demonstrates 5 independent occurrences of lifting exclusion-zone failures,
        plus baseline candidate patterns, negated examples, and duplicate examples.
        """
        # Baseline Pattern: Lifting Operations Exclusion-Zone Failure
        lifting_pattern = RecurringPattern(
            pattern_id="PAT-LIFT-01",
            title="Lifting Operations: Exclusion-Zone Segregation Failure",
            underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control",
            activity="Mechanical Lifting",
            hazard="Suspended / Moving Crane Load",
            critical_barrier="Lifting Exclusion Zone & Personnel Segregation",
            independent_occurrences_count=5,
            duplicate_count=1,
            event_ids=[
                "EVT-HIST-001",
                "EVT-HIST-002",
                "EVT-HIST-003",
                "EVT-HIST-004",
                "EVT-HIST-005"
            ],
            duplicate_event_ids=["EVT-HIST-001-DUP"],
            locations=["Drilling Rig Floor", "Pipe Yard Beta", "Offloading Bay 2", "Wellhead Sector 4", "Lifting Zone 03"],
            top_life_saving_rules=["Safe Mechanical Lifting", "Line of Fire"],
            validation_status=HSEValidationStatus.CANDIDATE,  # Starts as CANDIDATE for demonstration
            future_work_precondition="Continuous exclusion zone barricade and personnel clearance verified before lift commencement.",
            required_evidence_type="Continuous CCTV / physical barricade clearance confirmation before lift commencement"
        )
        self.patterns[lifting_pattern.pattern_id] = lifting_pattern

        # Add the 5 independent historical events
        hist_events = [
            SafetyEvent(
                event_id="EVT-HIST-001",
                incident_id="SR-2025-0104",
                source="HUMAN_REPORT",
                evidence_source_type="OBSERVED",
                timestamp="2025-04-12T10:15:00",
                location="Drilling Rig Floor",
                activity="Mechanical Lifting",
                hazard="Suspended Drill Collar",
                energy_source="Gravitational / Suspended Load",
                exposure="Roustabout in crane slewing radius",
                critical_barrier="Rig Floor Exclusion Zone",
                barrier_state="VIOLATED",
                potential_consequence="Struck-by / Crushing injury beneath suspended drill collar",
                sif_potential="HIGH",
                life_saving_rule="Safe Mechanical Lifting",
                raw_narrative="Worker crossed crane exclusion zone while drill collar was suspended 1.5m above rotary table.",
                underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
            ),
            SafetyEvent(
                event_id="EVT-HIST-002",
                incident_id="SR-2025-0219",
                source="HUMAN_REPORT",
                evidence_source_type="OBSERVED",
                timestamp="2025-06-20T14:30:00",
                location="Pipe Yard Beta",
                activity="Mechanical Lifting",
                hazard="Overhead Pipe Casing Spool",
                energy_source="Gravitational / Suspended Load",
                exposure="Contractor entered lifting drop area",
                critical_barrier="Drop Zone Perimeter Barricade",
                barrier_state="VIOLATED",
                potential_consequence="Catastrophic crushing from dropped casing bundle",
                sif_potential="HIGH",
                life_saving_rule="Line of Fire",
                raw_narrative="Contractor entered lifting drop area during casing pipe offloading operation.",
                underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
            ),
            SafetyEvent(
                event_id="EVT-HIST-003",
                incident_id="SR-2025-0342",
                source="CCTV",
                evidence_source_type="OBSERVED",
                timestamp="2025-08-11T09:45:00",
                camera_id="C-02",
                location="Offloading Bay 2",
                activity="Mechanical Lifting",
                hazard="Suspended Manifold Skid",
                energy_source="Gravitational / Suspended Load",
                exposure="Personnel observed below suspended load",
                critical_barrier="Physical Exclusion Barricade",
                barrier_state="VIOLATED",
                potential_consequence="Fatal crushing / struck-by trauma",
                sif_potential="HIGH",
                life_saving_rule="Safe Mechanical Lifting",
                raw_narrative="Personnel observed below suspended load while crane hoist was actively maneuvering manifold skid.",
                underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
            ),
            SafetyEvent(
                event_id="EVT-HIST-004",
                incident_id="SR-2025-0455",
                source="HUMAN_REPORT",
                evidence_source_type="OBSERVED",
                timestamp="2025-10-05T16:20:00",
                location="Wellhead Sector 4",
                activity="Mechanical Lifting",
                hazard="Wireline Lubricator Assembly",
                energy_source="Gravitational / Suspended Load",
                exposure="Pedestrian segregation failed during lifting",
                critical_barrier="Segregated Pedestrian Walkway",
                barrier_state="VIOLATED",
                potential_consequence="Severe blunt force impact from swinging lubricator",
                sif_potential="HIGH",
                life_saving_rule="Line of Fire",
                raw_narrative="Pedestrian segregation failed during lifting of lubricator over wellhead cluster.",
                underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
            ),
            SafetyEvent(
                event_id="EVT-HIST-005",
                incident_id="SR-2025-0588",
                source="HUMAN_REPORT",
                evidence_source_type="OBSERVED",
                timestamp="2025-11-18T11:05:00",
                location="Lifting Zone 03",
                activity="Mechanical Lifting",
                hazard="Mobile Crane Counterweight & Boom",
                energy_source="Mechanical / Kinetic Slewing Energy",
                exposure="Helper entered restricted tail-swing zone",
                critical_barrier="Crane Tail-Swing Exclusion Zone",
                barrier_state="VIOLATED",
                potential_consequence="Crushed against barrier by rotating crane counterweight",
                sif_potential="HIGH",
                life_saving_rule="Line of Fire",
                raw_narrative="Helper entered restricted tail-swing zone without banksman visual authorization.",
                underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control"
            ),
            # Duplicate entry (reported by second observer for EVT-HIST-001)
            SafetyEvent(
                event_id="EVT-HIST-001-DUP",
                incident_id="SR-2025-0104-D",
                source="HUMAN_REPORT",
                evidence_source_type="OBSERVED",
                timestamp="2025-04-12T10:22:00",
                location="Drilling Rig Floor",
                activity="Mechanical Lifting",
                hazard="Suspended Drill Collar",
                energy_source="Gravitational / Suspended Load",
                exposure="Roustabout in crane slewing radius",
                critical_barrier="Rig Floor Exclusion Zone",
                barrier_state="VIOLATED",
                potential_consequence="Struck-by / Crushing injury beneath suspended drill collar",
                sif_potential="HIGH",
                life_saving_rule="Safe Mechanical Lifting",
                raw_narrative="Worker crossed crane exclusion zone while drill collar was suspended 1.5m above rotary table.",
                underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control",
                is_duplicate=True,
                duplicate_of="EVT-HIST-001"
            )
        ]

        for ev in hist_events:
            self.events[ev.event_id] = ev

        # Baseline Pattern 2: Energy Isolation Verification Deficiencies
        isolation_pattern = RecurringPattern(
            pattern_id="PAT-LOTO-02",
            title="Energy Isolation: Physical Zero-Energy Verification Absence",
            underlying_control_mechanism="Positive Energy Isolation & Zero-Energy State Verification",
            activity="Energy Isolation",
            hazard="Stored High-Pressure Hydrocarbon & Electrical Feed",
            critical_barrier="Lockout-Tagout (LOTO) & Physical Bleed/Try Step",
            independent_occurrences_count=4,
            duplicate_count=0,
            event_ids=["EVT-HIST-010", "EVT-HIST-011", "EVT-HIST-012", "EVT-HIST-013"],
            locations=["Compressor Station 1", "Separator Train B", "Booster Pump House", "Main Substation"],
            top_life_saving_rules=["Energy Isolation"],
            validation_status=HSEValidationStatus.HSE_VALIDATED,  # Already HSE validated to demonstrate future work requirements
            hse_validated_at="2025-11-20T16:00:00",
            hse_validated_by="HSE Manager (Duliajan HQ)",
            hse_notes="Validated based on repeated audits showing failure to perform physical 'try' step before unbolting flanges.",
            future_work_precondition="Mandatory physical try step, independent second-person verification, and signed zero-energy cert.",
            required_evidence_type="Signed zero-energy cert with physical manometer bleed reading and calibrated detector photo"
        )
        self.patterns[isolation_pattern.pattern_id] = isolation_pattern

        # Generate future work requirement for the already-validated LOTO pattern
        req_loto = FutureWorkRequirement(
            requirement_id="REQ-LOTO-001",
            derived_from_pattern_id=isolation_pattern.pattern_id,
            pattern_title=isolation_pattern.title,
            activity=isolation_pattern.activity,
            mandatory_control_precondition=isolation_pattern.future_work_precondition,
            required_safety_evidence=isolation_pattern.required_evidence_type,
            verification_method="PHYSICAL_ZERO_ENERGY",
            hse_validated_date="2025-11-20",
            enforcement_status="ACTIVE_MANDATORY"
        )
        self.future_requirements[req_loto.requirement_id] = req_loto

    def classify_recurrence(self, event: SafetyEvent) -> Tuple[RecurrenceClassification, Optional[RecurringPattern], Optional[str]]:
        """
        Determines whether a new safety observation represents:
        1. DUPLICATE: Same event reported again (identical text or same location+activity within 30 min)
        2. INDEPENDENT RECURRENCE: Independent occurrence of the same underlying control mechanism
        3. RELATED BUT DIFFERENT: Same domain/activity, different control failure
        4. REVIEW REQUIRED: Insufficient context / borderline correlation
        """
        norm_narrative = re.sub(r"\s+", " ", event.raw_narrative.strip().lower())

        # 1. Duplicate Check
        for existing_id, existing_ev in self.events.items():
            if existing_id == event.event_id:
                continue
            exist_norm = re.sub(r"\s+", " ", existing_ev.raw_narrative.strip().lower())
            
            # Exact or near-exact narrative match
            if norm_narrative and exist_norm and norm_narrative == exist_norm:
                return RecurrenceClassification.DUPLICATE, None, existing_id
            
            # Same location, activity, barrier, and within 30 minutes
            if (event.location == existing_ev.location and 
                event.activity == existing_ev.activity and 
                event.critical_barrier == existing_ev.critical_barrier):
                try:
                    t1 = datetime.fromisoformat(event.timestamp)
                    t2 = datetime.fromisoformat(existing_ev.timestamp)
                    if abs((t1 - t2).total_seconds()) < 1800:
                        return RecurrenceClassification.DUPLICATE, None, existing_id
                except Exception:
                    pass

        # 2. Check for Independent Recurrence against existing Control Patterns
        event_mechanism = event.underlying_control_mechanism.lower()
        event_activity = event.activity.lower()

        # Specific lifting exclusion zone keywords
        is_lifting_exclusion = (
            ("lifting" in event_activity or "crane" in event.raw_narrative.lower() or "suspended" in event.raw_narrative.lower()) and
            ("exclusion" in event.raw_narrative.lower() or "drop zone" in event.raw_narrative.lower() or 
             "segregation" in event.raw_narrative.lower() or "zone" in event.critical_barrier.lower() or
             "restricted" in event.raw_narrative.lower())
        )

        for pat in self.patterns.values():
            pat_mechanism = pat.underlying_control_mechanism.lower()
            pat_activity = pat.activity.lower()

            if is_lifting_exclusion and "lifting" in pat_activity and "segregation" in pat_mechanism:
                return RecurrenceClassification.INDEPENDENT_RECURRENCE, pat, None

            if event_mechanism and pat_mechanism and (event_mechanism == pat_mechanism or pat_mechanism in event_mechanism):
                return RecurrenceClassification.INDEPENDENT_RECURRENCE, pat, None

        # 3. Check for Related But Different (shared activity or location)
        for pat in self.patterns.values():
            if pat.activity.lower() == event_activity or event.location in pat.locations:
                return RecurrenceClassification.RELATED_BUT_DIFFERENT, pat, None

        return RecurrenceClassification.REVIEW_REQUIRED, None, None

    def record_safety_event(self, event: SafetyEvent) -> Dict[str, Any]:
        """
        Ingests a safety event into Safety Memory, performs recurrence classification,
        updates patterns, and links evidence.
        """
        classification, matched_pattern, duplicate_of_id = self.classify_recurrence(event)

        if classification == RecurrenceClassification.DUPLICATE:
            event.is_duplicate = True
            event.duplicate_of = duplicate_of_id
            self.events[event.event_id] = event
            if matched_pattern:
                matched_pattern.duplicate_count += 1
                matched_pattern.duplicate_event_ids.append(event.event_id)
            return {
                "event_id": event.event_id,
                "classification": "DUPLICATE",
                "message": f"Identified as duplicate of {duplicate_of_id}. Recurrence count not inflated.",
                "pattern": matched_pattern,
                "independent_count": matched_pattern.independent_occurrences_count if matched_pattern else 0
            }

        elif classification == RecurrenceClassification.INDEPENDENT_RECURRENCE and matched_pattern:
            event.is_duplicate = False
            self.events[event.event_id] = event
            
            # Increment independent occurrences
            matched_pattern.independent_occurrences_count += 1
            matched_pattern.event_ids.append(event.event_id)
            if event.location not in matched_pattern.locations:
                matched_pattern.locations.append(event.location)
            if event.life_saving_rule and event.life_saving_rule not in matched_pattern.top_life_saving_rules:
                matched_pattern.top_life_saving_rules.append(event.life_saving_rule)

            return {
                "event_id": event.event_id,
                "classification": "INDEPENDENT_RECURRENCE",
                "message": f"Independent occurrence of recurring control failure. Recurrence updated: {matched_pattern.independent_occurrences_count} independent occurrences.",
                "pattern": matched_pattern,
                "independent_count": matched_pattern.independent_occurrences_count
            }

        else:
            event.is_duplicate = False
            self.events[event.event_id] = event
            return {
                "event_id": event.event_id,
                "classification": classification.value,
                "message": f"Recorded in Safety Memory under classification '{classification.value}'.",
                "pattern": matched_pattern,
                "independent_count": matched_pattern.independent_occurrences_count if matched_pattern else 1
            }

    def validate_pattern(self, pattern_id: str, decision: str, reviewer: str = "HSE Manager", notes: Optional[str] = None) -> Optional[RecurringPattern]:
        """
        HSE Governance Layer:
        Validates, rejects, or corrects a Candidate Recurring Pattern.
        When confirmed, automatically derives future-work safety requirements.
        """
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            return None

        now_iso = datetime.now().isoformat()
        if decision.upper() == "CONFIRM":
            pattern.validation_status = HSEValidationStatus.HSE_VALIDATED
            pattern.hse_validated_at = now_iso
            pattern.hse_validated_by = reviewer
            pattern.hse_notes = notes or "Pattern confirmed by HSE based on verified historical control failures."

            # Automatically establish future-work requirement
            req_id = f"REQ-{pattern.activity[:4].upper()}-{int(datetime.now().timestamp()) % 10000:04d}"
            req = FutureWorkRequirement(
                requirement_id=req_id,
                derived_from_pattern_id=pattern.pattern_id,
                pattern_title=pattern.title,
                activity=pattern.activity,
                mandatory_control_precondition=pattern.future_work_precondition or f"Mandatory continuous verification of {pattern.critical_barrier}.",
                required_safety_evidence=pattern.required_evidence_type or f"Verified clearance record for {pattern.critical_barrier}.",
                verification_method="CCTV_CLEARANCE" if "Lifting" in pattern.activity else "PHYSICAL_ZERO_ENERGY",
                hse_validated_date=datetime.now().strftime("%Y-%m-%d"),
                enforcement_status="ACTIVE_MANDATORY"
            )
            self.future_requirements[req_id] = req

        elif decision.upper() == "REJECT":
            pattern.validation_status = HSEValidationStatus.REJECTED
            pattern.hse_validated_at = now_iso
            pattern.hse_validated_by = reviewer
            pattern.hse_notes = notes or "Pattern rejected by HSE as isolated non-systemic event."

        elif decision.upper() == "CORRECT":
            pattern.validation_status = HSEValidationStatus.CORRECTED
            pattern.hse_validated_at = now_iso
            pattern.hse_validated_by = reviewer
            pattern.hse_notes = notes or "Pattern scope corrected by HSE."

        return pattern

    def check_work_package(self, package: Dict[str, Any]) -> WorkPackageEvaluation:
        """
        Evaluates a future work package against HSE Validated Safety Patterns and requirements.
        If required evidence is missing, returns "REQUIRED_SAFETY_EVIDENCE_MISSING".
        """
        pkg_id = package.get("package_id", f"WP-2026-{uuid.uuid4().hex[:6].upper()}")
        activity = package.get("activity", "Mechanical Lifting")
        location = package.get("location", "Lifting Zone 03")
        planned_time = package.get("planned_time", datetime.now().isoformat())

        has_iso = package.get("has_isolation_record", True)
        has_phys_verif = package.get("has_physical_verification_evidence", False)
        has_exclusion_ev = package.get("has_exclusion_zone_evidence", False)

        missing = []
        linked_pattern = None

        if "lifting" in activity.lower():
            # Check lifting exclusion requirements
            linked_pattern = "Lifting Operations: Exclusion-Zone Segregation Failure"
            if not has_exclusion_ev:
                missing.append("Active CCTV / physical exclusion zone clearance evidence not verified prior to lift")
                missing.append("Pre-lift exclusion zone boundary confirmation missing from supervisor package")

        if "isolation" in activity.lower() or "loto" in activity.lower():
            linked_pattern = "Energy Isolation: Physical Zero-Energy Verification Absence"
            if not has_phys_verif:
                missing.append("Physical manometer bleed reading / physical try verification evidence missing")
                missing.append("Independent second-person verification signature absent")

        is_missing = len(missing) > 0
        return WorkPackageEvaluation(
            package_id=pkg_id,
            activity=activity,
            location=location,
            planned_time=planned_time,
            has_isolation_record=has_iso,
            has_physical_verification_evidence=has_phys_verif,
            has_exclusion_zone_evidence=has_exclusion_ev,
            status="REQUIRED_SAFETY_EVIDENCE_MISSING" if is_missing else "EVIDENCE_VERIFIED_CLEAR",
            missing_evidence_details=missing,
            authorization_review_required=is_missing,
            linked_pattern_title=linked_pattern
        )

    def get_summary(self) -> Dict[str, Any]:
        """Returns consolidated Safety Memory status for UI overview."""
        patterns_list = list(self.patterns.values())
        validated_count = sum(1 for p in patterns_list if p.validation_status == HSEValidationStatus.HSE_VALIDATED)
        candidate_count = sum(1 for p in patterns_list if p.validation_status == HSEValidationStatus.CANDIDATE)

        return {
            "total_events_in_memory": len(self.events),
            "total_patterns": len(patterns_list),
            "candidate_patterns": candidate_count,
            "hse_validated_patterns": validated_count,
            "future_work_requirements": len(self.future_requirements),
            "patterns": [p.dict() for p in sorted(patterns_list, key=lambda x: x.independent_occurrences_count, reverse=True)],
            "future_requirements": [r.dict() for r in self.future_requirements.values()]
        }

    def reset(self):
        """Cleanly resets Safety Memory to default baseline state."""
        self.events.clear()
        self.patterns.clear()
        self.future_requirements.clear()
        self._seed_baseline_memory()


# Global Singleton Safety Memory Store
safety_memory = SafetyMemoryStore()
