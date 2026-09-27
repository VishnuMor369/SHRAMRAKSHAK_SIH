"""
SHRAMRAKSHAK: Dataset Intelligence & AnalysisRun Manager
SIH 2026 Problem Statement: SIH26165

Manages isolated Dataset Analysis Runs (AR-XXXX) for uploaded CSV, Excel, JSON, and PDF files.
Runs the complete NLP, SIF, LSR, and Pattern Discovery pipeline strictly on the uploaded dataset,
WITHOUT polluting the live real-time safety memory or demo workspace.
Persists run metadata and outputs to backend/data/analysis_runs/ and provides downloadable PDF reports.
"""

import io
import os
import re
import json
import uuid
import time
import math
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import csv
try:
    import pandas as pd
except Exception:
    pd = None
from pypdf import PdfReader

try:
    from backend.nlp_engine.assertion_detector import assertion_detector
    from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
    from backend.nlp_engine.lsr_classifier import lsr_classifier
    from backend.analysis_pdf_generator import generate_analysis_run_pdf
except ImportError:
    from nlp_engine.assertion_detector import assertion_detector
    from nlp_engine.sif_pathway_engine import sif_pathway_engine
    from nlp_engine.lsr_classifier import lsr_classifier
    from analysis_pdf_generator import generate_analysis_run_pdf

logger = logging.getLogger("DatasetAnalysisManager")

RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "analysis_runs")
os.makedirs(RUNS_DIR, exist_ok=True)


