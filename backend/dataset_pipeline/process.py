"""
SHRAMRAKSHAK: Single-Record Safety Intelligence Processing Engine
SIH 2026 Problem Statement: SIH26165

Implements P1.1 processing flow:
NORMALIZE -> SAFETY EVENT -> NLP ASSERTION -> SIF PATHWAY -> LSR MAPPER -> EMBEDDING -> MEMORY -> RECURRENCE -> PERSISTENCE
"""

from typing import Dict, Any, Optional, Tuple

try:
    from backend.models_canonical import SafetyEvent, SIFStatus
    from backend.database import db
    from backend.nlp_engine.assertion_detector import assertion_detector
    from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
    from backend.nlp_engine.lsr_classifier import lsr_classifier
    from backend.nlp_engine.recurrence_engine import recurrence_engine
except ImportError:
    try:
        from models_canonical import SafetyEvent, SIFStatus
        from database import db
        from nlp_engine.assertion_detector import assertion_detector
        from nlp_engine.sif_pathway_engine import sif_pathway_engine
        from nlp_engine.lsr_classifier import lsr_classifier
        from nlp_engine.recurrence_engine import recurrence_engine
    except ImportError:
        from ..models_canonical import SafetyEvent, SIFStatus
        from ..database import db
        from ..nlp_engine.assertion_detector import assertion_detector
        from ..nlp_engine.sif_pathway_engine import sif_pathway_engine
        from ..nlp_engine.lsr_classifier import lsr_classifier
        from ..nlp_engine.recurrence_engine import recurrence_engine


class DatasetProcessor:
    def __init__(self):
        self.db = db
        self.assertion_detector = assertion_detector
        self.sif_engine = sif_pathway_engine
        self.lsr_engine = lsr_classifier
        self.recurrence_engine = recurrence_engine

    def process_normalized_record(self, norm_rec: Dict[str, Any]) -> SafetyEvent:
        """
        Executes end-to-end intelligence pipeline on a normalized record:
        Persists report -> Generates SafetyEvent -> SIF -> LSR -> Embeddings -> Recurrence -> Persistent DB.
        """
        report_id = norm_rec["report_id"]
        narrative = norm_rec["narrative"]
        site = norm_rec["site"]
        location = norm_rec["location"]
        activity = norm_rec["activity"]
        timestamp = norm_rec["date"]
        provenance = norm_rec["provenance"]

        # 1. Insert Report to SQLite
        self.db.insert_report(
            report_id=report_id,
            raw_text=narrative,
            source=provenance.get("source_type", "DATASET"),
            site=site,
            location=location,
            reporter="External Data Record",
            metadata=provenance
        )

        # 2. NLP Assertion & Entity Extraction -> Canonical SafetyEvent
        event_id = f"EVT-{report_id}"
        event = self.assertion_detector.analyze(
            narrative,
            context={
                "event_id": event_id,
                "report_id": report_id,
                "source": "DATASET",
                "site": site,
                "location": location,
                "activity": activity
            }
        )

        # 3. Deterministic SIF Pathway Reasoning
        event = self.sif_engine.evaluate(event)

        # 4. Multi-Label IOGP LSR Mapping
        lsr_matches = self.lsr_engine.classify_event(event)
        event.lsr = [m["lsr"] for m in lsr_matches]

        # 5. Attach Provenance
        event.provenance = provenance

        # 6. Save Canonical SafetyEvent to SQLite
        self.db.save_event(event)

        # 7. Semantic Memory & Two-Stage Recurrence
        try:
            self.recurrence_engine.process_event(event)
        except Exception:
            pass

        return event


dataset_processor = DatasetProcessor()
