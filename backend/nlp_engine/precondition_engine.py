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

    def _get_db(self):
        try:
            from backend.database import db as active_db
            return active_db
        except Exception:
            return self.db

    def create_precondition_from_pattern(
        self,
        pattern_id: str,
        custom_title: Optional[str] = None,
        required_evidence_types: Optional[List[str]] = None,
        status: str = "ACTIVE",
        created_by: str = "HSE_MANAGER"
    ) -> WorkPrecondition:
        """
        Creates a future-work precondition from an HSE_VALIDATED SafetyPattern.
        Only validated patterns can generate preconditions (Rule 17).
        """
        active_db = self._get_db()
        pattern = active_db.get_pattern(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found.")

        # STRICT GATING (Rule 17): Only HSE_VALIDATED patterns can generate work preconditions
        val_status = pattern.validation_status.value if hasattr(pattern.validation_status, 'value') else str(pattern.validation_status)
        if val_status != ReviewStatus.HSE_VALIDATED.value:
            raise ValueError(
                f"Pattern '{pattern_id}' has validation status '{val_status}'. "
                f"Only HSE_VALIDATED patterns can generate active work preconditions (CANDIDATE/REJECTED patterns cannot generate preconditions)."
            )

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
            status=status,
            created_by=created_by,
            created_at=datetime.now().isoformat()
        )

        return active_db.save_precondition(prec)

    def propose_precondition_from_pattern(
        self,
        pattern_id: str,
        custom_title: Optional[str] = None,
        required_evidence_types: Optional[List[str]] = None
    ) -> WorkPrecondition:
        """Rule 17: Generates an AI-proposed precondition with status PROPOSED for HSE review."""
        return self.create_precondition_from_pattern(
            pattern_id=pattern_id,
            custom_title=custom_title,
            required_evidence_types=required_evidence_types,
            status="PROPOSED",
            created_by="AI_SAFETY_ENGINE"
        )

    def accept_precondition(
        self,
        precondition_id: str,
        reviewer_role: str = "HSE_MANAGER",
        notes: str = ""
    ) -> WorkPrecondition:
        """Rule 17: HSE authority accepts a PROPOSED precondition, moving it to ACTIVE."""
        active_db = self._get_db()
        prec = active_db.get_precondition(precondition_id)
        if not prec:
            raise ValueError(f"Precondition {precondition_id} not found.")

        prev_status = prec.status
        prec.status = "ACTIVE"
        prec.reviewed_by = reviewer_role
        prec.review_notes = notes or "HSE accepted future-work precondition"
        active_db.save_precondition(prec)

        active_db.log_review(
            review_id=f"REV-PREC-{uuid.uuid4().hex[:6]}",
            target_type="PRECONDITION",
            target_id=prec.precondition_id,
            reviewer_role=reviewer_role,
            action="ACCEPT",
            previous_value={"status": prev_status},
            new_value={"status": "ACTIVE"},
            reason=prec.review_notes
        )
        return prec

    def reject_precondition(
        self,
        precondition_id: str,
        reviewer_role: str = "HSE_MANAGER",
        reason: str = ""
    ) -> WorkPrecondition:
        """Rule 17: HSE authority rejects a proposed precondition."""
        active_db = self._get_db()
        prec = active_db.get_precondition(precondition_id)
        if not prec:
            raise ValueError(f"Precondition {precondition_id} not found.")

        prev_status = prec.status
        prec.status = "REJECTED"
        prec.reviewed_by = reviewer_role
        prec.review_notes = reason or "HSE rejected future-work precondition"
        active_db.save_precondition(prec)

        active_db.log_review(
            review_id=f"REV-PREC-{uuid.uuid4().hex[:6]}",
            target_type="PRECONDITION",
            target_id=prec.precondition_id,
            reviewer_role=reviewer_role,
            action="REJECT",
            previous_value={"status": prev_status},
            new_value={"status": "REJECTED"},
            reason=prec.review_notes
        )
        return prec

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
        active_db = self._get_db()
        active_preconditions = active_db.list_preconditions(active_only=True)
        
        applicable_preconditions = []
        act_lower = (activity or "").lower()
        for p in active_preconditions:
            b_upper = (p.required_barrier or "").upper()
            is_app = False
            if any(kw in act_lower for kw in ["lift", "crane"]) and ("EXCLUSION" in b_upper or "LIFT" in b_upper):
                is_app = True
            elif any(kw in act_lower for kw in ["isolat", "loto", "electric"]) and "ISOLATION" in b_upper:
                is_app = True
            elif any(kw in act_lower for kw in ["height", "scaffold", "fall"]) and "FALL" in b_upper:
                is_app = True
            elif any(kw in act_lower for kw in ["tank", "confined", "vessel"]) and "GAS" in b_upper:
                is_app = True
            elif any(kw in act_lower for kw in ["hot work", "weld", "grind"]) and any(b in b_upper for b in ["FIRE", "GAS"]):
                is_app = True
            elif any(kw in act_lower for kw in ["pressure", "hydrotest"]) and any(b in b_upper for b in ["PRESSURE", "EXCLUSION"]):
                is_app = True
            elif p.pattern_id:
                pat = active_db.get_pattern(p.pattern_id)
                if pat and (pat.activity.lower() in act_lower or act_lower in pat.activity.lower()):
                    is_app = True

            if is_app:
                applicable_preconditions.append(p)

        if not applicable_preconditions:
            check_result = WorkCheckResult(
                check_id=f"CHK-{uuid.uuid4().hex[:8]}",
                package_id=package_id,
                activity=activity,
                location=location,
                precondition_id=None,
                status="NOT_APPLICABLE",
                findings=["No specialized high-consequence recurring preconditions active for this standard activity."],
                missing_evidence=[],
                evaluated_at=datetime.now().isoformat()
            )
            return active_db.save_work_check(check_result)

        primary_prec = applicable_preconditions[0]
        missing_evidence = []
        verified_evidence = []
        findings = []

        is_multi = len(applicable_preconditions) > 1
        if is_multi:
            findings.append(f"Evaluated {len(applicable_preconditions)} applicable active preconditions: {', '.join(p.precondition_id for p in applicable_preconditions)}.")

        total_requirements_count = 0

        # Evaluate EVERY applicable precondition
        for p in applicable_preconditions:
            prefix = f"[{p.precondition_id} - {p.title}] " if is_multi else ""
            for req_ev in p.required_evidence_types:
                total_requirements_count += 1
                evidence_val = submitted_evidence.get(req_ev)
                if not evidence_val:
                    if req_ev not in missing_evidence:
                        missing_evidence.append(req_ev)
                    findings.append(f"{prefix}Required evidence missing: {req_ev}")
                else:
                    # Rule 19: Evidence Quality ("COMPLETION IS NOT PROOF")
                    # Distinguish DECLARED vs DOCUMENTED / EVIDENCED / VERIFIED
                    val_str = str(evidence_val).strip()
                    low_val = val_str.lower()
                    is_naked_declared = (
                        low_val in ["completed", "done", "yes", "true", "isolation completed", "finished", "ok"]
                        or (isinstance(evidence_val, dict) and evidence_val.get("quality") == "DECLARED")
                    )
                    is_critical_barrier = any(kw in req_ev for kw in ["ZERO_ENERGY", "GAS_TEST", "ISOLATION", "LOTO", "CERTIFICAT"])

                    if is_naked_declared and is_critical_barrier:
                        findings.append(
                            f"{prefix}Evidence Quality Warning: '{val_str}' is DECLARED only. "
                            f"Critical barrier '{req_ev}' requires DOCUMENTED or EVIDENCED verification. Completion is not proof."
                        )
                        if req_ev not in missing_evidence:
                            missing_evidence.append(req_ev)
                    else:
                        if req_ev not in verified_evidence:
                            verified_evidence.append(req_ev)
                        findings.append(f"{prefix}Evidence verified: {req_ev} -> {evidence_val}")

            # CCTV observable condition check for this precondition
            if "OBSERVABLE_CCTV_CLEAR_ZONE" in p.required_evidence_types:
                cctv_obs = submitted_evidence.get("OBSERVABLE_CCTV_CLEAR_ZONE")
                if cctv_obs is not None:
                    cctv_prefix = f"[{p.precondition_id}] " if is_multi else ""
                    if cctv_obs is True or str(cctv_obs).lower() == "clear":
                        findings.append(f"{cctv_prefix}CCTV Corroboration: Zone visually confirmed clear of unauthorized personnel.")
                    else:
                        findings.append(f"{cctv_prefix}CCTV Corroboration Warning: Observable personnel or obstruction in restricted perimeter.")

        # Determine Overall Status across all applicable preconditions
        if not missing_evidence:
            status = "PASS"
            findings.append("All evidence requirements satisfied. Ready for human HSE permit authority review.")
        elif not verified_evidence:
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

        return active_db.save_work_check(check_result)


precondition_engine = PreconditionEngine()