class DatasetAnalysisManager:
    """
    Manages isolated Analysis Runs for uploaded company datasets.
    """

    def __init__(self, runs_dir: str = RUNS_DIR):
        self.runs_dir = runs_dir
        os.makedirs(self.runs_dir, exist_ok=True)
        self._ensure_default_run()

    def _ensure_default_run(self):
        """Seeds a default baseline Analysis Run (AR-0001) if no runs exist."""
        existing = self.list_runs()
        if existing:
            return
        
        # Seed an initial baseline run using representative dataset records
        default_run_id = "AR-0001"
        sample_reports = [
            {
                "report_id": "REP-001",
                "narrative": "Worker stepped into the lifting zone without hard hat while crane was hoisting pipe.",
                "activity": "Mechanical Lifting",
                "location": "Drilling Rig 04 - Drill Floor",
                "date": "2026-09-20"
            },
            {
                "report_id": "REP-002",
                "narrative": "Rigger crossed the barricaded perimeter under suspended drill collar during repositioning.",
                "activity": "Mechanical Lifting",
                "location": "Drilling Rig 04 - Drill Floor",
                "date": "2026-09-21"
            },
            {
                "report_id": "REP-003",
                "narrative": "Personnel observed standing in drop radius while 10-ton mud motor was suspended by crane.",
                "activity": "Mechanical Lifting",
                "location": "Drilling Rig 04 - Drill Floor",
                "date": "2026-09-22"
            },
            {
                "report_id": "REP-004",
                "narrative": "Hot work permit was approved; welder had full fire blanket and continuous atmospheric monitoring.",
                "activity": "Hot Work Operations",
                "location": "Separator Skid Area",
                "date": "2026-09-23"
            },
            {
                "report_id": "REP-005",
                "narrative": "Technician observed entering confined vessel before gas test results were officially posted.",
                "activity": "Confined Space Entry",
                "location": "Crude Storage Tank T-102",
                "date": "2026-09-24"
            }
        ]

        self.process_records(
            run_id=default_run_id,
            filename="oil_representative_sample_q3.csv",
            file_type="CSV",
            records=sample_reports,
            provenance="Representative demonstration observations — not actual OIL incident records."
        )

    def extract_text_from_file(self, filename: str, contents: bytes) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extracts raw records from CSV, Excel, JSON, or PDF file.
        Throws clear exception if PDF text extraction fails (e.g. scanned image).
        """
        ext = os.path.splitext(filename)[1].lower()
        records: List[Dict[str, Any]] = []

        if ext == ".csv":
            if pd is not None:
                df = pd.read_csv(io.BytesIO(contents), low_memory=False)
                df = df.where(pd.notnull(df), None)
                records = df.to_dict(orient="records")
            else:
                reader = csv.DictReader(io.StringIO(contents.decode("utf-8", errors="replace")))
                records = [row for row in reader]
            return "CSV", records

        elif ext in [".xlsx", ".xls"]:
            if pd is not None:
                df = pd.read_excel(io.BytesIO(contents))
                df = df.where(pd.notnull(df), None)
                records = df.to_dict(orient="records")
                return "EXCEL", records
            else:
                raise ValueError("Excel parsing requires pandas which is currently unavailable.")

        elif ext == ".json":
            parsed = json.loads(contents.decode("utf-8"))
            if isinstance(parsed, list):
                records = parsed
            elif isinstance(parsed, dict):
                for k in ["records", "data", "reports", "incidents", "events"]:
                    if k in parsed and isinstance(parsed[k], list):
                        records = parsed[k]
                        break
                if not records:
                    records = [parsed]
            return "JSON", records

        elif ext == ".pdf":
            reader = PdfReader(io.BytesIO(contents))
            all_text = ""
            for page in reader.pages:
                txt = page.extract_text() or ""
                all_text += "\n" + txt

            # Check if PDF text extraction yielded extractable digital text
            if not all_text.strip() or len(all_text.strip()) < 30:
                raise ValueError("TEXT EXTRACTION FAILED / OCR REQUIRED: The provided PDF contains scanned images or non-extractable text. Please supply a text-encoded PDF or CSV dataset.")

            blocks = re.split(r"(?:\n\s*(?:Incident|Report|Observation|Case|ID)\s*[:#\d]+|\n\s*---\s*\n|\n\s*\d+[\.\)]\s+)", all_text)
            for idx, block in enumerate(blocks):
                clean_blk = block.strip()
                if len(clean_blk) > 25:
                    records.append({
                        "narrative": clean_blk,
                        "location": f"Operational Site (PDF Page {idx + 1})",
                        "activity": "Operational Safety Report",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "page": idx + 1
                    })

            if not records:
                raise ValueError("TEXT EXTRACTION FAILED / OCR REQUIRED: No distinct safety observation records could be parsed from the PDF document structure.")

            return "PDF", records

        else:
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .csv, .xlsx, .json, .pdf")

    def _find_field(self, sample: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        keys = list(sample.keys())
        for c in candidates:
            for k in keys:
                if c.lower() in k.lower():
                    return k
        return None

    def process_records(
        self,
        run_id: str,
        filename: str,
        file_type: str,
        records: List[Dict[str, Any]],
        max_rows: Optional[int] = None,
        provenance: str = "External safety dataset used for stress testing."
    ) -> Dict[str, Any]:
        """
        Executes isolated safety intelligence analysis on records without mutating live memory.
        """
        total_detected = len(records)
        target_records = records[:max_rows] if max_rows else records

        # Identify narrative column
        sample = target_records[0] if target_records else {}
        narr_field = self._find_field(sample, ["narrative", "description", "incident", "what_happened", "summary", "text", "event"])
        loc_field = self._find_field(sample, ["location", "site", "rig", "area", "employer", "facility"])
        act_field = self._find_field(sample, ["activity", "eventtitle", "operation", "task", "job"])

        analyzed_reports: List[Dict[str, Any]] = []
        sif_count = 0
        non_sif_count = 0
        review_count = 0
        failed_count = 0

        iogp_distribution: Dict[str, int] = {}
        hazard_distribution: Dict[str, int] = {}
        activity_distribution: Dict[str, int] = {}
        barrier_failure_distribution: Dict[str, int] = {}

        # Candidate pattern grouping: key = (activity, barrier)
        pattern_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

        for idx, rec in enumerate(target_records):
            # Extract narrative text
            raw_text = None
            if narr_field and rec.get(narr_field):
                raw_text = str(rec[narr_field]).strip()
            elif "narrative" in rec:
                raw_text = str(rec["narrative"]).strip()
            else:
                for k, v in rec.items():
                    if isinstance(v, str) and len(v.strip()) > 30:
                        raw_text = v.strip()
                        break

            if not raw_text:
                failed_count += 1
                continue

            loc_val = str(rec.get(loc_field, "Operational Site") if loc_field else "Operational Site")
            act_val = str(rec.get(act_field, "Industrial Operations") if act_field else "Industrial Operations")
            report_id = f"REP-{run_id}-{idx+1:04d}"

            try:
                # 1. Contextual NLP Assertion
                ev = assertion_detector.analyze(
                    raw_text,
                    context={"event_id": f"EVT-{report_id}", "location": loc_val, "activity": act_val}
                )

                # 2. SIF Pathway Reasoning
                ev = sif_pathway_engine.evaluate(ev)

                # 3. Multi-label LSR mapping
                lsr_matches = lsr_classifier.classify_event(ev)
                lsr_list = [m["lsr"] for m in lsr_matches] if lsr_matches else ["General Industrial Safety"]

                # SIF counting
                sif_status_str = (ev.sif_status.value if hasattr(ev.sif_status, "value") else str(ev.sif_status)).upper().replace("-", "_")
                if "SIF_POTENTIAL" in sif_status_str or sif_status_str in ["HIGH", "CRITICAL"]:
                    sif_count += 1
                    sif_category = "HIGH"
                elif "REVIEW" in sif_status_str or sif_status_str in ["MEDIUM"]:
                    review_count += 1
                    sif_category = "REVIEW_REQUIRED"
                else:
                    non_sif_count += 1
                    sif_category = "NON_SIF"

                # Update distributions
                for rule in lsr_list:
                    iogp_distribution[rule] = iogp_distribution.get(rule, 0) + 1

                haz_val = ev.energy or "Gravitational / Mechanical"
                hazard_distribution[haz_val] = hazard_distribution.get(haz_val, 0) + 1

                act_clean = ev.activity or act_val
                activity_distribution[act_clean] = activity_distribution.get(act_clean, 0) + 1

                barrier_name = ev.barrier[0] if ev.barrier else "Control Perimeter"
                if ev.barrier_state and str(ev.barrier_state[0]) in ["BYPASSED", "VIOLATED", "INEFFECTIVE", "FAILED"]:
                    barrier_failure_distribution[barrier_name] = barrier_failure_distribution.get(barrier_name, 0) + 1

                report_item = {
                    "report_id": report_id,
                    "original_text": raw_text,
                    "activity": act_clean,
                    "location": loc_val,
                    "hazard": haz_val,
                    "exposure": ev.exposure,
                    "barrier": barrier_name,
                    "barrier_state": str(ev.barrier_state[0]) if ev.barrier_state else "UNKNOWN",
                    "consequence": ev.consequence,
                    "sif_potential": sif_category,
                    "assertion": ev.assertion.value if hasattr(ev.assertion, "value") else str(ev.assertion),
                    "lsr": ", ".join(lsr_list),
                    "evidence_spans": [s.to_dict() if hasattr(s, "to_dict") else s for s in ev.evidence]
                }
                analyzed_reports.append(report_item)

                # Group for candidate patterns if SIF potential or barrier breach
                if sif_category == "HIGH" or barrier_name != "Control Perimeter":
                    grp_key = (act_clean, barrier_name)
                    pattern_groups.setdefault(grp_key, []).append(report_item)

            except Exception as e:
                logger.warning(f"Error analyzing record #{idx}: {e}")
                failed_count += 1

        # Form candidate patterns from groups with >= 2 occurrences
        candidate_patterns = []
        for (p_act, p_bar), members in pattern_groups.items():
            if len(members) >= 2:
                candidate_patterns.append({
                    "pattern_id": f"PAT-{p_bar.replace(' ', '_').upper()}-{len(candidate_patterns)+1:02d}",
                    "title": f"Recurring Control Breach: {p_bar} during {p_act}",
                    "occurrence_count": len(members),
                    "activity": p_act,
                    "barrier": p_bar,
                    "sif_potential": "HIGH",
                    "validation_status": "CANDIDATE",
                    "source_reports": [m["report_id"] for m in members]
                })

        # Sort candidate patterns by occurrence count descending
        candidate_patterns.sort(key=lambda x: x["occurrence_count"], reverse=True)

        analyzed_count = len(analyzed_reports)
        sif_percentage = round((sif_count / max(analyzed_count, 1)) * 100, 2)

        # High potential cases
        high_cases = [r for r in analyzed_reports if r["sif_potential"] == "HIGH"][:10]

        run_data = {
            "run_id": run_id,
            "filename": filename,
            "file_type": file_type,
            "upload_time": datetime.now().isoformat(),
            "provenance": provenance,
            "records_detected": total_detected,
            "records_analyzed": analyzed_count,
            "failed_count": failed_count,
            "review_required_count": review_count,
            "sif_count": sif_count,
            "non_sif_count": non_sif_count,
            "sif_percentage": sif_percentage,
            "status": "COMPLETED",
            "candidate_patterns": candidate_patterns,
            "high_potential_cases": high_cases,
            "hazard_distribution": hazard_distribution,
            "activity_distribution": activity_distribution,
            "barrier_failure_distribution": barrier_failure_distribution,
            "iogp_distribution": iogp_distribution,
            "reports": analyzed_reports
        }

        # Save to file
        self._save_run(run_id, run_data)
        return run_data

    def _save_run(self, run_id: str, data: Dict[str, Any]):
        filepath = os.path.join(self.runs_dir, f"{run_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        filepath = os.path.join(self.runs_dir, f"{run_id}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_runs(self) -> List[Dict[str, Any]]:
        runs = []
        if not os.path.exists(self.runs_dir):
            return []
        for fname in os.listdir(self.runs_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.runs_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        runs.append({
                            "run_id": data.get("run_id"),
                            "filename": data.get("filename"),
                            "file_type": data.get("file_type"),
                            "upload_time": data.get("upload_time"),
                            "records_detected": data.get("records_detected"),
                            "records_analyzed": data.get("records_analyzed"),
                            "sif_count": data.get("sif_count"),
                            "sif_percentage": data.get("sif_percentage"),
                            "status": data.get("status", "COMPLETED"),
                            "provenance": data.get("provenance")
                        })
                except Exception as e:
                    logger.warning(f"Error reading run file {fname}: {e}")
        runs.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
        return runs

    def export_pdf(self, run_id: str) -> bytes:
        run = self.get_run(run_id)
        if not run:
            raise ValueError(f"Analysis Run '{run_id}' not found.")
        return generate_analysis_run_pdf(run)

    def create_analysis_run(self, file_bytes: bytes, filename: str, max_rows: Optional[int] = None):
        """Creates, executes, and persists a unique AnalysisRun (AR-XXXX) for uploaded file."""
        file_type, records = self.extract_text_from_file(filename, file_bytes)
        run_id = f"AR-{len(self.list_runs()) + 1:04d}"
        provenance = "External safety dataset used for stress testing." if any(k in filename.lower() for k in ["osha", "severe", "dataset"]) else "Uploaded dataset intelligence file."
        run_data = self.process_records(
            run_id=run_id,
            filename=filename,
            file_type=file_type,
            records=records,
            max_rows=max_rows,
            provenance=provenance
        )
        return AnalysisRun(run_data)

    list_analysis_runs = list_runs
    get_analysis_run = get_run

class AnalysisRun:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.run_id = data.get("run_id")

    def to_dict(self) -> Dict[str, Any]:
        return self.data

    def __getitem__(self, item):
        return self.data[item]

    def get(self, item, default=None):
        return self.data.get(item, default)


# Global Singleton Dataset Analysis Manager
dataset_analysis_manager = DatasetAnalysisManager()
