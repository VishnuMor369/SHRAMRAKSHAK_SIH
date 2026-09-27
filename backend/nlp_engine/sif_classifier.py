"""
SHRAMRAKSHAK: Canonical SIF Compatibility Wrapper
SIH 2026 Problem Statement: SIH26165

Converts legacy SIFClassifier into a strict delegation wrapper to SIFPathwayEngine.
All final safety truth is produced exclusively by SIFPathwayEngine.
Contains NO independent final SIF logic or conflicting regex scoring rules.
"""

from typing import Dict, List, Tuple, Any, Optional

try:
    from backend.models_canonical import SIFStatus, SafetyEvent
    from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
except ImportError:
    try:
        from models_canonical import SIFStatus, SafetyEvent
        from nlp_engine.sif_pathway_engine import sif_pathway_engine
    except ImportError:
        from ..models_canonical import SIFStatus, SafetyEvent
        from .sif_pathway_engine import sif_pathway_engine


class SIFClassifier:
    """
    Compatibility wrapper delegating exclusively to SIFPathwayEngine.
    Enforces Rule 1: ONE Authoritative SIF Engine.
    """

    def __init__(self):
        self.engine = sif_pathway_engine

    def classify(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, int, str, str, List[str]]:
        """
        Classifies incident narrative and context strictly through SIFPathwayEngine.
        Returns:
            (sif_potential, risk_score, risk_level, reason, why_flagged)
        """
        event = self.engine.evaluate_narrative(text, context)
        is_sif = (event.sif_status == SIFStatus.SIF_POTENTIAL)
        is_review = (event.sif_status == SIFStatus.REVIEW_REQUIRED)

        risk_score = 95 if is_sif else (50 if is_review else 20)
        risk_level = "CRITICAL" if is_sif else ("MEDIUM" if is_review else "LOW")
        reason = event.sif_reasons[0] if event.sif_reasons else ("SIF Potential identified" if is_sif else "No SIF potential identified")
        why_flagged = event.sif_reasons if event.sif_reasons else [reason]

        return is_sif, risk_score, risk_level, reason, why_flagged


sif_classifier = SIFClassifier()
