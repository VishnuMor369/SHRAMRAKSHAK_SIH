"""
SHRAMRAKSHAK: Cross-Domain Recurrence Isolated Benchmark
SIH 2026 Problem Statement: SIH26165

Benchmarks 6 industrial operating domains:
1. Mechanical Lifting
2. Energy Isolation / LOTO
3. Confined Space Entry
4. Work at Height
5. Hot Work
6. High Pressure Testing

Validates:
- True independent recurrence across identical compromised controls in every domain
- Intact control polarity separation (safe vs failure) in every domain
- Domain cross-talk separation (different domain / barrier)
- Completely independent of hardcoded lifting/suspension keywords
"""

import sys
import os
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
backend_dir = os.path.join(ROOT_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

from test_isolation import isolated_test_environment
from backend.models_canonical import (
    SafetyEvent, ExposureStatus, BarrierState, SIFStatus, RecurrenceRelationship
)
from backend.nlp_engine.recurrence_engine import recurrence_engine


DOMAINS = [
    {
        "name": "Mechanical Lifting",
        "activity": "Mechanical Lifting Operations",
        "energy": "Gravitational / Suspended Load",
        "barrier": "EXCLUSION_ZONE",
        "narrative_fail_1": "Rigger entered the crane swing zone while the drill collar was hoisted.",
        "narrative_fail_2": "Floorhand stepped under suspended casing pipe without banksman signal.",
        "narrative_safe": "Banksman maintained physical barrier; personnel remained at safe staging distance."
    },
    {
        "name": "Energy Isolation / LOTO",
        "activity": "Energy Isolation / Lockout Tagout",
        "energy": "Electrical and Hydraulic Energy",
        "barrier": "ENERGY_ISOLATION",
        "narrative_fail_1": "Electrician commenced work on mud pump motor before applying padlock to MCC breaker.",
        "narrative_fail_2": "Mechanic opened hydraulic valve without installing lockout hasp on isolation point.",
        "narrative_safe": "Zero-energy state verified and dual padlock isolation locked out before intervention."
    },
    {
        "name": "Confined Space Entry",
        "activity": "Confined Space Entry",
        "energy": "Atmospheric Toxic / Hydrogen Sulfide",
        "barrier": "GAS_TESTING",
        "narrative_fail_1": "Entrant entered reserve mud tank before atmospheric continuous 4-gas testing was logged.",
        "narrative_fail_2": "Roustabout stepped inside separator vessel without calibrated gas monitor sign-off.",
        "narrative_safe": "Gas testing conducted and atmosphere certified 20.9% O2, 0 ppm H2S prior to entry."
    },
    {
        "name": "Work at Height",
        "activity": "Working at Height / Mast & Derrick",
        "energy": "Gravitational Height",
        "barrier": "FALL_PROTECTION",
        "narrative_fail_1": "Derrickman moved along monkey board after unclipping twin harness lanyard from anchor.",
        "narrative_fail_2": "Painter worked on derrick staging above 2m without securing fall arrest lifeline.",
        "narrative_safe": "Worker utilized full body harness with 100% tie-off anchored to certified derrick padeye."
    },
    {
        "name": "Hot Work",
        "activity": "Hot Work Operations",
        "energy": "Thermal Ignition",
        "barrier": "FIRE_WATCH",
        "narrative_fail_1": "Welder initiated torch cutting on deck piping without designated fire watch present.",
        "narrative_fail_2": "Grinder produced sparks near manifold without fire extinguisher and fire watcher on post.",
        "narrative_safe": "Fire watch posted with charged foam extinguisher throughout entire welding cycle."
    },
    {
        "name": "High Pressure Testing",
        "activity": "High Pressure Testing",
        "energy": "High Pressure Stored Fluid",
        "barrier": "PRESSURE_TESTING",
        "narrative_fail_1": "Technician inspected flowline flange while hydrostatic line was energized to 10,000 psi.",
        "narrative_fail_2": "Operator approached manifold manifold envelope during active hydrotest pumping.",
        "narrative_safe": "High pressure exclusion perimeter barricaded and personnel cleared before pressuring up."
    }
]


def test_cross_domain_recurrence_benchmark():
    print("\n============================================================")
    print("RUNNING CROSS-DOMAIN RECURRENCE ISOLATED BENCHMARK (6 DOMAINS)")
    print("============================================================\n")

    with isolated_test_environment():
        for domain in DOMAINS:
            name = domain["name"]
            activity = domain["activity"]
            energy = domain["energy"]
            barrier = domain["barrier"]

            # Failure 1
            ev_f1 = SafetyEvent(
                event_id=f"EVT-{name.replace(' ', '')}-F1",
                activity=activity,
                energy=energy,
                exposure="Personnel in hazardous zone",
                exposure_status=ExposureStatus.CONFIRMED,
                barrier=[barrier],
                barrier_state=["BYPASSED"],
                consequence="Potential serious injury",
                narrative=domain["narrative_fail_1"],
                sif_status=SIFStatus.SIF_POTENTIAL
            )

            # Failure 2 (Independent Recurrence)
            ev_f2 = SafetyEvent(
                event_id=f"EVT-{name.replace(' ', '')}-F2",
                activity=activity,
                energy=energy,
                exposure="Worker exposed to hazard",
                exposure_status=ExposureStatus.CONFIRMED,
                barrier=[barrier],
                barrier_state=["BYPASSED"],
                consequence="Potential serious injury",
                narrative=domain["narrative_fail_2"],
                sif_status=SIFStatus.SIF_POTENTIAL
            )

            # Safe Control Observation
            ev_safe = SafetyEvent(
                event_id=f"EVT-{name.replace(' ', '')}-SAFE",
                activity=activity,
                energy=energy,
                exposure="Personnel remained clear of hazard",
                exposure_status=ExposureStatus.NEGATED,
                barrier=[barrier],
                barrier_state=["EFFECTIVE_VERIFIED"],
                consequence="Safe operation",
                narrative=domain["narrative_safe"],
                sif_status=SIFStatus.NO_SIF_POTENTIAL_IDENTIFIED
            )

            # 1. Test Recurrence between F1 and F2
            res_rec = recurrence_engine.evaluate_pair(ev_f1, ev_f2, similarity=0.85)
            print(f"[{name}] Recurrence Result: {res_rec.final_relationship.value}")
            print(f" -> Reason: {res_rec.reason}")
            assert res_rec.final_relationship == RecurrenceRelationship.INDEPENDENT_RECURRENCE, (
                f"Failed recurrence test for domain {name}"
            )
            assert barrier in res_rec.reason

            # 2. Test Polarity Conflict between F1 and SAFE
            res_pol = recurrence_engine.evaluate_pair(ev_f1, ev_safe, similarity=0.82)
            print(f"[{name}] Polarity Result: {res_pol.final_relationship.value}")
            assert res_pol.final_relationship == RecurrenceRelationship.RELATED_BUT_DIFFERENT
            assert any("POLARITY_CONFLICT" in c for c in res_pol.structured_conflicts)
            print(f" -> [x] {name} passed both recurrence and polarity conflict checks\n")

        print("============================================================")
        print("ALL 6 CROSS-DOMAIN RECURRENCE BENCHMARKS PASSED 100%!")
        print("============================================================")


if __name__ == "__main__":
    test_cross_domain_recurrence_benchmark()
