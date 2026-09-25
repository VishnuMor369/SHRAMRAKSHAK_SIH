"""
SHRAMRAKSHAK: Mandatory Recurrence Test Suite (Events A, B, C)
SIH 2026 Problem Statement: SIH26165

Directly verifies P1.4:
A: "Worker entered exclusion zone during suspended load."
B: "Rigger crossed the lifting boundary while pipe was suspended."
-> Eligible for same control mechanism / INDEPENDENT_RECURRENCE.

C: "Worker remained outside the exclusion zone and barricade was intact."
-> Must NOT become a failure recurrence merely because lifting/exclusion-zone words match.
-> Classified as RELATED_BUT_DIFFERENT (control polarity conflict).
"""

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

import backend
from backend.models_canonical import RecurrenceRelationship, ReviewStatus
from backend.nlp_engine.assertion_detector import assertion_detector
from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
from backend.nlp_engine.recurrence_engine import recurrence_engine
from backend.database import db

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)
from test_isolation import isolated_test_environment


def test_recurrence_a_b_c():
    with isolated_test_environment():
        print("============================================================")
        print("RUNNING MANDATORY RECURRENCE TESTS: EVENTS A, B, C")
        print("============================================================")

        # Event A
        text_a = "Worker entered exclusion zone during suspended load."
        ev_a = assertion_detector.analyze(text_a, context={"event_id": "EVT-TEST-A"})
        ev_a = sif_pathway_engine.evaluate(ev_a)
        db.save_event(ev_a)
        backend.nlp_engine.semantic_memory.semantic_memory.add_event(ev_a)
        print(f"\n[EVENT A] SIF: {ev_a.sif_status}, Barrier: {ev_a.barrier}, States: {ev_a.barrier_state}")

        # Event B
        text_b = "Rigger crossed the lifting boundary while pipe was suspended."
        ev_b = assertion_detector.analyze(text_b, context={"event_id": "EVT-TEST-B"})
        ev_b = sif_pathway_engine.evaluate(ev_b)
        db.save_event(ev_b)
        print(f"[EVENT B] SIF: {ev_b.sif_status}, Barrier: {ev_b.barrier}, States: {ev_b.barrier_state}")

        # Event C
        text_c = "Worker remained outside the exclusion zone and barricade was intact."
        ev_c = assertion_detector.analyze(text_c, context={"event_id": "EVT-TEST-C"})
        ev_c = sif_pathway_engine.evaluate(ev_c)
        db.save_event(ev_c)
        print(f"[EVENT C] SIF: {ev_c.sif_status}, Barrier: {ev_c.barrier}, States: {ev_c.barrier_state}")

        # Test Recurrence between A and B
        res_ab = recurrence_engine.evaluate_pair(ev_a, ev_b, similarity=0.88)
        print(f"\n[PAIR A & B] Relationship: {res_ab.final_relationship}")
        print(f" -> Reason: {res_ab.reason}")
        assert res_ab.final_relationship == RecurrenceRelationship.INDEPENDENT_RECURRENCE
        print(" [x] A & B PASSED: Correctly identified as INDEPENDENT_RECURRENCE of same control mechanism breach")

        # Test Recurrence between A and C (Intact barrier vs failure)
        res_ac = recurrence_engine.evaluate_pair(ev_a, ev_c, similarity=0.82)
        print(f"\n[PAIR A & C] Relationship: {res_ac.final_relationship}")
        print(f" -> Reason: {res_ac.reason}")
        print(f" -> Conflicts: {res_ac.structured_conflicts}")
        assert res_ac.final_relationship != RecurrenceRelationship.INDEPENDENT_RECURRENCE
        assert res_ac.final_relationship == RecurrenceRelationship.RELATED_BUT_DIFFERENT
        assert any("POLARITY_CONFLICT" in c for c in res_ac.structured_conflicts)
        print(" [x] A & C PASSED: Intact barrier NOT misclassified as failure recurrence despite matching keywords!")

        # Test Pattern creation and CANDIDATE status
        results, pattern = recurrence_engine.process_event(ev_b)
        if pattern:
            print(f"\n[PATTERN CREATED] ID: {pattern.pattern_id}, Status: {pattern.validation_status}")
            assert pattern.validation_status == ReviewStatus.CANDIDATE
            print(" [x] PATTERN STATUS PASSED: Pattern is CANDIDATE, NOT automatically HSE_VALIDATED")

        print("\n============================================================")
        print("ALL MANDATORY RECURRENCE TESTS PASSED 100%!")
        print("============================================================")


if __name__ == "__main__":
    test_recurrence_a_b_c()
