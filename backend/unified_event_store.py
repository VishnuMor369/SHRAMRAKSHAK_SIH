"""
SHRAMRAKSHAK: Canonical Unified Safety Event Model & Store
SIH 2026 Problem Statement: SIH26165

Unifies HUMAN REPORTS, IMPORTED COMPANY DATA, and CCTV MACHINE OBSERVATIONS
into ONE underlying canonical SafetyEvent data structure.

Every event conforms to the core pipeline:
UNDERSTAND -> REMEMBER -> LEARN -> PREVENT -> VERIFY
"""

import os
import json
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

try:
    from backend.database import db
    from backend.models_canonical import SafetyEvent as CanonicalSafetyEvent, SIFStatus
except ImportError:
    try:
        from database import db
        from models_canonical import SafetyEvent as CanonicalSafetyEvent, SIFStatus
    except ImportError:
        from .database import db
        from .models_canonical import SafetyEvent as CanonicalSafetyEvent, SIFStatus

# Ensure data directory exists
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
EVENTS_FILE = os.path.join(DATA_DIR, "safety_events.json")


class SafetyEvent(BaseModel):
    """
    Canonical Unified Safety Event Schema (Phase 1).
    All Human Reports, Imported Records, and CCTV Observations conform to this.
    """
    event_id: str
    source: str = "HUMAN"  # "HUMAN" | "IMPORTED" | "CCTV"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    location: str = "OIL Site Operations"
    activity: str = "General Industrial Operations"
    narrative: str = ""
    hazard: str = "Mechanical / Gravitational Hazard"
    exposure: str = "Personnel inside line-of-fire boundary"
    critical_barrier: str = "Physical Exclusion Barrier / Barricade"
    barrier_condition: str = "VIOLATED"  # "VIOLATED" | "INEFFECTIVE" | "ABSENT" | "INTACT" | "POST_EVENT_REMEDY"
    consequence: str = "Severe blunt impact or crush trauma"
    sif_potential: str = "HIGH"  # "HIGH" | "MEDIUM" | "LOW" | "NOT_SIF"
    lsr: Optional[str] = "Line of Fire / Safe Mechanical Lifting"
    assertion_status: str = "ASSERTED"  # "ASSERTED" | "NEGATED" | "HYPOTHETICAL" | "POST_EVENT"
    temporal_status: str = "CURRENT"  # "CURRENT" | "POST_EVENT" | "PRE_EVENT" | "HYPOTHETICAL"
    evidence_spans: List[Dict[str, Any]] = []
    evidence_sources: List[str] = ["HUMAN_REPORT"]  # ["HUMAN_REPORT", "CCTV", "DOCUMENT", "HSE_VALIDATION", "SYSTEM_INFERENCE"]
    recurrence_classification: Optional[str] = "INDEPENDENT_RECURRENCE"  # "INDEPENDENT_RECURRENCE" | "DUPLICATE" | "RELATED_BUT_DIFFERENT"
    corroboration_status: Optional[str] = None  # "CORROBORATED" | "CCTV_ONLY" | "HUMAN_REPORT_ONLY" | "EVIDENCE_CONFLICT"
    lifecycle_state: str = "DETECTED"  # "DETECTED", "ANALYZING", "SIF_ASSESSED", "ACTION_REQUIRED", "ACTION_IN_PROGRESS", "AWAITING_VERIFICATION", "VERIFIED", "VERIFICATION_FAILED", "REOPENED", "RESOLVED"
    machine_observation: bool = False
    camera_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class UnifiedEventStore:
    """
    Thread-safe, persistent, unified repository for all Safety Events.
    Maintains index by ID, timestamp ordering, and calculates dynamic metrics.
    """

    def __init__(self, persistence_file: str = EVENTS_FILE):
        self._lock = threading.RLock()
        self.persistence_file = persistence_file
        self.events: Dict[str, SafetyEvent] = {}
        self.ordered_ids: List[str] = []
        self._load_from_disk()

    def _load_from_disk(self):
        """Loads events from disk cache or seeds realistic OIL historical baseline."""
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        ev = SafetyEvent(**item)
                        self.events[ev.event_id] = ev
                        if ev.event_id not in self.ordered_ids:
                            self.ordered_ids.append(ev.event_id)
                print(f"[UnifiedEventStore] Loaded {len(self.events)} events from disk.")
                return
            except Exception as e:
                print(f"[UnifiedEventStore] Warning loading disk cache: {e}. Seeding baseline.")

        self.seed_baseline_events()

    def _save_to_disk(self):
        """Saves current state to JSON file safely."""
        try:
            payload = [self.events[eid].to_dict() for eid in self.ordered_ids if eid in self.events]
            serialized = json.dumps(payload, indent=2)
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                f.write(serialized)
                f.flush()
        except Exception as e:
            print(f"[UnifiedEventStore] Error persisting to disk: {e}")

    def seed_baseline_events(self):
        """Seeds realistic historical OIL-style baseline safety events."""
        with self._lock:
            self.events.clear()
            self.ordered_ids.clear()

            baseline = [
                SafetyEvent(
                    event_id="EVT-OIL-2026-001",
                    source="HUMAN",
                    timestamp="2026-09-24T10:14:00",
                    location="Drilling Rig 04 - Drill Floor",
                    activity="Mechanical Lifting Operations",
                    narrative="Worker crossed red barricade tape into crane exclusion zone while drill collar was suspended 2m overhead.",
                    hazard="Suspended 15T Drill Collar",
                    exposure="Roustabout inside lifting radius",
                    critical_barrier="Lifting Exclusion Zone & Segregation",
                    barrier_condition="VIOLATED",
                    consequence="Fatal crush or severe blunt impact trauma",
                    sif_potential="HIGH",
                    lsr="Line of Fire / Safe Mechanical Lifting",
                    assertion_status="ASSERTED",
                    temporal_status="CURRENT",
                    evidence_spans=[
                        {"category": "HAZARD", "span_text": "drill collar was suspended 2m overhead", "start_char": 56, "end_char": 96},
                        {"category": "EXPOSURE", "span_text": "Worker crossed red barricade tape into crane exclusion zone", "start_char": 0, "end_char": 59},
                        {"category": "BARRIER", "span_text": "red barricade tape into crane exclusion zone", "start_char": 15, "end_char": 59}
                    ],
                    evidence_sources=["HUMAN_REPORT"],
                    recurrence_classification="INDEPENDENT_RECURRENCE",
                    lifecycle_state="RESOLVED"
                ),
                SafetyEvent(
                    event_id="EVT-OIL-2026-002",
                    source="HUMAN",
                    timestamp="2026-09-24T11:30:00",
                    location="Pipe Yard 02",
                    activity="Tubular Pipe Handling",
                    narrative="No worker entered the exclusion zone during pipe offloading operation. Perimeter remained clear.",
                    hazard="Moving Mobile Crane Boom",
                    exposure="NEGATED (No worker entry)",
                    critical_barrier="Physical Hard Barricading",
                    barrier_condition="INTACT",
                    consequence="None - safety perimeter held intact",
                    sif_potential="NOT_SIF",
                    lsr="Work Authorization",
                    assertion_status="NEGATED",
                    temporal_status="CURRENT",
                    evidence_spans=[
                        {"category": "ASSERTION", "span_text": "No worker entered", "start_char": 0, "end_char": 17},
                        {"category": "BARRIER", "span_text": "exclusion zone", "start_char": 22, "end_char": 36}
                    ],
                    evidence_sources=["HUMAN_REPORT"],
                    recurrence_classification="RELATED_BUT_DIFFERENT",
                    lifecycle_state="RESOLVED"
                ),
                SafetyEvent(
                    event_id="EVT-OIL-2026-003",
                    source="HUMAN",
                    timestamp="2026-09-24T14:15:00",
                    location="Wellhead 08 - Manifold Area",
                    activity="Rigging and Crane Hoisting",
                    narrative="If the sling fails, the suspended load could fall into the active wellhead manifold area.",
                    hazard="Potential Dropped Object",
                    exposure="Hypothetical line-of-fire exposure",
                    critical_barrier="Certified Webbing Sling",
                    barrier_condition="INTACT",
                    consequence="Hypothetical high-pressure release and equipment damage",
                    sif_potential="LOW",
                    lsr="Line of Fire",
                    assertion_status="HYPOTHETICAL",
                    temporal_status="HYPOTHETICAL",
                    evidence_spans=[
                        {"category": "ASSERTION", "span_text": "If the sling fails", "start_char": 0, "end_char": 18},
                        {"category": "CONSEQUENCE", "span_text": "suspended load could fall", "start_char": 24, "end_char": 49}
                    ],
                    evidence_sources=["HUMAN_REPORT"],
                    recurrence_classification="RELATED_BUT_DIFFERENT",
                    lifecycle_state="RESOLVED"
                ),
                SafetyEvent(
                    event_id="EVT-OIL-2026-004",
                    source="HUMAN",
                    timestamp="2026-09-24T16:45:00",
                    location="Compressor Station 01",
                    activity="High-Pressure Gas Line Maintenance",
                    narrative="Maintenance commenced on discharge manifold without verified zero-energy bleed or physical isolation lock applied.",
                    hazard="Flammable Pressurized Gas",
                    exposure="Maintenance technician at valve flange",
                    critical_barrier="LOTO / Positive Isolation Verification",
                    barrier_condition="INEFFECTIVE",
                    consequence="High-pressure gas explosion or toxic release",
                    sif_potential="HIGH",
                    lsr="Energy Isolation (LOTO)",
                    assertion_status="ASSERTED",
                    temporal_status="CURRENT",
                    evidence_spans=[
                        {"category": "HAZARD", "span_text": "discharge manifold", "start_char": 25, "end_char": 43},
                        {"category": "BARRIER", "span_text": "without verified zero-energy bleed or physical isolation lock", "start_char": 44, "end_char": 105}
                    ],
                    evidence_sources=["HUMAN_REPORT"],
                    recurrence_classification="INDEPENDENT_RECURRENCE",
                    lifecycle_state="RESOLVED"
                ),
                SafetyEvent(
                    event_id="EVT-OIL-2026-005",
                    source="HUMAN",
                    timestamp="2026-09-25T08:20:00",
                    location="Substation B - Switchgear Room",
                    activity="Electrical Control Panel Overhaul",
                    narrative="Danger barricade was installed after the incident occurred. Breaker was found unlocked during earlier shift inspection.",
                    hazard="415V Energized Busbars",
                    exposure="Post-incident barrier installation",
                    critical_barrier="Safety Lockout Hasps & Padlocks",
                    barrier_condition="POST_EVENT_REMEDY",
                    consequence="Historical arc flash potential rectified retrospectively",
                    sif_potential="MEDIUM",
                    lsr="Energy Isolation",
                    assertion_status="POST_EVENT",
                    temporal_status="POST_EVENT",
                    evidence_spans=[
                        {"category": "ASSERTION", "span_text": "installed after the incident occurred", "start_char": 22, "end_char": 59},
                        {"category": "BARRIER", "span_text": "Breaker was found unlocked", "start_char": 61, "end_char": 87}
                    ],
                    evidence_sources=["HUMAN_REPORT"],
                    recurrence_classification="RELATED_BUT_DIFFERENT",
                    lifecycle_state="RESOLVED"
                ),
                SafetyEvent(
                    event_id="EVT-CCTV-2026-001",
                    source="CCTV",
                    timestamp="2026-09-25T10:42:18",
                    location="Lifting Zone 03",
                    activity="Mechanical Crane Hoisting",
                    narrative="Machine-Generated Safety Observation: Worker detected inside restricted lifting exclusion zone for 5 consecutive frames.",
                    hazard="Suspended 10T Mud Motor",
                    exposure="Person bottom-center inside exclusion polygon",
                    critical_barrier="CCTV Defined Exclusion Zone",
                    barrier_condition="VIOLATED",
                    consequence="Fatal crush trauma under suspended load",
                    sif_potential="HIGH",
                    lsr="Line of Fire / Safe Mechanical Lifting",
                    assertion_status="ASSERTED",
                    temporal_status="CURRENT",
                    evidence_spans=[
                        {"category": "EXPOSURE", "span_text": "Worker detected inside restricted lifting exclusion zone", "start_char": 38, "end_char": 94},
                        {"category": "BARRIER", "span_text": "restricted lifting exclusion zone", "start_char": 61, "end_char": 94}
                    ],
                    evidence_sources=["CCTV"],
                    recurrence_classification="INDEPENDENT_RECURRENCE",
                    corroboration_status="CCTV_ONLY",
                    lifecycle_state="ACTION_REQUIRED",
                    machine_observation=True,
                    camera_id="C-01"
                )
            ]

            for ev in baseline:
                self.events[ev.event_id] = ev
                self.ordered_ids.append(ev.event_id)

            self._save_to_disk()

    def add_event(self, event: SafetyEvent) -> SafetyEvent:
        """Adds a new SafetyEvent to the store and persists to disk."""
        with self._lock:
            # Ensure unique ID
            if not event.event_id:
                prefix = "EVT-HUMAN" if event.source == "HUMAN" else ("EVT-CCTV" if event.source == "CCTV" else "EVT-IMP")
                event.event_id = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

            event.updated_at = datetime.now().isoformat()
            self.events[event.event_id] = event
            if event.event_id in self.ordered_ids:
                self.ordered_ids.remove(event.event_id)
            self.ordered_ids.insert(0, event.event_id)  # Prepend newest

            self._save_to_disk()
            return event

    def get_event(self, event_id: str) -> Optional[SafetyEvent]:
        """Returns single event by ID."""
        with self._lock:
            self._sync_with_db()
            return self.events.get(event_id)

    def _sync_with_db(self):
        """Pulls events from persistent SQLite database so dataset and human records are always live."""
        try:
            db_events = db.list_events(limit=500)
            for dbe in db_events:
                if dbe.event_id not in self.events:
                    sif_p = "NOT_SIF"
                    sif_status_str = dbe.sif_status.value if hasattr(dbe.sif_status, "value") else str(dbe.sif_status)
                    if dbe.sif_status == SIFStatus.SIF_POTENTIAL or sif_status_str == "SIF-POTENTIAL":
                        sif_p = "HIGH"
                    elif dbe.sif_status == SIFStatus.REVIEW_REQUIRED or sif_status_str == "REVIEW_REQUIRED":
                        sif_p = "MEDIUM"

                    ev = SafetyEvent(
                        event_id=dbe.event_id,
                        source=dbe.source or "IMPORTED",
                        timestamp=dbe.timestamp,
                        location=dbe.location or "Site Area",
                        activity=dbe.activity or "Operational Work",
                        narrative=dbe.narrative or "",
                        hazard=dbe.energy or "Energy Hazard",
                        exposure=dbe.exposure or "Worker Interaction",
                        critical_barrier=", ".join(dbe.barrier) if dbe.barrier else "Safety Barrier",
                        barrier_condition=", ".join(dbe.barrier_state) if dbe.barrier_state else "UNKNOWN",
                        consequence=dbe.consequence or "Industrial trauma",
                        sif_potential=sif_p,
                        lsr=", ".join(dbe.lsr) if dbe.lsr else "General Operational Safety",
                        assertion_status=dbe.assertion.value if hasattr(dbe.assertion, "value") else str(dbe.assertion),
                        temporal_status=dbe.temporal_status.value if hasattr(dbe.temporal_status, "value") else str(dbe.temporal_status),
                        evidence_spans=[s.to_dict() if hasattr(s, "to_dict") else s for s in dbe.evidence],
                        evidence_sources=[dbe.source or "DATASET"],
                        recurrence_classification="INDEPENDENT_RECURRENCE",
                        lifecycle_state=dbe.lifecycle_state or "DETECTED",
                        machine_observation=dbe.machine_observation,
                        metadata=dbe.provenance or {}
                    )
                    self.events[ev.event_id] = ev
                    if ev.event_id not in self.ordered_ids:
                        self.ordered_ids.append(ev.event_id)
        except Exception:
            pass

    def get_events(
        self,
        source: Optional[str] = None,
        sif_status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Returns filtered, paginated events."""
        with self._lock:
            self._sync_with_db()
            filtered = [self.events[eid] for eid in self.ordered_ids if eid in self.events]

            if source and source != "ALL":
                filtered = [e for e in filtered if e.source.upper() == source.upper()]

            if sif_status and sif_status != "ALL":
                filtered = [e for e in filtered if e.sif_potential.upper() == sif_status.upper()]

            if search:
                q = search.lower()
                filtered = [
                    e for e in filtered
                    if q in e.narrative.lower()
                    or q in e.location.lower()
                    or q in e.activity.lower()
                    or q in e.hazard.lower()
                    or q in e.event_id.lower()
                ]

            total = len(filtered)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            items = [e.to_dict() for e in filtered[start_idx:end_idx]]

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1,
                "events": items
            }

    def update_lifecycle(
        self,
        event_id: str,
        new_state: str,
        verified_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[SafetyEvent]:
        """Updates event lifecycle state and timestamps."""
        with self._lock:
            ev = self.events.get(event_id)
            if not ev:
                return None

            ev.lifecycle_state = new_state
            ev.updated_at = datetime.now().isoformat()
            if verified_by:
                ev.metadata["verified_by"] = verified_by
            if notes:
                ev.metadata["verification_notes"] = notes

            self._save_to_disk()
            return ev

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Dynamically computes all high-level SIF intelligence metrics from real stored events.
        NEVER returns hardcoded counts!
        """
        with self._lock:
            self._sync_with_db()
            all_events = list(self.events.values())
            total = len(all_events)

            sif_high = sum(1 for e in all_events if e.sif_potential in ["HIGH", "CRITICAL / HIGH"])
            sif_medium = sum(1 for e in all_events if e.sif_potential == "MEDIUM")
            sif_low = sum(1 for e in all_events if e.sif_potential == "LOW")
            not_sif = sum(1 for e in all_events if e.sif_potential in ["NOT_SIF", "NONE"])

            human_count = sum(1 for e in all_events if e.source == "HUMAN")
            imported_count = sum(1 for e in all_events if e.source == "IMPORTED")
            cctv_count = sum(1 for e in all_events if e.source == "CCTV")

            awaiting_verification = sum(1 for e in all_events if e.lifecycle_state == "AWAITING_VERIFICATION")
            action_required = sum(1 for e in all_events if e.lifecycle_state in ["ACTION_REQUIRED", "DETECTED"])
            action_in_progress = sum(1 for e in all_events if e.lifecycle_state == "ACTION_IN_PROGRESS")
            verified_count = sum(1 for e in all_events if e.lifecycle_state in ["VERIFIED", "RESOLVED"])

            # Top hazards
            hazard_counts: Dict[str, int] = {}
            for e in all_events:
                hz = e.hazard or "Unspecified"
                hazard_counts[hz] = hazard_counts.get(hz, 0) + 1
            top_hazards = [{"hazard": k, "name": k, "count": v} for k, v in sorted(hazard_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

            # Top Life-Saving Rules
            lsr_counts: Dict[str, int] = {}
            for e in all_events:
                rule = e.lsr or "General Safety"
                lsr_counts[rule] = lsr_counts.get(rule, 0) + 1
            top_lsrs = [{"rule": k, "name": k, "count": v} for k, v in sorted(lsr_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

            # Top Activities
            activity_counts: Dict[str, int] = {}
            for e in all_events:
                act = e.activity or "Operations"
                activity_counts[act] = activity_counts.get(act, 0) + 1
            top_activities = [{"activity": k, "name": k, "count": v} for k, v in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

            # Top Failed Critical Barriers
            barrier_counts: Dict[str, int] = {}
            for e in all_events:
                if e.barrier_condition in ["VIOLATED", "INEFFECTIVE", "ABSENT", "COMPROMISED / BREACHED", "BYPASSED", "FAILED"]:
                    bar = e.critical_barrier or "Barrier"
                    barrier_counts[bar] = barrier_counts.get(bar, 0) + 1
            top_failed_barriers = [{"barrier": k, "name": k, "count": v} for k, v in sorted(barrier_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

            patterns_in_db = db.list_patterns()
            patterns_count = len(patterns_in_db)

            return {
                "total_events": total,
                "sif_potential_count": sif_high,  # Standardized key for UI
                "sif_high_count": sif_high,
                "sif_medium_count": sif_medium,
                "sif_low_count": sif_low,
                "not_sif_count": not_sif,
                "non_sif_count": not_sif + sif_low,
                "sif_rate": round((sif_high / total * 100), 1) if total > 0 else 0.0,
                "human_count": human_count,
                "imported_count": imported_count,
                "cctv_count": cctv_count,
                "open_actions_count": action_required + action_in_progress,
                "awaiting_verification_count": awaiting_verification,
                "verified_count": verified_count,
                "recurring_patterns_count": patterns_count,
                "pattern_count": patterns_count,
                "top_hazards": top_hazards,
                "top_lsrs": top_lsrs,
                "top_activities": top_activities,
                "top_barriers": top_failed_barriers,
                "top_failed_barriers": top_failed_barriers
            }

    def reset(self):
        """Resets store to default baseline events."""
        with self._lock:
            if os.path.exists(self.persistence_file):
                try:
                    os.remove(self.persistence_file)
                except Exception:
                    pass
            self.seed_baseline_events()


# Global Singleton Store
unified_event_store = UnifiedEventStore()
