"""
SHRAMRAKSHAK: Run Manifest & Pipeline Reproducibility Manager
SIH 2026 Problem Statement: SIH26165

Implements P1.6:
- Generates reproducible, cryptographic run manifests for dataset runs
- Persists all execution telemetry (dataset hash, model version, ontology version, counts)
- Writes directly to SQLite table run_manifests and local JSON logs
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from backend.models_canonical import RunManifest
    from backend.database import db
except ImportError:
    try:
        from models_canonical import RunManifest
        from database import db
    except ImportError:
        from ..models_canonical import RunManifest
        from ..database import db

MANIFEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manifests")


class ManifestManager:
    def __init__(self, manifest_dir: str = MANIFEST_DIR):
        self.manifest_dir = manifest_dir
        os.makedirs(self.manifest_dir, exist_ok=True)
        self.db = db

    def compute_config_hash(self, config_dict: Dict[str, Any]) -> str:
        """Computes deterministic MD5/SHA256 of pipeline configuration."""
        dumped = json.dumps(config_dict, sort_keys=True).encode("utf-8")
        return hashlib.sha256(dumped).hexdigest()[:16]

    def create_and_save_manifest(
        self,
        run_id: str,
        dataset_name: str,
        dataset_hash: str,
        records_seen: int,
        records_processed: int,
        records_failed: int,
        events_created: int,
        patterns_created: int,
        reviews_executed: int,
        embeddings_created: int,
        execution_time_seconds: float,
        model_name: str = "intfloat/e5-small-v2",
        ontology_version: str = "1.0.0",
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> RunManifest:
        """Creates, validates, and persists a RunManifest to SQLite and file."""
        now_iso = datetime.now().isoformat()
        cfg_hash = self.compute_config_hash({
            "model": model_name,
            "ontology": ontology_version,
            "dataset_hash": dataset_hash
        })

        manifest = RunManifest(
            run_id=run_id,
            timestamp=now_iso,
            dataset_name=dataset_name,
            dataset_hash=dataset_hash,
            code_version="SHRAMRAKSHAK-2.0-SIH26165",
            model_name=model_name,
            model_version="e5-small-v2-transformers-torch",
            ontology_version=ontology_version,
            config_hash=cfg_hash,
            records_seen=records_seen,
            records_processed=records_processed,
            records_failed=records_failed,
            events_created=events_created,
            patterns_created=patterns_created,
            reviews_executed=reviews_executed,
            embeddings_created=embeddings_created,
            execution_time_seconds=execution_time_seconds
        )

        # 1. Persist to SQLite
        self.db.save_manifest(manifest)

        # 2. Persist to disk JSON
        manifest_file = os.path.join(self.manifest_dir, f"{run_id}.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            data = manifest.to_dict()
            if extra_metadata:
                data["extra_metadata"] = extra_metadata
            json.dump(data, f, indent=2)

        return manifest


manifest_manager = ManifestManager()
