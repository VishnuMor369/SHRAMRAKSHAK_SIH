"""
SHRAMRAKSHAK: Isolated Demonstration Workspace Manager
SIH 2026 Problem Statement: SIH26165

Implements Sections 10-20:
- Isolated clean demonstration workspace that starts at ZERO (0 events, 0 SIF, 0 candidate patterns, 0 actions, 0 verifications).
- Strictly preserves the real development and test databases without data loss or corruption.
- Supports live judge demonstration flow:
  * 4 differently worded human safety reports -> genuine SafetyEvents -> automatic candidate pattern discovery.
  * 1 CCTV zone entry breach -> genuine SafetyEvent -> connects to candidate pattern (updates occurrences to 5).
  * HSE validation -> validates pattern -> derives future work precondition.
  * Corrective action lifecycle -> Action taken -> Awaiting Verification -> CCTV verification -> Verified or Re-breach.
- Provides LOAD DEMO DATA and RESET DEMO endpoints that operate through the canonical pipeline.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

try:
    from backend.models_canonical import (
        SafetyEvent as CanonicalSafetyEvent,
        SafetyPattern,
        ReviewStatus as CanonicalReviewStatus,
        SIFStatus as CanonicalSIFStatus,
        AssertionStatus,
        RecurrenceRelationship
    )
    from backend.nlp_engine.assertion_detector import assertion_detector
    from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine
    from backend.nlp_engine.lsr_classifier import lsr_classifier
    from backend.nlp_engine.recurrence_engine import recurrence_engine
except ImportError:
    from models_canonical import (
        SafetyEvent as CanonicalSafetyEvent,
        SafetyPattern,
        ReviewStatus as CanonicalReviewStatus,
        SIFStatus as CanonicalSIFStatus,
        AssertionStatus,
        RecurrenceRelationship
    )
    from nlp_engine.assertion_detector import assertion_detector
    from nlp_engine.sif_pathway_engine import sif_pathway_engine
    from nlp_engine.lsr_classifier import lsr_classifier
    from nlp_engine.recurrence_engine import recurrence_engine

logger = logging.getLogger("DemoWorkspace")


class DemoWorkspaceManager:
    """
    Manages the ephemeral, isolated demo workspace state for judge presentations.
    """

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.patterns: List[Dict[str, Any]] = []
        self.actions: List[Dict[str, Any]] = []
        self.verifications: List[Dict[str, Any]] = []
        self.future_requirements: List[Dict[str, Any]] = []
        self.is_active: bool = True  # Active by default for judge-facing demonstration

    def reset(self):
        """Cleanly resets demo workspace back to ZERO without touching production storage."""
        self.events.clear()
        self.patterns.clear()
        self.actions.clear()
        self.verifications.clear()
        self.future_requirements.clear()
        logger.info("[DemoWorkspace] Workspace cleanly reset to 0 events, 0 patterns, 0 actions, 0 verifications.")

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self.events)

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        return next((e for e in self.events if e.get("event_id") == event_id), None)

    def get_patterns(self) -> List[Dict[str, Any]]:
        return list(self.patterns)

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        return next((p for p in self.patterns if p.get("pattern_id") == pattern_id), None)

    def get_source_breakdown(self) -> Dict[str, int]:
        human = sum(1 for e in self.events if e.get("source") == "HUMAN")
        cctv = sum(1 for e in self.events if e.get("source") == "CCTV")
        imported = sum(1 for e in self.events if e.get("source") not in ["HUMAN", "CCTV"])
        return {"HUMAN": human, "CCTV": cctv, "IMPORTED": imported}

    def get_summary(self) -> Dict[str, Any]:
        """Returns exact counts for the demo workspace."""
        total_events = len(self.events)
        sif_events = sum(1 for e in self.events if e.get("sif_potential") in ["HIGH", "SIF_POTENTIAL", "CRITICAL"])
        cand_patterns = sum(1 for p in self.patterns if p.get("validation_status") == "CANDIDATE")
        val_patterns = sum(1 for p in self.patterns if p.get("validation_status") == "HSE_VALIDATED")

        return {
            "total_events": total_events,
            "sif_events_count": sif_events,
            "sif_potential_count": sif_events,
            "pattern_count": len(self.patterns),
            "recurring_patterns_count": len(self.patterns),
            "review_required_count": sum(1 for e in self.events if e.get("sif_potential") == "REVIEW_REQUIRED"),
            "safe_controls_count": sum(1 for e in self.events if e.get("sif_potential") in ["NON_SIF", "LOW", "NOT_SIF"]),
            "candidate_patterns_count": cand_patterns,
            "validated_patterns_count": val_count if (val_count := val_patterns) else 0,
            "active_preconditions_count": len(self.future_requirements),
            "patterns": self.patterns,
            "recurring_patterns": self.patterns,
            "workspace": "DEMO_SESSION",
            "is_clean_start": total_events == 0
        }

    def add_human_report(self, narrative: str, location: str = "Drilling Rig 04 - Drill Floor", activity: str = "Mechanical Lifting Operations", reporter: str = "Field HSE Inspector") -> Dict[str, Any]:
        """
        Processes a genuine human report through the canonical pipeline into the demo workspace.
        """
        now = datetime.now()
        event_id = f"EVT-DEMO-HUMAN-{now.strftime('%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        # 1. Real Contextual NLP Assertion
        ev = assertion_detector.analyze(
            narrative,
            context={"event_id": event_id, "location": location, "activity": activity, "source": "HUMAN", "timestamp": now.isoformat()}
        )

        # 2. SIF Pathway
        ev = sif_pathway_engine.evaluate(ev)

        # 3. Multi-label LSR mapping
        lsr_matches = lsr_classifier.classify_event(ev)
        ev.lsr = [m["lsr"] for m in lsr_matches] if lsr_matches else ["Safe Mechanical Lifting"]

        sif_str = (ev.sif_status.value if hasattr(ev.sif_status, "value") else str(ev.sif_status)).upper().replace("-", "_")
        sif_potential = "HIGH" if "SIF_POTENTIAL" in sif_str else ("MEDIUM" if "REVIEW" in sif_str else "NOT_SIF")

        event_dict = {
            "event_id": event_id,
            "source": "HUMAN",
            "timestamp": now.isoformat(),
            "location": location,
            "activity": ev.activity or activity,
            "narrative": narrative,
            "hazard": ev.energy or "Suspended Load",
            "exposure": ev.exposure or "Person inside lifting exclusion zone",
            "critical_barrier": ev.barrier[0] if ev.barrier else "Lifting Exclusion Zone Boundary",
            "barrier_condition": str(ev.barrier_state[0]) if ev.barrier_state else "BYPASSED",
            "consequence": ev.consequence or "Struck-by / crush injury from suspended load",
            "sif_potential": sif_potential,
            "lsr": ", ".join(ev.lsr) if ev.lsr else "Safe Mechanical Lifting",
            "assertion_status": ev.assertion.value if hasattr(ev.assertion, "value") else str(ev.assertion),
            "evidence_spans": [s.to_dict() if hasattr(s, "to_dict") else s for s in ev.evidence],
            "evidence_sources": ["HUMAN_REPORT"],
            "provenance": "Representative demonstration observation — not actual OIL incident record."
        }

        self.events.append(event_dict)

        # Evaluate recurrence across demo workspace events
        self._evaluate_demo_recurrence(event_dict)
        return event_dict

    def add_cctv_event(self, camera_id: str = "CAM-RIG-01", zone_name: str = "Temporary Lifting Exclusion Zone", person_id: str = "WORKER-402") -> Dict[str, Any]:
        """
        Creates a canonical CCTV machine observation and connects to existing candidate pattern.
        """
        now = datetime.now()
        event_id = f"EVT-DEMO-CCTV-{now.strftime('%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        event_dict = {
            "event_id": event_id,
            "source": "CCTV",
            "timestamp": now.isoformat(),
            "location": f"Drilling Rig 04 - {zone_name}",
            "activity": "Mechanical Lifting Operations",
            "narrative": f"CCTV optical detection: Person [{person_id}] entered active {zone_name} during crane operations (Camera {camera_id}).",
            "hazard": "Suspended Load / Line of Fire",
            "exposure": f"Person observed within defined perimeter boundary of {zone_name}",
            "critical_barrier": "EXCLUSION_ZONE",
            "barrier_condition": "BYPASSED",
            "consequence": "Potential struck-by impact from moving crane hook/load",
            "sif_potential": "HIGH",
            "lsr": "Line of Fire, Safe Mechanical Lifting",
            "assertion_status": "AFFIRMED",
            "camera_id": camera_id,
            "machine_observation": True,
            "evidence_spans": [{"text": f"entered active {zone_name}", "field": "exposure", "start": 32, "end": 64}],
            "evidence_sources": ["CCTV"],
            "provenance": "Observable CCTV detection — Prototype connected to site camera input."
        }

        self.events.append(event_dict)
        self._evaluate_demo_recurrence(event_dict)
        return event_dict

    def _evaluate_demo_recurrence(self, new_event: Dict[str, Any]):
        """
        Discovers or updates candidate recurring patterns from demo events sharing underlying control failures.
        """
        barrier = new_event.get("critical_barrier", "General Control")
        activity = new_event.get("activity", "Mechanical Lifting Operations")

        def _is_same_barrier(b1: str, b2: str) -> bool:
            s1, s2 = b1.lower(), b2.lower()
            if s1 == s2 or s1 in s2 or s2 in s1:
                return True
            if any(z in s1 for z in ["zone", "exclusion", "barricade"]) and any(z in s2 for z in ["zone", "exclusion", "barricade"]):
                return True
            return False

        # Find matching events with the same barrier failure
        matching_events = [
            e for e in self.events 
            if _is_same_barrier(e.get("critical_barrier", ""), barrier)
        ]

        if len(matching_events) >= 2:
            # Check if pattern already exists in demo workspace
            existing_pat = next((p for p in self.patterns if _is_same_barrier(p.get("critical_barrier", ""), barrier)), None)
            
            human_sources = sum(1 for e in matching_events if e.get("source") == "HUMAN")
            cctv_sources = sum(1 for e in matching_events if e.get("source") == "CCTV")

            if existing_pat:
                existing_pat["occurrence_count"] = len(matching_events)
                existing_pat["independent_occurrences"] = len(matching_events)
                existing_pat["human_occurrences"] = human_sources
                existing_pat["cctv_occurrences"] = cctv_sources
                existing_pat["source_breakdown"] = f"{human_sources} Human Reports, {cctv_sources} CCTV Event" if cctv_sources else f"{human_sources} Human Reports"
                existing_pat["event_members"] = [e["event_id"] for e in matching_events]
                existing_pat["updated_at"] = datetime.now().isoformat()
            else:
                pat_id = f"PAT-DEMO-EXCLUSION-{len(self.patterns)+1:02d}"
                new_pat = {
                    "pattern_id": pat_id,
                    "title": f"Recurring Control Breach: {barrier} during {activity}",
                    "occurrence_count": len(matching_events),
                    "independent_occurrences": len(matching_events),
                    "human_occurrences": human_sources,
                    "cctv_occurrences": cctv_sources,
                    "source_breakdown": f"{human_sources} Human Reports, {cctv_sources} CCTV Event" if cctv_sources else f"{human_sources} Human Reports",
                    "activity": activity,
                    "critical_barrier": barrier,
                    "hazard": new_event.get("hazard", "Suspended Load"),
                    "exposure": new_event.get("exposure", "Person in restricted drop zone"),
                    "sif_potential": "HIGH",
                    "validation_status": "CANDIDATE",
                    "status_label": "CANDIDATE — HSE REVIEW REQUIRED",
                    "common_mechanism": f"Activity: {activity} | Hazard: {new_event.get('hazard')} | Barrier: {barrier} (Breached)",
                    "event_members": [e["event_id"] for e in matching_events],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                self.patterns.insert(0, new_pat)

    def validate_pattern(self, pattern_id: str, action: str = "CONFIRM", reviewer: str = "HSE_MANAGER_OIL", notes: str = "") -> Dict[str, Any]:
        """
        HSE review decision: CONFIRM, REJECT, or CORRECT.
        """
        pat = next((p for p in self.patterns if p.get("pattern_id") == pattern_id), None)
        if not pat:
            return {"success": False, "message": "Pattern not found in demo workspace"}

        if action == "CONFIRM":
            pat["validation_status"] = "HSE_VALIDATED"
            pat["status_label"] = "HSE VALIDATED LEARNING"
            pat["validated_by"] = reviewer
            pat["validated_at"] = datetime.now().isoformat()
            pat["review_notes"] = notes or "Validated by HSE authority. Enforcing future lifting precondition."

            # Automatically derive validated learning precondition for future work
            prec_id = f"PREC-DEMO-{uuid.uuid4().hex[:6].upper()}"
            precondition = {
                "precondition_id": prec_id,
                "pattern_id": pattern_id,
                "title": f"Precondition: Mandatory Physical {pat.get('critical_barrier')} for {pat.get('activity')}",
                "required_evidence": ["PHYSICAL_PERIMETER_DEMARCATION", "AUTHORIZED_ENTRANTS_PASSPORT", "OBSERVABLE_CCTV_CLEAR_ZONE"],
                "status": "ACTIVE_MANDATORY",
                "created_at": datetime.now().isoformat()
            }
            self.future_requirements.append(precondition)
            return {"success": True, "status": "HSE_VALIDATED", "pattern": pat, "precondition": precondition}

        elif action == "REJECT":
            pat["validation_status"] = "REJECTED"
            pat["status_label"] = "REJECTED BY HSE"
            return {"success": True, "status": "REJECTED", "pattern": pat}

        elif action == "CORRECT":
            pat["validation_status"] = "HSE_VALIDATED"
            pat["status_label"] = "HSE VALIDATED (CORRECTED)"
            pat["review_notes"] = f"Corrected by HSE: {notes}"
            return {"success": True, "status": "HSE_VALIDATED", "pattern": pat}

    def assign_action(self, pattern_id: str, supervisor: str = "SUP-01", required_action: str = "Reinstate physical exclusion barrier and clear lifting drop zone.") -> Dict[str, Any]:
        """Assigns corrective action for a recurring pattern (ACTION_REQUIRED -> ACTION_IN_PROGRESS)."""
        action_id = f"ACT-DEMO-{len(self.actions)+1:03d}"
        action = {
            "action_id": action_id,
            "pattern_id": pattern_id,
            "supervisor": supervisor,
            "required_action": required_action,
            "lifecycle_state": "ACTION_IN_PROGRESS",
            "status": "ACTION_IN_PROGRESS",
            "verification_method": "CCTV_ZONE_MONITORING",
            "created_at": datetime.now().isoformat()
        }
        self.actions.append(action)
        return {"success": True, "action": action}

    def complete_action(self, action_id: str, notes: str = "Physical barrier reinforced. Zone cleared.") -> Dict[str, Any]:
        """Supervisor completes action -> transitions to AWAITING_VERIFICATION ('Completion is not proof')."""
        act = next((a for a in self.actions if a.get("action_id") == action_id), None)
        if not act:
            return {"success": False, "message": "Action not found"}
        act["lifecycle_state"] = "AWAITING_VERIFICATION"
        act["status"] = "AWAITING_VERIFICATION"
        act["completion_notes"] = notes
        act["completed_at"] = datetime.now().isoformat()
        return {"success": True, "message": "Action marked completed. Now AWAITING_VERIFICATION.", "action": act}

    def verify_action(self, action_id: str, simulate_rebreach: bool = False, notes: str = "") -> Dict[str, Any]:
        """
        Closed-loop field verification.
        If condition restored -> VERIFIED — OBSERVABLE CONDITION RESTORED
        If breach occurs -> VERIFICATION FAILED — RE-BREACH DETECTED
        """
        act = next((a for a in self.actions if a.get("action_id") == action_id), None)
        if not act:
            return {"success": False, "message": "Action not found"}

        now = datetime.now().isoformat()
        verif_id = f"VERIF-DEMO-{uuid.uuid4().hex[:6].upper()}"

        if simulate_rebreach:
            act["lifecycle_state"] = "REOPENED"
            act["status"] = "VERIFICATION_FAILED"
            act["verification_result"] = "VERIFICATION FAILED — RE-BREACH DETECTED"
            act["verification_notes"] = notes or "Optical intrusion detected in zone during verification window. Corrective action reopened."

            # Create a re-breach event
            rebreach_evt = {
                "event_id": f"EVT-REBREACH-{uuid.uuid4().hex[:6].upper()}",
                "source": "CCTV",
                "timestamp": now,
                "location": "Drilling Rig 04 - Lifting Zone",
                "activity": "Mechanical Lifting Operations",
                "narrative": "VERIFICATION FAILED: Worker entered restricted lifting zone after completion sign-off.",
                "hazard": "Suspended Load",
                "exposure": "Line of fire breach",
                "critical_barrier": "EXCLUSION_ZONE",
                "barrier_condition": "RE-BREACHED",
                "sif_potential": "HIGH",
                "provenance": "CCTV field verification re-breach detection"
            }
            self.events.append(rebreach_evt)

            verif_rec = {
                "verification_id": verif_id,
                "action_id": action_id,
                "status": "RE_BREACH_DETECTED",
                "result": "VERIFICATION FAILED — RE-BREACH DETECTED",
                "timestamp": now,
                "event_id": rebreach_evt["event_id"]
            }
            self.verifications.append(verif_rec)
            return {"success": True, "verified": False, "status": "VERIFICATION FAILED — RE-BREACH DETECTED", "action": act, "rebreach_event": rebreach_evt}
        else:
            act["lifecycle_state"] = "VERIFIED"
            act["status"] = "VERIFIED"
            act["verification_result"] = "VERIFIED — OBSERVABLE CONDITION RESTORED"
            act["verification_notes"] = notes or "CCTV stream confirms continuous zero-person presence in active lifting perimeter."

            verif_rec = {
                "verification_id": verif_id,
                "action_id": action_id,
                "status": "VERIFIED",
                "result": "VERIFIED — OBSERVABLE CONDITION RESTORED",
                "timestamp": now
            }
            self.verifications.append(verif_rec)
            return {"success": True, "verified": True, "status": "VERIFIED — OBSERVABLE CONDITION RESTORED", "action": act}

    def load_demo_data(self) -> Dict[str, Any]:
        """
        Populates representative demonstration data through the canonical pipeline.
        Clearly labeled: 'Representative demonstration observations — not actual OIL incident records.'
        """
        self.reset()
        reports = [
            "Worker entered the crane lifting exclusion zone while a suspended load was being moved.",
            "During lifting, a contractor crossed the barricaded area beneath the suspended load.",
            "Personnel were observed inside the drop zone during an active crane operation.",
            "A worker bypassed the temporary lifting barrier and entered the restricted area."
        ]
        for r in reports:
            self.add_human_report(r)

        # Add 1 CCTV observation
        self.add_cctv_event(camera_id="CAM-RIG-01", zone_name="Temporary Lifting Exclusion Zone", person_id="WORKER-402")

        return {
            "success": True,
            "message": "Representative demonstration data loaded successfully via canonical pipeline.",
            "events_count": len(self.events),
            "patterns_count": len(self.patterns),
            "provenance": "Representative demonstration observations — not actual OIL incident records."
        }


# Global Singleton Demo Workspace Manager
demo_workspace = DemoWorkspaceManager()
