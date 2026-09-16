import re
from typing import Dict, List, Tuple

class SIFClassifier:
    """
    Deterministic & Explainable SIF (Serious Injury & Fatality) Precursor Classifier.
    Evaluates incident narratives and contextual fields according to standard
    Campbell Institute / Oil & Gas Industry SIF precursor criteria.
    """

    # High-energy / high-consequence hazard indicators (Campbell Institute SIF Matrix)
    SIF_HAZARD_PATTERNS = [
        (r"\b(lifting\s+exclusion\s+zone|suspended\s+load|crane|hoist|rigging|slewing|spool|load\s+line)\b", 
         "High-energy mechanical lifting hazard with potential suspended load release", 35),
        (r"\b(restricted\s+zone|exclusion\s+zone|danger\s+zone|perimeter\s+breach|exclusion\s+boundary)\b", 
         "Physical entry into an active high-risk exclusion boundary", 25),
        (r"\b(line\s+of\s+fire|crush(ing)?|pinch\s+point|swing\s+radius|struck\s+by|recoil)\b", 
         "Worker positioned directly in the trajectory/line of fire of moving machinery", 25),
        (r"\b(working\s+at\s+height|fall\s+hazard|scaffold(ing)?|elevat(ed|ion)|ladder|lanyard|cellar)\b", 
         "Fall-from-height potential capable of causing serious trauma", 30),
        (r"\b(hot\s+work|explosive\s+atmosphere|open\s+flame|spark|weld(ing)?|torch|flammable)\b", 
         "Thermal/combustion hazard in active hydrocarbon processing area", 30),
        (r"\b(confined\s+space|toxic\s+gas|oxygen\s+deficiency|asphyxiation|manway|tank\s+t-|culvert|pit)\b", 
         "Atmospheric / asphyxiation hazard in an enclosed compartment", 35),
        (r"\b(pressur(ized|e)|high\s+voltage|stored\s+energy|loto|breaker|zero\s+energy|isolation)\b", 
         "Uncontrolled stored energy / high-pressure release mechanism", 35),
        (r"\b(revers(ing)?|pedestrian\s+walkway|pedestrian\s+corridor|banksman|forklift|truck)\b", 
         "Heavy plant and pedestrian trajectory intersection in shared corridor", 25),
    ]

    # Barrier / Control failure indicators
    BARRIER_FAILURE_PATTERNS = [
        (r"\b(barrier\s+(breach(ed)?|fail(ed)?)|uncontrolled\s+access|bypassed|omitted|skipped|missing|compromised|displaced|unlatched|loos(e|ened))\b",
         "Primary physical or operational safety barrier was compromised or bypassed", 20),
        (r"\b(passport\s+paused|permit\s+breach|unauthorized|unverified|lock-?out|tag-?out|loto\s+padlock)\b",
         "Formal administrative / permit-to-work / isolation control broken", 15),
        (r"\b(secondary\s+control|visual\s+monitoring\s+alone|standby|attendant|spotter|banksman|fire\s+watch)\b",
         "Absence of secondary redundant safeguarding barrier or standby attendant", 15),
    ]

    # Routine PPE indicators (explicitly non-SIF in isolation)
    ROUTINE_PPE_PATTERNS = [
        r"\b(helmet|ppe|hard\s*hat|head\s+protection|safety\s+glasses|gloves)\b"
    ]

    def classify(self, text: str, context: Dict = None) -> Tuple[bool, int, str, str, List[str]]:
        """
        Classifies incident narrative and context into:
        (sif_potential, risk_score, risk_level, reason, why_flagged)
        """
        context = context or {}
        event_type = str(context.get("event_type", "")).upper()
        activity = str(context.get("activity", "")).lower()
        hazard = str(context.get("hazard", "")).lower()
        barrier_failure = str(context.get("barrier_failure", "")).lower()
        full_text = f"{text} {activity} {hazard} {barrier_failure} {event_type}".lower()

        why_flagged: List[str] = []
        score_components: List[int] = []

        # Check for High-Energy SIF Hazard patterns
        high_energy_matched = False
        for pattern, explanation, points in self.SIF_HAZARD_PATTERNS:
            if re.search(pattern, full_text):
                high_energy_matched = True
                score_components.append(points)
                if explanation not in why_flagged:
                    why_flagged.append(explanation)

        # Check for Barrier Failures
        barrier_matched = False
        for pattern, explanation, points in self.BARRIER_FAILURE_PATTERNS:
            if re.search(pattern, full_text):
                barrier_matched = True
                score_components.append(points)
                if explanation not in why_flagged:
                    why_flagged.append(explanation)

        # Special Rule 1: Low-energy housekeeping / trip hazard
        if re.search(r"\b(dunnage|trip\s+hazard|protruding|walkway\s+obstruction|housekeeping)\b", full_text) and not high_energy_matched:
            risk_score = 28
            risk_level = "LOW"
            sif_potential = False
            reason = "Low-energy physical obstruction in walkway. No stored energy, suspended load, fall from height, or mobile plant collision hazard present."
            why_flagged = [
                "Minor physical walkway obstruction without high-energy mechanism",
                "Low consequence potential (slips, trips, low-level falls on same level)",
                "Standard workplace housekeeping observation"
            ]
            return sif_potential, risk_score, risk_level, reason, why_flagged

        # Special Rule 2: Vehicle administrative non-compliance without pedestrian conflict (seatbelt/radio)
        if ("seatbelt" in full_text or "radio" in full_text) and "revers" not in full_text and "pedestrian" not in full_text and not ("corridor" in full_text and "walk" in full_text):
            risk_score = 45
            risk_level = "MEDIUM"
            sif_potential = False
            reason = "Vehicle operation policy non-compliance (seatbelt/handset use). Standard driving safety observation without high-speed collision trajectory or pedestrian conflict."
            why_flagged = [
                "Occupant restraint or distracted driving policy non-compliance",
                "Internal site transit speed; no immediate collision trajectory observed",
                "Classified as preventive driver safety observation"
            ]
            return sif_potential, risk_score, risk_level, reason, why_flagged

        # Special Rule 3: Isolated PPE non-compliance is NOT a SIF event
        is_ppe_violation = ("helmet" in event_type.lower() or "ppe" in event_type.lower() or "cranial" in full_text or "hard hat" in full_text)
        has_restricted_zone = ("zone" in event_type.lower() or "breach" in event_type.lower() or "passport" in event_type.lower())
        has_lifting_context = ("lift" in activity or "lift" in hazard or "suspended" in full_text or "crane" in full_text)

        if is_ppe_violation and not has_restricted_zone and not has_lifting_context and not high_energy_matched:
            # Baseline PPE non-compliance
            risk_score = 42
            risk_level = "MEDIUM"
            sif_potential = False
            reason = (
                "Worker non-compliance with required personal protective equipment (head protection). "
                "Classified as a standard PPE safety observation; does not meet SIF precursor criteria "
                "in the absence of high-energy overhead hazards or active mechanical lifting."
            )
            why_flagged = [
                "Mandatory head PPE omitted by detected personnel",
                "Routine safety observation without direct high-energy line-of-fire exposure",
                "Administrative PPE barrier breached; no catastrophic release mechanism identified"
            ]
            return sif_potential, risk_score, risk_level, reason, why_flagged

        # Calculate deterministic risk score
        base_score = 20
        calculated_score = base_score + sum(score_components)

        # Activity-based multipliers
        if "lifting" in activity or "lifting" in full_text:
            calculated_score += 15
            if "Mechanical lifting operations active" not in why_flagged:
                why_flagged.append("Active mechanical lifting operation in progress within camera perimeter")

        # Clamp score between 10 and 100
        risk_score = max(10, min(100, calculated_score))

        # Determine SIF Potential and Risk Level
        # Prioritize recall: High energy hazard + barrier failure or zone breach = SIF YES
        if (high_energy_matched or has_restricted_zone or has_lifting_context) and risk_score >= 60:
            sif_potential = True
        else:
            sif_potential = False

        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 65:
            risk_level = "HIGH"
        elif risk_score >= 45:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Generate clear reason statement
        if sif_potential:
            reason = (
                f"Flagged as a SIF PRECURSOR ({risk_level} risk, score {risk_score}/100): "
                f"Incident involves an active high-risk zone/activity ({activity or 'Exclusion Area'}) "
                f"where compromised control barriers expose personnel to potential life-altering or fatal harm."
            )
        else:
            reason = (
                f"Standard Safety Observation ({risk_level} risk, score {risk_score}/100): "
                f"Identified hazard requires corrective supervisory action but lacks immediate SIF consequence energy."
            )

        return sif_potential, risk_score, risk_level, reason, why_flagged
