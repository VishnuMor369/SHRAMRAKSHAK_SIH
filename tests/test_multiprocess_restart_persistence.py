"""
SHRAMRAKSHAK: Multi-Process Restart Persistence Verification
SIH 2026 Problem Statement: SIH26165

True multi-process test:
- Process A: Initializes isolated storage -> writes SafetyEvent -> saves SQLite + FAISS -> terminates
- Process B (New OS Process): Starts fresh -> reloads SQLite + FAISS from disk -> searches vector index -> verifies canonical event -> exits 0.
"""

import sys
import os
import subprocess
import tempfile
import shutil

SCRATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "scratch_restart_test")

PROCESS_A_CODE = f"""
import sys
import os
ROOT_DIR = r"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}"
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from backend.database import DatabaseManager
from backend.models_canonical import SafetyEvent, ExposureStatus, SIFStatus
from backend.nlp_engine.semantic_memory import SemanticMemory

db_path = os.path.join(r"{SCRATCH_DIR}", "test_restart.db")
faiss_path = os.path.join(r"{SCRATCH_DIR}", "test_restart.index")
map_path = os.path.join(r"{SCRATCH_DIR}", "test_restart_map.json")

# Initialize isolated storage
import backend.database
backend.database.db = DatabaseManager(db_path)
db = backend.database.db
sm = SemanticMemory(index_path=faiss_path, map_path=map_path, db=db)

event = SafetyEvent(
    event_id="EVT-RESTART-999",
    activity="High Pressure Testing",
    energy="High Pressure Stored Fluid",
    exposure="Inspector in cellar",
    exposure_status=ExposureStatus.CONFIRMED,
    barrier=["PRESSURE_TESTING"],
    barrier_state=["BYPASSED"],
    consequence="Pressure blowout",
    narrative="Spool flange bolt severed during high pressure hydrostatic proof test in rig cellar.",
    sif_status=SIFStatus.SIF_POTENTIAL
)

db.save_event(event)
sm.add_event(event)

print(f"[PROCESS A] Event EVT-RESTART-999 saved. FAISS total vectors: {{sm.index.ntotal}}")
assert sm.index.ntotal == 1
assert os.path.exists(faiss_path)
assert os.path.exists(map_path)
assert os.path.exists(db_path)
sys.exit(0)
"""

PROCESS_B_CODE = f"""
import sys
import os
ROOT_DIR = r"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}"
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from backend.database import DatabaseManager
from backend.models_canonical import SIFStatus
from backend.nlp_engine.semantic_memory import SemanticMemory

db_path = os.path.join(r"{SCRATCH_DIR}", "test_restart.db")
faiss_path = os.path.join(r"{SCRATCH_DIR}", "test_restart.index")
map_path = os.path.join(r"{SCRATCH_DIR}", "test_restart_map.json")

# Process B starts fresh and reloads from disk
import backend.database
backend.database.db = DatabaseManager(db_path)
db = backend.database.db
sm = SemanticMemory(index_path=faiss_path, map_path=map_path, db=db)

print(f"[PROCESS B] Reloaded storage. FAISS ntotal: {{sm.index.ntotal}}")
assert sm.index.ntotal == 1, f"Expected 1 vector on disk, found {{sm.index.ntotal}}"

# Query semantic vector index
candidates = sm.search_candidates("flange bolt severed high pressure hydrostatic test", top_k=3, min_similarity=0.60)
print(f"[PROCESS B] Vector Search candidates: {{candidates}}")
assert len(candidates) > 0, "Failed to retrieve event from reloaded vector index"
retrieved_id, score = candidates[0]
assert retrieved_id == "EVT-RESTART-999", f"Expected EVT-RESTART-999, got {{retrieved_id}}"
assert score > 0.75, f"Similarity score too low: {{score}}"

# Verify SQLite event data
reloaded_event = db.get_event("EVT-RESTART-999")
assert reloaded_event is not None, "Event not found in SQLite on reload"
assert "Spool flange bolt" in reloaded_event.narrative
assert reloaded_event.barrier == ["PRESSURE_TESTING"]
assert reloaded_event.sif_status == SIFStatus.SIF_POTENTIAL or reloaded_event.sif_status.value == "SIF-POTENTIAL"

print("[PROCESS B] Persistence verification 100% SUCCESS!")
sys.exit(0)
"""


def test_multiprocess_restart():
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    try:
        print("\n============================================================")
        print("LAUNCHING PROCESS A (WRITE & PERSIST)")
        print("============================================================")
        res_a = subprocess.run([sys.executable, "-c", PROCESS_A_CODE], capture_output=True, text=True)
        print("STDOUT A:\n", res_a.stdout)
        if res_a.stderr:
            print("STDERR A:\n", res_a.stderr)
        assert res_a.returncode == 0, f"Process A failed with code {res_a.returncode}"

        print("============================================================")
        print("LAUNCHING PROCESS B (FRESH PROCESS RELOAD & RETRIEVAL)")
        print("============================================================")
        res_b = subprocess.run([sys.executable, "-c", PROCESS_B_CODE], capture_output=True, text=True)
        print("STDOUT B:\n", res_b.stdout)
        if res_b.stderr:
            print("STDERR B:\n", res_b.stderr)
        assert res_b.returncode == 0, f"Process B failed with code {res_b.returncode}"

        print("============================================================")
        print("MULTI-PROCESS RESTART PERSISTENCE VERIFIED SUCCESSFULLY!")
        print("============================================================")
    finally:
        shutil.rmtree(SCRATCH_DIR, ignore_errors=True)


if __name__ == "__main__":
    test_multiprocess_restart()
