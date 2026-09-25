"""
SHRAMRAKSHAK: Central Safety Ontology Loader & Validator
SIH 2026 Problem Statement: SIH26165

Implements P0.4: Centralized ontology loader and schema validator.
Loads definitions from ontology/*.yaml.
Ensures consistency and validates safety event combinations against physical impossibility.
"""

import os
import yaml
from typing import Dict, List, Any, Optional

ONTOLOGY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ontology")


class SafetyOntology:
    def __init__(self, ontology_dir: str = ONTOLOGY_DIR):
        self.ontology_dir = ontology_dir
        self.activities: Dict[str, Any] = {}
        self.energies: Dict[str, Any] = {}
        self.exposures: Dict[str, Any] = {}
        self.barriers: Dict[str, Any] = {}
        self.barrier_states: Dict[str, Any] = {}
        self.consequences: Dict[str, Any] = {}
        self.lsr_rules: List[Dict[str, Any]] = []
        self.uncertainty_rules: Dict[str, Any] = {}
        self.load_all()

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.ontology_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Ontology file missing: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def load_all(self):
        act_data = self._load_yaml("activities.yaml")
        self.activities = {item["id"]: item for item in act_data.get("activities", [])}

        eng_data = self._load_yaml("energies.yaml")
        self.energies = {item["id"]: item for item in eng_data.get("energies", [])}

        exp_data = self._load_yaml("exposures.yaml")
        self.exposures = {item["id"]: item for item in exp_data.get("exposures", [])}

        bar_data = self._load_yaml("barriers.yaml")
        self.barriers = {item["id"]: item for item in bar_data.get("barriers", [])}

        bs_data = self._load_yaml("barrier_states.yaml")
        self.barrier_states = {item["id"]: item for item in bs_data.get("barrier_states", [])}

        csq_data = self._load_yaml("consequences.yaml")
        self.consequences = {item["id"]: item for item in csq_data.get("consequences", [])}

        lsr_data = self._load_yaml("lsr_rules.yaml")
        self.lsr_rules = lsr_data.get("lsr_rules", [])

        unc_data = self._load_yaml("uncertainty.yaml")
        self.uncertainty_rules = unc_data.get("uncertainty_rules", {})

    def validate_combination(self, activity_id: Optional[str],
                             barrier_id: Optional[str],
                             barrier_state_id: Optional[str]) -> List[str]:
        """Flags contradictory or physically incongruent safety combinations."""
        warnings = []
        if barrier_state_id:
            if barrier_state_id not in self.barrier_states:
                warnings.append(f"Invalid barrier state: {barrier_state_id}")

        if barrier_id and barrier_id not in self.barriers:
            warnings.append(f"Unrecognized barrier: {barrier_id}")

        if activity_id and activity_id in self.activities:
            act_info = self.activities[activity_id]
            applicable_barriers = act_info.get("applicable_barriers", [])
            # If well control barrier applied to standard office or logistics
            if barrier_id in ["PRIMARY_WELL_CONTROL", "BOP_INTEGRITY", "CEMENT_BARRIER"] and activity_id in ["VEHICLE_LOGISTICS", "OFFICE"]:
                warnings.append(f"Incongruent barrier {barrier_id} for activity {activity_id}")

        return warnings


# Global ontology singleton
ontology = SafetyOntology()
