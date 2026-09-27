"""
SHRAMRAKSHAK: Batch Dataset Ingestion Pipeline & Execution Runner
SIH 2026 Problem Statement: SIH26165

Implements P1.1 & P6:
- Validates input files
- Normalizes records with provenance
- Routes records through end-to-end NLP/SIF/LSR/FAISS pipeline
- Persists all state to SQLite and FAISS
- Generates and writes verifiable RunManifest
"""

import os
import time
import uuid
import json
import logging
from typing import Dict, List, Any, Optional, Callable
import csv
try:
    import pandas as pd
except Exception:
    pd = None

from .validate import DatasetValidator
from .normalize import DatasetNormalizer
from .manifest import manifest_manager
from .process import dataset_processor

try:
    from backend.models_canonical import SIFStatus, RunManifest
    from backend.database import db
except ImportError:
    try:
        from models_canonical import SIFStatus, RunManifest
        from database import db
    except ImportError:
        from ..models_canonical import SIFStatus, RunManifest
        from ..database import db

logger = logging.getLogger("DatasetIngester")


class DatasetIngester:
    def __init__(self):
        self.validator = DatasetValidator
        self.normalizer = DatasetNormalizer
        self.processor = dataset_processor
        self.manifest_mgr = manifest_manager
        self.db = db

    def ingest_file(
        self,
        filepath: str,
        max_records: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes complete batch ingestion of a dataset file.
        Returns execution statistics and manifest summary.
        """
        start_time = time.time()
        run_id = f"RUN-{uuid.uuid4().hex[:8]}"

        # 1. Validate file
        is_valid, errors, meta = self.validator.validate_file(filepath)
        if not is_valid:
            raise ValueError(f"File validation failed: {'; '.join(errors)}")

        dataset_name = meta["filename"]
        dataset_hash = meta["sha256"]

        # 2. Read records
        ext = meta["extension"]
        records = []
        if ext == ".csv":
            if pd is not None:
                df = pd.read_csv(filepath, nrows=max_records if max_records else None, low_memory=False)
                df = df.where(pd.notnull(df), None)
                records = df.to_dict(orient="records")
            else:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        if max_records and idx >= max_records:
                            break
                        records.append(row)
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data if isinstance(data, list) else [data]
                if max_records:
                    records = records[:max_records]
        elif ext == ".jsonl":
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
                        if max_records and len(records) >= max_records:
                            break

        records_seen = len(records)
        records_processed = 0
        records_failed = 0
        sif_potential_count = 0
        review_required_count = 0
        no_sif_count = 0
        events_created = 0

        # 3. Process records through pipeline
        for idx, raw_row in enumerate(records):
            try:
                # Row validation
                valid_row, row_err = self.validator.validate_row_record(raw_row, idx)
                if not valid_row:
                    records_failed += 1
                    continue

                # Normalization with provenance
                norm = self.normalizer.normalize_record(raw_row, idx)
                if not norm["narrative"]:
                    records_failed += 1
                    continue

                # End-to-end processing
                event = self.processor.process_normalized_record(norm)
                records_processed += 1
                events_created += 1

                if event.sif_status == SIFStatus.SIF_POTENTIAL:
                    sif_potential_count += 1
                elif event.sif_status == SIFStatus.REVIEW_REQUIRED:
                    review_required_count += 1
                else:
                    no_sif_count += 1

                if progress_callback and idx % 25 == 0:
                    progress_callback(idx + 1, records_seen, f"Processed {idx + 1}/{records_seen}")

            except Exception as e:
                logger.error(f"Error processing record {idx}: {e}")
                records_failed += 1

        exec_duration = time.time() - start_time

        # 4. Count patterns and reviews in DB
        patterns_count = len(self.db.list_patterns())
        reviews_count = len(self.db.list_reviews())

        # 5. Create and save RunManifest
        manifest = self.manifest_mgr.create_and_save_manifest(
            run_id=run_id,
            dataset_name=dataset_name,
            dataset_hash=dataset_hash,
            records_seen=records_seen,
            records_processed=records_processed,
            records_failed=records_failed,
            events_created=events_created,
            patterns_created=patterns_count,
            reviews_executed=reviews_count,
            embeddings_created=records_processed,
            execution_time_seconds=round(exec_duration, 2),
            extra_metadata={
                "sif_potential_count": sif_potential_count,
                "review_required_count": review_required_count,
                "no_sif_count": no_sif_count,
                "is_oil_data": False,
                "provenance_note": "UNLABELED STRESS-TEST DATA; injury outcome fields not used as SIF ground truth."
            }
        )

        return {
            "run_id": run_id,
            "dataset_name": dataset_name,
            "dataset_hash": dataset_hash,
            "records_seen": records_seen,
            "records_processed": records_processed,
            "records_failed": records_failed,
            "events_created": events_created,
            "sif_potential_count": sif_potential_count,
            "review_required_count": review_required_count,
            "no_sif_count": no_sif_count,
            "patterns_count": patterns_count,
            "execution_time_seconds": round(exec_duration, 2),
            "manifest": manifest.to_dict()
        }


dataset_ingester = DatasetIngester()
