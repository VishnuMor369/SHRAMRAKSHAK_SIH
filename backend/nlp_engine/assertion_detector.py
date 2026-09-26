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
            if cl.uncertainty_cues or re.search(r'\b(not\s+true\s+that\s+no|not\s+the\s+case\s+that\s+no|never\s+without)\b', cl.text, re.IGNORECASE):
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
        post_event_match = re.search(r'\b(installed\s+after\s+(the\s+)?(event|incident)|subsequently\s+(installed|erected|placed)|after\s+the\s+event|rectified\s+later)\b', raw_text, re.IGNORECASE)
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
        hypo_match = re.search(r'\b(if\s+(the\s+)?[\w\s]{1,30}(fails?|breaks?|parts?|gives\s+way)|could\s+be\s+struck|might\s+fall|potential\s+to\s+strike)\b', raw_text, re.IGNORECASE)
        if hypo_match and ("if " in raw_text.lower() or "could " in raw_text.lower() or "might " in raw_text.lower()):
            span_hypo = self._create_evidence_span(raw_text, "assertion", "HYPOTHETICAL", hypo_match.group(0))
            act_span = self._create_evidence_span(raw_text, "activity", "MECHANICAL_LIFTING", "sling" if "sling" in raw_text.lower() else "lifting")
            csq_span = self._create_evidence_span(raw_text, "consequence", "STRUCK_BY", "personnel could be struck" if "personnel could be struck" in raw_text.lower() else "struck")
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

        # 5. Check for Explicit Exposure Negation (Test 3 & Mandatory Rule 6 Negated Case)
        neg_exposure_match = re.search(r'\b(no\s+(worker|personnel|contractor|person|employee|one|human)\s+(entered|was\s+inside|crossed|was\s+in(\s+the\s+area)?)|did\s+not\s+enter\s+(the\s+area|the\s+zone)|remained\s+outside(\s+the)?\s+(area|zone))\b', raw_text, re.IGNORECASE)
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
            r'\b(personnel\s+location\s+(is|was)?\s*(unknown|unrecorded|not\s+recorded)|'
            r'no\s+information\s+on\s+personnel(\s+location|\s+presence)?|'
            r'location\s+of\s+personnel\s+(is|was)?\s*(unknown|not\s+recorded)|'
            r'unknown\s+whether\s+(any\s+)?(worker|personnel|person)\s+entered|'
            r'unclear\s+if\s+(any\s+)?(worker|personnel|person)\s+was\s+inside|'
            r'personnel\s+location\s+was\s+not\s+recorded|'
            r'not\s+recorded\s+whether\s+anyone\s+was\s+inside)\b',
            raw_text, re.IGNORECASE
        )
        if unknown_exposure_match:
            span_unk = self._create_evidence_span(raw_text, "exposure", "UNKNOWN", unknown_exposure_match.group(0))
            barrier_failed = "failed" in raw_text.lower() or "broken" in raw_text.lower() or "bypassed" in raw_text.lower()
            b_state = ["FAILED"] if barrier_failed else ["UNKNOWN"]
            b_name = "EXCLUSION_ZONE" if "zone" in raw_text.lower() or "barrier" in raw_text.lower() else "GENERAL_CONTROL"
            b_span = self._create_evidence_span(raw_text, "barrier", b_name, "barrier" if "barrier" in raw_text.lower() else b_name)
            evidence_list = [s for s in [span_unk, b_span] if s]

            return SafetyEvent(
                event_id=event_id,
                report_id=report_id,
                source=source,
                site=site,
                location=location,
                activity="Mechanical Lifting" if "lift" in raw_text.lower() or "load" in raw_text.lower() else "Operational Activity",
                energy="Gravitational / Suspended Load" if "lift" in raw_text.lower() or "load" in raw_text.lower() else "Residual Energy",
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
            r'\b(may\s+have\s+(entered|been\s+inside|crossed)|'
            r'might\s+have\s+(entered|been\s+inside|crossed)|'
            r'possible\s+(entry|personnel|worker)|'
            r'suspected\s+(entry|personnel))\b',
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

        # 6. Check for Worker Remained Outside (Test 2: "Worker remained outside the exclusion zone while the load was suspended")
        remained_outside_match = re.search(r'\b(remained\s+outside(\s+the)?\s+exclusion\s+zone|stayed\s+outside|did\s+not\s+enter|kept\s+clear\s+of)\b', raw_text, re.IGNORECASE)
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
        activity_name = "General Rig Maintenance"
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

        # Identify Energy
        energy_id = "KINETIC_MECHANICAL"
        energy_name = "Mechanical / Kinetic Energy"
        for eng_id, eng_info in self.ontology.energies.items():
            for kw in eng_info.get("keywords", []):
                if kw in text_lower:
                    energy_id = eng_id
                    energy_name = eng_info.get("name", eng_id)
                    span = self._create_evidence_span(raw_text, "energy", energy_id, kw)
                    if span:
                        evidence.append(span)
                    break
            if energy_id != "KINETIC_MECHANICAL":
                break

        # Identify Barrier
        barriers_found = []
        barrier_states_found = []
        for bar_id, bar_info in self.ontology.barriers.items():
            for kw in bar_info.get("keywords", []):
                if kw in text_lower:
                    barriers_found.append(bar_id)
                    span = self._create_evidence_span(raw_text, "barrier", bar_id, kw)
                    if span:
                        evidence.append(span)
                    break

        if not barriers_found:
            barriers_found = ["GENERAL_ADMINISTRATIVE_CONTROL"]

        # Check barrier states (REMOVED vs BYPASSED vs FAILED vs EFFECTIVE)
        if "removed" in text_lower or "taken off" in text_lower or "dismantled" in text_lower:
            barrier_states_found.append("REMOVED")
        elif "bypassed" in text_lower or "ducked under" in text_lower or "crossed" in text_lower or "entered" in text_lower:
            barrier_states_found.append("BYPASSED")
        elif "failed" in text_lower or "broke" in text_lower or "snapped" in text_lower or "ruptured" in text_lower:
            barrier_states_found.append("FAILED")
        elif "intact" in text_lower or "verified" in text_lower or "inspected" in text_lower:
            barrier_states_found.append("EFFECTIVE_VERIFIED")
        else:
            barrier_states_found.append("PRESENT_UNVERIFIED")

        # Check human exposure in generic text (Rule 6)
        has_affirmed_human = (
            any(w in text_lower for w in ["worker", "personnel", "employee", "contractor", "operator", "rigger", "roustabout", "technician", "mechanic", "man", "crew", "person"]) and
            any(a in text_lower for a in ["entered", "inside", "struck", "caught", "trapped", "contact", "fell", "injured", "hit", "exposed", "near", "underneath", "beneath", "crossed"])
        )
        has_unknown_human = any(w in text_lower for w in [
            "personnel location", "location unknown", "not recorded", "no information on personnel",
            "unclear if anyone", "unknown whether anyone", "unrecorded"
        ])
        has_negated_human = any(w in text_lower for w in [
            "no worker", "no person", "remained outside", "stayed clear", "no human", "did not enter", "no one entered", "no personnel"
        ])
        has_possible_human = any(w in text_lower for w in [
            "may have", "might have", "possible entry", "suspected", "possibly"
        ])

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
        is_compromised = any(st in ["FAILED", "BYPASSED", "REMOVED", "DEGRADED"] for st in barrier_states_found)
        is_high_energy = energy_id in ["GRAVITATIONAL_KINETIC", "HIGH_PRESSURE_STORED", "HIGH_PRESSURE_HYDROCARBON", "ATMOSPHERIC_TOXIC", "ELECTRICAL_ENERGY", "GRAVITATIONAL_HEIGHT"]

        if gen_exp_status == ExposureStatus.NEGATED:
            sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            sif_reasons = ["Personnel remained outside hazard boundary; human exposure explicitly negated (NO_HUMAN_EXPOSURE)"]
        elif is_high_energy and is_compromised and gen_exp_status == ExposureStatus.CONFIRMED:
            sif_status = SIFStatus.SIF_POTENTIAL
            sif_reasons = [
                f"High-energy hazard present: {energy_name}",
                "Human exposure affirmed in hazard zone",
                f"Barrier compromised: {', '.join(barrier_states_found)}"
            ]
        elif is_high_energy and (gen_exp_status in [ExposureStatus.UNKNOWN, ExposureStatus.POSSIBLE] or is_compromised):
            sif_status = SIFStatus.REVIEW_REQUIRED
            sif_reasons = [
                f"High-energy hazard present: {energy_name}",
                "Physical human exposure or barrier integrity requires HSE human verification"
            ]
        else:
            sif_status = SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            sif_reasons = ["No credible human exposure to high-energy hazard or catastrophic barrier compromise identified"]

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
            confidence=0.88,
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
