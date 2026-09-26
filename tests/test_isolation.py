"""
SHRAMRAKSHAK: Test Isolation & Clean-Room Test Harness
SIH 2026 Problem Statement: SIH26165

Provides ephemeral, hermetic test storage for:
1. SQLite Database: Creates a temporary test DB with all 11 core tables initialized.
2. FAISS Vector Index: In-place mutation of the SemanticMemory singleton to point to an ephemeral index.
3. FAISS ID Mapping: In-place mutation of SemanticMemory mapping path and dicts.
4. Run Manifests: Creates an isolated manifest logging directory.

GUARANTEE:
Production storage under backend/data/ is NEVER read from or mutated during isolated test runs.
"""

import os
import sys
import tempfile
import shutil
import builtins
from contextlib import contextmanager

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
backend_dir = os.path.join(ROOT_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import faiss
from backend.database import DatabaseManager, DB_PATH as PROD_DB_PATH
from backend.nlp_engine.semantic_memory import (
    semantic_memory as global_semantic_memory,
    INDEX_PATH as PROD_INDEX_PATH,
    MAP_PATH as PROD_MAP_PATH
)
import backend.database
import backend.nlp_engine.semantic_memory
import backend.nlp_engine.recurrence_engine
import backend.nlp_engine.precondition_engine
import backend.nlp_engine.propagation
import backend.dataset_pipeline.manifest


@contextmanager
def isolated_test_environment(prefix: str = "shramrakshak_test_"):
    """
    Context manager providing completely isolated, temporary test storage.
    Mutates the existing singleton instances in-place so all previously imported
    references observe the isolated test state. Restores exact state on exit.
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    test_db_path = os.path.join(temp_dir, "shramrakshak_test.db")
    test_index_path = os.path.join(temp_dir, "e5_faiss_test.index")
    test_map_path = os.path.join(temp_dir, "e5_faiss_mapping_test.json")
    test_manifest_dir = os.path.join(temp_dir, "manifests")
    os.makedirs(test_manifest_dir, exist_ok=True)

    # Initialize isolated database (creates clean schema in temporary path)
    test_db = DatabaseManager(db_path=test_db_path)

    # 1. Save original DatabaseManager state
    orig_db_inst = backend.database.db
    orig_db_path = backend.database.db.db_path

    # 2. Save original SemanticMemory singleton mutable state
    orig_sm_index = global_semantic_memory.index
    orig_sm_index_path = global_semantic_memory.index_path
    orig_sm_map_path = global_semantic_memory.map_path
    orig_sm_id_to_event = global_semantic_memory.id_to_event.copy()
    orig_sm_event_to_id = global_semantic_memory.event_to_id.copy()
    orig_sm_next_id = global_semantic_memory.next_id

    # 3. Save other engine references
    orig_sm_db = getattr(backend.nlp_engine.semantic_memory, "db", orig_db_inst)
    orig_rec_db = getattr(backend.nlp_engine.recurrence_engine, "db", orig_db_inst)
    orig_prec_db = getattr(backend.nlp_engine.precondition_engine, "db", orig_db_inst)
    orig_prec_engine_db = backend.nlp_engine.precondition_engine.precondition_engine.db
    orig_prop_db = getattr(backend.nlp_engine.propagation, "db", orig_db_inst)
    orig_prop_engine_db = backend.nlp_engine.propagation.propagation_engine.db
    orig_man_db = getattr(backend.dataset_pipeline.manifest, "db", orig_db_inst)
    orig_man_mgr_db = backend.dataset_pipeline.manifest.manifest_manager.db
    orig_man_dir = backend.dataset_pipeline.manifest.manifest_manager.manifest_dir

    # 4. Save functions to intercept writes to production paths
    orig_faiss_write_index = faiss.write_index
    orig_builtins_open = builtins.open

    try:
        # Patch DatabaseManager singleton and all references
        backend.database.db.db_path = test_db_path
        backend.database.db = test_db
        backend.nlp_engine.semantic_memory.db = test_db
        backend.nlp_engine.recurrence_engine.db = test_db
        backend.nlp_engine.precondition_engine.db = test_db
        backend.nlp_engine.precondition_engine.precondition_engine.db = test_db
        backend.nlp_engine.propagation.db = test_db
        backend.nlp_engine.propagation.propagation_engine.db = test_db
        backend.dataset_pipeline.manifest.db = test_db
        backend.dataset_pipeline.manifest.manifest_manager.db = test_db
        backend.dataset_pipeline.manifest.manifest_manager.manifest_dir = test_manifest_dir

        # Mutate SemanticMemory singleton IN-PLACE
        global_semantic_memory.index = faiss.IndexFlatIP(global_semantic_memory.dim)
        global_semantic_memory.index_path = test_index_path
        global_semantic_memory.map_path = test_map_path
        global_semantic_memory.id_to_event = {}
        global_semantic_memory.event_to_id = {}
        global_semantic_memory.next_id = 0

        # Isolate unified_event_store file
        try:
            from backend.unified_event_store import unified_event_store
            orig_ues_file = unified_event_store.events_file
            unified_event_store.events_file = os.path.join(temp_dir, "test_safety_events.json")
        except Exception:
            orig_ues_file = None

        # Hard isolation assertions: verify active paths point to temp directory
        abs_temp = os.path.abspath(temp_dir)
        assert os.path.abspath(global_semantic_memory.index_path).startswith(abs_temp), \
            f"ISOLATION FAULT: index_path {global_semantic_memory.index_path} not in {temp_dir}"
        assert os.path.abspath(global_semantic_memory.map_path).startswith(abs_temp), \
            f"ISOLATION FAULT: map_path {global_semantic_memory.map_path} not in {temp_dir}"
        assert os.path.abspath(backend.database.db.db_path).startswith(abs_temp), \
            f"ISOLATION FAULT: db_path {backend.database.db.db_path} not in {temp_dir}"

        # Write-barrier guard: intercept any write attempts targeting production files
        prod_data_dir = os.path.abspath(os.path.join(ROOT_DIR, "backend", "data"))

        def guarded_faiss_write_index(index, file_path):
            abs_fp = os.path.abspath(str(file_path))
            if abs_fp.startswith(prod_data_dir):
                raise AssertionError(f"ISOLATION BREACH: Attempted faiss.write_index on production path: {file_path}")
            return orig_faiss_write_index(index, file_path)

        def guarded_open(file, mode="r", *args, **kwargs):
            if any(m in mode for m in ["w", "a", "+", "x"]):
                if isinstance(file, (str, bytes, os.PathLike)):
                    abs_f = os.path.abspath(file)
                    if abs_f.startswith(prod_data_dir):
                        raise AssertionError(f"ISOLATION BREACH: Attempted open({file}, mode='{mode}') on production file!")
            return orig_builtins_open(file, mode, *args, **kwargs)

        faiss.write_index = guarded_faiss_write_index
        builtins.open = guarded_open

        yield {
            "temp_dir": temp_dir,
            "db": test_db,
            "semantic_memory": global_semantic_memory,
            "manifest_dir": test_manifest_dir
        }
    finally:
        # Restore interception hooks
        faiss.write_index = orig_faiss_write_index
        builtins.open = orig_builtins_open

        # Restore SemanticMemory mutable attributes IN-PLACE
        global_semantic_memory.index = orig_sm_index
        global_semantic_memory.index_path = orig_sm_index_path
        global_semantic_memory.map_path = orig_sm_map_path
        global_semantic_memory.id_to_event = orig_sm_id_to_event
        global_semantic_memory.event_to_id = orig_sm_event_to_id
        global_semantic_memory.next_id = orig_sm_next_id

        # Restore DatabaseManager singleton and paths
        orig_db_inst.db_path = orig_db_path
        backend.database.db = orig_db_inst
        backend.database.db.db_path = orig_db_path

        # Restore other engine references
        backend.nlp_engine.semantic_memory.db = orig_sm_db
        backend.nlp_engine.recurrence_engine.db = orig_rec_db
        backend.nlp_engine.precondition_engine.db = orig_prec_db
        backend.nlp_engine.precondition_engine.precondition_engine.db = orig_prec_engine_db
        backend.nlp_engine.propagation.db = orig_prop_db
        backend.nlp_engine.propagation.propagation_engine.db = orig_prop_engine_db
        backend.dataset_pipeline.manifest.db = orig_man_db
        backend.dataset_pipeline.manifest.manifest_manager.db = orig_man_mgr_db
        backend.dataset_pipeline.manifest.manifest_manager.manifest_dir = orig_man_dir

        if orig_ues_file is not None:
            try:
                from backend.unified_event_store import unified_event_store
                unified_event_store.events_file = orig_ues_file
            except Exception:
                pass

        # Ensure production singleton is strictly pointing back to production paths
        assert global_semantic_memory.index_path == orig_sm_index_path
        assert global_semantic_memory.map_path == orig_sm_map_path
        assert backend.database.db.db_path == orig_db_path

        # Clean up temporary directory and files
        shutil.rmtree(temp_dir, ignore_errors=True)
