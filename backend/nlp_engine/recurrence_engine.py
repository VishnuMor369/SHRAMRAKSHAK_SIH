"""
SHRAMRAKSHAK: Two-Stage Semantic & Structured Recurrence Engine
SIH 2026 Problem Statement: SIH26165

Implements P1.4 & P1.7:
- Stage 1: E5 transformer + FAISS vector candidate retrieval
- Stage 2: Deep multi-attribute structured compatibility analysis
- Classifies relationships into:
    * DUPLICATE
    * INDEPENDENT_RECURRENCE
    * RELATED_BUT_DIFFERENT
    * REVIEW_REQUIRED
- Distinguishes failure recurrence from effective control contrast (Event C test)
- Proposes CANDIDATE SafetyPattern (NEVER automatically HSE validated)
- Persists all matches, conflicts, and pattern linkages in SQLite.
"""

from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

try:
    from backend.models_canonical import (
        SafetyEvent, RecurrenceResult, RecurrenceRelationship,
        SafetyPattern, ReviewStatus, SIFStatus
    )
    from backend.nlp_engine.semantic_memory import semantic_memory
    from backend.database import db
except ImportError:
    try:
        from models_canonical import (
            SafetyEvent, RecurrenceResult, RecurrenceRelationship,
            SafetyPattern, ReviewStatus, SIFStatus
        )
        from nlp_engine.semantic_memory import semantic_memory
        from database import db
    except ImportError:
        from ..models_canonical import (
            SafetyEvent, RecurrenceResult, RecurrenceRelationship,
            SafetyPattern, ReviewStatus, SIFStatus
        )
        from .semantic_memory import semantic_memory
        from ..database import db


