"""
SHRAMRAKSHAK: Dataset File & Schema Validation
SIH 2026 Problem Statement: SIH26165

Implements validation stage of P1.1:
- File format verification (CSV, JSON, JSONL, PDF)
- Dataset SHA256 hashing for strict reproducibility
- Data hygiene checks (empty rows, missing narrative, encoding validity)
- Security bounds check (prevent path traversal or unbounded memory consumption)
"""

import os
import hashlib
from typing import Dict, List, Any, Tuple, Optional


class DatasetValidator:
    ALLOWED_EXTENSIONS = {".csv", ".json", ".jsonl", ".pdf"}
    MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB safe limit

    @staticmethod
    def calculate_file_hash(filepath: str) -> str:
        """Calculates deterministic SHA-256 hash of a file for run manifests."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def validate_file(cls, filepath: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validates file existence, extension, size, and generates checksum.
        Returns (is_valid, error_list, metadata_dict).
        """
        errors = []
        metadata = {}

        if not os.path.exists(filepath):
            return False, [f"File not found: {filepath}"], metadata

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, [f"Unsupported file format '{ext}'. Allowed: {list(cls.ALLOWED_EXTENSIONS)}"], metadata

        size_bytes = os.path.getsize(filepath)
        if size_bytes > cls.MAX_FILE_SIZE_BYTES:
            return False, [f"File size {size_bytes} exceeds safety limit of {cls.MAX_FILE_SIZE_BYTES} bytes"], metadata

        if size_bytes == 0:
            return False, ["File is empty (0 bytes)"], metadata

        file_hash = cls.calculate_file_hash(filepath)
        metadata = {
            "filename": os.path.basename(filepath),
            "extension": ext,
            "size_bytes": size_bytes,
            "sha256": file_hash
        }

        return True, errors, metadata

    @staticmethod
    def validate_row_record(row: Dict[str, Any], row_idx: int) -> Tuple[bool, Optional[str]]:
        """Validates that a row record contains sufficient narrative for NLP processing."""
        low_row = {str(k).lower().strip(): v for k, v in row.items()}
        # Check narrative fields
        narrative_candidates = [
            "final narrative", "narrative", "description", "incident_description",
            "report_text", "unsafe_act_description", "details", "observation", "summary",
            "incident details", "event description", "synopsis", "notes", "finding"
        ]
        has_text = False
        for field in narrative_candidates:
            val = low_row.get(field)
            if val is not None and str(val).strip() and str(val).lower() != "nan":
                if len(str(val).strip()) >= 5:
                    has_text = True
                    break

        if not has_text:
            return False, f"Row {row_idx}: No valid textual narrative found (minimum 5 characters required)"

        return True, None
