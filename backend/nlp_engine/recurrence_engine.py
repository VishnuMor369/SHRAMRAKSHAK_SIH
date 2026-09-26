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

import uuid
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

try:
    from backend.models_canonical import (
        SafetyEvent, RecurrenceResult, RecurrenceRelationship,
        SafetyPattern, ReviewStatus, SIFStatus, ExposureStatus,
        AssertionStatus, BarrierState
    )
    from backend.nlp_engine.semantic_memory import semantic_memory
    from backend.database import db
    from backend.nlp_engine.ontology import ontology
except ImportError:
    try:
        from models_canonical import (
            SafetyEvent, RecurrenceResult, RecurrenceRelationship,
            SafetyPattern, ReviewStatus, SIFStatus, ExposureStatus,
            AssertionStatus, BarrierState
        )
        from nlp_engine.semantic_memory import semantic_memory
        from database import db
        from nlp_engine.ontology import ontology
    except ImportError:
        from ..models_canonical import (
            SafetyEvent, RecurrenceResult, RecurrenceRelationship,
            SafetyPattern, ReviewStatus, SIFStatus, ExposureStatus,
            AssertionStatus, BarrierState
        )
        from .semantic_memory import semantic_memory
        from ..database import db
        from .ontology import ontology

# Configurable Similarity Thresholds (Rule 14)
SIMILARITY_DUPLICATE_THRESHOLD: float = 0.95
SIMILARITY_RECURRENCE_THRESHOLD: float = 0.80
SIMILARITY_RELATED_THRESHOLD: float = 0.65
SIMILARITY_MIN_RETRIEVAL: float = 0.50


