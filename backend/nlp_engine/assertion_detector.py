"""
SHRAMRAKSHAK: Context-Aware Assertion & Evidence Spans Engine
SIH 2026 Problem Statement: SIH26165

Implements deep linguistic modality analysis:
- OBSERVED FACT
- NEGATED CONDITION (e.g. "No worker entered the exclusion zone")
- HYPOTHETICAL CONDITION (e.g. "If the sling fails, the suspended load could fall")
- POST-EVENT CONDITION (e.g. "Barricade was installed after the incident")

Extracts exact character evidence spans to guarantee explainability and prevent
superficial keyword matching.
"""

import re
from typing import Dict, List, Any, Tuple, Optional
from safety_memory import AssertionStatus, EvidenceSpan, SafetyEvent, HSEValidationStatus


class AssertionDetector:
    """
    Evaluates linguistic assertion status, modality, and temporal framing
    of safety reports to prevent false positive SIF precursor classifications.
    """

    # Negation trigger patterns that modify exposure or violation
    NEGATION_PATTERNS = [
        (r"\b(no\s+(worker|personnel|contractor|person|employee|one|body)\s+(entered|stepped|crossed|went\s+into|was\s+inside))\b", "Exposure explicitly negated"),
        (r"\b(neither\s+\w+\s+nor\s+\w+\s+(entered|breached))\b", "Exposure explicitly negated"),
        (r"\b(did\s+not\s+(enter|cross|breach|step\s+into|approach))\b", "Action did not occur"),
        (r"\b(without\s+any\s+(breach|entry|violation|incident))\b", "No breach observed"),
        (r"\b(zero\s+(workers?|personnel)\s+(inside|in|entered))\b", "Zero personnel exposure"),
        (r"\b(prevented\s+from\s+entering)\b", "Exposure successfully prevented"),
        (r"\b(no\s+breach\s+(occurred|observed|detected))\b", "Absence of breach"),
        (r"\b(no\s+worker\s+was\s+(exposed|present|in\s+the))\b", "Worker presence negated")
    ]

    # Hypothetical / Counterfactual patterns
    HYPOTHETICAL_PATTERNS = [
        (r"\b(if\s+the\s+[\w\s]{1,25}\s+(fails?|breaks?|parts?|gives\s+way|snaps?|drops?))\b", "Hypothetical barrier failure clause"),
        (r"\b(should\s+the\s+[\w\s]{1,20}\s+fail)\b", "Hypothetical conditional clause"),
        (r"\b(in\s+case\s+of\s+[\w\s]{1,20}\s+failure)\b", "Contingency hypothetical clause"),
        (r"\b(could\s+have\s+(fallen|struck|dropped|injured|released))\b", "Potential consequence, not observed occurrence"),
        (r"\b(might\s+have\s+(resulted|led|caused))\b", "Potential consequence, not observed occurrence"),
        (r"\b(potential\s+for\s+[\w\s]{1,25}\s+if)\b", "Conditional consequence potential")
    ]

    # Post-Event / Temporal corrective patterns
    POST_EVENT_PATTERNS = [
        (r"\b(installed\s+after\s+(the\s+)?(incident|event|observation|inspection))\b", "Action taken after the event; barrier was absent during original incident"),
        (r"\b(rectified\s+(afterwards|subsequently|later))\b", "Post-event remediation"),
        (r"\b(barricade\s+was\s+(placed|installed|erected)\s+after)\b", "Post-event barrier installation"),
        (r"\b(subsequently\s+(isolated|barricaded|cleared|corrected))\b", "Post-event condition"),
        (r"\b(following\s+the\s+(event|incident),\s+[\w\s]{1,30}\s+(was\s+|were\s+)?installed)\b", "Post-event condition")
    ]

    # Core high-energy hazard indicators
    HAZARD_PATTERNS = [
        (r"\b(suspended\s+load|suspended\s+pipe|suspended\s+drill|crane\s+load|hoisted\s+load)\b", "Suspended Load", "Gravitational Potential Energy"),
        (r"\b(crane|hoist|derrick|rigging|wireline|boom)\b", "Mechanical Crane / Rigging", "Kinetic / Mechanical Energy"),
        (r"\b(high\s+pressure|pressurized\s+line|manifold|bleed-off|wellhead\s+pressure)\b", "High-Pressure Fluid / Gas", "Stored Pressure Energy"),
        (r"\b(hot\s+work|open\s+flame|spark|welding|grinding\s+near\s+flammables?)\b", "Thermal Ignition / Flash Fire", "Thermal / Chemical Energy"),
        (r"\b(confined\s+space|toxic\s+gas|h2s|atmospheric\s+deficiency|vessel\s+entry)\b", "Atmospheric Toxicity / Asphyxiation", "Atmospheric / Chemical Energy"),
        (r"\b(working\s+at\s+height|elevated\s+platform|scaffolding|fall\s+hazard)\b", "Fall From Height", "Gravitational Energy (>1.8m)"),
        (r"\b(mobile\s+plant|heavy\s+vehicle|tanker|forklift|reversing\s+truck)\b", "Heavy Vehicle Movement", "Kinetic Vehicle Energy")
    ]

    # Exposure indicators
    EXPOSURE_PATTERNS = [
        (r"\b(personnel\s+observed\s+below|worker\s+under|working\s+under|stepped\s+under)\b", "Personnel positioned directly beneath hazard"),
        (r"\b(entered\s+[\w\s]{0,15}\s+(exclusion\s+zone|drop\s+area|restricted\s+area|swing\s+radius))\b", "Person inside defined exclusion boundary"),
        (r"\b(crossed\s+[\w\s]{0,10}\s+(crane\s+exclusion\s+zone|perimeter|barricade))\b", "Person crossed boundary barrier into hazard zone"),
        (r"\b(line\s+of\s+fire|in\s+the\s+trajectory|in\s+crush\s+zone)\b", "Worker directly in line of fire / crush trajectory"),
        (r"\b(in\s+active\s+corridor|in\s+shared\s+walkway)\b", "Pedestrian in vehicle path")
    ]

    # Barrier & Barrier Condition indicators
    BARRIER_PATTERNS = [
        (r"\b(exclusion\s+zone|exclusion\s+boundary|drop\s+zone\s+perimeter)\b", "Lifting Exclusion Zone", "Exclusion Boundary"),
        (r"\b(physical\s+barricade|barricade|barrier\s+tape|hard\s+guarding)\b", "Physical Barricade", "Physical Guarding"),
        (r"\b(zero\s+energy\s+verification|lockout-?tagout|loto|lock\s+out)\b", "Positive Isolation / LOTO", "Energy Isolation"),
        (r"\b(continuous\s+gas\s+test(ing)?|atmospheric\s+monitor|gas\s+detector)\b", "Continuous Gas Detection", "Atmospheric Clearance"),
        (r"\b(fall\s+arrest\s+system|harness|100%\s+tie-?off|lanyard)\b", "Fall Arrest System", "Personal Fall Protection"),
        (r"\b(pedestrian\s+segregation|banksman|spotter)\b", "Personnel Segregation & Spotter", "Procedural & Segregation Barrier")
    ]

    @classmethod
    def analyze_assertion(cls, text: str) -> Tuple[AssertionStatus, List[EvidenceSpan], Optional[str]]:
        """
        Detects whether the report contains negated, hypothetical, or post-event framing.
        Returns (assertion_status, assertion_spans, explanatory_note).
        """
        spans = []

        # 1. Check for Negation
        for pat, note in cls.NEGATION_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                spans.append(EvidenceSpan(
                    text=match.group(0),
                    category="assertion",
                    start=match.start(),
                    end=match.end(),
                    note=note
                ))
                return AssertionStatus.NEGATED, spans, f"Negated Condition: {note} ('{match.group(0)}'). Exposure did not occur."

        # 2. Check for Hypothetical statements
        for pat, note in cls.HYPOTHETICAL_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                spans.append(EvidenceSpan(
                    text=match.group(0),
                    category="assertion",
                    start=match.start(),
                    end=match.end(),
                    note=note
                ))
                return AssertionStatus.HYPOTHETICAL, spans, f"Hypothetical Condition: {note} ('{match.group(0)}'). Not an observed failure."

        # 3. Check for Post-Event statements
        for pat, note in cls.POST_EVENT_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                spans.append(EvidenceSpan(
                    text=match.group(0),
                    category="assertion",
                    start=match.start(),
                    end=match.end(),
                    note=note
                ))
                return AssertionStatus.POST_EVENT, spans, f"Post-Event Condition: {note} ('{match.group(0)}'). Barricade installed after incident."

        return AssertionStatus.OBSERVED_FACT, spans, "Observed Fact: Report describes an actual occurring event."

    @classmethod
    def extract_evidence_spans(cls, text: str) -> List[EvidenceSpan]:
        """
        Extracts all explainable evidence spans across Hazard, Exposure, Barrier, and Consequence.
        """
        spans: List[EvidenceSpan] = []

        # Hazard Spans
        for pat, h_name, _ in cls.HAZARD_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                spans.append(EvidenceSpan(
                    text=match.group(0),
                    category="hazard",
                    start=match.start(),
                    end=match.end(),
                    note=f"Identified Hazard: {h_name}"
                ))

        # Exposure Spans
        for pat, desc in cls.EXPOSURE_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                spans.append(EvidenceSpan(
                    text=match.group(0),
                    category="exposure",
                    start=match.start(),
                    end=match.end(),
                    note=desc
                ))

        # Barrier Spans
        for pat, b_name, b_type in cls.BARRIER_PATTERNS:
            for match in re.finditer(pat, text, re.IGNORECASE):
                spans.append(EvidenceSpan(
                    text=match.group(0),
                    category="barrier",
                    start=match.start(),
                    end=match.end(),
                    note=f"Critical Barrier: {b_name} ({b_type})"
                ))

        return spans

    @classmethod
    def evaluate_safety_event(cls, text: str, context: Optional[Dict[str, Any]] = None) -> SafetyEvent:
        """
        Core reasoning function that translates text into a fully qualified SafetyEvent,
        honoring negation, hypothetical reasoning, temporal status, and evidence spans.
        """
        context = context or {}
        event_id = context.get("event_id", f"EVT-NLP-{int(datetime.now().timestamp()*1000) % 1000000:06d}")
        location = context.get("location", "Demo Lifting Area")
        activity = context.get("activity", "Mechanical Lifting")
        source = context.get("source", "HUMAN_REPORT")
        camera_id = context.get("camera_id")

        # 1. Assertion and Modality analysis
        assertion_status, assertion_spans, assertion_note = cls.analyze_assertion(text)

        # 2. Extract Evidence Spans
        evidence_spans = cls.extract_evidence_spans(text) + assertion_spans

        # 3. Resolve Hazard and Energy
        hazard = "Suspended Crane Load"
        energy_source = "Gravitational / Kinetic Energy"
        for pat, h_name, e_name in cls.HAZARD_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                hazard = h_name
                energy_source = e_name
                break

        # 4. Resolve Exposure and Barrier
        exposure = "Worker positioned in hazardous exclusion zone"
        barrier = "Lifting Exclusion Zone & Barricade"
        barrier_state = "VIOLATED"
        consequence = "Catastrophic crushing / struck-by fatal injury"
        lsr = "Safe Mechanical Lifting"

        if "lifting" in activity.lower() or "crane" in text.lower() or "suspended" in text.lower():
            hazard = "Suspended / Moving Load"
            energy_source = "Mechanical / Gravitational Potential Energy"
            exposure = "Person inside lifting exclusion zone"
            barrier = "Lifting Exclusion Zone"
            barrier_state = "VIOLATED"
            consequence = "Catastrophic crushing / struck-by trauma"
            lsr = "Safe Mechanical Lifting"
            if "line of fire" in text.lower() or "swing" in text.lower():
                lsr = "Line of Fire"

        elif "isolation" in activity.lower() or "loto" in text.lower() or "pressure" in text.lower():
            hazard = "Uncontrolled Stored Pressure / Electrical Energy"
            energy_source = "Stored High-Pressure Hydraulic / Hydrocarbon"
            exposure = "Technician intervening on unverified system"
            barrier = "Positive Lockout-Tagout (LOTO) & Zero-Energy Verification"
            barrier_state = "NOT_VERIFIED"
            consequence = "High-pressure fluid injection / arc flash fatality"
            lsr = "Energy Isolation"

        elif "confined" in activity.lower() or "gas" in text.lower():
            hazard = "Atmospheric Toxicity / Oxygen Depletion"
            energy_source = "Toxic Chemical / Asphyxiating Gas"
            exposure = "Worker inside enclosed space without clearance"
            barrier = "Continuous Multi-Gas Detector Clearance"
            barrier_state = "COMPROMISED"
            consequence = "Asphyxiation / fatal atmospheric poisoning"
            lsr = "Confined Space Entry"

        elif "height" in activity.lower() or "scaffold" in text.lower() or "fall" in text.lower():
            hazard = "Elevation Fall Hazard (>1.8m)"
            energy_source = "Gravitational Potential Energy"
            exposure = "Worker active at elevated perimeter unhooked"
            barrier = "100% Tie-Off Fall Arrest System"
            barrier_state = "VIOLATED"
            consequence = "Fatal blunt force impact from height"
            lsr = "Working at Height"

        # 5. Apply Modality Rules to SIF Potential (Crucial SIH Requirement!)
        temporal_status = "DURING_EVENT"
        consequence_type = "POTENTIAL"

        if assertion_status == AssertionStatus.NEGATED:
            # "No worker entered the exclusion zone"
            sif_potential = "NOT_SIF"
            exposure = "Exposure NEGATED (No worker was present in exclusion zone)"
            barrier_state = "MAINTAINED"
            confidence = 90
            consequence = "No injury potential; physical controls prevented exposure"

        elif assertion_status == AssertionStatus.HYPOTHETICAL:
            # "If the sling fails, the suspended load could fall"
            sif_potential = "LOW"
            consequence_type = "HYPOTHETICAL"
            barrier_state = "MAINTAINED"
            exposure = "Hypothetical scenario; no active barrier breach occurred"
            confidence = 85
            consequence = "Hypothetical scenario; not an observed failure"

        elif assertion_status == AssertionStatus.POST_EVENT:
            # "Barricade was installed after the incident"
            temporal_status = "POST_EVENT"
            barrier_state = "POST_INSTALLATION"
            sif_potential = "HIGH"  # The original event was high, but note explains barrier was missing during event
            confidence = 85

        else:
            # OBSERVED FACT
            # Campbell Institute Matrix: High Energy + Exposure + Barrier Failure = HIGH SIF
            is_low_energy = re.search(r"\b(trip|dunnage|housekeeping|sweeping|office)\b", text, re.IGNORECASE)
            is_routine_ppe_only = re.search(r"\b(helmet|gloves?|glasses)\b", text, re.IGNORECASE) and not re.search(r"\b(zone|crane|suspended|height|gas|pressure|fall)\b", text, re.IGNORECASE)

            if is_low_energy or is_routine_ppe_only:
                sif_potential = "LOW" if is_low_energy else "MEDIUM"
                consequence = "Minor surface abrasion / first aid treatment"
            else:
                sif_potential = "HIGH"

        return SafetyEvent(
            event_id=event_id,
            incident_id=context.get("incident_id"),
            source=source,
            evidence_source_type="OBSERVED" if source in ["CCTV", "HUMAN_REPORT"] else "INFERRED",
            timestamp=context.get("timestamp", datetime.now().isoformat()),
            camera_id=camera_id,
            location=location,
            activity=activity,
            hazard=hazard,
            energy_source=energy_source,
            exposure=exposure,
            exposure_assertion=assertion_status,
            critical_barrier=barrier,
            barrier_state=barrier_state,
            potential_consequence=consequence,
            consequence_type=consequence_type,
            sif_potential=sif_potential,
            life_saving_rule=lsr,
            evidence_spans=evidence_spans,
            assertion_status=assertion_status,
            temporal_status=temporal_status,
            confidence=85,
            validation_status=HSEValidationStatus.CANDIDATE,
            raw_narrative=text,
            underlying_control_mechanism="Personnel Segregation / Exclusion-Zone Control" if "lifting" in activity.lower() else "Operational Safety Controls"
        )


from datetime import datetime
