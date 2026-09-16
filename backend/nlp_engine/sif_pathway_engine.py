from typing import Dict, List, Any, Optional, Tuple
from nlp_engine.semantic_layer import SemanticSafetyLayer
from nlp_engine.event_normalizer import NormalizedSafetyEvent

# Prototype SIF risk model. Requires validation and calibration against HSE-labelled OIL data before operational use.

class SIFPathwayEngine:
    """
    Central AI Risk Pathway Intelligence Layer for ShramRakshak (SIH 26165).
    Transforms safety events into structured, explainable causal reasoning:
    HAZARD → ENERGY → EXPOSURE → BARRIER → BARRIER FAILURE → POTENTIAL CONSEQUENCE → SIF

    Strict Safety Communication Rule:
    The engine identifies POTENTIAL SIF pathways from available evidence;
    it does NOT claim to predict exact accidents.
    """

    def analyze_event(self, event: NormalizedSafetyEvent, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        narrative = event.narrative or ""
        activity = event.activity or context.get("activity", "General Operations")
        hazard_in = event.hazard or context.get("hazard", "")

        # 1. Semantic NLP Analysis for Paraphrase & Intent Resolution
        semantic_res = SemanticSafetyLayer.analyze_semantics(narrative, {
            "activity": activity,
            "hazard": hazard_in,
            "location": event.location
        })

        # 2. Extract 6 Core Pathway Dimensions
        # Hazard
        hazard = event.hazard if event.hazard and event.hazard != "Unspecified Safety Hazard" else (
            semantic_res["domain"] + " Hazard" if semantic_res["matched"] else "Operational Safety Hazard"
        )
        
        # Energy Source
        energy_source = semantic_res.get("energy_source") or self._infer_energy_source(narrative, activity)

        # Human Exposure
        exposure = event.exposure if event.exposure and "worker" in event.exposure.lower() else (
            semantic_res.get("exposure") or self._infer_exposure(narrative, event)
        )

        # Barrier / Control
        barrier = event.barrier if event.barrier and event.barrier != "Standard Operational Controls" else (
            semantic_res.get("barrier") or self._infer_barrier(narrative, activity)
        )

        # Barrier Failure
        barrier_failure = event.barrier_failure if event.barrier_failure and "not verified" not in event.barrier_failure.lower() else (
            semantic_res.get("barrier_failure") or self._infer_barrier_failure(narrative)
        )

        # Potential Consequence (Never "Predicted Accident")
        potential_consequence = semantic_res.get("potential_consequence") or self._infer_consequence(energy_source, activity)

        # 3. Construct the Structured SIF Pathway String
        sif_pathway = (
            f"{hazard} → "
            f"Energy Source: {energy_source} → "
            f"Exposure: {exposure} → "
            f"Barrier: {barrier} → "
            f"Failure: {barrier_failure} → "
            f"Potential Consequence: {potential_consequence}"
        )

        # 4. Multidimensional Safety Scoring (0-100)
        score_breakdown, risk_score = self._compute_multidimensional_score(
            narrative=narrative,
            energy_source=energy_source,
            exposure=exposure,
            barrier_failure=barrier_failure,
            potential_consequence=potential_consequence,
            semantic_matched=semantic_res["matched"],
            has_visual_evidence=bool(event.evidence_image or event.evidence_url)
        )

        # 5. SIF Potential Determination (Recall-Oriented Campbell Institute Logic)
        is_low_energy = "low-energy" in energy_source.lower() or "housekeeping" in activity.lower()
        if is_low_energy and "suspended" not in narrative.lower() and "height" not in narrative.lower():
            sif_potential = False
            risk_score = min(risk_score, 45)
            risk_level = "MEDIUM" if risk_score >= 35 else "LOW"
        else:
            sif_potential = risk_score >= 60 or (
                ("high" in energy_source.lower() or "stored" in energy_source.lower() or "gravitational" in energy_source.lower())
                and ("breach" in barrier_failure.lower() or "bypassed" in barrier_failure.lower() or "exposed" in exposure.lower())
            )
            risk_level = "CRITICAL" if risk_score >= 80 else ("HIGH" if risk_score >= 60 else ("MEDIUM" if risk_score >= 40 else "LOW"))

        # 6. Separate Confidence & Evidence Strength
        confidence, confidence_level, needs_review = self._evaluate_confidence(
            narrative=narrative,
            semantic_res=semantic_res,
            has_visual_evidence=bool(event.evidence_image or event.evidence_url),
            source=event.source
        )

        evidence_strength = "HIGH" if bool(event.evidence_image or event.evidence_url) or len(narrative.split()) > 18 else (
            "MEDIUM" if len(narrative.split()) >= 8 else "LOW"
        )

        # 7. Explainable "WHY FLAGGED?" Reasoning Bullets
        reasoning = self._generate_reasoning_bullets(
            energy_source=energy_source,
            exposure=exposure,
            barrier_failure=barrier_failure,
            potential_consequence=potential_consequence,
            sif_potential=sif_potential,
            risk_score=risk_score
        )

        # 8. Operational Action Generation
        recommended_action = self._generate_recommended_actions(
            activity=activity,
            barrier=barrier,
            barrier_failure=barrier_failure
        )

        return {
            "hazard": hazard,
            "energy_source": energy_source,
            "exposure": exposure,
            "barrier": barrier,
            "barrier_failure": barrier_failure,
            "potential_consequence": potential_consequence,
            "sif_pathway": sif_pathway,
            "sif_potential": sif_potential,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "evidence_strength": evidence_strength,
            "needs_hse_review": needs_review,
            "reasoning": reasoning,
            "score_breakdown": score_breakdown,
            "recommended_action": recommended_action,
            "model_version": "Hybrid Safety Reasoning v1",
            "rule_version": "SIF Rules v1 (Campbell Matrix)",
            "validation_note": "Prototype SIF risk model. Requires validation and calibration against HSE-labelled OIL data before operational use."
        }

    def _infer_energy_source(self, text: str, activity: str) -> str:
        t = text.lower()
        if any(w in t for w in ["crane", "hoist", "suspended", "sling", "lift", "rigging"]):
            return "Mechanical / Gravitational Potential Energy"
        if any(w in t for w in ["height", "fall", "scaffold", "ladder", "lanyard", "grating", "cellar"]):
            return "Gravitational Potential Energy (>1.8m)"
        if any(w in t for w in ["voltage", "breaker", "electrical", "arc", "motor"]):
            return "High-Voltage Electrical Stored Energy"
        if any(w in t for w in ["pressure", "manifold", "valve", "pneumatic", "bleed"]):
            return "High-Pressure Hydraulic / Pneumatic Stored Energy"
        if any(w in t for w in ["welding", "torch", "flame", "spark", "hydrocarbon", "hot work"]):
            return "Thermal Combustion / Flammable Vapor Energy"
        if any(w in t for w in ["tank", "confined", "h2s", "toxic", "gas", "manway"]):
            return "Chemical Toxicity / Oxygen Deficient Atmosphere"
        if any(w in t for w in ["truck", "forklift", "vehicle", "tanker", "reverse"]):
            return "Mobile Heavy Equipment Kinetic Momentum"
        if any(w in t for w in ["dunnage", "trip", "housekeeping", "offcut"]):
            return "Low-Energy Physical Walkway Obstruction"
        return "Mechanical / Operational Equipment Energy"

    def _infer_exposure(self, text: str, event: NormalizedSafetyEvent) -> str:
        t = text.lower()
        if "walkway" in t or "corridor" in t:
            return "Personnel active in shared pedestrian access corridor"
        if "under" in t or "line of fire" in t or "swing" in t:
            return "Personnel positioned directly in drop radius / line of fire"
        if "at height" in t or "elevation" in t:
            return "Worker active at elevated work point without continuous secondary tie-off"
        if "manway" in t or "tank" in t:
            return "Worker present inside uncertified confined compartment"
        return f"Personnel present within active equipment operational boundary"

    def _infer_barrier(self, text: str, activity: str) -> str:
        t = text.lower()
        if "lift" in activity.lower() or "crane" in t:
            return "Lifting Exclusion Zone & Controlled Swing Radius"
        if "height" in activity.lower() or "scaffold" in t:
            return "100% Tie-Off Fall Arrest System & Perimeter Handrails"
        if "isolation" in activity.lower() or "loto" in t or "valve" in t:
            return "Positive Lockout-Tagout (LOTO) & Zero-Energy Verification"
        if "hot work" in activity.lower() or "weld" in t:
            return "Continuous Gas Testing Certification & Fire Watch Containment"
        if "confined" in activity.lower() or "tank" in t:
            return "Atmospheric Certification & Dedicated Entry Standby Attendant"
        if "driving" in activity.lower() or "truck" in t:
            return "Banksman Marshaling & Pedestrian Segregation Barrier"
        return "Standard Exclusion Perimeter & Personal Protective Equipment"

    def _infer_barrier_failure(self, text: str) -> str:
        t = text.lower()
        if "chain barrier was left open" in t or "barrier was displaced" in t:
            return "Physical exclusion barrier was left open / displaced"
        if "disconnected" in t or "unhooked" in t:
            return "Mandatory 100% tie-off fall arrest anchorage was discontinued"
        if "before" in t and ("lock" in t or "gas test" in t or "loto" in t):
            return "Pre-work verification step bypassed before initiating hazardous task"
        if "bypassed" in t or "defeated" in t:
            return "Safety control procedure was bypassed or overridden"
        if "without banksman" in t or "ground marshal" in t:
            return "Required human safeguarding marshal was absent during heavy movement"
        return "Exclusion boundary breached during active hazard presence"

    def _infer_consequence(self, energy_source: str, activity: str) -> str:
        e = energy_source.lower()
        if "gravitational" in e and "height" in e:
            return "Uncontrolled fall from elevation resulting in catastrophic trauma"
        if "gravitational" in e or "lifting" in e:
            return "Struck-by, crushing, or fatal blunt force trauma under dropped load"
        if "electrical" in e:
            return "Arc flash blast, severe electrical burns, or electrocution"
        if "pneumatic" in e or "pressure" in e:
            return "High-pressure fluid injection or projectile impact injury"
        if "thermal" in e or "combustion" in e:
            return "Vapor cloud flash fire, explosion, or third-degree burns"
        if "toxic" in e or "asphyxiat" in e:
            return "Acute toxic gas poisoning or asphyxiation"
        if "kinetic" in e or "momentum" in e:
            return "Run-over collision, pinned against structure, or fatal crushing"
        return "Physical struck-by or acute occupational injury"

    def _compute_multidimensional_score(
        self,
        narrative: str,
        energy_source: str,
        exposure: str,
        barrier_failure: str,
        potential_consequence: str,
        semantic_matched: bool,
        has_visual_evidence: bool
    ) -> Tuple[Dict[str, int], int]:
        """
        Multidimensional prototype SIF scoring formula:
        Hazard severity: 0-20
        Energy source magnitude: 0-15
        Human exposure: 0-20
        Barrier failure: 0-20
        Potential consequence severity: 0-15
        LSR relevance: 0-5
        Evidence / context consistency: 0-5
        Total = 100
        """
        t = narrative.lower()
        e = energy_source.lower()

        # 1. Hazard severity (0-20)
        if any(w in t for w in ["crane", "suspended", "height", "tank", "confined", "loto", "415v", "high pressure"]):
            hazard_score = 18 if not any(w in t for w in ["3-ton", "24m", "95%", "fatal"]) else 20
        elif any(w in t for w in ["revers", "forklift", "weld", "spark"]):
            hazard_score = 15
        elif any(w in t for w in ["housekeeping", "trip", "offcut"]):
            hazard_score = 6
        else:
            hazard_score = 12

        # 2. Energy source magnitude (0-15)
        if "high-voltage" in e or "toxic" in e or "24m" in t or "3-ton" in t:
            energy_score = 15
        elif any(w in e for w in ["gravitational", "kinetic", "thermal", "pressure", "stored"]):
            energy_score = 12
        elif "low-energy" in e:
            energy_score = 4
        else:
            energy_score = 8

        # 3. Human exposure (0-20)
        if any(w in t for w in ["stepped inside", "under suspended", "crossed", "unhooked", "opened terminal"]):
            exposure_score = 18 if not any(w in t for w in ["walkway", "occupied", "active"]) else 20
        elif any(w in t for w in ["corridor", "near"]):
            exposure_score = 14
        else:
            exposure_score = 8

        # 4. Barrier failure (0-20)
        if any(w in t for w in ["bypassed", "left open", "displaced", "disconnected", "removed", "without"]):
            barrier_score = 18 if not any(w in t for w in ["chain barrier", "lanyard", "lock-out"]) else 20
        elif any(w in t for w in ["unmonitored", "not established"]):
            barrier_score = 14
        else:
            barrier_score = 8

        # 5. Potential consequence severity (0-15)
        if any(w in potential_consequence.lower() for w in ["fatal", "catastrophic", "crushing", "electrocution", "asphyxiation", "explosion"]):
            consequence_score = 15
        elif any(w in potential_consequence.lower() for w in ["injection", "burns", "struck-by"]):
            consequence_score = 12
        elif "slip" in potential_consequence.lower() or "abrasion" in potential_consequence.lower():
            consequence_score = 4
        else:
            consequence_score = 8

        # 6. LSR relevance (0-5)
        lsr_score = 5 if semantic_matched else 3

        # 7. Evidence / context consistency (0-5)
        evidence_score = 5 if has_visual_evidence else 4

        total_score = min(100, max(0, (
            hazard_score + energy_score + exposure_score + barrier_score + consequence_score + lsr_score + evidence_score
        )))

        breakdown = {
            "hazard_severity": hazard_score,
            "energy_source": energy_score,
            "exposure": exposure_score,
            "barrier_failure": barrier_score,
            "potential_consequence": consequence_score,
            "lsr_relevance": lsr_score,
            "evidence_context": evidence_score
        }

        return breakdown, total_score

    def _evaluate_confidence(
        self,
        narrative: str,
        semantic_res: Dict[str, Any],
        has_visual_evidence: bool,
        source: str
    ) -> Tuple[int, str, bool]:
        """
        Calculates AI Confidence independently from Risk Score:
        Confidence evaluates signal clarity, completeness of data, and consistency.
        If confidence < 55: triggers 'HUMAN HSE REVIEW REQUIRED'.
        """
        words = len(narrative.split())
        score = 50

        if semantic_res.get("matched"):
            score += 25
        if has_visual_evidence:
            score += 15
        if words >= 15:
            score += 10
        elif words < 6:
            score -= 25

        if source == "CCTV_EVENT" and has_visual_evidence:
            score += 10

        confidence = min(95, max(25, score))

        if confidence >= 75:
            confidence_level = "HIGH"
            needs_review = False
        elif confidence >= 55:
            confidence_level = "MEDIUM"
            needs_review = False
        else:
            confidence_level = "LOW"
            needs_review = True

        return confidence, confidence_level, needs_review

    def _generate_reasoning_bullets(
        self,
        energy_source: str,
        exposure: str,
        barrier_failure: str,
        potential_consequence: str,
        sif_potential: bool,
        risk_score: int
    ) -> List[str]:
        if sif_potential:
            return [
                f"High-energy hazard source identified: {energy_source}",
                f"Personnel exposure confirmed: {exposure}",
                f"Critical safety barrier compromised: {barrier_failure}",
                f"Potential severe consequence: {potential_consequence}",
                f"Campbell Institute SIF precursor threshold exceeded (Score: {risk_score}/100)"
            ]
        else:
            return [
                f"Low-energy hazard source observed: {energy_source}",
                "No active stored energy, elevated fall potential, or heavy mobile plant line-of-fire",
                f"Minor barrier non-compliance: {barrier_failure}",
                f"Potential localized consequence: {potential_consequence}",
                "Classified as routine workplace safety observation below SIF precursor threshold"
            ]

    def _generate_recommended_actions(
        self,
        activity: str,
        barrier: str,
        barrier_failure: str
    ) -> Dict[str, Any]:
        act_lower = activity.lower()
        if "lifting" in act_lower:
            primary = "Immediately halt crane movement and clear all personnel from the lifting exclusion zone."
            steps = [
                "Issue immediate stop-work command to crane operator and dogman",
                "Ensure workers clear the swing radius and drop trajectory boundary",
                "Re-establish physical barricades around the crane lifting perimeter",
                "Supervisor confirms barrier restored before lifting operations resume"
            ]
        elif "height" in act_lower:
            primary = "Halt elevated work activity and enforce 100% positive tie-off anchorage."
            steps = [
                "Instruct elevated personnel to anchor dual lanyards to certified structural lifeline",
                "Inspect scaffolding platform for missing toe-boards or loose gratings",
                "Verify working-at-height permit compliance and harness inspection tags",
                "Supervisor re-evaluates work-at-height controls prior to re-entry"
            ]
        elif "isolation" in act_lower:
            primary = "Stop electrical/maintenance task and perform verified zero-energy lockout-tagout."
            steps = [
                "Suspend maintenance activity on motor/breaker/piping equipment",
                "Apply personal LOTO padlock and tag to primary circuit isolation point",
                "Witness residual pressure bleed-down or electrical zero-energy verification",
                "Authorize work resumption only after positive energy isolation is witnessed"
            ]
        elif "hot work" in act_lower:
            primary = "Extinguish open flame/sparks and execute atmospheric combustible gas testing."
            steps = [
                "De-energize welding rig or oxy-acetylene torch cutting equipment",
                "Deploy certified four-gas monitor across work area and drain sumps",
                "Install fire-retardant blankets around sparks trajectory boundary",
                "Confirm gas testing values are 0% LEL before re-igniting hot work equipment"
            ]
        elif "confined" in act_lower:
            primary = "Evacuate personnel from compartment and station dedicated standby attendant."
            steps = [
                "Direct personnel to exit vessel/pit compartment immediately",
                "Station dedicated entry attendant with emergency retrieval winch at manway",
                "Perform continuous multi-gas atmosphere testing (O2, H2S, LEL, CO)",
                "Authorize re-entry only with valid confined space entry permit"
            ]
        elif "driving" in act_lower:
            primary = "Halt heavy vehicle movement and post banksman spotter in pedestrian corridor."
            steps = [
                "Order driver to apply park brake and cease reversing maneuver",
                "Deploy banksman with high-visibility flags to direct vehicle movements",
                "Verify pedestrian barriers and audible reversing warning horns are functional",
                "Resume transit only with continuous eye-contact guidance"
            ]
        else:
            primary = "Address physical workplace obstruction and re-verify perimeter boundaries."
            steps = [
                "Remove physical dunnage or obstacle from pedestrian transit walkway",
                "Confirm correct fit and fastening of mandatory PPE (hard hat with chin strap)",
                "Review daily toolbox talk safety expectations with work crew",
                "Log safety observation in asset HSSE tracking system"
            ]

        return {
            "primary": primary,
            "steps": steps,
            "barrier_context": barrier
        }