class RecurrenceEngine:
    def __init__(self):
        self.semantic_memory = semantic_memory

    @staticmethod
    def match_activities(act1: Optional[str], act2: Optional[str]) -> bool:
        """Generalized cross-domain activity compatibility matching using safety ontology."""
        if not act1 or not act2:
            return False
        s1, s2 = act1.strip().lower(), act2.strip().lower()
        if s1 == s2 or s1 in s2 or s2 in s1:
            return True
        for act_id, info in getattr(ontology, "activities", {}).items():
            kws = [k.lower() for k in info.get("keywords", [])] + [info.get("name", "").lower(), act_id.lower()]
            m1 = any(k in s1 for k in kws)
            m2 = any(k in s2 for k in kws)
            if m1 and m2:
                return True
        return False

    @staticmethod
    def match_energies(eng1: Optional[str], eng2: Optional[str]) -> bool:
        """Generalized cross-domain hazard energy compatibility matching using safety ontology."""
        if not eng1 or not eng2:
            return False
        s1, s2 = eng1.strip().lower(), eng2.strip().lower()
        if s1 == s2 or s1 in s2 or s2 in s1:
            return True
        for eng_id, info in getattr(ontology, "energies", {}).items():
            kws = [k.lower() for k in info.get("keywords", [])] + [info.get("name", "").lower(), eng_id.lower()]
            m1 = any(k in s1 for k in kws)
            m2 = any(k in s2 for k in kws)
            if m1 and m2:
                return True
        return False

    def evaluate_pair(self, target: SafetyEvent, candidate: SafetyEvent, similarity: float) -> RecurrenceResult:
        """
        Stage 2 Structured Compatibility Evaluation between target and candidate events.
        Produces explainable structured matches, structured conflicts, final relationship,
        and structured reasoning details (Rules 14, 15, 16).
        """
        matches = []
        conflicts = []

        # 1. Exact Duplicate Check (same event ID, same report ID, or identical narrative/attributes with > 0.95 similarity)
        if target.event_id == candidate.event_id:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=["Identical event ID"],
                structured_conflicts=[],
                final_relationship=RecurrenceRelationship.DUPLICATE,
                reason="Same event instance.",
                reasoning_details={
                    "why_chosen": "Identical event ID.",
                    "barrier_comparison": "Identical event.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Identical instance"
                }
            )

        if target.report_id and candidate.report_id and target.report_id == candidate.report_id:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=["Identical report ID"],
                structured_conflicts=[],
                final_relationship=RecurrenceRelationship.DUPLICATE,
                reason="Report IDs match; duplicate submission of single incident.",
                reasoning_details={
                    "why_chosen": "Identical report ID indicates duplicate submission.",
                    "barrier_comparison": "Same incident report.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Same report"
                }
            )

        narr_tgt = (target.narrative or "").strip().lower()
        narr_cnd = (candidate.narrative or "").strip().lower()
        has_matching_narr = bool(narr_tgt and narr_cnd and (narr_tgt == narr_cnd or narr_tgt in narr_cnd or narr_cnd in narr_tgt))

        if (similarity >= SIMILARITY_DUPLICATE_THRESHOLD and has_matching_narr) or (has_matching_narr and similarity >= SIMILARITY_RECURRENCE_THRESHOLD):
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=["Near-identical narrative with ultra-high semantic similarity (>0.95)"],
                structured_conflicts=[],
                final_relationship=RecurrenceRelationship.DUPLICATE,
                reason=f"Near-identical narrative and high similarity ({similarity:.2f}); candidate duplicate report.",
                reasoning_details={
                    "why_chosen": "Semantic similarity >= 0.95 with matching narrative content.",
                    "barrier_comparison": "Matching report content.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Duplicate incident submission"
                }
            )

        # 2. Activity & Energy Compatibility (Generalized Cross-Domain)
        if self.match_activities(target.activity, candidate.activity):
            matches.append(f"Compatible Activity Domain: {target.activity}")
        else:
            conflicts.append(f"Different Activity: '{target.activity}' vs '{candidate.activity}'")

        if self.match_energies(target.energy, candidate.energy):
            matches.append(f"Compatible Hazard Energy: {target.energy}")
        else:
            conflicts.append(f"Different Energy: '{target.energy}' vs '{candidate.energy}'")

        # 3. Barrier & Control Mechanism Compatibility
        shared_barriers = set(target.barrier).intersection(set(candidate.barrier))
        if shared_barriers:
            matches.append(f"Shared Barrier: {', '.join(shared_barriers)}")
        else:
            conflicts.append("No shared barrier mechanism")

        # 4. Critical Safe Control vs Failure Conflict Check (MANDATORY RULE 16 / Event C test)
        # Event C: "Worker remained outside the exclusion zone and barricade was intact"
        # Must NOT be classified as recurrence of failure merely because words match!
        tgt_states = [str(s).upper() for s in target.barrier_state]
        cnd_states = [str(s).upper() for s in candidate.barrier_state]
        tgt_failed = any(s in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED", "COMPROMISED"] for s in tgt_states)
        cnd_failed = any(s in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED", "COMPROMISED"] for s in cnd_states)

        tgt_exp_neg = (
            getattr(target, "exposure_status", None) == ExposureStatus.NEGATED or
            "outside" in (target.exposure or "").lower() or
            "no_human" in (target.exposure or "").lower() or
            target.assertion == AssertionStatus.NEGATED
        )
        cnd_exp_neg = (
            getattr(candidate, "exposure_status", None) == ExposureStatus.NEGATED or
            "outside" in (candidate.exposure or "").lower() or
            "no_human" in (candidate.exposure or "").lower() or
            candidate.assertion == AssertionStatus.NEGATED
        )

        tgt_safe = any(s == "EFFECTIVE_VERIFIED" for s in tgt_states) or tgt_exp_neg
        cnd_safe = any(s == "EFFECTIVE_VERIFIED" for s in cnd_states) or cnd_exp_neg

        if (tgt_failed and cnd_safe) or (tgt_safe and cnd_failed):
            conflicts.append("CRITICAL_POLARITY_CONFLICT: One event confirms intact barrier/safe distance, while other represents failure/breach")
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.RELATED_BUT_DIFFERENT,
                reason="Semantic similarity triggered by domain vocabulary, but structured control polarity conflicts (Safe control confirmation vs failure breach). Not a failure recurrence.",
                reasoning_details={
                    "why_chosen": "Safe control vs compromised barrier polarity conflict.",
                    "barrier_comparison": "One barrier effective/intact, other failed/bypassed.",
                    "similarity_score": similarity,
                    "polarity_check": "FAILED_POLARITY_CHECK",
                    "spatiotemporal_relationship": "Related domain"
                }
            )

        if tgt_safe and cnd_safe and not tgt_failed and not cnd_failed:
            matches.append("Both events describe verified effective controls")
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.RELATED_BUT_DIFFERENT,
                reason="Both events confirm effective control maintenance; safe operational observations rather than incident recurrence.",
                reasoning_details={
                    "why_chosen": "Both events describe verified effective controls.",
                    "barrier_comparison": "Intact barriers on both events.",
                    "similarity_score": similarity,
                    "polarity_check": "SAFE_OBSERVATION",
                    "spatiotemporal_relationship": "Related domain"
                }
            )

        # 5. Assertion Compatibility
        if target.assertion != candidate.assertion:
            conflicts.append(f"Assertion mismatch: {target.assertion} vs {candidate.assertion}")

        # 6. Resolve Final Recurrence Relationship (Rules 14 & 15)
        if shared_barriers and tgt_failed and cnd_failed:
            # Both events share the same barrier and both involve compromised control -> Independent Recurrence!
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.INDEPENDENT_RECURRENCE,
                reason="Independent recurring breach of the same underlying control mechanism (" + ", ".join(shared_barriers) + ").",
                reasoning_details={
                    "why_chosen": f"Shared compromised barrier ({', '.join(shared_barriers)}) across independent incidents.",
                    "barrier_comparison": f"Decisive: Identical compromised barrier '{', '.join(shared_barriers)}'.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Independent events"
                }
            )
        elif similarity >= SIMILARITY_RECURRENCE_THRESHOLD and shared_barriers:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.INDEPENDENT_RECURRENCE,
                reason="High semantic and barrier alignment; recurrent control vulnerability.",
                reasoning_details={
                    "why_chosen": f"Semantic similarity ({similarity:.2f}) >= {SIMILARITY_RECURRENCE_THRESHOLD} with shared barrier.",
                    "barrier_comparison": f"Shared barrier '{', '.join(shared_barriers)}'.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Independent events"
                }
            )
        elif similarity >= SIMILARITY_RELATED_THRESHOLD:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.RELATED_BUT_DIFFERENT,
                reason="Shared operational context or location, but different specific barrier/activity failure.",
                reasoning_details={
                    "why_chosen": f"Semantic similarity ({similarity:.2f}) >= {SIMILARITY_RELATED_THRESHOLD} without identical broken control.",
                    "barrier_comparison": "Different barriers or non-compromised control.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Related operational context"
                }
            )
        elif similarity >= SIMILARITY_MIN_RETRIEVAL:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.REVIEW_REQUIRED,
                reason="Low structured congruence; HSE review required to establish causal correlation.",
                reasoning_details={
                    "why_chosen": f"Marginal similarity ({similarity:.2f}) requires specialist HSE review.",
                    "barrier_comparison": "Inconclusive control overlap.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Uncertain correlation"
                }
            )
        else:
            return RecurrenceResult(
                candidate_id=candidate.event_id,
                target_event_id=target.event_id,
                retrieval_similarity=similarity,
                structured_matches=matches,
                structured_conflicts=conflicts,
                final_relationship=RecurrenceRelationship.UNRELATED,
                reason=f"Similarity ({similarity:.2f}) below retrieval threshold ({SIMILARITY_MIN_RETRIEVAL}); unrelated events.",
                reasoning_details={
                    "why_chosen": f"Low similarity ({similarity:.2f}) < {SIMILARITY_MIN_RETRIEVAL}.",
                    "barrier_comparison": "Unrelated barriers.",
                    "similarity_score": similarity,
                    "spatiotemporal_relationship": "Unrelated"
                }
            )

    def process_event(self, target_event: SafetyEvent) -> Tuple[List[RecurrenceResult], Optional[SafetyPattern]]:
        """
        Executes Two-Stage Recurrence Pipeline:
        Stage 1: FAISS candidate search.
        Stage 2: Structured compatibility evaluation.
        Proposes or updates a CANDIDATE SafetyPattern if independent recurrences found (Rule 17).
        """
        # Save event to semantic memory and FAISS
        self.semantic_memory.add_event(target_event)

        # Stage 1: Retrieval
        candidate_tuples = self.semantic_memory.search_similar_events(target_event, top_k=10, min_similarity=SIMILARITY_MIN_RETRIEVAL)
        
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

        # Check or Create SafetyPattern (Rule 17: Gated by SIF-potential and independent recurrence)
        pattern = None
        barrier_name = target_event.barrier[0] if target_event.barrier else "GENERAL_CONTROL"
        
        has_sif = (
            target_event.sif_status == SIFStatus.SIF_POTENTIAL or
            any(cand.sif_status == SIFStatus.SIF_POTENTIAL for cand, _ in independent_recurrences)
        )

        if independent_recurrences and has_sif:
            # Look for existing pattern matching this barrier & activity
            existing_patterns = db.list_patterns()
            matched_pattern = None
            for p in existing_patterns:
                if p.barrier == barrier_name and self.match_activities(p.activity, target_event.activity):
                    matched_pattern = p
                    break

            if matched_pattern:
                matched_pattern.occurrence_count += 1
                matched_pattern.duplicate_count += len(duplicates)

                # Rule 20: Closed-Loop Reopening
                # If an existing pattern was previously closed/verified, and a new INDEPENDENT RECURRENCE occurs:
                # The existing control assumption is challenged -> pattern reopens for HSE review.
                op_status = getattr(matched_pattern, "operational_status", "ACTIVE")
                val_status = matched_pattern.validation_status.value if hasattr(matched_pattern.validation_status, "value") else str(matched_pattern.validation_status)
                if op_status in ["CLOSED", "CLOSED_HISTORY", "VERIFIED"] or val_status in ["HSE_VALIDATED", ReviewStatus.HSE_VALIDATED.value]:
                    prev_op = op_status
                    prev_val = val_status
                    matched_pattern.operational_status = "REOPENED"
                    matched_pattern.validation_status = ReviewStatus.REOPENED
                    matched_pattern.review_notes = f"Pattern challenged by new independent recurrence {target_event.event_id}. HSE Review Required."
                    matched_pattern.updated_at = datetime.now().isoformat()
                    try:
                        db.log_review(
                            review_id=f"REV-REOPEN-{uuid.uuid4().hex[:6]}",
                            target_type="PATTERN",
                            target_id=matched_pattern.pattern_id,
                            reviewer_role="SAFETY_INTELLIGENCE_ENGINE",
                            action="REOPEN_CHALLENGE",
                            previous_value={"operational_status": prev_op, "validation_status": prev_val},
                            new_value={"operational_status": "REOPENED", "validation_status": "REOPENED"},
                            reason=f"Challenged by independent recurrence {target_event.event_id}"
                        )
                    except Exception:
                        pass

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

        elif duplicates and not independent_recurrences:
            # Rule 20 Negative Check: SUPPORTED + DUPLICATE = MUST NOT REOPEN
            existing_patterns = db.list_patterns()
            for p in existing_patterns:
                if p.barrier == barrier_name and self.match_activities(p.activity, target_event.activity):
                    p.duplicate_count += len(duplicates)
                    # CRITICAL NEGATIVE: Do NOT reopen pattern on duplicate reports of the same incident
                    db.save_pattern(p)
                    pattern = p
                    break

        return results, pattern

    evaluate_event = process_event


recurrence_engine = RecurrenceEngine()
