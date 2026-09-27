"""
SHRAMRAKSHAK: Diagnostic Memory Integrity Tool
SIH 2026 Problem Statement: SIH26165

Audits alignment across:
1. SQLite events table (backend/data/shramrakshak.db)
2. SQLite embeddings table (backend/data/shramrakshak.db)
3. FAISS vector index (backend/data/e5_faiss.index)
4. FAISS ID mapping dictionary (backend/data/e5_faiss_mapping.json)

Reports:
- events count
- embedding rows count
- FAISS vectors (ntotal)
- mappings count
- valid mappings
- orphan vectors (in FAISS with no mapping entry)
- orphan mappings (in mapping file but missing from SQLite events or FAISS)
- missing embeddings (in events but not in FAISS or SQLite embeddings)
- dimension mismatches
- invalid IDs
- persistence state

RULE: Do not silently repair corruption. Reports FAIL and REPAIR REQUIRED if discrepancies exist.
"""

import os
import sys
import json
import sqlite3
import hashlib
from typing import Dict, Any, List

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "backend", "data", "shramrakshak.db")
INDEX_PATH = os.path.join(ROOT_DIR, "backend", "data", "e5_faiss.index")
MAP_PATH = os.path.join(ROOT_DIR, "backend", "data", "e5_faiss_mapping.json")
EXPECTED_DIM = 384


