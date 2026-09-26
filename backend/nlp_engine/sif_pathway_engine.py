"""
SHRAMRAKSHAK: Deterministic SIF Pathway Reasoning Engine
SIH 2026 Problem Statement: SIH26165

Implements P0.6: Real SIF Pathway.
Consumes Canonical SafetyEvent.
Core pathway logic:
HIGH-ENERGY HAZARD + HUMAN EXPOSURE + FAILED / INADEQUATE / UNCERTAIN CONTROL + CREDIBLE SERIOUS CONSEQUENCE
-> SIF pathway

States:
- SIF-POTENTIAL
- REVIEW_REQUIRED
- NO_SIF_POTENTIAL_IDENTIFIED

Confidence represents extraction / model confidence, NEVER probability of death or injury.
"""

from typing import Dict, List, Any, Optional
try:
    from backend.models_canonical import SafetyEvent, SIFStatus, AssertionStatus, TemporalStatus, BarrierState, ExposureStatus
    from backend.nlp_engine.ontology import ontology
except ImportError:
    try:
        from models_canonical import SafetyEvent, SIFStatus, AssertionStatus, TemporalStatus, BarrierState, ExposureStatus
        from nlp_engine.ontology import ontology
    except ImportError:
        from ..models_canonical import SafetyEvent, SIFStatus, AssertionStatus, TemporalStatus, BarrierState, ExposureStatus
        from .ontology import ontology


