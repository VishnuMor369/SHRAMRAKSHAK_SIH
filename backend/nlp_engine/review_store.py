import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class HSEReviewSubmission(BaseModel):
    decision: str  # "CONFIRM" | "CORRECT" | "REJECT"
    corrected_sif: Optional[bool] = None
    corrected_risk: Optional[int] = None
    corrected_barrier: Optional[str] = None
    corrected_lsr: Optional[str] = None
    corrected_consequence: Optional[str] = None
    reviewer_role: Optional[str] = "HSE Officer"
    notes: Optional[str] = None

class HSEReviewRecord(BaseModel):
    report_id: str
    decision: str
    ai_sif: bool
    ai_risk: int
    hse_sif: bool
    hse_risk: int
    corrected_barrier: Optional[str] = None
    corrected_lsr: Optional[str] = None
    corrected_consequence: Optional[str] = None
    reviewer_role: str = "HSE Officer"
    notes: Optional[str] = None
    timestamp: str
    engine_version: str = "Hybrid Safety Reasoning v1"
    rule_version: str = "SIF Rules v1"

class HSEReviewStore:
    """
    Stores human HSE review decisions, confirmations, and corrections.
    Creates an auditable feedback loop for continuous model evaluation without fabricating data.
    """

    def __init__(self):
        self._reviews: Dict[str, HSEReviewRecord] = {}

    def save_review(
        self,
        report_id: str,
        submission: Any,
        ai_sif: bool = True,
        ai_risk: int = 80
    ) -> Dict[str, Any]:
        if isinstance(submission, dict):
            sub_dict = submission
            decision = str(sub_dict.get("decision", "CONFIRM")).upper()
            corr_sif = sub_dict.get("corrected_sif")
            corr_risk = sub_dict.get("corrected_risk")
            corr_barrier = sub_dict.get("corrected_barrier")
            corr_lsr = sub_dict.get("corrected_lsr")
            corr_consequence = sub_dict.get("corrected_consequence")
            reviewer_role = sub_dict.get("reviewer_role") or "HSE Officer"
            notes = sub_dict.get("notes") or ""
            if "ai_sif" in sub_dict:
                ai_sif = sub_dict["ai_sif"]
            if "ai_risk" in sub_dict:
                ai_risk = sub_dict["ai_risk"]
        else:
            decision = str(submission.decision).upper()
            corr_sif = submission.corrected_sif
            corr_risk = submission.corrected_risk
            corr_barrier = submission.corrected_barrier
            corr_lsr = submission.corrected_lsr
            corr_consequence = submission.corrected_consequence
            reviewer_role = submission.reviewer_role or "HSE Officer"
            notes = submission.notes or ""

        if decision == "CONFIRM":
            hse_sif = ai_sif
            hse_risk = ai_risk
        elif decision == "REJECT":
            hse_sif = False
            hse_risk = min(ai_risk, 30)
        else:  # "CORRECT"
            hse_sif = corr_sif if corr_sif is not None else ai_sif
            hse_risk = corr_risk if corr_risk is not None else ai_risk

        record = HSEReviewRecord(
            report_id=report_id,
            decision=decision,
            ai_sif=ai_sif,
            ai_risk=ai_risk,
            hse_sif=hse_sif,
            hse_risk=hse_risk,
            corrected_barrier=corr_barrier,
            corrected_lsr=corr_lsr,
            corrected_consequence=corr_consequence,
            reviewer_role=reviewer_role,
            notes=notes,
            timestamp=datetime.now().isoformat(),
            engine_version="Hybrid Safety Reasoning v1",
            rule_version="SIF Rules v1"
        )

        self._reviews[report_id] = record
        return record.dict()

    def get_review(self, report_id: str) -> Optional[Dict[str, Any]]:
        rec = self._reviews.get(report_id)
        return rec.dict() if rec else None

    def get_all_reviews(self) -> List[HSEReviewRecord]:
        return list(self._reviews.values())

    def clear_reviews(self):
        self._reviews.clear()

# Global Review Store Instance
review_store = HSEReviewStore()
