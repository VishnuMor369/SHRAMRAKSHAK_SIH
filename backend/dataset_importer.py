"""
SHRAMRAKSHAK: Multi-Format Company Safety Dataset Importer & Normalizer
SIH 2026 Problem Statement: SIH26165

Supports importing:
- CSV (.csv)
- Excel (.xlsx, .xls)
- JSON (.json)
- PDF (.pdf) - Extracts text & tables using pypdf

Normalizes records into canonical SafetyEvents and routes them through:
IMPORT -> PARSE -> NORMALIZE -> NLP -> SIF ANALYSIS -> UNIFIED STORE -> SAFETY MEMORY
"""

import io
import os
import re
import json
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import math
import pandas as pd
from pypdf import PdfReader

from unified_event_store import unified_event_store, SafetyEvent
from safety_memory import safety_memory
from nlp_engine.assertion_detector import AssertionDetector


class DatasetNormalizer:
    """
    Intelligent field mapping across various company safety data schemas.
    """

    NARRATIVE_FIELDS = [
        "final narrative", "narrative", "description", "incident_description",
        "report_text", "unsafe_act_description", "details", "observation", "summary",
        "incident details", "event description", "synopsis", "notes", "finding"
    ]

    LOCATION_FIELDS = [
        "location", "site", "employer", "plant", "facility", "facility_name",
        "rig", "field", "area", "address1", "city", "state", "department"
    ]

    ACTIVITY_FIELDS = [
        "activity", "operation", "eventtitle", "category", "job_type", "task_type",
        "task", "job", "event", "nature of work", "work type"
    ]

    HAZARD_FIELDS = [
        "naturetitle", "nature", "source title", "sourcetitle", "hazard", "risk_type",
        "primary hazard", "hazard type", "energy source", "unsafe condition"
    ]

    CONSEQUENCE_FIELDS = [
        "consequence", "injury", "potential consequence", "hospitalized", "amputation",
        "damage", "severity", "incident consequence"
    ]

    DATE_FIELDS = [
        "eventdate", "date", "incident_date", "report_date", "created_at", "timestamp",
        "occurrence date", "date of occurrence"
    ]

    @classmethod
    def find_best_field(cls, record: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """Case-insensitive fuzzy key match."""
        keys = list(record.keys())
        # Exact match
        for cand in candidates:
            for k in keys:
                if str(k).strip().lower() == cand:
                    val = str(record[k]).strip()
                    if val and val.lower() not in ["none", "nan", "null", ""]:
                        return val

        # Partial substring match
        for cand in candidates:
            for k in keys:
                if cand in str(k).strip().lower():
                    val = str(record[k]).strip()
                    if val and val.lower() not in ["none", "nan", "null", ""]:
                        return val

        return None


class DatasetImportManager:
    """
    Manages dataset file parsing, asynchronous batch processing, and progress telemetry.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self.status: str = "IDLE"  # IDLE | VALIDATED | PROCESSING | COMPLETED | FAILED
        self.progress: float = 0.0
        self.current_filename: Optional[str] = None
        self.total_rows: int = 0
        self.processed_rows: int = 0
        self.successful_rows: int = 0
        self.review_rows: int = 0
        self.error_message: Optional[str] = None
        self.column_mapping: Dict[str, Any] = {}
        self.preview_records: List[Dict[str, Any]] = []
        self._cached_records: List[Dict[str, Any]] = []

    @property
    def processed_count(self) -> int:
        return self.processed_rows

    def parse_file(self, filename: str, contents: bytes) -> Dict[str, Any]:
        """
        Parses raw bytes from CSV, XLSX, JSON, or PDF into normalized row dictionaries.
        """
        ext = os.path.splitext(filename)[1].lower()
        records: List[Dict[str, Any]] = []

        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(contents), low_memory=False)
            try:
                df = df.where(pd.notnull(df), None)
            except Exception:
                pass
            records = df.to_dict(orient="records")

        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(contents))
            try:
                df = df.where(pd.notnull(df), None)
            except Exception:
                pass
            records = df.to_dict(orient="records")

        elif ext == ".json":
            parsed = json.loads(contents.decode("utf-8"))
            if isinstance(parsed, list):
                records = parsed
            elif isinstance(parsed, dict):
                # Try common keys
                for key in ["records", "data", "reports", "incidents", "events"]:
                    if key in parsed and isinstance(parsed[key], list):
                        records = parsed[key]
                        break
                if not records:
                    records = [parsed]

        elif ext == ".pdf":
            # Extract text lines/paragraphs from PDF using pypdf
            reader = PdfReader(io.BytesIO(contents))
            all_text = ""
            for page in reader.pages:
                txt = page.extract_text() or ""
                all_text += "\n" + txt

            # Split into incident blocks by common incident markers
            blocks = re.split(r"(?:\n\s*(?:Incident|Report|Observation|Case|ID)\s*[:#\d]+|\n\s*---\s*\n|\n\s*\d+[\.\)]\s+)", all_text)
            for idx, block in enumerate(blocks):
                clean_blk = block.strip()
                if len(clean_blk) > 25:
                    records.append({
                        "narrative": clean_blk,
                        "location": "OIL Operational Site (PDF Dossier)",
                        "activity": "Operational Safety Report",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "document_page": idx + 1
                    })

        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .csv, .xlsx, .json, .pdf")

        if not records:
            raise ValueError("The provided file contains zero readable safety records.")

        # Identify sample mapping from first non-empty record
        sample = records[0]
        mapping = {
            "narrative_field": DatasetNormalizer.find_best_field(sample, DatasetNormalizer.NARRATIVE_FIELDS) or list(sample.keys())[0],
            "location_field": DatasetNormalizer.find_best_field(sample, DatasetNormalizer.LOCATION_FIELDS) or "OIL Field Location",
            "activity_field": DatasetNormalizer.find_best_field(sample, DatasetNormalizer.ACTIVITY_FIELDS) or "General Operations",
            "hazard_field": DatasetNormalizer.find_best_field(sample, DatasetNormalizer.HAZARD_FIELDS) or "Operational Hazard"
        }

        # Clean preview records to guarantee JSON compliance (no nan/inf floats)
        def _clean_val(v):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return v
        clean_preview = [{k: _clean_val(v) for k, v in r.items()} for r in records[:5]]

        with self._lock:
            self.current_filename = filename
            self.total_rows = len(records)
            self.processed_rows = 0
            self.successful_rows = 0
            self.review_rows = 0
            self.progress = 0.0
            self.status = "VALIDATED"
            self.error_message = None
            self.column_mapping = mapping
            self.preview_records = clean_preview
            self._cached_records = records

        return {
            "filename": filename,
            "total_rows": len(records),
            "detected_mapping": mapping,
            "preview_samples": clean_preview
        }

    def parse_default_dataset(self) -> Dict[str, Any]:
        """Loads and normalizes the default company dataset January2015toNovember2025.csv."""
        import zipfile
        current_dir = os.path.dirname(os.path.abspath(__file__))
        home_dir = os.path.expanduser("~")
        possible_paths = [
            os.path.join(current_dir, "data", "January2015toNovember2025.zip"),
            os.path.join(current_dir, "data", "January2015toNovember2025.csv"),
            os.path.join(current_dir, "January2015toNovember2025.zip"),
            os.path.join(current_dir, "January2015toNovember2025.csv"),
            os.path.join(home_dir, "Downloads", "SIH FINAL PROJECT SHRAMRAKSHAK ZIP", "SIH FINAL PROJECT SHRAMRAKSHAK", "January2015toNovember2025.zip"),
            os.path.join(home_dir, "Downloads", "January2015toNovember2025.zip")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    if path.endswith(".zip"):
                        with zipfile.ZipFile(path, 'r') as z:
                            csv_members = [m for m in z.namelist() if m.endswith(".csv")]
                            if csv_members:
                                with z.open(csv_members[0]) as f:
                                    return self.parse_file(csv_members[0], f.read())
                    elif path.endswith(".csv"):
                        with open(path, 'rb') as f:
                            return self.parse_file(os.path.basename(path), f.read())
                except Exception as e:
                    print(f"Default dataset parse warning: {e}")

        # Fallback to realistic demo records
        csv_fallback = (
            "narrative,location,activity,hazard,consequence\n"
            "Worker entered lifting exclusion zone while 15T pipe was suspended.,Drilling Rig 04 - Drill Floor,Mechanical Lifting,Suspended Load,Fatal crush\n"
            "Maintenance commenced on discharge manifold without verified zero-energy bleed.,Compressor Station 01,High-Pressure Maintenance,Flammable Gas,High pressure injection\n"
            "No worker entered the exclusion zone during pipe handling operations.,Pipe Yard 02,Tubular Handling,Mobile Crane,None\n"
            "Worker observed on rig sub-structure without fall arrest lanyard secured.,Drill Floor Substructure,Rig Move,Elevation Fall,Fall from height\n"
            "Contractor bypassed zone interlock switch during hydraulic testing.,Hydraulic Workshop,Equipment Testing,Hydraulic Energy,Pinch trauma\n"
        ).encode('utf-8')
        return self.parse_file("January2015toNovember2025.csv", csv_fallback)

    def start_background_import(self, max_rows: Optional[int] = None):
        """Spawns background thread to execute batched NLP ingestion without freezing UI."""
        with self._lock:
            if not self._cached_records:
                raise ValueError("No validated dataset in memory. Please upload a file first.")
            self.status = "PROCESSING"
            self.progress = 0.05

        def _worker():
            try:
                target_records = self._cached_records
                if max_rows and max_rows > 0:
                    target_records = target_records[:max_rows]

                total = len(target_records)
                successful = 0
                requiring_review = 0

                batch_size = 20
                for i in range(0, total, batch_size):
                    batch = target_records[i:i + batch_size]
                    for row in batch:
                        narrative = (
                            DatasetNormalizer.find_best_field(row, DatasetNormalizer.NARRATIVE_FIELDS) or
                            str(row.get("narrative") or row.get("description") or list(row.values())[0])
                        ).strip()

                        location = DatasetNormalizer.find_best_field(row, DatasetNormalizer.LOCATION_FIELDS) or "OIL Industrial Facility"
                        activity = DatasetNormalizer.find_best_field(row, DatasetNormalizer.ACTIVITY_FIELDS) or "General Operations"

                        if not narrative or len(narrative) < 10:
                            requiring_review += 1
                            continue

                        # Execute NLP Reasoning
                        event_id = f"EVT-IMP-{int(time.time() * 1000) % 1000000:06d}-{uuid.uuid4().hex[:4].upper()}"
                        parsed_se = AssertionDetector.evaluate_safety_event(
                            narrative,
                            context={
                                "event_id": event_id,
                                "location": location,
                                "activity": activity,
                                "source": "IMPORTED"
                            }
                        )

                        # Create canonical unified event
                        canonical = SafetyEvent(
                            event_id=event_id,
                            source="IMPORTED",
                            timestamp=parsed_se.timestamp,
                            location=location,
                            activity=activity,
                            narrative=narrative,
                            hazard=parsed_se.hazard,
                            exposure=parsed_se.exposure,
                            critical_barrier=parsed_se.critical_barrier,
                            barrier_condition=parsed_se.barrier_state,
                            consequence=parsed_se.potential_consequence,
                            sif_potential=parsed_se.sif_potential,
                            lsr=parsed_se.life_saving_rule,
                            assertion_status=parsed_se.assertion_status.value if hasattr(parsed_se.assertion_status, "value") else str(parsed_se.assertion_status),
                            temporal_status=parsed_se.temporal_status,
                            evidence_spans=[s.dict() if hasattr(s, "dict") else s for s in parsed_se.evidence_spans],
                            evidence_sources=["DOCUMENT", "SYSTEM_INFERENCE"],
                            lifecycle_state="RESOLVED" if parsed_se.sif_potential in ["NOT_SIF", "LOW"] else "SIF_ASSESSED",
                            metadata={"original_row": {str(k): str(v)[:100] for k, v in row.items() if v}}
                        )

                        unified_event_store.add_event(canonical)

                        # Feed into Safety Memory
                        try:
                            safety_memory.record_safety_event(parsed_se)
                        except Exception:
                            pass

                        successful += 1

                    # Update progress
                    current_processed = min(i + len(batch), total)
                    with self._lock:
                        self.processed_rows = current_processed
                        self.successful_rows = successful
                        self.review_rows = requiring_review
                        self.progress = round(current_processed / total, 2)

                    time.sleep(0.01)  # Yield CPU to prevent thread starving

                with self._lock:
                    self.status = "COMPLETED"
                    self.progress = 1.0

            except Exception as e:
                with self._lock:
                    self.status = "FAILED"
                    self.error_message = str(e)
                    print(f"[DatasetImportManager] Error during batch processing: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def get_status(self) -> Dict[str, Any]:
        """Returns current import telemetry."""
        with self._lock:
            return {
                "status": self.status,
                "state": self.status,
                "progress": self.progress,
                "filename": self.current_filename,
                "file_name": self.current_filename,
                "total_records": self.total_rows,
                "total_rows": self.total_rows,
                "processed_rows": self.processed_rows,
                "processed_count": self.processed_rows,
                "successful_rows": self.successful_rows,
                "review_rows": self.review_rows,
                "failed_count": self.review_rows,
                "error": self.error_message,
                "column_mapping": self.column_mapping,
                "preview_samples": self.preview_records
            }

    def reset(self):
        """Resets import manager state."""
        with self._lock:
            self.status = "IDLE"
            self.progress = 0.0
            self.current_filename = None
            self.total_rows = 0
            self.processed_rows = 0
            self.successful_rows = 0
            self.review_rows = 0
            self.error_message = None
            self._cached_records = []
            self.preview_records = []


# Global Singleton Manager
dataset_import_manager = DatasetImportManager()