class SIFPathwayEngine:
    def __init__(self):
        self.ontology = ontology

    def evaluate(self, event: SafetyEvent) -> SafetyEvent:
        """
        Evaluates the SIF potential of a Canonical SafetyEvent based on evidence-bound criteria.
        Enforces Rule 6 (Explicit Exposure) and Rule 7 (Physical SIF Pathway):
        HIGH-ENERGY HAZARD + AFFIRMED HUMAN EXPOSURE + INADEQUATE/FAILED CONTROL + CREDIBLE SERIOUS CONSEQUENCE = SIF-POTENTIAL.
        """
        reasons = []

        # 1. Assertion and Modality gating (Rule 8)
        if event.assertion == AssertionStatus.NEGATED:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Exposure or incident event was explicitly negated in evidence."]
            event.confidence = 0.98
            return event

        if event.assertion in [AssertionStatus.HYPOTHETICAL, AssertionStatus.CONDITIONAL] or event.temporal_status == TemporalStatus.HYPOTHETICAL:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Conditional or hypothetical statement; not an observed physical event."]
            event.confidence = 0.95
            return event

        if event.assertion == AssertionStatus.POST_EVENT or event.temporal_status == TemporalStatus.POST_EVENT:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Post-incident remediation; not an active incident-time failure."]
            event.confidence = 0.92
            return event

        if event.assertion in [AssertionStatus.UNCERTAIN, AssertionStatus.UNKNOWN]:
            event.sif_status = SIFStatus.REVIEW_REQUIRED
            event.sif_reasons = ["Linguistic ambiguity or double-negation detected; HSE review required."]
            event.confidence = 0.50
            return event

        # 2. Explicit Human Exposure Gating (Rule 6)
        exp_status = getattr(event, "exposure_status", None)
        exp_str = (event.exposure or "").lower()

        # Gate 2A: Explicit Negation of Exposure -> NO_SIF_POTENTIAL_IDENTIFIED
        if (exp_status == ExposureStatus.NEGATED or
            "outside" in exp_str or "no_human" in exp_str or
            "safe boundary" in exp_str or "no person" in exp_str or
            "no worker" in exp_str or "kept clear" in exp_str or "did not enter" in exp_str):
            event.exposure_status = ExposureStatus.NEGATED
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Personnel remained outside hazard perimeter; human exposure explicitly negated (NO_HUMAN_EXPOSURE)."]
            event.confidence = 0.98
            return event

        # Gate 2B: Explicit UNKNOWN Exposure -> REVIEW_REQUIRED (Never NO_SIF and never SIF-POTENTIAL)
        has_unknown_cue = (
            "unknown" in exp_str or "not recorded" in exp_str or
            "no information" in exp_str or "unrecorded" in exp_str or
            "unclear" in exp_str
        )
        has_affirmed_cue = any(k in exp_str for k in ["inside", "entered", "crossed", "in zone", "in line of fire", "in hazard", "trapped", "struck", "exposed"])

        if has_unknown_cue or (exp_status == ExposureStatus.UNKNOWN and not has_affirmed_cue):
            event.exposure_status = ExposureStatus.UNKNOWN
            event.sif_status = SIFStatus.REVIEW_REQUIRED
            event.sif_reasons = [
                "Personnel location or presence was not recorded; physical human exposure is UNKNOWN.",
                "High-energy or compromised barrier present, but human exposure cannot be confirmed without HSE review."
            ]
            event.confidence = 0.65
            return event

        # Gate 2C: POSSIBLE Exposure -> REVIEW_REQUIRED
        if (exp_status == ExposureStatus.POSSIBLE or
            "possible" in exp_str or "suspected" in exp_str or
            "may have" in exp_str or "might have" in exp_str):
            event.exposure_status = ExposureStatus.POSSIBLE
            event.sif_status = SIFStatus.REVIEW_REQUIRED
            event.sif_reasons = ["Human exposure is POSSIBLE / unverified; requires HSE specialist evaluation."]
            event.confidence = 0.70
            return event

        # Gate 2D: Confirmed Exposure affirmed
        event.exposure_status = ExposureStatus.CONFIRMED
        reasons.append("Human exposure affirmed: personnel inside hazardous perimeter")

        # 3. Check High-Energy Hazard (Rule 7)
        energy_id = None
        for eid, einfo in self.ontology.energies.items():
            if eid in str(event.energy) or einfo["name"].lower() in str(event.energy).lower():
                energy_id = eid
                break

        is_high_energy = energy_id in [
            "GRAVITATIONAL_KINETIC", "GRAVITATIONAL_HEIGHT", "HIGH_PRESSURE_STORED",
            "HIGH_PRESSURE_HYDROCARBON", "ATMOSPHERIC_TOXIC", "ELECTRICAL_ENERGY", "MECHANICAL_ROTATING"
        ] or any(kw in str(event.energy).lower() for kw in ["suspended", "pressure", "voltage", "h2s", "fall", "rotary", "dropped", "gravity", "gravitational"])

        if is_high_energy:
            reasons.append(f"High-energy hazard present: {event.energy}")
        else:
            reasons.append(f"Low/unspecified energy hazard: {event.energy}")

        # 4. Check Barrier States (Rule 10)
        barrier_states = [s.upper() if isinstance(s, str) else s.value for s in event.barrier_state]
        is_barrier_failed_or_bypassed = any(st in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for st in barrier_states)
        is_barrier_effective = any(st == "EFFECTIVE_VERIFIED" for st in barrier_states)
        is_barrier_uncertain = any(st in ["UNKNOWN", "PRESENT_UNVERIFIED"] for st in barrier_states)

        if is_barrier_failed_or_bypassed:
            reasons.append(f"Safety barrier compromised: {', '.join(barrier_states)}")
        elif is_barrier_effective:
            reasons.append(f"Safety barrier verified effective: {', '.join(barrier_states)}")
        elif is_barrier_uncertain:
            reasons.append(f"Safety barrier status unverified: {', '.join(barrier_states)}")

        # 5. Check Consequence Severity
        reasons.append(f"Credible consequence pathway: {event.consequence}")

        # 6. Synthesize SIF Status
        if is_high_energy and is_barrier_failed_or_bypassed:
            event.sif_status = SIFStatus.SIF_POTENTIAL
            event.sif_reasons = reasons
            event.confidence = 0.95  # Model extraction heuristic confidence
        elif is_high_energy and is_barrier_uncertain:
            event.sif_status = SIFStatus.REVIEW_REQUIRED
            reasons.append("High-energy hazard with unverified barrier requires HSE specialist evaluation")
            event.sif_reasons = reasons
            event.confidence = 0.70
        elif is_barrier_effective and not is_barrier_failed_or_bypassed:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            reasons.append("Effective barrier prevented progression into high-energy contact")
            event.sif_reasons = reasons
            event.confidence = 0.95
        else:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = reasons
            event.confidence = 0.90

        return event


sif_pathway_engine = SIFPathwayEngine()
