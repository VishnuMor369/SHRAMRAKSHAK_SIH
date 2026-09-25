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
    from backend.models_canonical import SafetyEvent, SIFStatus, AssertionStatus, TemporalStatus, BarrierState
    from backend.nlp_engine.ontology import ontology
except ImportError:
    try:
        from models_canonical import SafetyEvent, SIFStatus, AssertionStatus, TemporalStatus, BarrierState
        from nlp_engine.ontology import ontology
    except ImportError:
        from ..models_canonical import SafetyEvent, SIFStatus, AssertionStatus, TemporalStatus, BarrierState
        from .ontology import ontology


class SIFPathwayEngine:
    def __init__(self):
        self.ontology = ontology

    def evaluate(self, event: SafetyEvent) -> SafetyEvent:
        """
        Evaluates the SIF potential of a Canonical SafetyEvent based on evidence-bound criteria.
        Updates event.sif_status, event.sif_reasons, and event.confidence.
        """
        reasons = []

        # 1. Assertion and Modality gating
        if event.assertion == AssertionStatus.NEGATED:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Exposure or incident event was explicitly negated in evidence."]
            return event

        if event.assertion == AssertionStatus.HYPOTHETICAL or event.temporal_status == TemporalStatus.HYPOTHETICAL:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Conditional or hypothetical statement; not an observed physical event."]
            return event

        if event.assertion == AssertionStatus.POST_EVENT or event.temporal_status == TemporalStatus.POST_EVENT:
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Post-incident remediation; not an active incident-time failure."]
            return event

        if event.assertion == AssertionStatus.UNCERTAIN:
            event.sif_status = SIFStatus.REVIEW_REQUIRED
            event.sif_reasons = ["Linguistic ambiguity or double-negation detected; HSE review required."]
            return event

        # 2. Check for Safe Boundary Respected / No Exposure
        if "outside" in event.exposure.lower() or "no_human" in event.exposure.lower() or "safe boundary" in event.exposure.lower():
            event.sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            event.sif_reasons = ["Personnel remained outside hazard perimeter; human exposure not affirmed."]
            return event

        # 3. Check High-Energy Hazard
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

        # 4. Check Barrier States
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
            event.confidence = 0.95
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
