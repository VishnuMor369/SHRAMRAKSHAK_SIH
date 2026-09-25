"""
SHRAMRAKSHAK: Industrial Dataset Record Normalizer & Provenance Tracker
SIH 2026 Problem Statement: SIH26165

Implements P1.1 & P1.2:
- Intelligent field extraction across external safety schemas
- Strict Dataset Provenance tagging (P1.2):
    * is_oil_data = False
    * has_sif_ground_truth = False
    * label_status = UNLABELED_FOR_SIF
    * Explicit separation: Injury outcome fields (Hospitalized, Amputation, Loss of Eye)
      are NEVER treated as SIF precursor ground truth.
- Sanitizes NaN / Inf floats to prevent serialization faults.
"""

from typing import Dict, Any, Optional
import math


class DatasetNormalizer:
    NARRATIVE_FIELDS = [
        "final narrative", "narrative", "description", "incident_description",
        "report_text", "unsafe_act_description", "details", "observation", "summary",
        "incident details", "event description", "synopsis", "notes", "finding"
    ]

    LOCATION_FIELDS = [
        "employer", "location", "site", "plant", "facility", "facility_name",
        "rig", "field", "area", "address1", "city", "state", "department"
    ]

    ACTIVITY_FIELDS = [
        "eventtitle", "activity", "operation", "category", "job_type", "task_type",
        "task", "job", "event", "nature of work", "work type"
    ]

    @classmethod
    def sanitize_val(cls, val: Any) -> Any:
        """Sanitizes NaN, inf, or empty strings to None/clean string."""
        if val is None:
            return None
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
        val_str = str(val).strip()
        if val_str.lower() in ["nan", "null", "none", ""]:
            return None
        return val_str

    @classmethod
    def normalize_record(cls, raw_row: Dict[str, Any], record_idx: int, default_source: str = "EXTERNAL_DATASET") -> Dict[str, Any]:
        """
        Normalizes a heterogeneous raw dataset row into a clean intermediate dictionary
        with strict provenance metadata.
        """
        # Lowercase mapping for robust column lookup
        low_row = {str(k).lower().strip(): v for k, v in raw_row.items()}

        # 1. Extract Narrative
        narrative = ""
        for field in cls.NARRATIVE_FIELDS:
            if field in low_row and cls.sanitize_val(low_row[field]):
                narrative = str(low_row[field]).strip()
                break

        # 2. Extract Location / Site
        employer = cls.sanitize_val(low_row.get("employer")) or "Industrial Facility"
        city = cls.sanitize_val(low_row.get("city")) or ""
        state = cls.sanitize_val(low_row.get("state")) or ""
        loc_parts = [p for p in [employer, city, state] if p]
        location_str = ", ".join(loc_parts) if loc_parts else "General Work Area"

        # 3. Extract Activity / Task
        activity_str = "Operational Work"
        for field in cls.ACTIVITY_FIELDS:
            if field in low_row and cls.sanitize_val(low_row[field]):
                activity_str = str(low_row[field]).strip()
                break

        # 4. Extract Event Date
        date_str = cls.sanitize_val(low_row.get("eventdate")) or cls.sanitize_val(low_row.get("date")) or "2024-01-01"

        # 5. Record ID
        raw_id = cls.sanitize_val(low_row.get("id")) or cls.sanitize_val(low_row.get("upa")) or f"REC-{record_idx:05d}"
        report_id = f"RPT-DS-{raw_id}"

        # 6. Strict Dataset Provenance (P1.2)
        # Never treat external injury outcomes (Hospitalized, Amputation, NatureTitle) as SIF ground truth
        provenance = {
            "source_name": "External Industrial Dataset (OSHA Severe Injury Stress-Test)",
            "source_type": "EXTERNAL_STRESS_TEST",
            "source_country": "USA",
            "is_oil_data": False,
            "has_sif_ground_truth": False,
            "label_status": "UNLABELED_FOR_SIF",
            "external_record_id": str(raw_id),
            "unverified_outcome_fields": {
                "hospitalized": cls.sanitize_val(low_row.get("hospitalized")),
                "amputation": cls.sanitize_val(low_row.get("amputation")),
                "loss_of_eye": cls.sanitize_val(low_row.get("loss of eye")),
                "nature_title": cls.sanitize_val(low_row.get("naturetitle")),
                "event_title": cls.sanitize_val(low_row.get("eventtitle"))
            }
        }

        return {
            "report_id": report_id,
            "raw_id": raw_id,
            "narrative": narrative,
            "location": location_str,
            "site": employer,
            "activity": activity_str,
            "date": date_str,
            "provenance": provenance
        }


normalizer = DatasetNormalizer()