def compute_sha256(path: str) -> str:
    if not os.path.exists(path):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_memory_integrity(
    db_path: str = DB_PATH,
    index_path: str = INDEX_PATH,
    map_path: str = MAP_PATH
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "status": "PASS",
        "db_path": db_path,
        "index_path": index_path,
        "map_path": map_path,
        "hashes": {
            "db_sha256": compute_sha256(db_path),
            "index_sha256": compute_sha256(index_path),
            "map_sha256": compute_sha256(map_path)
        },
        "counts": {},
        "valid_mappings": 0,
        "orphan_vectors": [],
        "orphan_mappings": [],
        "missing_embeddings_in_db": [],
        "unindexed_events": [],
        "dimension_mismatches": [],
        "invalid_ids": [],
        "persistence_state": "UNKNOWN",
        "issues": []
    }

    # 1. SQLite Inspection
    if not os.path.exists(db_path):
        report["status"] = "FAIL"
        report["issues"].append(f"Database file not found: {db_path}")
        return report

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT event_id FROM events")
    db_events = set(r[0] for r in cur.fetchall())

    cur.execute("SELECT embedding_id, event_id, dim FROM embeddings")
    db_embeddings_rows = cur.fetchall()
    db_embeddings = {r[1]: (r[0], r[2]) for r in db_embeddings_rows}

    conn.close()

    report["counts"]["events"] = len(db_events)
    report["counts"]["embedding_rows"] = len(db_embeddings_rows)

    # 2. FAISS Inspection
    if not os.path.exists(index_path):
        report["status"] = "FAIL"
        report["issues"].append(f"FAISS index file not found: {index_path}")
        return report

    try:
        import faiss
        index = faiss.read_index(index_path)
        faiss_ntotal = index.ntotal
        faiss_dim = index.d
        report["counts"]["faiss_vectors"] = faiss_ntotal
        report["counts"]["faiss_dim"] = faiss_dim

        if faiss_dim != EXPECTED_DIM:
            dim_err = f"FAISS dimension mismatch: got {faiss_dim}, expected {EXPECTED_DIM}"
            report["dimension_mismatches"].append(dim_err)
            report["issues"].append(dim_err)
    except Exception as e:
        report["status"] = "FAIL"
        report["issues"].append(f"Failed to load FAISS index: {e}")
        return report

    # 3. Mapping Inspection
    if not os.path.exists(map_path):
        report["status"] = "FAIL"
        report["issues"].append(f"Mapping file not found: {map_path}")
        return report

    try:
        with open(map_path, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
    except Exception as e:
        report["status"] = "FAIL"
        report["issues"].append(f"Failed to parse mapping JSON: {e}")
        return report

    id_to_event_raw = mapping_data.get("id_to_event", {})
    event_to_id_raw = mapping_data.get("event_to_id", {})
    next_id = mapping_data.get("next_id", 0)

    report["counts"]["mappings"] = len(id_to_event_raw)
    report["counts"]["next_id"] = next_id

    # Parse and validate IDs
    id_to_event: Dict[int, str] = {}
    for k, v in id_to_event_raw.items():
        try:
            int_k = int(k)
            if int_k < 0:
                report["invalid_ids"].append(f"Negative FAISS vector ID: {k}")
            id_to_event[int_k] = str(v)
        except ValueError:
            report["invalid_ids"].append(f"Non-integer mapping key: {k}")

    # 4. Check Mapping Bijectivity & Consistency
    for vid, eid in id_to_event.items():
        # Check if vector id is within FAISS index range
        if vid >= faiss_ntotal:
            orphan_map_desc = f"Mapping references vector_id {vid} >= faiss_ntotal {faiss_ntotal} (target event: {eid})"
            report["orphan_mappings"].append(orphan_map_desc)
            report["issues"].append(orphan_map_desc)

        # Check if event exists in SQLite events
        if eid not in db_events:
            orphan_map_desc = f"Mapping references event_id '{eid}' (vector {vid}) which does not exist in SQLite events"
            report["orphan_mappings"].append(orphan_map_desc)
            report["issues"].append(orphan_map_desc)
        else:
            if vid < faiss_ntotal:
                report["valid_mappings"] += 1

        # Check reverse mapping
        rev_id = event_to_id_raw.get(eid)
        if rev_id != vid:
            report["issues"].append(f"Bijective mismatch: id_to_event[{vid}]={eid}, but event_to_id[{eid}]={rev_id}")

    # 5. Check Orphan Vectors (vectors in FAISS with no mapping entry)
    mapped_vector_ids = set(id_to_event.keys())
    for vid in range(faiss_ntotal):
        if vid not in mapped_vector_ids:
            report["orphan_vectors"].append(vid)
            report["issues"].append(f"FAISS vector id {vid} has no entry in mapping")

    # 6. Check Events without FAISS Vectors
    mapped_events = set(id_to_event.values())
    for eid in sorted(db_events):
        if eid not in mapped_events:
            report["unindexed_events"].append(eid)

    # 7. Check SQLite Embeddings Table Coverage
    for vid, eid in id_to_event.items():
        if eid in db_events and eid not in db_embeddings:
            report["missing_embeddings_in_db"].append(eid)

    # 8. Check Embedding Dimensions in SQLite
    for eid, (emb_id, dim) in db_embeddings.items():
        if dim != EXPECTED_DIM:
            report["dimension_mismatches"].append(f"SQLite embedding {emb_id} for event {eid} has dim {dim} != {EXPECTED_DIM}")

    # Final Status
    if (report["orphan_mappings"] or report["orphan_vectors"] or 
        report["dimension_mismatches"] or report["invalid_ids"] or 
        report["missing_embeddings_in_db"] or report["unindexed_events"]):
        report["status"] = "FAIL"
        report["persistence_state"] = "REPAIR_REQUIRED"
    else:
        report["status"] = "PASS"
        report["persistence_state"] = "CLEAN"

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check and optionally reconcile semantic memory integrity.")
    parser.add_argument("--reconcile", action="store_true", help="Atomically reconcile and rebuild FAISS index and mappings from SQLite canonical events.")
    args = parser.parse_args()

    if args.reconcile:
        print("[INFO] Reconciling and rebuilding semantic memory from SQLite canonical events...")
        try:
            from backend.nlp_engine.semantic_memory import semantic_memory
        except ImportError:
            sys.path.insert(0, ROOT_DIR)
            from backend.nlp_engine.semantic_memory import semantic_memory
        rec_res = semantic_memory.reconcile_and_rebuild(force=True)
        print(f"[INFO] Rebuild completed: {rec_res}")

    rep = check_memory_integrity()
    print(json.dumps(rep, indent=2))
    print(f"\nFinal Memory Integrity Status: {rep['status']}")
    print(f"Persistence State: {rep['persistence_state']}")
    if rep["issues"]:
        print(f"Issues detected ({len(rep['issues'])}):")
        for iss in rep["issues"]:
            print(f"  - {iss}")

    # Enforce strict exit codes: 0 for PASS, 1 for FAIL
    sys.exit(0 if rep["status"] == "PASS" else 1)
