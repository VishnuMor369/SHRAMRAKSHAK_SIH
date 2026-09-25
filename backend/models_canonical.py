"""
SHRAMRAKSHAK: Canonical Safety Event & Domain Ontology Models
SIH 2026 Problem Statement: SIH26165

Canonical Safety Event Model (P0.1) consumed by ALL downstream components:
RAW REPORT / CCTV / DATASET -> PREPROCESSING -> ASSERTION -> CANONICAL SAFETY EVENT
-> SIF PATHWAY -> IOGP LSR -> SEMANTIC MEMORY -> RECURRENCE -> PATTERN -> HSE REVIEW -> PRECONDITION -> VERIFICATION
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


class AssertionStatus(str, Enum):
    AFFIRMED = "AFFIRMED"
    NEGATED = "NEGATED"
    HYPOTHETICAL = "HYPOTHETICAL"
    POST_EVENT = "POST_EVENT"
    UNCERTAIN = "UNCERTAIN"


class TemporalStatus(str, Enum):
    DURING_EVENT = "DURING_EVENT"
    POST_EVENT = "POST_EVENT"
    PRE_EVENT = "PRE_EVENT"
    HISTORICAL = "HISTORICAL"
    HYPOTHETICAL = "HYPOTHETICAL"


class BarrierState(str, Enum):
    EFFECTIVE_VERIFIED = "EFFECTIVE_VERIFIED"
    PRESENT_UNVERIFIED = "PRESENT_UNVERIFIED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    BYPASSED = "BYPASSED"
    REMOVED = "REMOVED"
    UNKNOWN = "UNKNOWN"


class SIFStatus(str, Enum):
    SIF_POTENTIAL = "SIF-POTENTIAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_SIF_POTENTIAL_IDENTIFIED = "NO_SIF_POTENTIAL_IDENTIFIED"


class ReviewStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    CANDIDATE = "CANDIDATE"
    HSE_VALIDATED = "HSE_VALIDATED"
    REJECTED = "REJECTED"
    CORRECTED = "CORRECTED"
    REOPENED = "REOPENED"


class RecurrenceRelationship(str, Enum):
    DUPLICATE = "DUPLICATE"
    INDEPENDENT_RECURRENCE = "INDEPENDENT_RECURRENCE"
    RELATED_BUT_DIFFERENT = "RELATED_BUT_DIFFERENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass
class EvidenceSpan:
    field: str
    value: str
    start_offset: int
    end_offset: int
    text: str
    confidence: float = 1.0
    source: str = "TEXT_EXTRACTION"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def verify_against(self, raw_text: str) -> bool:
        """Verifies character exactness against original text without fabrication."""
        if 0 <= self.start_offset <= self.end_offset <= len(raw_text):
            return raw_text[self.start_offset:self.end_offset] == self.text
        return False


@dataclass
class BarrierRecord:
    barrier: str
    barrier_state: BarrierState = BarrierState.UNKNOWN
    evidence_span: Optional[EvidenceSpan] = None
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "barrier": self.barrier,
            "barrier_state": self.barrier_state.value if isinstance(self.barrier_state, BarrierState) else str(self.barrier_state),
            "evidence_span": self.evidence_span.to_dict() if self.evidence_span else None,
            "is_verified": self.is_verified
        }


@dataclass
class SafetyEvent:
    event_id: str
    report_id: Optional[str] = None
    source: str = "HUMAN"  # HUMAN | IMPORTED | CCTV
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    site: str = "OIL Field Duliajan"
    location: str = "Drilling Rig 04 - Drill Floor"

    activity: str = "Mechanical Lifting"
    energy: str = "Gravitational / Kinetic Energy"
    exposure: str = "Person inside hazardous perimeter"

    barrier: List[str] = field(default_factory=list)
    barrier_state: List[str] = field(default_factory=list)

    consequence: str = "Crush trauma / blunt impact"

    assertion: AssertionStatus = AssertionStatus.AFFIRMED
    temporal_status: TemporalStatus = TemporalStatus.DURING_EVENT

    sif_status: SIFStatus = SIFStatus.SIF_POTENTIAL
    sif_reasons: List[str] = field(default_factory=list)

    lsr: List[str] = field(default_factory=list)

    evidence: List[EvidenceSpan] = field(default_factory=list)
    uncertainty: List[str] = field(default_factory=list)

    confidence: float = 0.95
    review_status: ReviewStatus = ReviewStatus.CANDIDATE

    embedding_id: Optional[str] = None
    pattern_id: Optional[str] = None

    provenance: Dict[str, Any] = field(default_factory=lambda: {
        "source_name": "Field Safety Reporting",
        "source_type": "OBSERVATION",
        "is_oil_data": True,
        "has_sif_ground_truth": True,
        "label_status": "MANUAL_FIELD_ENTRY"
    })

    lifecycle_state: str = "REPORTED"  # REPORTED | ACTION_REQUIRED | ACTION_IN_PROGRESS | AWAITING_VERIFICATION | RESOLVED | REOPENED
    machine_observation: bool = False
    narrative: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "report_id": self.report_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "site": self.site,
            "location": self.location,
            "activity": self.activity,
            "energy": self.energy,
            "exposure": self.exposure,
            "barrier": self.barrier,
            "barrier_state": self.barrier_state,
            "consequence": self.consequence,
            "assertion": self.assertion.value if isinstance(self.assertion, AssertionStatus) else str(self.assertion),
            "temporal_status": self.temporal_status.value if isinstance(self.temporal_status, TemporalStatus) else str(self.temporal_status),
            "sif_status": self.sif_status.value if isinstance(self.sif_status, SIFStatus) else str(self.sif_status),
            "sif_reasons": self.sif_reasons,
            "lsr": self.lsr,
            "evidence": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.evidence],
            "uncertainty": self.uncertainty,
            "confidence": self.confidence,
            "review_status": self.review_status.value if isinstance(self.review_status, ReviewStatus) else str(self.review_status),
            "embedding_id": self.embedding_id,
            "pattern_id": self.pattern_id,
            "provenance": self.provenance,
            "lifecycle_state": self.lifecycle_state,
            "machine_observation": self.machine_observation,
            "narrative": self.narrative,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class RecurrenceResult:
    candidate_id: str
    target_event_id: str
    retrieval_similarity: float
    structured_matches: List[str]
    structured_conflicts: List[str]
    final_relationship: RecurrenceRelationship
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "target_event_id": self.target_event_id,
            "retrieval_similarity": self.retrieval_similarity,
            "structured_matches": self.structured_matches,
            "structured_conflicts": self.structured_conflicts,
            "final_relationship": self.final_relationship.value if isinstance(self.final_relationship, RecurrenceRelationship) else str(self.final_relationship),
            "reason": self.reason
        }


@dataclass
class SafetyPattern:
    pattern_id: str
    title: str
    activity: str
    energy: str
    exposure: str
    barrier: str
    occurrence_count: int = 1
    duplicate_count: int = 0
    validation_status: ReviewStatus = ReviewStatus.CANDIDATE
    reviewer_role: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "title": self.title,
            "activity": self.activity,
            "energy": self.energy,
            "exposure": self.exposure,
            "barrier": self.barrier,
            "occurrence_count": self.occurrence_count,
            "duplicate_count": self.duplicate_count,
            "validation_status": self.validation_status.value if isinstance(self.validation_status, ReviewStatus) else str(self.validation_status),
            "reviewer_role": self.reviewer_role,
            "reviewed_at": self.reviewed_at,
            "review_notes": self.review_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class WorkPrecondition:
    precondition_id: str
    pattern_id: str
    title: str
    required_barrier: str
    required_evidence_types: List[str] = field(default_factory=list)
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkCheckResult:
    check_id: str
    package_id: str
    activity: str
    location: str
    precondition_id: str
    status: str  # PASS | MISSING_EVIDENCE | REVIEW_REQUIRED | NOT_APPLICABLE
    findings: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunManifest:
    run_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    dataset_name: str = ""
    dataset_hash: str = ""
    code_version: str = "SHRAMRAKSHAK-2.0-SIH26165"
    model_name: str = "intfloat/e5-small-v2"
    model_version: str = "e5-small-v2"
    ontology_version: str = "1.0.0"
    config_hash: str = ""
    records_seen: int = 0
    records_processed: int = 0
    records_failed: int = 0
    events_created: int = 0
    patterns_created: int = 0
    reviews_executed: int = 0
    embeddings_created: int = 0
    execution_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
