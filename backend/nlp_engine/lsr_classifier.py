"""
SHRAMRAKSHAK: Structured Multi-Label IOGP Life-Saving Rules Mapper
SIH 2026 Problem Statement: SIH26165

Implements P0.7:
- Consumes Canonical SafetyEvent
- Uses centralized ontology/lsr_rules.yaml
- Structured multi-label assignment with explicit evidence, reason, and confidence
- Eliminates superficial keyword guessing
"""

from typing import List, Dict, Any, Optional
try:
    from backend.models_canonical import SafetyEvent
    from backend.nlp_engine.ontology import ontology
except ImportError:
    try:
        from models_canonical import SafetyEvent
        from nlp_engine.ontology import ontology
    except ImportError:
        from ..models_canonical import SafetyEvent
        from .ontology import ontology


class LSRClassifier:
    def __init__(self):
        self.ontology = ontology

    def classify_event(self, event: SafetyEvent) -> List[Dict[str, Any]]:
        """
        Maps a Canonical SafetyEvent to applicable IOGP Life-Saving Rules.
        Returns a list of structured mappings:
        [{
            "lsr": str,
            "evidence": str,
            "reason": str,
            "confidence": float
        }]
        """
        matches = []
        rules = self.ontology.lsr_rules

        # Collect event properties
        act = (event.activity or "").upper()
        energy = (event.energy or "").upper()
        barriers = [b.upper() for b in event.barrier]
        states = [s.upper() for s in event.barrier_state]
        exposure = (event.exposure or "").upper()
        narrative = (event.narrative or "").lower()

        for rule in rules:
            rule_id = rule["id"]
            rule_name = rule["rule_name"]
            matched_triggers = []
            evidence_snippets = []

            # Check Activity trigger
            for t_act in rule.get("trigger_activities", []):
                if t_act in act:
                    matched_triggers.append(f"Activity matches {t_act}")
                    evidence_snippets.append(event.activity)
                    break

            # Check Energy trigger
            for t_eng in rule.get("trigger_energies", []):
                if t_eng in energy:
                    matched_triggers.append(f"Energy source matches {t_eng}")
                    evidence_snippets.append(event.energy)
                    break

            # Check Barrier trigger
            for t_bar in rule.get("trigger_barriers", []):
                if t_bar in barriers:
                    matched_triggers.append(f"Safety barrier involves {t_bar}")
                    evidence_snippets.append(t_bar)
                    break

            # Check Exposure trigger
            for t_exp in rule.get("trigger_exposures", []):
                if t_exp in exposure or any(kw in exposure.lower() for kw in ["inside", "line of fire", "under", "unprotected"]):
                    matched_triggers.append(f"Exposure profile matches {t_exp}")
                    evidence_snippets.append(event.exposure)
                    break

            # Check Barrier State trigger (e.g. BYPASSING_SAFETY_CONTROLS)
            for t_bs in rule.get("trigger_barrier_states", []):
                if t_bs in states:
                    matched_triggers.append(f"Barrier state compromised ({t_bs})")
                    evidence_snippets.append(t_bs)
                    break

            # Qualification check: must have at least 2 distinct trigger factors or a primary critical barrier match
            is_valid_match = False
            confidence = 0.85
            if len(matched_triggers) >= 2:
                is_valid_match = True
                confidence = 0.95
            elif rule_id == "SAFE_MECHANICAL_LIFTING" and ("LIFT" in act or "LIFTING" in barriers or "SUSPENDED" in energy):
                is_valid_match = True
                confidence = 0.90
            elif rule_id == "LINE_OF_FIRE" and ("LINE OF FIRE" in exposure or "TRAJECTORY" in exposure or "DROPPED" in energy):
                is_valid_match = True
                confidence = 0.92
            elif rule_id == "BYPASSING_SAFETY_CONTROLS" and any(st in ["BYPASSED", "REMOVED"] for st in states):
                is_valid_match = True
                confidence = 0.94
            elif rule_id == "ENERGY_ISOLATION" and ("ISOLATION" in act or "LOTO" in act or "ELECTRICAL" in energy):
                is_valid_match = True
                confidence = 0.92
            elif rule_id == "WORKING_AT_HEIGHT" and ("HEIGHT" in act or "HEIGHT" in energy or "FALL_PROTECTION" in barriers):
                is_valid_match = True
                confidence = 0.92

            if is_valid_match:
                matches.append({
                    "lsr": rule_id,
                    "rule_name": rule_name,
                    "evidence": "; ".join(filter(None, set(evidence_snippets))),
                    "reason": f"Triggered by: {', '.join(matched_triggers)}",
                    "confidence": confidence
                })

        return matches

    def classify(self, event: SafetyEvent) -> SafetyEvent:
        """Convenience method that assigns classified rules to event.lsr and returns the event."""
        matches = self.classify_event(event)
        event.lsr = [m["lsr"] for m in matches]
        return event


lsr_classifier = LSRClassifier()
