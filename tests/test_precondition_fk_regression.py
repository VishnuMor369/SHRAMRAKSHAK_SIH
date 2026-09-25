"""
SHRAMRAKSHAK: Precondition Foreign Key Regression Test
SIH 2026 Problem Statement: SIH26165

Regression Test:
Proves that when evaluate_work_package() is called for an activity with NO applicable
active preconditions:
1. Result status is NOT_APPLICABLE
2. precondition_id is None / SQL NULL (NOT string "NONE")
3. future_work_checks row persists successfully in SQLite
4. No sqlite3.IntegrityError (foreign key violation) occurs.
"""

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
backend_dir = os.path.join(ROOT_DIR, "backend")
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from test_isolation import isolated_test_environment
from backend.nlp_engine.precondition_engine import precondition_engine


def test_precondition_fk_regression():
    print("============================================================")
    print("RUNNING PRECONDITION FOREIGN KEY REGRESSION TEST")
    print("============================================================")

    with isolated_test_environment() as env:
        db = env["db"]

        # Verify initial clean state has 0 preconditions
        initial_preconditions = db.list_preconditions(active_only=True)
        print(f"[TEST SETUP] Active preconditions in clean DB: {len(initial_preconditions)}")
        assert len(initial_preconditions) == 0

        # Evaluate a standard activity with NO applicable preconditions active
        package_id = "PKG-STANDARD-NO-PRECOND-01"
        activity = "General Landscaping and Perimeter Groundskeeping"
        location = "Administration Complex Sector A"

        print(f"\n[STEP 1] Evaluating work package for activity: '{activity}'")
        chk = precondition_engine.evaluate_work_package(
            package_id=package_id,
            activity=activity,
            location=location,
            submitted_evidence={}
        )

        print(f"[STEP 2] Check Result evaluated:")
        print(f" -> check_id:        {chk.check_id}")
        print(f" -> status:          {chk.status}")
        print(f" -> precondition_id: {chk.precondition_id} (type: {type(chk.precondition_id).__name__})")
        print(f" -> findings:        {chk.findings}")

        # Assertions required by regression test specification
        assert chk.status == "NOT_APPLICABLE", f"Expected NOT_APPLICABLE, got {chk.status}"
        assert chk.precondition_id is None, f"Expected precondition_id to be None, got {chk.precondition_id}"

        # Verify direct SQLite persistence and NULL value in future_work_checks table
        with db.get_connection() as conn:
            cur = conn.execute("SELECT check_id, package_id, activity, precondition_id, status FROM future_work_checks WHERE check_id = ?", (chk.check_id,))
            row = cur.fetchone()

        assert row is not None, "future_work_checks row was not persisted!"
        print(f"\n[STEP 3] Verified SQLite persistence in future_work_checks:")
        print(f" -> check_id:        {row['check_id']}")
        print(f" -> package_id:      {row['package_id']}")
        print(f" -> activity:        {row['activity']}")
        print(f" -> precondition_id: {row['precondition_id']} (is None: {row['precondition_id'] is None})")
        print(f" -> status:          {row['status']}")

        assert row["precondition_id"] is None, f"Database column precondition_id must be NULL, got {row['precondition_id']}"
        assert row["status"] == "NOT_APPLICABLE"

        print("\n [x] REGRESSION TEST PASSED: No FK IntegrityError, status=NOT_APPLICABLE, precondition_id=NULL")

    print("============================================================")
    print("PRECONDITION FOREIGN KEY REGRESSION TEST PASSED 100%!")
    print("============================================================")


if __name__ == "__main__":
    test_precondition_fk_regression()
