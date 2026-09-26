from typing import List, Dict, Optional, Any
from models import Alert, SafetyReport, AnalysisSummary, RecurringPattern
from nlp_engine.report_generator import ReportGenerator
from nlp_engine.pattern_miner import PatternMiner
from nlp_engine.lsr_classifier import LSRClassifier
from nlp_engine.sif_classifier import SIFClassifier
from nlp_engine.precursor_extractor import PrecursorExtractor
from nlp_engine.sif_pathway_engine import SIFPathwayEngine
from nlp_engine.event_normalizer import EventNormalizer
from nlp_engine.review_store import review_store
from nlp_engine.validation_engine import validation_engine
from nlp_engine.dataset_store import dataset_store

class NLPSafetyAnalyzer:
    """
    Central AI + NLP Safety Analysis Engine (SIH PS 26165).
    Coordinates the translation of visual CCTV safety events into structured
    safety observations, executes multi-label IOGP Life-Saving Rules mapping,
    performs explainable SIF precursor classification, and mines recurring patterns.
    """

    def __init__(self):
        self.report_generator = ReportGenerator()
        self.pattern_miner = PatternMiner()
        self.lsr_classifier = LSRClassifier()
        self.sif_classifier = SIFClassifier()
        self.precursor_extractor = PrecursorExtractor()
        self.pathway_engine = SIFPathwayEngine()

    def sync_and_get_reports(self, alerts: List[Alert]) -> List[SafetyReport]:
        """
        Transforms all current and historical CCTV alerts into safety reports
        and returns the consolidated list.
        """
        return self.report_generator.sync_from_alerts(alerts)

    def get_report_by_id(self, report_id: str, alerts: List[Alert]) -> Optional[SafetyReport]:
        """
        Retrieves a single safety report by ID, checking generated reports and dataset_store.
        """
        if report_id in self.report_generator.generated_reports:
            return self.report_generator.generated_reports[report_id]

        # Check dataset_store for uploaded dataset reports
        ds_item = dataset_store.get_report_by_id(report_id)
        if ds_item:
            return SafetyReport(**ds_item)

        # Try sync and lookup
        self.report_generator.sync_from_alerts(alerts)
        if report_id in self.report_generator.generated_reports:
            return self.report_generator.generated_reports[report_id]
        return None

    def analyze_report(self, report_id: str, alerts: List[Alert]) -> Optional[SafetyReport]:
        """
        Runs on-demand AI/NLP re-analysis for a specific safety report.
        """
        report = self.get_report_by_id(report_id, alerts)
        if not report:
            return None

        context = {
            "event_type": report.event_type,
            "location": report.location,
            "activity": report.activity,
            "hazard": report.hazard,
            "barrier_failure": report.barrier_failure
        }

        # 1. Structured HSSE extraction
        extracted = self.precursor_extractor.extract(report.description, context)
        context.update(extracted)
        report.activity = extracted["activity"]
        report.location = extracted["location"]
        report.hazard = extracted["hazard"]
        report.unsafe_act = extracted["unsafe_act"]
        report.unsafe_condition = extracted["unsafe_condition"]
        report.barrier_failure = extracted["barrier_failure"]
        report.precursor = extracted["precursor"]
        report.ai_recommendation = extracted["ai_recommendation"]

        # 2. Multi-label IOGP Life-Saving Rules
        lsr_detailed = self.lsr_classifier.classify_detailed(report.description, context)
        report.life_saving_rules = [item["rule"] for item in lsr_detailed]
        report.lsr_evidence = lsr_detailed

        # 3. SIF Classification & Explainability
        sif_pot, score, lvl, reason, why = self.sif_classifier.classify(report.description, context)
        report.sif_potential = sif_pot
        report.risk_score = score
        report.risk_level = lvl
        report.reason = reason
        report.why_flagged = why

        # 4. SIF Pathway Engine
        event_dict = {
            "id": report.report_id,
            "description": report.description,
            "location": report.location,
            "activity": report.activity,
            "hazard": report.hazard,
            "unsafe_act": report.unsafe_act,
            "unsafe_condition": report.unsafe_condition,
            "barrier_failure": report.barrier_failure,
            "timestamp": report.timestamp,
            "evidence_image": report.evidence_image,
            "evidence_url": report.evidence_url
        }
        if report.source == "CCTV_EVENT":
            norm = EventNormalizer.normalize_cctv_alert(event_dict)
        else:
            norm = EventNormalizer.normalize_prototype_record(event_dict)

        pathway = self.pathway_engine.analyze_event(norm, context)
        report.energy_source = pathway.get("energy_source")
        report.exposure = pathway.get("exposure")
        report.barrier = pathway.get("barrier")
        report.potential_consequence = pathway.get("potential_consequence")
        report.sif_pathway = pathway.get("sif_pathway")
        report.confidence = pathway.get("confidence", 85)
        report.confidence_level = pathway.get("confidence_level", "HIGH")
        report.evidence_strength = pathway.get("evidence_strength", "HIGH")
        report.needs_hse_review = pathway.get("needs_hse_review", False)
        report.recommended_action = pathway.get("recommended_action")
        report.score_breakdown = pathway.get("score_breakdown")
        report.model_version = pathway.get("model_version")
        report.rule_version = pathway.get("rule_version")
        report.validation_note = pathway.get("validation_note")

        # Attach review if present
        report.hse_review = review_store.get_review(report.report_id)

        return report

    def analyze_raw_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes raw report text (demonstrating how OIL's real UA/UC or Incident reports
        plug directly into the exact same NLP pipeline).
        """
        from nlp_engine.assertion_detector import AssertionDetector
        context = context or {}
        safety_event = AssertionDetector.evaluate_safety_event(text, context)

        extracted = self.precursor_extractor.extract(text, context)
        combined_context = {**context, **extracted}
        lsrs = self.lsr_classifier.classify(text, combined_context)
        sif_pot, score, lvl, reason, why = self.sif_classifier.classify(text, combined_context)

        ass_val = safety_event.assertion.value if hasattr(safety_event.assertion, "value") else str(safety_event.assertion)
        temp_val = safety_event.temporal_status.value if hasattr(safety_event.temporal_status, "value") else str(safety_event.temporal_status)

        # Override SIF potential and reasoning if negation or hypothetical is detected
        if ass_val == "NEGATED":
            sif_pot = False
            score = 15
            lvl = "LOW"
            reason = "Exposure explicitly NEGATED in report narrative. No person was present in the hazard area; does not constitute a positive SIF precursor."
            why = ["Exposure assertion is NEGATED", "Active barriers/controls prevented entry", "Classified as non-exposure observation"]
        elif ass_val == "HYPOTHETICAL":
            sif_pot = False
            score = 35
            lvl = "LOW"
            reason = "Hypothetical / conditional statement. Consequence described is what could happen if a barrier failed, not an observed barrier breach."
            why = ["Hypothetical conditional clause", "No actual barrier failure observed on site", "Evaluated as preventive risk scenario"]
        elif ass_val == "POST_EVENT" or temp_val == "POST_EVENT":
            reason = "Temporal / post-event action. Note: Barricade was installed following the observation, meaning barrier was absent during original event."
            why.append("Post-event condition noted: barrier was installed after the incident")

        spans_serialized = [s.to_dict() if hasattr(s, "to_dict") else s for s in getattr(safety_event, "evidence", [])]
        ev_dict = safety_event.to_dict() if hasattr(safety_event, "to_dict") else {}

        return {
            "description": text,
            "extracted_entities": extracted,
            "life_saving_rules": lsrs,
            "sif_potential": sif_pot,
            "risk_score": score,
            "risk_level": lvl,
            "reason": reason,
            "why_flagged": why,
            "safety_event": ev_dict,
            "assertion_status": ass_val,
            "temporal_status": temp_val,
            "consequence_type": getattr(safety_event, "consequence", "UNSPECIFIED"),
            "evidence_spans": spans_serialized
        }

    def get_summary(self, alerts: List[Alert]) -> AnalysisSummary:
        """
        Generates the comprehensive analysis summary metrics, risk distribution,
        top LSRs, mined patterns, and area risk prioritizations.
        """
        reports = self.sync_and_get_reports(alerts)
        total = len(reports)
        sif_count = sum(1 for r in reports if r.sif_potential)
        sif_pct = round((sif_count / total) * 100, 1) if total > 0 else 0.0

        patterns = self.pattern_miner.mine_patterns(reports)
        priorities = self.pattern_miner.calculate_prioritization(reports)

        return AnalysisSummary(
            reports_analyzed=total,
            sif_potential_count=sif_count,
            sif_percentage=sif_pct,
            risk_distribution=priorities["risk_distribution"],
            top_life_saving_rules=priorities["top_life_saving_rules"],
            recurring_patterns=patterns,
            high_risk_locations=priorities["high_risk_locations"],
            high_risk_activities=priorities["high_risk_activities"]
        )

    def get_recurring_patterns(self, alerts: List[Alert]) -> List[RecurringPattern]:
        """
        Returns mined recurring precursor patterns across all reports.
        """
        reports = self.sync_and_get_reports(alerts)
        return self.pattern_miner.mine_patterns(reports)


    def submit_hse_review(self, report_id: str, review_payload: Dict[str, Any], alerts: List[Alert]) -> Optional[SafetyReport]:
        """
        Stores an official HSE human review decision (CONFIRM / CORRECT / REJECT)
        and feeds the sample to the validation engine for confusion matrix calculation.
        """
        report = self.get_report_by_id(report_id, alerts)
        if not report:
            return None

        # Determine effective HSE SIF ground truth for validation
        decision = review_payload.get("decision", "CONFIRM").upper()
        if decision == "CONFIRM":
            hse_sif = report.sif_potential
        elif decision == "CORRECT":
            corr = review_payload.get("corrected_sif")
            hse_sif = corr if corr is not None else report.sif_potential
        else:  # REJECT
            hse_sif = not report.sif_potential

        # Record validation sample
        validation_engine.record_validation_sample(report_id, ai_sif=report.sif_potential, hse_sif=hse_sif)

        # Persist review
        review_record = review_store.save_review(report_id, review_payload)
        report.hse_review = review_record

        # Apply corrections to active in-memory report instance
        if decision == "CORRECT":
            if review_payload.get("corrected_sif") is not None:
                report.sif_potential = review_payload["corrected_sif"]
            if review_payload.get("corrected_risk") is not None:
                report.risk_score = int(review_payload["corrected_risk"])
                report.risk_level = "CRITICAL" if report.risk_score >= 80 else ("HIGH" if report.risk_score >= 60 else ("MEDIUM" if report.risk_score >= 40 else "LOW"))
            if review_payload.get("corrected_barrier"):
                report.barrier = review_payload["corrected_barrier"]
            if review_payload.get("corrected_lsr"):
                report.life_saving_rules = [review_payload["corrected_lsr"]]
            if review_payload.get("corrected_consequence"):
                report.potential_consequence = review_payload["corrected_consequence"]
        elif decision == "REJECT":
            report.sif_potential = False

        return report

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Returns statistical validation metrics (TP, TN, FP, FN, Precision, Recall, F1)
        or INSUFFICIENT_LABELLED_DATA status if insufficient labelled evaluations exist.
        """
        return validation_engine.get_validation_summary()

    def export_summary_pdf(self, alerts: List[Alert]) -> bytes:
        """
        Exports all reports and summary intelligence as a formatted HSE PDF.
        """
        reports = self.sync_and_get_reports(alerts)
        summary = self.get_summary(alerts)
        from nlp_engine.pdf_exporter import pdf_exporter
        return pdf_exporter.export_summary_pdf(reports, summary)

    def export_single_report_pdf(self, report_id: str, alerts: List[Alert]) -> Optional[bytes]:
        """
        Exports an individual safety report dossier as a PDF.
        """
        report = self.get_report_by_id(report_id, alerts)
        if not report:
            return None
        from nlp_engine.pdf_exporter import pdf_exporter
        return pdf_exporter.export_single_report_pdf(report)

# Global Singleton NLP Analyzer Instance
nlp_analyzer = NLPSafetyAnalyzer()