class RecurrenceEngine:
    def __init__(self):
        self.semantic_memory = semantic_memory

    def evaluate_pair(self, target: SafetyEvent, candidate: SafetyEvent, similarity: float) -> RecurrenceResult:
        """
        Stage 2 Structured Compatibility Evaluation between target and candidate events.
        Produces explainable structured matches, structured conflicts, and final relationship.
        """
        matches = []
        conflicts = []

        # 1. Exact Duplicate Check (same report or identical narrative/event)
        if target.event_id == candidate.event_id:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=["Identical event ID"],
                structured_conflicts=[],
                final_relationship=RecurrenceRelationship.DUPLICATE,
                reason="Same event instance."
            )

        if target.report_id and candidate.report_id and target.report_id == candidate.report_id:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=["Identical report ID"],
                structured_conflicts=[],
                final_relationship=RecurrenceRelationship.DUPLICATE,
                reason="Report IDs match; duplicate submission of single incident."
            )

        # 2. Activity & Energy Compatibility
        act_tgt = (target.activity or "").lower()
        act_cnd = (candidate.activity or "").lower()
        if act_tgt == act_cnd or ("lift" in act_tgt and "lift" in act_cnd):
            matches.append(f"Same Activity: {target.activity}")
        else:
            conflicts.append(f"Different Activity: '{target.activity}' vs '{candidate.activity}'")

        eng_tgt = (target.energy or "").lower()
        eng_cnd = (candidate.energy or "").lower()
        if "suspended" in eng_tgt and "suspended" in eng_cnd:
            matches.append("Same Energy: Suspended Load")
        elif eng_tgt == eng_cnd:
            matches.append(f"Same Energy: {target.energy}")
        else:
            conflicts.append(f"Different Energy: '{target.energy}' vs '{candidate.energy}'")

        # 3. Barrier & Control Mechanism Compatibility
        shared_barriers = set(target.barrier).intersection(set(candidate.barrier))
        if shared_barriers:
            matches.append(f"Shared Barrier: {', '.join(shared_barriers)}")
        else:
            conflicts.append("No shared barrier mechanism")

        # 4. Critical Safe Control vs Failure Conflict Check (MANDATORY TEST C)
        # Event C: "Worker remained outside the exclusion zone and barricade was intact"
        # Must NOT be classified as recurrence of failure merely because words match!
        tgt_states = [s.upper() for s in target.barrier_state]
        cnd_states = [s.upper() for s in candidate.barrier_state]
        tgt_failed = any(s in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for s in tgt_states)
        cnd_failed = any(s in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for s in cnd_states)

        tgt_safe = any(s == "EFFECTIVE_VERIFIED" for s in tgt_states) or "outside" in target.exposure.lower()
        cnd_safe = any(s == "EFFECTIVE_VERIFIED" for s in cnd_states) or "outside" in candidate.exposure.lower()

        if (tgt_failed and cnd_safe) or (tgt_safe and cnd_failed):
            conflicts.append("CRITICAL_POLARITY_CONFLICT: One event confirms intact barrier/safe distance, while other represents failure/breach")
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.RELATED_BUT_DIFFERENT,
                reason="Semantic similarity triggered by domain vocabulary, but structured control polarity conflicts (Safe control confirmation vs failure breach). Not a failure recurrence."
            )

        # 5. Assertion Compatibility
        if target.assertion != candidate.assertion:
            conflicts.append(f"Assertion mismatch: {target.assertion} vs {candidate.assertion}")

        # 6. Resolve Final Recurrence Relationship
        if shared_barriers and tgt_failed and cnd_failed:
            # Both events share the same barrier and both involve compromised control -> Independent Recurrence!
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.INDEPENDENT_RECURRENCE,
                reason="Independent recurring breach of the same underlying control mechanism (" + ", ".join(shared_barriers) + ")."
            )
        elif similarity >= 0.75 and shared_barriers:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.INDEPENDENT_RECURRENCE,
                reason="High semantic and barrier alignment; recurrent control vulnerability."
            )
        elif similarity >= 0.60:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.RELATED_BUT_DIFFERENT,
                reason="Shared operational context or location, but different specific barrier/activity failure."
            )
        else:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.REVIEW_REQUIRED,
                reason="Low structured congruence; HSE review required to establish causal correlation."
            )

    def process_event(self, target_event: SafetyEvent) -> Tuple[List[RecurrenceResult], Optional[SafetyPattern]]:
        """
        Executes Two-Stage Recurrence Pipeline:
        Stage 1: FAISS candidate search.
        Stage 2: Structured compatibility evaluation.
        Proposes or updates a CANDIDATE SafetyPattern if independent recurrences found.
        """
        # Save event to semantic memory and FAISS
        self.semantic_memory.add_event(target_event)

        # Stage 1: Retrieval
        candidate_tuples = self.semantic_memory.search_similar_events(target_event, top_k=10, min_similarity=0.45)
        
        results: List[RecurrenceResult] = []
        independent_recurrences: List[Tuple[SafetyEvent, RecurrenceResult]] = []
        duplicates: List[Tuple[SafetyEvent, RecurrenceResult]] = []

        # Stage 2: Evaluation
        for cand_id, sim in candidate_tuples:
            cand_event = db.get_event(cand_id)
            if not cand_event:
                continue
            res = self.evaluate_pair(target_event, cand_event, sim)
            results.append(res)
            
            if res.final_relationship == RecurrenceRelationship.INDEPENDENT_RECURRENCE:
                independent_recurrences.append((cand_event, res))
            elif res.final_relationship == RecurrenceRelationship.DUPLICATE:
                duplicates.append((cand_event, res))

        # Check or Create SafetyPattern
        pattern = None
        barrier_name = target_event.barrier[0] if target_event.barrier else "GENERAL_CONTROL"
        
        if independent_recurrences:
            # Look for existing pattern matching this barrier & activity
            existing_patterns = db.list_patterns()
            matched_pattern = None
            for p in existing_patterns:
                if p.barrier == barrier_name and (p.activity == target_event.activity or "lift" in target_event.activity.lower()):
                    matched_pattern = p
                    break

            if matched_pattern:
                matched_pattern.occurrence_count += 1
                matched_pattern.duplicate_count += len(duplicates)
                db.save_pattern(matched_pattern)
                pattern = matched_pattern
            else:
                pattern_id = f"PAT-{barrier_name}-{int(datetime.now().timestamp()) % 10000:04d}"
                pattern = SafetyPattern(
                    pattern_id=pattern_id,
                    title=f"Recurring Control Breach: {barrier_name} during {target_event.activity}",
                    activity=target_event.activity,
                    energy=target_event.energy,
                    exposure=target_event.exposure,
                    barrier=barrier_name,
                    occurrence_count=1 + len(independent_recurrences),
                    duplicate_count=len(duplicates),
                    validation_status=ReviewStatus.CANDIDATE  # Strictly CANDIDATE, NEVER auto HSE_VALIDATED
                )
                db.save_pattern(pattern)

            # Link target event to pattern
            target_event.pattern_id = pattern.pattern_id
            db.save_event(target_event)

            # Add pattern members
            for cand, rec_res in independent_recurrences:
                db.add_pattern_member(
                    pattern_id=pattern.pattern_id,
                    event_id=cand.event_id,
                    relationship=rec_res.final_relationship.value,
                    similarity=rec_res.retrieval_similarity,
                    reason=rec_res.reason
                )

        return results, pattern


recurrence_engine = RecurrenceEngine()
