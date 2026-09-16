from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models import Alert, SafetyReport
from nlp_engine.lsr_classifier import LSRClassifier
from nlp_engine.sif_classifier import SIFClassifier
from nlp_engine.precursor_extractor import PrecursorExtractor
from nlp_engine.event_normalizer import EventNormalizer
from nlp_engine.sif_pathway_engine import SIFPathwayEngine
from nlp_engine.review_store import review_store

class ReportGenerator:
    """
    Transforms raw Computer Vision alerts and event history records
    into standardized, natural-language Safety Reports with full AI/NLP analysis
    and explainable SIF Risk Pathway reasoning.
    """

    def __init__(self):
        self.lsr_classifier = LSRClassifier()
        self.sif_classifier = SIFClassifier()
        self.precursor_extractor = PrecursorExtractor()
        self.pathway_engine = SIFPathwayEngine()
        # In-memory storage for generated safety reports (keyed by report_id)
        self.generated_reports: Dict[str, SafetyReport] = {}

    def generate_narrative_from_alert(self, alert: Alert) -> str:
        """
        Creates a clear, contextual natural language incident narrative from an Alert.
        """
        alert_type = alert.type.lower()
        location = alert.location or "Demo Work Zone"
        camera = alert.camera or "C-01"
        count = alert.person_count or 1

        if "passport" in alert_type or "breach" in alert_type:
            return (
                f"Personnel entered an active lifting exclusion zone at {location} (Camera {camera}) "
                f"while a Start Work Safety Passport was active. Physical exclusion perimeter was breached, "
                f"halting high-risk mechanical lifting operations."
            )
        elif "zone" in alert_type:
            return (
                f"Unauthorized person detected inside the restricted boundary at {location} (Camera {camera}). "
                f"Worker crossed marked safety perimeter into active equipment operational zone."
            )
        elif "helmet" in alert_type or "ppe" in alert_type:
            worker_str = f"{count} worker{'s' if count > 1 else ''}"
            return (
                f"{worker_str.capitalize()} detected without required head protection (hard hat) in {location} "
                f"during monitored work activity on Camera {camera}."
            )
        else:
            return (
                f"Safety non-compliance event '{alert.type}' recorded at {location} (Camera {camera}). "
                f"{alert.notes or 'Observed during live automated CCTV monitoring.'}"
            )

    def convert_alert_to_report(self, alert: Alert) -> SafetyReport:
        """
        Converts an Alert object into a fully analyzed SafetyReport.
        """
        report_id = f"REP-{alert.id.replace('ALT-', '')}"

        # Generate narrative description
        description = self.generate_narrative_from_alert(alert)

        # Contextual mapping
        context = {
            "event_type": alert.type,
            "location": alert.location,
            "camera_id": alert.camera or alert.camera_id or "C-01",
            "hazard": alert.hazard,
            "activity": "Mechanical Lifting" if ("lift" in alert.location.lower() or "passport" in alert.type.lower()) else "General Site Operations"
        }

        # 1. Extract structured HSSE entities
        extracted = self.precursor_extractor.extract(description, context)
        context.update(extracted)

        # 2. Map IOGP Life-Saving Rules (Multi-label with evidence and confidence)
        lsr_detailed = self.lsr_classifier.classify_detailed(description, context)
        life_saving_rules = [item["rule"] for item in lsr_detailed]

        # 3. Classify SIF Potential and Risk (Campbell Institute criteria)
        sif_potential, risk_score, risk_level, reason, why_flagged = self.sif_classifier.classify(description, context)

        # 4. Normalize safety event for AI Risk Pathway Engine
        alert_dict = alert.dict() if hasattr(alert, "dict") else dict(alert)
        alert_dict.update({
            "activity": extracted["activity"],
            "hazard": extracted["hazard"],
            "unsafe_act": extracted["unsafe_act"],
            "unsafe_condition": extracted["unsafe_condition"],
            "barrier_failure": extracted["barrier_failure"],
            "details": description
        })
        norm_event = EventNormalizer.normalize_cctv_alert(alert_dict)

        # 5. Execute SIF Pathway Engine
        pathway_data = self.pathway_engine.analyze_event(norm_event, context)

        # 6. Check for human HSE review override
        stored_review = review_store.get_review(report_id)
        if stored_review:
            if stored_review.get("decision") == "CORRECT":
                if stored_review.get("corrected_sif") is not None:
                    sif_potential = stored_review["corrected_sif"]
                if stored_review.get("corrected_risk") is not None:
                    risk_score = stored_review["corrected_risk"]
                    risk_level = "CRITICAL" if risk_score >= 80 else ("HIGH" if risk_score >= 60 else ("MEDIUM" if risk_score >= 40 else "LOW"))
            elif stored_review.get("decision") == "REJECT":
                sif_potential = False

        # Merge dynamic reasoning into why_flagged if helpful
        final_why = why_flagged if why_flagged else pathway_data.get("reasoning", [])

        report = SafetyReport(
            report_id=report_id,
            alert_id=alert.id,
            source="CCTV_EVENT",
            event_type=alert.type,
            timestamp=alert.created_at or datetime.now().isoformat(),
            camera_id=alert.camera or "C-01",
            location=extracted["location"],
            activity=extracted["activity"],
            description=description,
            hazard=extracted["hazard"],
            unsafe_act=extracted["unsafe_act"],
            unsafe_condition=extracted["unsafe_condition"],
            barrier_failure=extracted["barrier_failure"],
            sif_potential=sif_potential,
            risk_score=risk_score,
            risk_level=risk_level,
            life_saving_rules=life_saving_rules,
            precursor=extracted["precursor"],
            reason=reason,
            why_flagged=final_why,
            ai_recommendation=extracted["ai_recommendation"],
            evidence_url=alert.evidence_url,
            evidence_image=alert.evidence_image,
            is_demo_sample=False,
            # Structured Causal Pathway Intelligence
            energy_source=pathway_data.get("energy_source"),
            exposure=pathway_data.get("exposure"),
            barrier=pathway_data.get("barrier"),
            potential_consequence=pathway_data.get("potential_consequence"),
            sif_pathway=pathway_data.get("sif_pathway"),
            confidence=pathway_data.get("confidence", 85),
            confidence_level=pathway_data.get("confidence_level", "HIGH"),
            evidence_strength=pathway_data.get("evidence_strength", "HIGH"),
            needs_hse_review=pathway_data.get("needs_hse_review", False),
            lsr_evidence=lsr_detailed,
            recommended_action=pathway_data.get("recommended_action"),
            score_breakdown=pathway_data.get("score_breakdown"),
            hse_review=stored_review,
            model_version=pathway_data.get("model_version", "Hybrid Safety Reasoning v1"),
            rule_version=pathway_data.get("rule_version", "SIF Rules v1 (Campbell Matrix)"),
            validation_note=pathway_data.get("validation_note")
        )

        self.generated_reports[report_id] = report
        return report

    def sync_from_alerts(self, alerts: List[Alert]) -> List[SafetyReport]:
        """
        Synchronizes all active and historical alerts into the safety report registry.
        """
        for alert in alerts:
            self.convert_alert_to_report(alert)
        
        # Return generated reports sorted newest first
        all_reports = list(self.generated_reports.values())
        all_reports.sort(key=lambda r: r.timestamp, reverse=True)
        return all_reports

