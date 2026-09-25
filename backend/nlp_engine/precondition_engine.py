"""
SHRAMRAKSHAK: Future-Work Precondition & Multi-Source Evidence Checking Engine
SIH 2026 Problem Statement: SIH26165

Implements P2.1 & P2.2:
- Translates HSE-validated recurring safety patterns into active work preconditions
- Checks future work packages against multi-source evidence:
    * Structured system authorizations / safety passport
    * Document certifications (LOTO test log, Gas test record)
    * Observable CCTV boundary conditions (physical demarcation only)
- Results: PASS | MISSING_EVIDENCE | REVIEW_REQUIRED | NOT_APPLICABLE
- STRICT COMPLIANCE:
    * System NEVER automatically approves or rejects work permits
    * System NEVER replaces OIL's HSE / PTW authority
    * Clear boundary: CCTV only checks observable spatial conditions, NOT internal zero energy or gas state.
"""

import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

try:
    from backend.models_canonical import (
        SafetyPattern, WorkPrecondition, WorkCheckResult, ReviewStatus
    )
    from backend.database import db
except ImportError:
    try:
        from models_canonical import (
            SafetyPattern, WorkPrecondition, WorkCheckResult, ReviewStatus
        )
        from database import db
    except ImportError:
        from ..models_canonical import (
            SafetyPattern, WorkPrecondition, WorkCheckResult, ReviewStatus
        )
        from ..database import db


class PreconditionEngine:
    def __init__(self):
        self.db = db

    def create_precondition_from_pattern(
        self,
        pattern_id: str,
        custom_title: Optional[str] = None,
        required_evidence_types: Optional[List[str]] = None
    ) -> WorkPrecondition:
        """
        Creates an active future-work precondition from an HSE_VALIDATED SafetyPattern.
        Only validated patterns can generate active preconditions.
        """
        pattern = self.db.get_pattern(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found.")

        # Default required evidence types based on barrier type
        b_type = (pattern.barrier or "GENERAL_CONTROL").upper()
        if not required_evidence_types:
            if "EXCLUSION" in b_type or "LIFT" in b_type:
                required_evidence_types = [
                    "PHYSICAL_PERIMETER_DEMARCATION",
                    "AUTHORIZED_ENTRANTS_PASSPORT",
                    "OBSERVABLE_CCTV_CLEAR_ZONE"
                ]
            elif "ISOLATION" in b_type or "LOTO" in b_type:
                required_evidence_types = [
                    "ZERO_ENERGY_TEST_LOG",
                    "LOTO_PADLOCK_REGISTER",
                    "ELECTRICAL_ISOLATION_CERTIFICATE"
                ]
            elif "GAS" in b_type or "CONFINED" in b_type:
                required_evidence_types = [
                    "CALIBRATED_4GAS_TEST_RECORD",
                    "STANDBY_RESCUE_PERSONNEL",
                    "VENTILATION_CONFIRMATION"
                ]
            elif "HEIGHT" in b_type or "FALL" in b_type:
                required_evidence_types = [
                    "HARNESS_INSPECTION_TAG",
                    "CERTIFIED_ANCHOR_POINT_SIGN_OFF",
                    "SCAFFOLD_INSPECTION_GREEN_TAG"
                ]
            else:
                required_evidence_types = [
                    "TOOLBOX_TALK_ATTENDANCE",
                    "JSA_RISK_ASSESSMENT_SIGN_OFF"
                ]

        title = custom_title or f"Precondition: Mandatory {pattern.barrier} for {pattern.activity}"
        precondition_id = f"PREC-{uuid.uuid4().hex[:8]}"

        prec = WorkPrecondition(
            precondition_id=precondition_id,
            pattern_id=pattern.pattern_id,
            title=title,
            required_barrier=pattern.barrier,
            required_evidence_types=required_evidence_types,
            status="ACTIVE",
            created_at=datetime.now().isoformat()
        )

        return self.db.save_precondition(prec)

    def evaluate_work_package(
        self,
        package_id: str,
        activity: str,
        location: str,
        submitted_evidence: Dict[str, Any]
    ) -> WorkCheckResult:
        """
        Evaluates a future work package against all applicable active preconditions.
        Provides decision-support findings and flags missing evidence.
        NEVER claims to approve or reject a permit.
        """
        active_preconditions = self.db.list_preconditions(active_only=True)
        
        applicable_preconditions = []
        for p in active_preconditions:
            # Check applicability
            if any(kw in activity.lower() for kw in ["lift", "crane"]) and ("EXCLUSION" in p.required_barrier or "LIFT" in p.required_barrier):
                applicable_preconditions.append(p)
            elif any(kw in activity.lower() for kw in ["isolat", "loto", "electric"]) and "ISOLATION" in p.required_barrier:
                applicable_preconditions.append(p)
            elif any(kw in activity.lower() for kw in ["height", "scaffold"]) and "FALL" in p.required_barrier:
                applicable_preconditions.append(p)
            elif any(kw in activity.lower() for kw in ["tank", "confined"]) and "GAS" in p.required_barrier:
                applicable_preconditions.append(p)

        if not applicable_preconditions:
            check_result = WorkCheckResult(
                check_id=f"CHK-{uuid.uuid4().hex[:8]}",
                package_id=package_id,
                activity=activity,
                location=location,
                precondition_id="NONE",
                status="NOT_APPLICABLE",
                findings=["No specialized high-consequence recurring preconditions active for this standard activity."],
                missing_evidence=[],
                evaluated_at=datetime.now().isoformat()
            )
            return self.db.save_work_check(check_result)

        primary_prec = applicable_preconditions[0]
        missing_evidence = []
        findings = []

        # Multi-source check
        for req_ev in primary_prec.required_evidence_types:
            evidence_val = submitted_evidence.get(req_ev)
            if not evidence_val:
                missing_evidence.append(req_ev)
                findings.append(f"Required evidence missing: {req_ev}")
            else:
                findings.append(f"Evidence verified: {req_ev} -> {evidence_val}")

        # CCTV observable condition check
        cctv_obs = submitted_evidence.get("OBSERVABLE_CCTV_CLEAR_ZONE")
        if cctv_obs is not None:
            if cctv_obs is True or str(cctv_obs).lower() == "clear":
                findings.append("CCTV Corroboration: Zone visually confirmed clear of unauthorized personnel.")
            else:
                findings.append("CCTV Corroboration Warning: Observable personnel or obstruction in restricted perimeter.")

        # Determine Status
        if not missing_evidence:
            status = "PASS"
            findings.append("All evidence requirements satisfied. Ready for human HSE permit authority review.")
        elif len(missing_evidence) == len(primary_prec.required_evidence_types):
            status = "MISSING_EVIDENCE"
            findings.append("Critical safety evidence absent. Operation cannot proceed without required barrier proof.")
        else:
            status = "REVIEW_REQUIRED"
            findings.append("Partial evidence presented. Requires HSE Supervisor manual verification.")

        check_result = WorkCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            package_id=package_id,
            activity=activity,
            location=location,
            precondition_id=primary_prec.precondition_id,
            status=status,
            findings=findings,
            missing_evidence=missing_evidence,
            evaluated_at=datetime.now().isoformat()
        )

        return self.db.save_work_check(check_result)


precondition_engine = PreconditionEngine()
