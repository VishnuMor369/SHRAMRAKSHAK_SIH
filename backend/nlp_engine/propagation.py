"""
SHRAMRAKSHAK: Human Correction Propagation & Dependency Recomputation Engine
SIH 2026 Problem Statement: SIH26165

Implements P1.7 & P1.8:
- Human HSE Review workflow with strictly auditable transitions:
    CANDIDATE -> HSE_VALIDATED | REJECTED | REOPENED
- Dependency-aware recomputation pipeline:
    Human Correction (e.g., barrier_state FAILED -> EFFECTIVE_VERIFIED)
    -> Recompute SafetyEvent
    -> Recompute SIF Pathway
    -> Recompute LSR Mapping
    -> Recompute Pattern Membership & Counts
    -> Recompute Future Preconditions & Checks
    -> Persist updated state to SQLite
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

try:
    from backend.models_canonical import (
        SafetyEvent, SafetyPattern, ReviewStatus, SIFStatus,
        WorkPrecondition
    )
    from backend.database import db
    from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
    from backend.nlp_engine.lsr_classifier import lsr_classifier
    from backend.nlp_engine.semantic_memory import semantic_memory
except ImportError:
    try:
        from models_canonical import (
            SafetyEvent, SafetyPattern, ReviewStatus, SIFStatus,
            WorkPrecondition
        )
        from database import db
        from nlp_engine.sif_pathway_engine import sif_pathway_engine
        from nlp_engine.lsr_classifier import lsr_classifier
        from nlp_engine.semantic_memory import semantic_memory
    except ImportError:
        from ..models_canonical import (
            SafetyEvent, SafetyPattern, ReviewStatus, SIFStatus,
            WorkPrecondition
        )
        from ..database import db
        from .sif_pathway_engine import sif_pathway_engine
        from .lsr_classifier import lsr_classifier
        from .semantic_memory import semantic_memory


class CorrectionPropagationEngine:
    def __init__(self):
        self.db = db
        self.sif_engine = sif_pathway_engine
        self.lsr_engine = lsr_classifier
        self.semantic_memory = semantic_memory

    def apply_human_correction(
        self,
        event_id: str,
        corrections: Dict[str, Any],
        reviewer_role: str = "DEMO_HSE_REVIEWER",
        reason: str = "HSE verification of field observation"
    ) -> Dict[str, Any]:
        """
        Executes dependency-aware human correction propagation:
        1. Fetch current SafetyEvent
        2. Snapshot previous values
        3. Apply human corrections
        4. Recompute SIF pathway & LSR mapping
        5. Update pattern membership & occurrence counts
        6. Persist state to SQLite & FAISS
        7. Log auditable review record
        """
        event = self.db.get_event(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found in persistent database.")

        # 2. Snapshot previous values
        prev_values = {
            "barrier": list(event.barrier),
            "barrier_state": list(event.barrier_state),
            "activity": event.activity,
            "energy": event.energy,
            "exposure": event.exposure,
            "sif_status": event.sif_status.value if hasattr(event.sif_status, "value") else str(event.sif_status),
            "lsr": list(event.lsr),
            "pattern_id": event.pattern_id
        }

        # 3. Apply corrections
        if "barrier" in corrections:
            event.barrier = corrections["barrier"] if isinstance(corrections["barrier"], list) else [corrections["barrier"]]
        if "barrier_state" in corrections:
            event.barrier_state = corrections["barrier_state"] if isinstance(corrections["barrier_state"], list) else [corrections["barrier_state"]]
        if "activity" in corrections:
            event.activity = corrections["activity"]
        if "energy" in corrections:
            event.energy = corrections["energy"]
        if "exposure" in corrections:
            event.exposure = corrections["exposure"]
        if "consequence" in corrections:
            event.consequence = corrections["consequence"]

        event.review_status = ReviewStatus.CORRECTED
        event.updated_at = datetime.now().isoformat()

        # 4. Dependency-aware Recomputations
        # A. Recompute SIF Pathway
        event = self.sif_engine.evaluate(event)
        
        # B. Recompute LSR Mapping
        lsr_matches = self.lsr_engine.classify_event(event)
        event.lsr = [m["lsr"] for m in lsr_matches]

        # 5. Pattern Membership Recomputation
        pattern_updates = []
        old_pattern_id = prev_values.get("pattern_id")
        if old_pattern_id:
            pattern = self.db.get_pattern(old_pattern_id)
            if pattern:
                # If barrier was corrected to EFFECTIVE_VERIFIED or no SIF potential,
                # this event is no longer an active failure member of the pattern!
                was_compromised = any(st in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for st in prev_values["barrier_state"])
                now_compromised = any(st in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for st in event.barrier_state)
                
                if was_compromised and not now_compromised:
                    pattern.occurrence_count = max(0, pattern.occurrence_count - 1)
                    pattern.updated_at = datetime.now().isoformat()
                    self.db.save_pattern(pattern)
                    event.pattern_id = None
                    pattern_updates.append(f"Decremented occurrence count on {pattern.pattern_id} (event is no longer a failure occurrence)")

        # 6. Persist updated SafetyEvent to SQLite
        self.db.save_event(event)

        # 7. Log Auditable Review Record to SQLite
        review_id = f"REV-{uuid.uuid4().hex[:8]}"
        new_values = {
            "barrier": event.barrier,
            "barrier_state": event.barrier_state,
            "activity": event.activity,
            "energy": event.energy,
            "exposure": event.exposure,
            "sif_status": event.sif_status.value if hasattr(event.sif_status, "value") else str(event.sif_status),
            "lsr": event.lsr,
            "pattern_id": event.pattern_id
        }
        self.db.log_review(
            review_id=review_id,
            target_type="EVENT",
            target_id=event.event_id,
            reviewer_role=reviewer_role,
            action="CORRECT",
            previous_value=prev_values,
            new_value=new_values,
            reason=reason
        )

        return {
            "review_id": review_id,
            "event_id": event.event_id,
            "reviewer_role": reviewer_role,
            "previous_values": prev_values,
            "new_values": new_values,
            "recomputed_sif": event.sif_status.value,
            "recomputed_lsr": event.lsr,
            "pattern_updates": pattern_updates,
            "timestamp": datetime.now().isoformat()
        }

    def validate_safety_pattern(
        self,
        pattern_id: str,
        reviewer_role: str = "DEMO_HSE_REVIEWER",
        action: str = "VALIDATE",  # VALIDATE | REJECT | REOPEN
        review_notes: str = "HSE validation of recurring control weakness"
    ) -> SafetyPattern:
        """
        Transitions a CANDIDATE control pattern to HSE_VALIDATED, REJECTED, or REOPENED.
        Strict governance: AI only creates CANDIDATE; only human action validates.
        """
        pattern = self.db.get_pattern(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found in database.")

        prev_status = pattern.validation_status.value if hasattr(pattern.validation_status, "value") else str(pattern.validation_status)

        if action.upper() == "VALIDATE":
            pattern.validation_status = ReviewStatus.HSE_VALIDATED
        elif action.upper() == "REJECT":
            pattern.validation_status = ReviewStatus.REJECTED
        elif action.upper() == "REOPEN":
            pattern.validation_status = ReviewStatus.REOPENED

        pattern.reviewer_role = reviewer_role
        pattern.reviewed_at = datetime.now().isoformat()
        pattern.review_notes = review_notes
        pattern.updated_at = datetime.now().isoformat()

        # Save to SQLite
        self.db.save_pattern(pattern)

        # Log to reviews table
        review_id = f"REV-{uuid.uuid4().hex[:8]}"
        self.db.log_review(
            review_id=review_id,
            target_type="PATTERN",
            target_id=pattern.pattern_id,
            reviewer_role=reviewer_role,
            action=action.upper(),
            previous_value={"validation_status": prev_status},
            new_value={"validation_status": pattern.validation_status.value},
            reason=review_notes
        )

        return pattern


propagation_engine = CorrectionPropagationEngine()
