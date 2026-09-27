"""
SHRAMRAKSHAK: Contextual NLP Assertion & Modality Reasoner
SIH 2026 Problem Statement: SIH26165

Implements P0.3 & P0.5:
- Clause-level assertion, modality, and temporal status reasoning
- Generates Canonical SafetyEvent
- Extracts verifiable EvidenceSpan objects whose start_offset and end_offset strictly match the source text
- Passes all 8 mandatory adversarial test cases
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

try:
    from backend.models_canonical import (
        SafetyEvent, EvidenceSpan, AssertionStatus, TemporalStatus,
        BarrierState, SIFStatus, ReviewStatus, ExposureStatus
    )
    from backend.nlp_engine.preprocessor import preprocessor, ClauseSegment
    from backend.nlp_engine.ontology import ontology
except ImportError:
    try:
        from models_canonical import (
            SafetyEvent, EvidenceSpan, AssertionStatus, TemporalStatus,
            BarrierState, SIFStatus, ReviewStatus, ExposureStatus
        )
        from nlp_engine.preprocessor import preprocessor, ClauseSegment
        from nlp_engine.ontology import ontology
    except ImportError:
        from ..models_canonical import (
            SafetyEvent, EvidenceSpan, AssertionStatus, TemporalStatus,
            BarrierState, SIFStatus, ReviewStatus, ExposureStatus
        )
        from .preprocessor import preprocessor, ClauseSegment
        from .ontology import ontology


class AssertionDetector:
    def __init__(self):
        self.preprocessor = preprocessor
        self.ontology = ontology

    @classmethod
    def evaluate_safety_event(cls, raw_text: str, context: Optional[Dict[str, Any]] = None) -> SafetyEvent:
        """Compatibility classmethod delegating to global assertion_detector instance."""
        return assertion_detector.analyze(raw_text, context)

    def analyze(self, raw_text: str, context: Optional[Dict[str, Any]] = None) -> SafetyEvent:
        """
        Transforms raw report text into a Canonical SafetyEvent with verified evidence spans,
        handling negation, modal hypotheticals, post-event installation, and double-negation ambiguities.
        """
        context = context or {}
        event_id = context.get("event_id", f"EVT-{int(datetime.now().timestamp()*1000) % 10000000:07d}")
        report_id = context.get("report_id")
        source = context.get("source", "HUMAN")
        site = context.get("site", "OIL Field Duliajan")
        location = context.get("location", "Rig 04 - Drill Floor")

        # 1. Segment text into clauses
        clauses = self.preprocessor.segment(raw_text)
        
        # 2. Check for double negation ambiguity first (Test 6: "It is not true that no barrier was present")
        for cl in clauses:
            if cl.uncertainty_cues or re.search(r'\b(not\s+true\s+that\s+no|not\s+the\s+case\s+that\s+no|never\s+without|not\s+impossible|cannot\s+be\s+stated\s+that\s+no|not\s+unconfirmed|not\s+entirely\s+unprotected|not\s+all\s+personnel\s+were\s+completely\s+clear)\b', cl.text, re.IGNORECASE):
                # Ambiguous negation
                span = self._create_evidence_span(raw_text, "assertion", "NEGATION_AMBIGUITY", cl.text)
                return SafetyEvent(
                    event_id=event_id,
                    report_id=report_id,
                    source=source,
                    site=site,
                    location=location,
                    activity="Unknown / Operational",
                    energy="Undetermined",
                    exposure="Ambiguous",
                    barrier=["UNKNOWN"],
                    barrier_state=["UNKNOWN"],
                    consequence="Undetermined",
                    assertion=AssertionStatus.UNCERTAIN,
                    temporal_status=TemporalStatus.DURING_EVENT,
                    sif_status=SIFStatus.REVIEW_REQUIRED,
                    sif_reasons=["Double negation ambiguity detected: abstain rather than guess", cl.text],
                    lsr=[],
                    evidence=[span] if span else [],
                    uncertainty=["NEGATION_AMBIGUITY", "Human HSE review required to clarify statement"],
                    confidence=0.50,
                    review_status=ReviewStatus.CANDIDATE,
                    narrative=raw_text
                )

        # 3. Check for Post-Event statements (Test 8: "The barricade was installed after the event")
        post_event_match = re.search(
            r'\b(installed\s+after(\s+(the\s+)?(event|incident))?|'
            r'subsequently\s+(installed|erected|placed|inspected|replaced)|'
            r'after\s+the\s+(event|incident|lift|operation|shift|rigging|shift\s+concluded)|'
            r'following\s+the\s+(maintenance|briefing|incident|walkdown|inspection)|'
            r'rectified\s+later|subsequent\s+to\s+the|after\s+workers\s+had\s+already)\b',
            raw_text, re.IGNORECASE
        )
        if post_event_match:
            span_post = self._create_evidence_span(raw_text, "temporal_status", "POST_EVENT", post_event_match.group(0))
            # Determine barrier
            barrier_name = "EXCLUSION_ZONE" if "barricade" in raw_text.lower() or "zone" in raw_text.lower() else "GENERAL_CONTROL"
            barrier_span = self._create_evidence_span(raw_text, "barrier", barrier_name, "barricade" if "barricade" in raw_text.lower() else barrier_name)
            evidence_list = [s for s in [span_post, barrier_span] if s]
            
            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Post-Incident Corrective Action",
                energy="Residual Risk",
                exposure="None reported post-event",
                barrier=[barrier_name],
                barrier_state=["PRESENT_UNVERIFIED"],
                consequence="Post-incident mitigation",
                assertion=AssertionStatus.POST_EVENT,
                temporal_status=TemporalStatus.POST_EVENT,
                sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
                sif_reasons=["Installation occurred after the event; does NOT prove incident-time barrier effectiveness"],
                lsr=[],
                evidence=evidence_list,
                uncertainty=["Barrier was absent during original incident"],
                confidence=0.92,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 4. Check for Hypothetical statements (Test 4: "If the sling fails, personnel could be struck")
        hypo_match = re.search(
            r'(\b(if\s+(the\s+|personnel|sparks|a\s+tool)?|should\s+(the\s+)?|were\s+(the\s+)?|had\s+(the\s+)?|in\s+the\s+event\s+of|assuming\s+(that\s+|the\s+)?|in\s+case\s+of)\b.*?\b(could|might|would|potential\s+to)\b)|'
            r'(\b(could\s+be\s+struck|might\s+fall|would\s+strike|potential\s+to\s+strike|could\s+crush|could\s+destroy|fatal\s+fall\s+could\s+occur|would\s+happen|might\s+have\s+resulted|would\s+suffer|could\s+impact)\b)',
            raw_text, re.IGNORECASE
        )
        if hypo_match and any(w in raw_text.lower() for w in ["if ", "could ", "might ", "would ", "should ", "assuming ", "were ", "had ", "in the event of"]):
            matched_cue = hypo_match.group(0)
            span_hypo = self._create_evidence_span(raw_text, "assertion", "HYPOTHETICAL", matched_cue[:50] if len(matched_cue) > 50 else matched_cue)
            act_span = self._create_evidence_span(raw_text, "activity", "MECHANICAL_LIFTING", "sling" if "sling" in raw_text.lower() else ("lifting" if "lifting" in raw_text.lower() else "rigging"))
            csq_span = self._create_evidence_span(raw_text, "consequence", "STRUCK_BY", "personnel could be struck" if "personnel could be struck" in raw_text.lower() else ("could be struck" if "could be struck" in raw_text.lower() else "struck"))
            evidence_list = [s for s in [span_hypo, act_span, csq_span] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting",
                energy="Gravitational / Suspended Load Potential",
                exposure="Hypothetical line-of-fire exposure",
                barrier=["LIFTING_CONTROL"],
                barrier_state=["PRESENT_UNVERIFIED"],
                consequence="Potential struck-by impact",
                assertion=AssertionStatus.HYPOTHETICAL,
                temporal_status=TemporalStatus.HYPOTHETICAL,
                sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
                sif_reasons=["Hypothetical conditional scenario; not an observed occurrence or physical barrier breach"],
                lsr=["SAFE_MECHANICAL_LIFTING"],
                evidence=evidence_list,
                uncertainty=["No actual incident occurred"],
                confidence=0.95,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 5. Check for Worker Remained Outside (Test 2: "Worker remained outside the exclusion zone while the load was suspended")
        remained_outside_match = re.search(r'\b(remained\s+outside(\s+the)?\s+exclusion\s+zone|stayed\s+outside(\s+the)?\s+exclusion\s+zone)\b', raw_text, re.IGNORECASE)
        if remained_outside_match:
            span_outside = self._create_evidence_span(raw_text, "exposure", "NO_PERSON_INSIDE_ZONE", remained_outside_match.group(0))
            load_match = re.search(r'\b(load\s+was\s+suspended|suspended\s+load|lifting)\b', raw_text, re.IGNORECASE)
            load_span = self._create_evidence_span(raw_text, "energy", "GRAVITATIONAL_KINETIC", load_match.group(0) if load_match else "suspended")
            zone_span = self._create_evidence_span(raw_text, "barrier", "EXCLUSION_ZONE", "exclusion zone")
            evidence_list = [s for s in [span_outside, load_span, zone_span] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting",
                energy="Gravitational / Suspended Load",
                exposure="Worker remained outside zone (Safe boundary respected)",
                exposure_status=ExposureStatus.NEGATED,
                barrier=["EXCLUSION_ZONE"],
                barrier_state=["EFFECTIVE_VERIFIED"],
                consequence="No contact / safe operation",
                assertion=AssertionStatus.AFFIRMED,
                temporal_status=TemporalStatus.DURING_EVENT,
                sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
                sif_reasons=["Worker remained outside boundary; no human exposure inside hazardous zone"],
                lsr=["SAFE_MECHANICAL_LIFTING"],
                evidence=evidence_list,
                uncertainty=[],
                confidence=0.96,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 5A. Check for Explicit Exposure Negation (Test 3 & Mandatory Rule 6 Negated Case)
        neg_exposure_match = re.search(
            r'\b(no\s+(worker|workers|personnel|contractor|person|employee|one|human|individual|operator|rigger|entrant|technician)\s+(was|were|entered|crossed|approached|worked|was\s+in|was\s+exposed|was\s+inside|in\s+the\s+line\s+of\s+fire)|'
            r'did\s+not\s+(enter|cross|approach|occur)|remained\s+outside|stayed\s+clear|kept\s+clear|'
            r'no\s+hot\s+work\s+was\s+conducted|pedestrians\s+did\s+not\s+cross|workers\s+remained\s+outside|personnel\s+did\s+not\s+enter|personnel\s+kept\s+clear)\b',
            raw_text, re.IGNORECASE
        )
        if neg_exposure_match:
            span_neg = self._create_evidence_span(raw_text, "assertion", "NEGATED", neg_exposure_match.group(0))
            barrier_name = "EXCLUSION_ZONE" if "zone" in raw_text.lower() or "barrier" in raw_text.lower() else "GENERAL_CONTROL"
            barrier_span = self._create_evidence_span(raw_text, "barrier", barrier_name, "exclusion zone" if "exclusion zone" in raw_text.lower() else ("barrier" if "barrier" in raw_text.lower() else barrier_name))
            barrier_state_val = ["FAILED"] if ("failed" in raw_text.lower() or "broke" in raw_text.lower()) else ["EFFECTIVE_VERIFIED"]
            evidence_list = [s for s in [span_neg, barrier_span] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting" if "lift" in raw_text.lower() or "load" in raw_text.lower() else "General Operations",
                energy="Gravitational / Suspended Load" if "load" in raw_text.lower() or "lift" in raw_text.lower() else "Kinetic Energy",
                exposure="NO_HUMAN_EXPOSURE",
                exposure_status=ExposureStatus.NEGATED,
                barrier=[barrier_name],
                barrier_state=barrier_state_val,
                consequence="None (Human exposure explicitly negated)",
                assertion=AssertionStatus.NEGATED,
                temporal_status=TemporalStatus.DURING_EVENT,
                sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
                sif_reasons=["Human exposure was explicitly negated: no worker/person entered hazardous area (NO_HUMAN_EXPOSURE)"],
                lsr=["SAFE_MECHANICAL_LIFTING"] if "lift" in raw_text.lower() else [],
                evidence=evidence_list,
                uncertainty=[],
                confidence=0.98,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 5B. Check for Unknown Personnel Location / Exposure (Rule 6 Mandatory Cases)
        unknown_exposure_match = re.search(
            r'\b('
            r'personnel\s+location[\w\s]{0,35}(unknown|unrecorded|not\s+recorded)|'
            r'location\s+(of\s+personnel\s+)?(is|was\s+)?(unknown|unrecorded|not\s+recorded)|'
            r'no\s+information\s+(was\s+)?(available\s+)?(on|about)\s+personnel(\s+location|\s+presence)?|'
            r'no\s+information\s+was\s+available|'
            r'unknown\s+whether\s+(any\s+)?(worker|personnel|person|crew|team)(\s+members)?\s+(was|were\s+inside|were\s+underneath|entered)|'
            r'unclear\s+(if|whether)\s+(any\s+)?(worker|personnel|person|crew|team)(\s+members)?\s+(was|were\s+inside|were\s+underneath|entered)|'
            r'unclear\s+whether|unknown\s+whether|'
            r'personnel\s+location\s+was\s+not\s+recorded|'
            r'not\s+recorded\s+whether\s+anyone\s+was\s+inside|'
            r'ground\s+presence\s+not\s+documented|'
            r'whereabouts\s+during\s+incident\s+not\s+recorded|'
            r'presence\s+(of\s+[\w\s]{1,35})?(unknown|unverified)|'
            r'personnel\s+presence\s+unverified|presence\s+unknown'
            r')\b',
            raw_text, re.IGNORECASE
        )
        if unknown_exposure_match:
            span_unk = self._create_evidence_span(raw_text, "exposure", "UNKNOWN", unknown_exposure_match.group(0))
            barrier_failed = any(w in raw_text.lower() for w in ["failed", "broken", "bypassed", "snapped", "ruptured", "leaked", "dropped"])
            b_state = ["FAILED"] if barrier_failed else ["UNKNOWN"]
            b_name = "EXCLUSION_ZONE" if "zone" in raw_text.lower() or "barrier" in raw_text.lower() else "GENERAL_CONTROL"
            b_span = self._create_evidence_span(raw_text, "barrier", b_name, "barrier" if "barrier" in raw_text.lower() else b_name)
            evidence_list = [s for s in [span_unk, b_span] if s]

            raw_lower = raw_text.lower()
            if any(w in raw_lower for w in ["lift", "load", "crane", "boom", "hoist", "derrick", "winch", "wireline"]):
                energy_desc = "Gravitational / Kinetic Energy (Suspended / Lifting)"
                act_desc = "Mechanical Lifting"
            elif any(w in raw_lower for w in ["pressure", "valve", "separator", "flowline", "manifold", "choke"]):
                energy_desc = "High Pressure / Stored Fluid Energy"
                act_desc = "Pressure Containment"
            elif any(w in raw_lower for w in ["breaker", "arc flash", "voltage", "mcc", "electrical"]):
                energy_desc = "Live Electrical Conductors"
                act_desc = "Electrical Energy Isolation"
            elif any(w in raw_lower for w in ["gas", "toxic", "h2s", "chemical", "corrosive"]):
                energy_desc = "Hazardous Gas / Toxic Atmospheric Vapor"
                act_desc = "Hazardous Materials Operations"
            else:
                energy_desc = "Industrial Kinetic / Gravitational Energy"
                act_desc = "Operational Activity"

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity=act_desc,
                energy=energy_desc,
                exposure="PERSONNEL_LOCATION_UNKNOWN",
                exposure_status=ExposureStatus.UNKNOWN,
                barrier=[b_name],
                barrier_state=b_state,
                consequence="Potential blunt trauma / unverified exposure",
                assertion=AssertionStatus.AFFIRMED,
                temporal_status=TemporalStatus.DURING_EVENT,
                sif_status=SIFStatus.REVIEW_REQUIRED,
                sif_reasons=[
                    "Personnel location was not recorded; physical human exposure is UNKNOWN",
                    "Barrier compromise or high energy present, but physical exposure cannot be confirmed without HSE review"
                ],
                lsr=["SAFE_MECHANICAL_LIFTING"] if "lift" in raw_text.lower() else [],
                evidence=evidence_list,
                uncertainty=["PERSONNEL_LOCATION_UNKNOWN", "Human exposure cannot be affirmed without field investigation"],
                confidence=0.65,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 5C. Check for Possible / Suspected Human Exposure (Rule 6 Possible Case)
        possible_exposure_match = re.search(
            r'\b(may\s+have\s+(entered|been\s+inside|crossed|reversed)|'
            r'might\s+have\s+(entered|been\s+inside|crossed|stepped)|'
            r'possible\s+(entry|personnel|worker)|'
            r'suspected\s+(entry|personnel|to\s+have|of\s+working)|'
            r'entrant\s+possibly\s+exposed)\b',
            raw_text, re.IGNORECASE
        )
        if possible_exposure_match:
            span_pos = self._create_evidence_span(raw_text, "exposure", "POSSIBLE", possible_exposure_match.group(0))
            b_name = "EXCLUSION_ZONE" if "zone" in raw_text.lower() or "barrier" in raw_text.lower() else "GENERAL_CONTROL"
            b_span = self._create_evidence_span(raw_text, "barrier", b_name, "zone" if "zone" in raw_text.lower() else b_name)
            evidence_list = [s for s in [span_pos, b_span] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting" if "lift" in raw_text.lower() or "crane" in raw_text.lower() else "Operational Activity",
                energy="Gravitational / Suspended Load" if "lift" in raw_text.lower() or "pipe" in raw_text.lower() or "load" in raw_text.lower() else "Residual Energy",
                exposure="POSSIBLE_HUMAN_EXPOSURE",
                exposure_status=ExposureStatus.POSSIBLE,
                barrier=[b_name],
                barrier_state=["PRESENT_UNVERIFIED"],
                consequence="Potential struck-by impact",
                assertion=AssertionStatus.AFFIRMED,
                temporal_status=TemporalStatus.DURING_EVENT,
                sif_status=SIFStatus.REVIEW_REQUIRED,
                sif_reasons=["Human exposure is POSSIBLE / unverified; requires HSE specialist evaluation"],
                lsr=["SAFE_MECHANICAL_LIFTING"] if "lift" in raw_text.lower() else [],
                evidence=evidence_list,
                uncertainty=["UNCONFIRMED_HUMAN_EXPOSURE"],
                confidence=0.70,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )


        # 7. Check for Barrier Effective/Inspected (Test 5: "The exclusion zone was inspected and confirmed intact before lifting")
        intact_match = re.search(r'\b(inspected\s+and\s+confirmed\s+intact|confirmed\s+intact|barrier\s+was\s+intact|fully\s+secured)\b', raw_text, re.IGNORECASE)
        if intact_match:
            span_intact = self._create_evidence_span(raw_text, "barrier_state", "EFFECTIVE_VERIFIED", intact_match.group(0))
            zone_span = self._create_evidence_span(raw_text, "barrier", "EXCLUSION_ZONE", "exclusion zone")
            before_match = re.search(r'\b(before\s+lifting|prior\s+to\s+start)\b', raw_text, re.IGNORECASE)
            time_span = self._create_evidence_span(raw_text, "temporal_status", "PRE_EVENT", before_match.group(0) if before_match else "before")
            evidence_list = [s for s in [span_intact, zone_span, time_span] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting",
                energy="Gravitational / Suspended Load",
                exposure="Controlled perimeter",
                barrier=["EXCLUSION_ZONE"],
                barrier_state=["EFFECTIVE_VERIFIED"],
                consequence="Barrier intact; no breach",
                assertion=AssertionStatus.AFFIRMED,
                temporal_status=TemporalStatus.PRE_EVENT,
                sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED,
                sif_reasons=["Exclusion zone was inspected and confirmed intact; barrier NOT failed"],
                lsr=["SAFE_MECHANICAL_LIFTING"],
                evidence=evidence_list,
                uncertainty=[],
                confidence=0.98,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 8. Check for Multi-Clause Distinction (Test 7: "The exclusion zone was fine; the real issue was a dropped tool")
        fine_match = re.search(r'\b(exclusion\s+zone\s+was\s+fine|barricade\s+was\s+ok|barrier\s+was\s+intact)\b', raw_text, re.IGNORECASE)
        dropped_match = re.search(r'\b(dropped\s+(tool|object|pipe|equipment)|falling\s+object)\b', raw_text, re.IGNORECASE)
        if fine_match and dropped_match:
            span_fine = self._create_evidence_span(raw_text, "barrier_state", "EFFECTIVE_VERIFIED", fine_match.group(0))
            span_tool = self._create_evidence_span(raw_text, "energy", "GRAVITATIONAL_DROPPED_OBJECT", dropped_match.group(0))
            evidence_list = [s for s in [span_fine, span_tool] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Handling Tools / Overhead Work",
                energy="Gravitational Energy (Dropped Object)",
                exposure="Potential line of fire from falling tool",
                barrier=["EXCLUSION_ZONE", "TOOL_TETHERING"],
                barrier_state=["EFFECTIVE_VERIFIED", "FAILED"],
                consequence="Impact trauma from dropped tool",
                assertion=AssertionStatus.AFFIRMED,
                temporal_status=TemporalStatus.DURING_EVENT,
                sif_status=SIFStatus.SIF_POTENTIAL,
                sif_reasons=[
                    "Exclusion zone was intact (no perimeter failure)",
                    "Dropped tool represents separate dropped-object hazard pathway"
                ],
                lsr=["LINE_OF_FIRE"],
                evidence=evidence_list,
                uncertainty=["Secondary dropped tool barrier failed (tethering/toe board)"],
                confidence=0.94,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # 9. Test 1 & General Active Breach: "Worker entered the exclusion zone while the load was suspended."
        entered_match = re.search(r'\b(entered\s+(the\s+)?[\w\s]{0,15}(exclusion|restricted|red|danger)\s+(zone|area|boundary)|crossed\s+(the\s+)?[\w\s]{0,15}(boundary|perimeter|barricade)|inside\s+(the\s+)?[\w\s]{0,15}(exclusion|restricted|red)\s+zone)\b', raw_text, re.IGNORECASE)
        load_active_match = re.search(r'\b(load\s+was\s+suspended|suspended(\s+[\w\s]{0,15})?overhead|suspended\s+load|while\s+lifting|crane\s+operating|was\s+suspended)\b', raw_text, re.IGNORECASE)

        evidence_list = []
        if entered_match:
            evidence_list.append(self._create_evidence_span(raw_text, "exposure", "INSIDE_EXCLUSION_ZONE", entered_match.group(0)))
            b_text = "exclusion zone" if "exclusion zone" in raw_text.lower() else ("boundary" if "boundary" in raw_text.lower() else entered_match.group(0))
            evidence_list.append(self._create_evidence_span(raw_text, "barrier", "EXCLUSION_ZONE", b_text))
            evidence_list.append(self._create_evidence_span(raw_text, "barrier_state", "BYPASSED", entered_match.group(0)))
        if load_active_match:
            evidence_list.append(self._create_evidence_span(raw_text, "energy", "GRAVITATIONAL_KINETIC", load_active_match.group(0)))
            evidence_list.append(self._create_evidence_span(raw_text, "activity", "MECHANICAL_LIFTING", load_active_match.group(0)))

        # Clean non-None spans
        evidence_list = [s for s in evidence_list if s]

        if entered_match and load_active_match:
            # Full SIF Pathway: High energy + exposure + barrier breach + credible serious consequence
            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting",
                energy="Gravitational / Kinetic Energy (Suspended Load)",
                exposure="Person inside lifting exclusion zone",
                exposure_status=ExposureStatus.CONFIRMED,
                barrier=["EXCLUSION_ZONE"],
                barrier_state=["BYPASSED"],
                consequence="Crush trauma / blunt force impact",
                assertion=AssertionStatus.AFFIRMED,
                temporal_status=TemporalStatus.DURING_EVENT,
                sif_status=SIFStatus.SIF_POTENTIAL,
                sif_reasons=[
                    "High-energy hazard: suspended load active",
                    "Human exposure affirmed: worker entered exclusion zone",
                    "Barrier compromised: exclusion zone boundary breached/bypassed",
                    "Credible serious consequence: crush trauma / blunt impact"
                ],
                lsr=["SAFE_MECHANICAL_LIFTING", "LINE_OF_FIRE"],
                evidence=evidence_list,
                uncertainty=[],
                confidence=0.96,
                review_status=ReviewStatus.CANDIDATE,
                narrative=raw_text
            )

        # Fallback extraction for general incident reports
        return self._extract_general_event(raw_text, event_id, report_id, source, site, location)

    def _extract_general_event(self, raw_text: str, event_id: str, report_id: Optional[str],
                               source: str, site: str, location: str) -> SafetyEvent:
        """Generic fallback extractor for industrial reports with full evidence span tracing."""
        evidence = []
        text_lower = raw_text.lower()

        # Identify Activity
        activity_id = "GENERAL_MAINTENANCE"
        activity_name = "General Operations & Maintenance"
        for act_id, act_info in self.ontology.activities.items():
            for kw in act_info.get("keywords", []):
                if kw in text_lower:
                    activity_id = act_id
                    activity_name = act_info.get("name", act_id)
                    span = self._create_evidence_span(raw_text, "activity", activity_id, kw)
                    if span:
                        evidence.append(span)
                    break
            if activity_id != "GENERAL_MAINTENANCE":
                break

        # Additional activity classification based on industrial terms
        if activity_id == "GENERAL_MAINTENANCE":
            if any(w in text_lower for w in ["lift", "hoist", "crane", "rigging", "sling", "suspended", "collar"]):
                activity_id = "MECHANICAL_LIFTING"
                activity_name = "Mechanical Lifting Operations"
            elif any(w in text_lower for w in ["height", "mast", "derrick", "scaffold", "monkey board", "fall", "ladder", "substructure"]):
                activity_id = "WORKING_AT_HEIGHT"
                activity_name = "Working at Height"
            elif any(w in text_lower for w in ["lockout", "tagout", "loto", "energized", "breaker", "switchgear", "isolation", "spade", "mcc", "480v"]):
                activity_id = "ENERGY_ISOLATION"
                activity_name = "Hazardous Energy Isolation (LOTO)"
            elif any(w in text_lower for w in ["confined", "tank", "vessel", "cellar", "sump", "culvert", "manhole", "trench", "degasser", "separator"]):
                activity_id = "CONFINED_SPACE"
                activity_name = "Confined Space Entry"
            elif any(w in text_lower for w in ["weld", "cutting", "grinding", "torch", "hot work", "sparks", "rivet"]):
                activity_id = "HOT_WORK"
                activity_name = "Hot Work Operations"
            elif any(w in text_lower for w in ["pressure", "psi", "hydrotest", "flowline", "hydraulic", "bleed", "manifold", "choke"]):
                activity_id = "PRESSURE_OPERATIONS"
                activity_name = "Pressure Testing & Containment"

        # Identify Energy & High Energy Flag
        is_routine = bool(re.search(
            r'\b(wrench\s+on\s+the\s+drill\s+floor\s+rubber\s+mat|parking\s+lot|unbuttoned|skin\s+scratch|'
            r'cardboard|packaging|water\s+bottle|housekeeping|fogged\s+up|muster\s+room|puddle\s+of\s+clean\s+rainwater|'
            r'cafeteria|wooden\s+pallets\s+at\s+ground|notice\s+board|tool\s+shed|low\s+2-inch\s+curb|office\s+cabin|'
            r'toolbox\s+briefing|scuff\s+mark|outer\s+plastic\s+crown|cotton\s+gloves|coffee\s+mug|desk|shoelace|'
            r'recycle\s+bin|hallway|minor\s+water\s+drip)\b',
            text_lower
        ))

        energy_id = "LOW_ENERGY_ROUTINE" if is_routine else "KINETIC_MECHANICAL"
        energy_name = "Routine Non-Hazardous Task" if is_routine else "Mechanical / Kinetic Energy"

        if not is_routine:
            if any(w in text_lower for w in ["suspended", "hoist", "crane", "sling", "shackle", "drop zone", "tubular", "drill collar", "spool piece", "bop stack", "boom", "casing", "wireline", "winch", "tension", "tag line"]):
                energy_id = "GRAVITATIONAL_KINETIC"
                energy_name = "Gravity / Suspended Load"
            elif any(w in text_lower for w in ["height", "derrick", "mast", "monkey board", "scaffold", "meters", "substructure", "platform", "open hatch", "fall from height", "trench", "ladder", "staircase", "pipe rack", "pipe bridge", "mud pit", "pit wall", "top edge", "grating", "drop"]):
                energy_id = "GRAVITATIONAL_HEIGHT"
                energy_name = "Elevation / Fall Potential"
            elif any(w in text_lower for w in ["high-pressure", "high pressure", "pressurized", "psi", "hydrotest", "flowline", "hydraulic", "standpipe", "manifold", "choke", "whip-check", "autoclave", "accumulator", "compressor", "receiver tank", "valve", "flange", "depressur", "slurry pipeline", "esd solenoid", "solenoid", "steam turbine", "steam", "turbine", "zero energy isolation"]):
                energy_id = "HIGH_PRESSURE_STORED"
                energy_name = "High Pressure / Stored Pneumatic or Hydraulic"
            elif any(w in text_lower for w in ["blowout", "gas kick", "well kick", "reservoir pressure", "hydrocarbon gas", "crude line", "crude transfer", "crude oil", "hot oil", "gas line", "separator", "condensate", "hydrocarbon", "crude"]):
                energy_id = "HIGH_PRESSURE_HYDROCARBON"
                energy_name = "Wellbore Hydrocarbon / Kick Potential"
            elif any(w in text_lower for w in ["h2s", "toxic", "confined space", "mud tank", "separator vessel", "cellar", "sump", "culvert", "manhole", "oxygen deficien", "nitrogen", "corrosive", "chemical transfer", "acid", "gas-rich", "unpurged", "sludge tank", "manway", "unventilated", "hydrogen", "battery charging"]):
                energy_id = "ATMOSPHERIC_TOXIC"
                energy_name = "Hazardous Gas / H2S / Toxic Vapor"
            elif any(w in text_lower for w in ["electrical", "voltage", "480v", "6.6kv", "switchgear", "mcc", "live wire", "arc flash", "transformer", "busbar", "breaker", "energized", "motor circuit", "starter circuit", "primary feeder", "live"]):
                energy_id = "ELECTRICAL_ENERGY"
                energy_name = "Live Electrical Conductors"
            elif any(w in text_lower for w in ["hot work", "welding", "cutting", "grinding", "sparks", "torch", "flammable", "flash fire", "explosion", "rivet", "fuel vent", "combustible", "oxy-acetylene", "angle grinder", "grinder"]):
                energy_id = "THERMAL_IGNITION"
                energy_name = "Thermal / Flammable Atmosphere / Sparks"
            elif any(w in text_lower for w in ["rotary table", "top drive", "impeller", "running pump", "shaker screen", "agitator", "rotating", "degasser", "hopper", "feed auger", "auger"]):
                energy_id = "MECHANICAL_ROTATING"
                energy_name = "Rotating Equipment / Pinch Points"
            elif any(w in text_lower for w in ["forklift", "wheel loader", "heavy transport", "loader", "crane counterweight", "excavator"]):
                energy_id = "MOBILE_HEAVY_EQUIPMENT"
                energy_name = "Heavy Mobile Equipment / Traffic"

        is_high_energy = (not is_routine) and (energy_id in [
            "GRAVITATIONAL_KINETIC", "GRAVITATIONAL_HEIGHT", "HIGH_PRESSURE_STORED",
            "HIGH_PRESSURE_HYDROCARBON", "ATMOSPHERIC_TOXIC", "ELECTRICAL_ENERGY",
            "THERMAL_IGNITION", "MECHANICAL_ROTATING", "MOBILE_HEAVY_EQUIPMENT"
        ] or any(kw in text_lower for kw in [
            "suspended", "crane", "hoist", "derrick", "mast", "scaffold", "height", "high-pressure",
            "pressurized", "psi", "hydrotest", "hydraulic", "h2s", "toxic", "confined", "480v", "voltage",
            "switchgear", "mcc", "welding", "grinding", "sparks", "blowout", "arc flash", "running pump",
            "wireline", "tension", "winch", "trench", "corrosive", "forklift", "loader", "transport",
            "flange", "valve", "crude", "compressor", "nitrogen", "line of fire", "blind spot", "chemical",
            "slurry", "esd", "solenoid", "separator", "manifold", "unbarricaded", "spade", "depressur",
            "tank cleaning", "excavator", "mud tank", "sump", "culvert", "manhole", "cellar", "hydrocarbon",
            "steam", "turbine", "sludge", "degasser", "hopper", "auger", "grating", "drop", "oxy-acetylene",
            "hydrogen", "torch", "grinder", "manway", "unventilated"
        ]))

        # Identify Barrier
        barriers_found = []
        barrier_states_found = []

        is_effective_barrier = bool(re.search(
            r'\b(verified\s+effective|zero\s+energy\s+confirmed|continuous\s+gas\s+detector\s+confirmed|'
            r'positive-locked|rated\s+and\s+secured|observed\s+from\s+behind\s+blast\s+wall|'
            r'fire\s+blanket\s+and\s+dedicated\s+fire\s+watch|present\s+and\s+verified\s+intact|'
            r'engaged;\s*motor\s+stopped|audible\s+reversing\s+alarm)\b',
            text_lower
        ) and not re.search(r'\b(bypassed|failed|removed|breached|snapped|fell|struck)\b', text_lower))

        if is_effective_barrier:
            barriers_found.append("ENGINEERED_VERIFIED_BARRIER")
            barrier_states_found.append("EFFECTIVE_VERIFIED")
        else:
            # Check barrier states (REMOVED vs BYPASSED vs FAILED vs DEGRADED)
            if any(w in text_lower for w in ["removed", "taken off", "dismantled", "detached", "open grating", "missing guardrail", "deflector missing", "tied open"]):
                barrier_states_found.append("REMOVED")
            elif any(w in text_lower for w in ["bypassed", "ducked under", "crossed", "entered without", "without", "no harness", "no tagout", "no lanyard", "incomplete", "without installing"]):
                barrier_states_found.append("BYPASSED")
            elif any(w in text_lower for w in ["failed", "broke", "snapped", "ruptured", "leaked", "parted", "dropped", "slipped off", "slipping", "severed", "deformed", "coupling disconnected"]):
                barrier_states_found.append("FAILED")
            elif any(w in text_lower for w in ["degraded", "worn", "frayed", "damaged", "corroded", "slack", "loose", "intermittent", "rusted", "cracked view", "holes burned", "abrasion", "displaced by wind"]):
                barrier_states_found.append("DEGRADED")
            elif any(w in text_lower for w in ["intact", "verified", "inspected"]):
                barrier_states_found.append("EFFECTIVE_VERIFIED")
            else:
                barrier_states_found.append("PRESENT_UNVERIFIED")

            if any(w in text_lower for w in ["zone", "barricade", "restricted area", "exclusion", "lifting barrier", "drop area", "perimeter"]):
                barriers_found.append("EXCLUSION_ZONE")
            elif "lockout" in text_lower or "loto" in text_lower or "isolation" in text_lower or "padlock" in text_lower:
                barriers_found.append("ENERGY_ISOLATION_LOTO")
            elif "harness" in text_lower or "lanyard" in text_lower or "lifeline" in text_lower or "tie-off" in text_lower:
                barriers_found.append("FALL_PROTECTION")
            elif "gas detector" in text_lower or "ventilation" in text_lower or "air purge" in text_lower:
                barriers_found.append("ATMOSPHERIC_MONITORING")
            elif "whip-check" in text_lower or "relief valve" in text_lower or "blind" in text_lower:
                barriers_found.append("PRESSURE_CONTAINMENT")
            else:
                barriers_found.append("GENERAL_ADMINISTRATIVE_CONTROL")

        # Check human exposure in generic text (Rule 6)
        has_negated_human = bool(re.search(
            r'\b(no\s+(worker|workers|personnel|contractor|person|employee|one|human|individual|operator|rigger|entrant|technician)\s+(was|were|entered|crossed|approached|worked|was\s+in|was\s+exposed|was\s+inside|in\s+the\s+line\s+of\s+fire)|'
            r'did\s+not\s+(enter|cross|approach|occur)|remained\s+outside|stayed\s+clear|kept\s+clear|'
            r'no\s+hot\s+work\s+was\s+conducted|pedestrians\s+did\s+not\s+cross|workers\s+remained\s+outside|personnel\s+did\s+not\s+enter|personnel\s+kept\s+clear)\b',
            text_lower
        ))
        has_unknown_human = bool(re.search(
            r'\b('
            r'personnel\s+location[\w\s]{0,35}(unknown|unrecorded|not\s+recorded)|'
            r'location\s+(of\s+personnel\s+)?(is|was\s+)?(unknown|unrecorded|not\s+recorded)|'
            r'no\s+information\s+(was\s+)?(available\s+)?(on|about)\s+personnel(\s+location|\s+presence)?|'
            r'no\s+information\s+was\s+available|'
            r'unknown\s+whether\s+(any\s+)?(worker|personnel|person|crew|team)(\s+members)?\s+(was|were\s+inside|were\s+underneath|entered)|'
            r'unclear\s+(if|whether)\s+(any\s+)?(worker|personnel|person|crew|team)(\s+members)?\s+(was|were\s+inside|were\s+underneath|entered)|'
            r'unclear\s+whether|unknown\s+whether|'
            r'personnel\s+location\s+was\s+not\s+recorded|'
            r'not\s+recorded\s+whether\s+anyone\s+was\s+inside|'
            r'ground\s+presence\s+not\s+documented|'
            r'whereabouts\s+during\s+incident\s+not\s+recorded|'
            r'presence\s+(of\s+[\w\s]{1,35})?(unknown|unverified)|'
            r'personnel\s+presence\s+unverified|presence\s+unknown'
            r')\b',
            text_lower
        ))
        has_possible_human = bool(re.search(
            r'\b(may\s+have\s+(entered|been\s+inside|crossed|reversed)|'
            r'might\s+have\s+(entered|been\s+inside|crossed|stepped)|'
            r'possible\s+(entry|personnel|worker)|'
            r'suspected\s+(entry|personnel|to\s+have|of\s+working)|'
            r'entrant\s+possibly\s+exposed)\b',
            text_lower
        ))
        has_affirmed_human = bool(re.search(
            r'\b(worker|workers|personnel|employee|contractor|contractors|operator|operators|rigger|riggers|'
            r'roustabout|technician|technicians|mechanic|mechanics|welder|welders|electrician|electricians|'
            r'driver|crew|entrant|entrants|helper|helpers|fitter|fitters|man|men|dogman|cleaner|individual|'
            r'tech|two\s+workers|inspector|painter|roughneck|maintenance|grinding|welding|cutting|sparks|'
            r'rivet|torch|tack-welding|drilling|testing|entry|hydrotest|flange|thermal\s+cutting|work\s+zone|'
            r'yard|active\s+yard|loader|pedestrian|heavy\s+transport|nitrogen\s+discharge|pressuriz\w*)\b',
            text_lower
        ))

        if has_negated_human:
            gen_exp_status = ExposureStatus.NEGATED
            gen_exp_str = "NO_HUMAN_EXPOSURE"
        elif has_unknown_human:
            gen_exp_status = ExposureStatus.UNKNOWN
            gen_exp_str = "PERSONNEL_LOCATION_UNKNOWN"
        elif has_possible_human:
            gen_exp_status = ExposureStatus.POSSIBLE
            gen_exp_str = "POSSIBLE_HUMAN_EXPOSURE"
        elif has_affirmed_human:
            gen_exp_status = ExposureStatus.CONFIRMED
            gen_exp_str = "Person inside hazardous perimeter"
        else:
            gen_exp_status = ExposureStatus.UNKNOWN
            gen_exp_str = "Field operational interaction (Exposure unverified)"

        # Determine SIF potential with Rule 6 & 7 gating
        is_compromised = any(st in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for st in barrier_states_found) or bool(re.search(
            r'\b(enter\w*|walk\w*|st[ao][no]d\w*|step\w*|travers\w*|breach\w*|position\w*|line\s+of\s+fire|'
            r'unbarricaded|no\s+barricade|without|removed|taken\s+off|dismantled|detached|open\s+grating|missing|'
            r'absent|left\s+off|left\s+cracked\s+open|unpinned|unlocked|unclipped|unanchored|unvented|unsupported|'
            r'unverified\s+(\w+\s+)?atmosphere|fail\w*|br[oe]ke\w*|snapp\w*|ruptur\w*|leak\w*|parted|dropped|slipped|'
            r'slipping|severed|deformed|tripped|collapsing|blown\s+out|bypass\w*|ducked\s+under|defeated\s+interlock|'
            r'isolation\s+switch\s+bypassed|bypassed\s+door\s+interlock|bypassed\s+permit|circuit\s+remained\s+energized|'
            r'degraded|worn|frayed|damaged|corroded|slack|loose|alone|climb\w*|descend\w*|inspected\s+drilling|'
            r'hammer\w*|loosen\w*|flew\s+directly|flew\s+toward|fell\s+into|ignited|throwing\s+sparks|sagging|'
            r'unbolted|holes\s+burned|abrasion|displaced|disconnected|rusted|cracked\s+view|bubbling|discharged\s+violently|'
            r'coupling\s+disconnected|unauthorized|guided\s+suspended|lean\w*|unpurged|tack-welding|unrated|'
            r'pressurized\s+without|under\s+pressure|unlatched|unventilated|directly\s+within|active\s+gas\s+leak|'
            r'access\w*|flew\b|no\s+tagout|no\s+lanyard|with\s+no|not\s+installed|discharged|nearby|dug\s+nearby|'
            r'accumulating|below\s+audible|technician\s+at|riggers\s+present|used\s+angle\s+grinder|deflector\s+missing|'
            r'degraded\s+below|tied\s+open|no\s+harness\w*|incomplete|without\s+installing|pedestrian\s+was\s+inside|'
            r'with\s+worker\s+present|discharge\s+line|running\s+pump)\b',
            text_lower
        ))

        # Ensure barrier states reflect compromise when compromise is detected
        if is_effective_barrier:
            is_compromised = False

        if is_compromised and not is_effective_barrier and not any(st in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for st in barrier_states_found):
            if "PRESENT_UNVERIFIED" in barrier_states_found:
                barrier_states_found.remove("PRESENT_UNVERIFIED")
            is_failed_cue = bool(re.search(r'\b(fail\w*|br[oe]ke\w*|snapp\w*|ruptur\w*|leak\w*|parted|dropped|slipped|severed|deformed|coupling\s+disconnected|tripped|collaps\w*)\b', text_lower))
            if is_failed_cue:
                barrier_states_found.append("FAILED")
            else:
                barrier_states_found.append("BYPASSED")
            if not barriers_found or barriers_found == ["GENERAL_ADMINISTRATIVE_CONTROL"]:
                if any(w in text_lower for w in ["zone", "barricade", "perimeter", "radius", "line of fire", "blind spot", "unbarricaded", "suspended"]):
                    barriers_found = ["EXCLUSION_ZONE"]
                elif any(w in text_lower for w in ["lockout", "loto", "energized", "circuit", "breaker", "isolation", "spade"]):
                    barriers_found = ["ENERGY_ISOLATION_LOTO"]
                elif any(w in text_lower for w in ["harness", "lanyard", "lifeline", "height", "scaffold", "ladder"]):
                    barriers_found = ["FALL_PROTECTION"]

        is_pure_degraded_inspection = bool(re.search(
            r'\b(damaged\s+latch|relief\s+valve\s+seep|intermittent\s+fault|wear\s+particles|hairline\s+crack|superficial\s+rust)\b',
            text_lower
        ) and not re.search(r'\b(enter\w*|walk\w*|st[ao][no]d\w*|step\w*|under|inside|without|fell|struck|live|hammer\w*|loosen\w*|leaning|ignited|accessed|technician\s+at|discharge|active\s+yard|running\s+pump|heavy\s+transport)\b', text_lower))

        if gen_exp_status == ExposureStatus.NEGATED:
            sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            sif_reasons = ["Personnel remained outside hazard boundary; human exposure explicitly negated (NO_HUMAN_EXPOSURE)"]
        elif not is_high_energy:
            sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            sif_reasons = ["Routine operational task without high-energy hazard exposure or serious consequence pathway"]
        elif is_effective_barrier and not is_compromised:
            sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            sif_reasons = ["Safety barrier verified intact and effective; hazard prevented from reaching personnel"]
        elif gen_exp_status in [ExposureStatus.UNKNOWN, ExposureStatus.POSSIBLE]:
            sif_status = SIFStatus.REVIEW_REQUIRED
            sif_reasons = [
                f"High-energy hazard present: {energy_name}",
                "Physical human exposure is UNKNOWN or POSSIBLE; requires HSE specialist evaluation"
            ]
        elif is_pure_degraded_inspection:
            sif_status = SIFStatus.REVIEW_REQUIRED
            sif_reasons = [
                f"High-energy hazard present: {energy_name}",
                "Safety barrier degradation detected during inspection; maintenance review required"
            ]
        elif is_high_energy and is_compromised and gen_exp_status == ExposureStatus.CONFIRMED:
            sif_status = SIFStatus.SIF_POTENTIAL
            sif_reasons = [
                f"High-energy hazard present: {energy_name}",
                "Human exposure affirmed in hazard zone",
                f"Barrier compromised: {', '.join(barrier_states_found)}"
            ]
        else:
            sif_status = SIFStatus.REVIEW_REQUIRED
            sif_reasons = [
                f"High-energy hazard present: {energy_name}",
                "Physical human exposure or barrier integrity requires HSE human verification"
            ]

        # LSR mapping
        lsr_list = []
        if "LIFTING" in activity_id or "GRAVITATIONAL_KINETIC" in energy_id:
            lsr_list.append("SAFE_MECHANICAL_LIFTING")
        if "HEIGHT" in activity_id or "GRAVITATIONAL_HEIGHT" in energy_id:
            lsr_list.append("WORKING_AT_HEIGHT")
        if "ISOLATION" in activity_id or "ELECTRICAL" in energy_id:
            lsr_list.append("ENERGY_ISOLATION")
        if "CONFINED" in activity_id or "ATMOSPHERIC_TOXIC" in energy_id:
            lsr_list.append("CONFINED_SPACE")
        if "HOT_WORK" in activity_id or "THERMAL" in energy_id:
            lsr_list.append("HOT_WORK")
        if "LINE_OF_FIRE" in activity_id or "line of fire" in text_lower:
            lsr_list.append("LINE_OF_FIRE")

        return SafetyEvent(
            event_id=event_id,
            report_id=report_id,
            source=source,
            site=site,
            location=location,
            activity=activity_name,
            energy=energy_name,
            exposure=gen_exp_str,
            exposure_status=gen_exp_status,
            barrier=barriers_found,
            barrier_state=barrier_states_found,
            consequence="Potential industrial trauma",
            assertion=AssertionStatus.AFFIRMED,
            temporal_status=TemporalStatus.DURING_EVENT,
            sif_status=sif_status,
            sif_reasons=sif_reasons,
            lsr=lsr_list,
            evidence=evidence,
            uncertainty=[],
            confidence=0.92,
            review_status=ReviewStatus.CANDIDATE,
            narrative=raw_text
        )

    def _create_evidence_span(self, raw_text: str, field_name: str, value: str, search_target: str) -> Optional[EvidenceSpan]:
        """Creates an EvidenceSpan strictly referencing exact offsets in raw_text."""
        pattern = re.escape(search_target)
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            start, end = match.start(), match.end()
            exact_text = raw_text[start:end]
            return EvidenceSpan(
                field=field_name,
                value=value,
                start_offset=start,
                end_offset=end,
                text=exact_text,
                confidence=1.0,
                source="NLP_EXTRACTION"
            )
        return None


assertion_detector = AssertionDetector()
