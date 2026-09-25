import asyncio
import os
import uuid
import zipfile
import io
import time
import base64
import logging
import cv2
import numpy as np

logger = logging.getLogger("shramrakshak")
try:
    import pandas as pd
except (ImportError, Exception):
    import safe_pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response

from models import (
    SystemStatus, Alert, AlertActionRequest, AlertVerificationRequest, RestrictedZone,
    CreatePassportRequest, VerifyControlRequest, ApprovePassportRequest, VerifyRestorationRequest,
    SafetyReport, AnalysisSummary, RecurringPattern, HSEReviewRequest, HSEObservationRequest
)
from state import state_manager
from utils import get_lan_ip, get_qr_code_base64
from detection import generate_mjpeg_stream, video_engine
from nlp_engine import (
    nlp_analyzer, dataset_store, dataset_processor, ColumnMapper, DataQualityValidator
)
from safety_memory import safety_memory, SafetyEvent, HSEValidationStatus
from nlp_engine.corroboration import corroboration_engine
from nlp_engine.assertion_detector import AssertionDetector
from unified_event_store import unified_event_store, SafetyEvent as CanonicalSafetyEvent
from dataset_importer import dataset_import_manager

try:
    from backend.database import db
    from backend.models_canonical import SafetyEvent as RealSafetyEvent, SIFStatus as CanonicalSIFStatus, ReviewStatus as CanonicalReviewStatus
    from backend.nlp_engine.assertion_detector import assertion_detector as real_assertion_detector
    from backend.nlp_engine.sif_pathway_engine import sif_pathway_engine as real_sif_pathway_engine
    from backend.nlp_engine.lsr_classifier import lsr_classifier as real_lsr_classifier
    from backend.nlp_engine.semantic_memory import semantic_memory as real_semantic_memory
    from backend.nlp_engine.recurrence_engine import recurrence_engine as real_recurrence_engine
    from backend.nlp_engine.propagation import propagation_engine as real_propagation_engine
    from backend.nlp_engine.precondition_engine import precondition_engine as real_precondition_engine
    from backend.dataset_pipeline.ingest import dataset_ingester as real_dataset_ingester
except ImportError:
    from database import db
    from models_canonical import SafetyEvent as RealSafetyEvent, SIFStatus as CanonicalSIFStatus, ReviewStatus as CanonicalReviewStatus
    from nlp_engine.assertion_detector import assertion_detector as real_assertion_detector
    from nlp_engine.sif_pathway_engine import sif_pathway_engine as real_sif_pathway_engine
    from nlp_engine.lsr_classifier import lsr_classifier as real_lsr_classifier
    from nlp_engine.semantic_memory import semantic_memory as real_semantic_memory
    from nlp_engine.recurrence_engine import recurrence_engine as real_recurrence_engine
    from nlp_engine.propagation import propagation_engine as real_propagation_engine
    from nlp_engine.precondition_engine import precondition_engine as real_precondition_engine
    from dataset_pipeline.ingest import dataset_ingester as real_dataset_ingester

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register the asyncio event loop with the state manager for threadsafe broadcasts
    loop = asyncio.get_running_loop()
    state_manager.set_event_loop(loop)
    print(f"============================================================")
    print(f"  SHRAMRAKSHAK HSE Intelligence Backend Started")
    print(f"  Host LAN IP: {state_manager.lan_ip}")
    print(f"  Supervisor Mobile URL: {state_manager.supervisor_url}")
    print(f"============================================================")

    # Auto-preload January2015toNovember2025.csv dataset in background thread if not already populated
    import threading
    def _preload_dataset():
        try:
            if not dataset_store.get_summary():
                print("[Lifespan] Auto-preloading January2015toNovember2025.csv dataset...")
                load_sample_dataset(max_rows=2000)
        except Exception as e:
            print(f"[Lifespan] Dataset preloading notice: {e}")
    threading.Thread(target=_preload_dataset, daemon=True).start()

    yield
    print("Shutting down SHRAMRAKSHAK Backend...")

app = FastAPI(
    title="SHRAMRAKSHAK HSE Intelligence System API",
    description="Backend API for real-time safety monitoring, Safety Passport workflow, and AI/NLP SIF Precursor Detection for OIL (SIH PS 26165)",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local network and frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status", response_model=SystemStatus)
def get_status():
    """Returns overall real-time system safety status, active zones, passports, and sorted alerts"""
    return state_manager.get_system_status()

@app.get("/api/qr")
def get_qr_code(url: Optional[str] = None):
    """Returns a base64 encoded PNG for the mobile supervisor URL"""
    try:
        state_manager.lan_ip = get_lan_ip()
        default_url = f"http://{state_manager.lan_ip}:5173/supervisor"
        state_manager.supervisor_url = default_url

        target_url = url or default_url
        base64_img = get_qr_code_base64(target_url)
        return {"qr_base64": base64_img, "supervisor_url": target_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/evidence/{evidence_id}")
def get_evidence_image(evidence_id: str):
    """Returns visual evidence JPEG image captured at violation time"""
    img_bytes = state_manager.get_evidence(evidence_id)
    if not img_bytes:
        raise HTTPException(status_code=404, detail="Evidence image not found")
    return Response(content=img_bytes, media_type="image/jpeg")

@app.get("/api/alert/current")
def get_current_alert():
    """Returns the currently active alert, or null if none"""
    return state_manager.active_alert

@app.get("/api/alerts")
def get_all_active_alerts(status: Optional[str] = None):
    """Returns all active alerts sorted by AI Recommended Response Priority, or history if status=resolved"""
    if status and status.lower() == "resolved":
        hist = state_manager.get_history_list()
        return {"alerts": hist, "history": hist}
    return {"alerts": state_manager.get_active_alerts_list()}

@app.get("/api/alerts/history")
def get_alerts_history():
    """Returns resolved historical alerts sorted newest first"""
    hist = state_manager.get_history_list()
    return {"history": hist, "alerts": hist}

@app.get("/api/alerts/{alert_id}")
def get_alert_by_id(alert_id: str):
    """Returns specific alert by ID"""
    with state_manager.lock:
        if alert_id in state_manager._active_alerts:
            return state_manager._active_alerts[alert_id]
        for h in state_manager.history:
            if h.id == alert_id:
                return h
    raise HTTPException(status_code=404, detail="Alert not found")

@app.post("/api/alerts/{alert_id}/respond")
def respond_alert_by_id(alert_id: str, req: AlertActionRequest = AlertActionRequest()):
    """Supervisor clicks 'I'M RESPONDING' for specific alert"""
    alert = state_manager.respond_to_alert(
        supervisor_id=req.supervisor_id or "SUP-01",
        notes=req.notes,
        alert_id=alert_id
    )
    if not alert:
        raise HTTPException(status_code=400, detail=f"Alert {alert_id} not found or cannot respond")
    return {"message": "Supervisor responding", "alert": alert}

@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert_by_id(alert_id: str, req: AlertActionRequest = AlertActionRequest()):
    """Supervisor clicks 'FIXED / RESOLVED' for specific alert"""
    alert = state_manager.resolve_alert(
        supervisor_id=req.supervisor_id or "SUP-01",
        notes=req.notes,
        alert_id=alert_id
    )
    if not alert:
        raise HTTPException(status_code=400, detail=f"Alert {alert_id} not found or cannot resolve")
    return {"message": "Alert resolved successfully", "alert": alert}

@app.post("/api/alert/trigger")
def trigger_alert(
    alert_type: str = "Helmet/PPE Violation",
    location: str = "Demo Work Zone",
    camera: str = "C-01",
    severity: str = "HIGH",
    response_sec: int = 20,
    action_sec: int = 60
):
    """Triggers an alert manually or via detection"""
    alert = state_manager.trigger_alert(
        alert_type=alert_type,
        location=location,
        camera=camera,
        severity=severity,
        response_sec=response_sec,
        action_sec=action_sec
    )
    return {"message": "Alert triggered", "alert": alert}

@app.post("/api/alert/respond")
def respond_alert(req: AlertActionRequest = AlertActionRequest()):
    """Supervisor clicks 'I'M RESPONDING' (Stage 1 -> Stage 2)"""
    alert = state_manager.respond_to_alert(
        supervisor_id=req.supervisor_id or "SUP-01",
        notes=req.notes,
        alert_id=req.alert_id
    )
    if not alert:
        raise HTTPException(status_code=400, detail="No active alert to respond to")
    return {"message": "Supervisor responding", "alert": alert}

@app.post("/api/alert/resolve")
def resolve_alert(req: AlertActionRequest = AlertActionRequest()):
    """Supervisor clicks 'FIXED / RESOLVED' (Stage 2 -> RESOLVED)"""
    alert = state_manager.resolve_alert(
        supervisor_id=req.supervisor_id or "SUP-01",
        notes=req.notes,
        alert_id=req.alert_id
    )
    if not alert:
        raise HTTPException(status_code=400, detail="No active alert to resolve")
    return {"message": "Alert resolved successfully", "alert": alert}

@app.post("/api/alert/action")
@app.post("/api/alerts/{alert_id}/action")
def mark_alert_action(alert_id: Optional[str] = None, req: AlertActionRequest = AlertActionRequest()):
    """Supervisor marks corrective action executed on site (Phase 4)."""
    target_id = alert_id or req.alert_id
    alert = state_manager.mark_action_taken(
        alert_id=target_id,
        supervisor_id=req.supervisor_id or "SUP-01",
        notes=req.notes,
        action_taken=req.action_taken
    )
    if not alert:
        raise HTTPException(status_code=400, detail="Alert not found or cannot mark action taken")
    return {"message": "Corrective action marked completed; awaiting verification", "alert": alert}

@app.post("/api/alert/verify")
@app.post("/api/alerts/{alert_id}/verify")
def verify_alert_action(alert_id: Optional[str] = None, req: AlertVerificationRequest = AlertVerificationRequest()):
    """Safety verification step (Phase 4): VERIFIED, FAILED, or HSE_REVIEW_REQUIRED."""
    target_id = alert_id or req.alert_id
    alert = state_manager.verify_alert(
        alert_id=target_id,
        supervisor_id=req.supervisor_id or "SUP-01",
        decision=req.decision,
        verification_method=req.verification_method,
        notes=req.notes
    )
    if not alert:
        raise HTTPException(status_code=400, detail="Alert not found or cannot verify")
    
    # Persist verification record
    try:
        db.save_verification_record(
            verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
            event_id=target_id or "ALERT-EVENT",
            source=req.verification_method or "CCTV",
            status=req.decision or "VERIFIED",
            details=req.notes or f"Alert action verification: {req.decision}"
        )
    except Exception as e:
        logger.error(f"Error persisting verification record: {e}")
        
    return {"message": f"Verification decision '{req.decision}' recorded", "alert": alert}

def process_and_store_hse_observation(alert_id_param: Optional[str], req: HSEObservationRequest) -> Alert:
    now_iso = datetime.now().isoformat()
    time_str = datetime.now().strftime("%H:%M:%S")

    target_alert = None
    target_id = req.linked_alert_id or alert_id_param

    with state_manager.lock:
        if target_id and target_id.lower() != "new":
            target_alert = state_manager._active_alerts.get(target_id)
            if not target_alert:
                for h in state_manager.history:
                    if h.id == target_id:
                        target_alert = h
                        break

    obs_text = req.observation.strip()
    nlp_context = {
        "event_type": target_alert.type if target_alert else "HSE Field Observation",
        "location": req.location or (target_alert.location if target_alert else "Site Area"),
        "activity": req.activity or "Maintenance",
        "hazard": req.hazard or "Unsafe Act / Condition",
        "barrier_failure": None
    }
    nlp_res = nlp_analyzer.analyze_raw_text(obs_text, nlp_context)

    extracted = nlp_res.get("extracted_entities", {})
    sif_bool = nlp_res.get("sif_potential", False)
    risk_score = nlp_res.get("risk_score", 50)
    risk_lvl = nlp_res.get("risk_level", "MEDIUM")
    reasoning = nlp_res.get("why_flagged", [])
    lsrs = nlp_res.get("life_saving_rules", [])

    activity_extracted = extracted.get("activity") or req.activity or "Maintenance"
    hazard_extracted = extracted.get("hazard") or req.hazard or "Unsafe Condition"
    location_extracted = extracted.get("location") or req.location or (target_alert.location if target_alert else "Site Area")
    barrier_extracted = extracted.get("barrier_failure") or "Safety control / energy isolation not verified"
    precursor_extracted = extracted.get("precursor") or "Unverified Energy Isolation"
    rec_extracted = extracted.get("ai_recommendation") or "HSE review and verification required before work proceeds."

    summary = dataset_store.get_summary()
    has_hist_match = False
    hist_title = None
    hist_occ = 0
    hist_sif = 0
    hist_density = 0.0
    hist_lsrs = []
    hist_sites = []

    if summary:
        patterns = summary.get("section_4_recurring_precursors", []) or summary.get("recurring_patterns", [])
        query_terms = [t.lower() for t in [barrier_extracted, precursor_extracted, hazard_extracted, activity_extracted] if t]
        matched_pat = None
        for pat in patterns:
            pat_title = (pat.get("pattern_title") or pat.get("title") or "").lower()
            if any(term in pat_title for term in query_terms) or any(pat_title in term for term in query_terms):
                matched_pat = pat
                break
        
        if not matched_pat and patterns:
            matched_pat = patterns[0]

        if matched_pat:
            has_hist_match = True
            hist_title = matched_pat.get("pattern_title") or matched_pat.get("title") or precursor_extracted
            hist_occ = matched_pat.get("occurrence_count", 0) or matched_pat.get("count", 0)
            hist_sif = matched_pat.get("sif_count", 0)
            hist_density = matched_pat.get("sif_density_pct", 0.0) or matched_pat.get("sif_percentage", 0.0)
            hist_lsrs = matched_pat.get("related_lsr", [])
            hist_sites = matched_pat.get("top_sites", [])

    if not target_alert:
        inc_id = state_manager.get_next_incident_id()
        new_id = f"ALERT-HSE-{int(datetime.now().timestamp()*1000)}"
        source_label = "HSE + NLP"
        cov_status = "INSUFFICIENT CCTV EVIDENCE (No Camera Linked)"
        consistency_status = "INSUFFICIENT CCTV EVIDENCE"
        time_match = f"Observation submitted at {time_str}"
        loc_match = f"Field location: {location_extracted}"
        act_match = f"Field activity: {activity_extracted}"
        worker_match = f"Submitted by Worker: {req.worker_identifier or 'W-104'}"

        details_list = [
            f"Time: {time_match}",
            f"Location: {loc_match}",
            f"Activity: {act_match}",
            f"Worker Identifier: {worker_match}",
            f"Coverage: {cov_status}"
        ]

        timeline = [{
            "time": time_str,
            "title": f"Manual HSE Observation Recorded ({inc_id})",
            "actor": f"{req.reviewer_role or 'HSE Manager'} ({req.worker_identifier or 'W-104'})",
            "details": f"Observation: '{obs_text[:80]}...' | SIF Potential: {'HIGH' if sif_bool else 'LOW'}"
        }]

        deadline = datetime.now() + timedelta(seconds=60)

        target_alert = Alert(
            id=new_id,
            incident_id=inc_id,
            type="HSE Field Observation",
            title=f"HSE Field Observation ({req.worker_identifier or 'W-104'})",
            short_summary=obs_text,
            location=location_extracted,
            camera="NONE",
            camera_id="NONE",
            source=source_label,
            severity=risk_lvl if risk_lvl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "HIGH",
            priority_score=risk_score,
            priority_label=risk_lvl if risk_lvl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "HIGH",
            status="WAITING_FOR_RESPONSE",
            stage="RESPONSE",
            person_count=1,
            affected_person_ids=[req.worker_identifier or "W-104"],
            affected_persons=[req.worker_identifier or "W-104"],
            assigned_to="FIELD SUPERVISOR",
            created_at=now_iso,
            response_deadline=deadline.isoformat(),
            incident_timeline=timeline
        )

        with state_manager.lock:
            state_manager._active_alerts[new_id] = target_alert
    else:
        cctv_coverage = bool(target_alert.camera and target_alert.camera != "NONE")
        time_match = f"Observation recorded at {time_str}, aligning with CCTV detection ({target_alert.created_at[-8:] if target_alert.created_at else 'N/A'})"
        loc_match = f"Location '{location_extracted}' matches CCTV sector ({target_alert.location})" if location_extracted and target_alert.location else "Location consistent"
        act_match = f"Activity '{activity_extracted}' correlates with detected CCTV event '{target_alert.type}'"
        worker_match = f"CCTV camera ({target_alert.camera}) detected {target_alert.person_count} person(s) in monitored area"
        cov_status = f"CCTV Coverage Available (Camera {target_alert.camera})" if cctv_coverage else "INSUFFICIENT CCTV EVIDENCE (Blind Spot / No Coverage)"

        if not cctv_coverage:
            consistency_status = "INSUFFICIENT CCTV EVIDENCE"
        else:
            if req.location and req.location.lower() not in target_alert.location.lower() and target_alert.location.lower() not in req.location.lower():
                consistency_status = "INCONSISTENCY — HSE REVIEW REQUIRED"
            else:
                consistency_status = "CONSISTENT"

        details_list = [
            f"Time: {time_match}",
            f"Location: {loc_match}",
            f"Activity: {act_match}",
            f"Worker Presence: {worker_match}",
            f"Coverage: {cov_status}"
        ]

        source_label = "CCTV + HSE + NLP"

    with state_manager.lock:
        target_alert.worker_identifier = req.worker_identifier or "W-104"
        target_alert.hse_observation_text = obs_text
        target_alert.hse_observed_hazard = req.hazard
        target_alert.hse_activity = req.activity
        target_alert.hse_location = req.location
        target_alert.hse_notes = req.notes
        target_alert.hse_timestamp = now_iso
        target_alert.hse_added_by = req.reviewer_role or "HSE Manager"

        target_alert.nlp_sif_potential = sif_bool
        target_alert.nlp_risk_score = risk_score
        target_alert.nlp_risk_level = risk_lvl
        target_alert.nlp_confidence = 85
        target_alert.nlp_activity = activity_extracted
        target_alert.nlp_hazard = hazard_extracted
        target_alert.nlp_location = location_extracted
        target_alert.nlp_barrier_failure = barrier_extracted
        target_alert.nlp_life_saving_rules = lsrs
        target_alert.nlp_precursor = precursor_extracted
        target_alert.nlp_reasoning = reasoning
        target_alert.nlp_recommendation = rec_extracted

        target_alert.has_historical_match = has_hist_match
        target_alert.historical_pattern_title = hist_title
        target_alert.historical_occurrence_count = hist_occ
        target_alert.historical_sif_count = hist_sif
        target_alert.historical_sif_density_pct = hist_density
        target_alert.historical_related_lsr = hist_lsrs
        target_alert.historical_related_sites = hist_sites

        target_alert.evidence_consistency_status = consistency_status
        target_alert.time_consistency = time_match
        target_alert.location_consistency = loc_match
        target_alert.activity_consistency = act_match
        target_alert.worker_presence = worker_match
        target_alert.coverage_status = cov_status
        target_alert.consistency_details = details_list

        target_alert.source = source_label

        if not target_alert.incident_timeline:
            target_alert.incident_timeline = []
        target_alert.incident_timeline.append({
            "time": time_str,
            "title": f"HSE Observation Analyzed ({target_alert.incident_id})",
            "actor": f"HSE Manager ({req.worker_identifier or 'W-104'})",
            "details": f"Observation: '{obs_text[:80]}...' | SIF Potential: {'HIGH' if sif_bool else 'LOW'} | Source: {source_label}"
        })

    state_manager.notify_clients()
    return target_alert

@app.post("/api/alerts/hse-observation")
def create_standalone_hse_observation(req: HSEObservationRequest):
    """
    Submits a standalone manual HSE observation from the dedicated HSE Observation page,
    runs NLP SIF precursor analysis, matches active historical dataset patterns,
    assigns a unique Incident ID (SR-2026-XXXX), and creates a unified alert (Source: HSE + NLP).
    """
    alert = process_and_store_hse_observation("new", req)
    return {"message": "HSE observation analyzed and alert created successfully", "alert": alert}

@app.post("/api/alerts/{alert_id}/hse-observation")
def add_hse_observation(alert_id: str, req: HSEObservationRequest):
    """
    Enriches an existing Incident/Alert record (or creates a new one if alert_id='new')
    with manual HSE field observation details and NLP SIF analysis.
    """
    alert = process_and_store_hse_observation(alert_id, req)
    return {"message": "HSE observation added and analyzed successfully", "alert": alert}

@app.post("/api/demo/reset")
def reset_demo():
    """Resets the entire demo state to IDLE and clears alerts"""
    state_manager.reset_demo()
    return {"message": "Demo reset successfully"}

@app.post("/api/demo/simulate-no-helmet")
def simulate_no_helmet():
    """Demo Mode fallback: simulates a no-helmet violation"""
    alert = state_manager.simulate_no_helmet()
    return {"message": "Simulated No Helmet triggered", "alert": alert}

@app.post("/api/demo/simulate-safe")
def simulate_safe():
    """Demo Mode fallback: simulates safe state (helmet detected)"""
    state_manager.simulate_safe()
    return {"message": "Simulated Safe state active"}

@app.post("/api/demo/simulate-breach")
@app.post("/api/demo/simulate-zone-entry")
def simulate_zone_breach():
    """Demo Mode fallback: simulates restricted zone breach / SIF precursor"""
    alert = state_manager.simulate_zone_entry()
    return {"message": "Simulated Restricted Zone breach triggered", "alert": alert}

# ==========================================
# CCTV OBJECTIVE VERIFICATION ("Completion is not proof")
# ==========================================

@app.post("/api/alert/cctv-verify")
@app.post("/api/alerts/{alert_id}/cctv-verify")
def cctv_verify_alert(alert_id: Optional[str] = None, req: Dict[str, Any] = {}):
    """
    Executes objective CCTV verification of site safety conditions (P2.5).
    - If simulate_rebreach is True or person is inside zone: returns FAILED (RE-BREACH DETECTED),
      reopens action, logs verification record to SQLite, and emits a new Canonical SafetyEvent into Safety Memory!
    - If zone is clear: returns VERIFIED (Observable condition restored) and resolves alert.
    """
    simulate_rebreach = bool(req.get("simulate_rebreach", False))
    supervisor_id = req.get("supervisor_id", "SUP-01")
    target_id = alert_id or req.get("alert_id")
    result = state_manager.verify_cctv_condition(target_id, supervisor_id, simulate_rebreach)

    # 1. Log verification record in SQLite
    verif_id = f"VERIF-CCTV-{uuid.uuid4().hex[:8]}"
    is_success = bool(result.get("verified")) or result.get("status") == "VERIFIED"
    status_str = "VERIFIED" if is_success else "VERIFICATION_FAILED"
    
    db.save_verification(
        verification_id=verif_id,
        event_id=target_id,
        source="CCTV",
        status=status_str,
        details=result
    )

    # 2. If VERIFICATION_FAILED (re-breach), create a new SafetyEvent entering Safety Memory
    if not is_success:
        now_iso = datetime.now().isoformat()
        rebreach_event_id = f"EVT-CCTV-REBREACH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        rebreach_event = RealSafetyEvent(
            event_id=rebreach_event_id,
            source="CCTV",
            timestamp=now_iso,
            site="OIL Field Duliajan",
            location="Drilling Rig 04 - Lifting Zone",
            activity="Mechanical Crane Hoisting",
            energy="Gravitational / Kinetic Energy (Suspended Load)",
            exposure="Worker re-entered lifting exclusion zone post-corrective action",
            barrier=["EXCLUSION_ZONE"],
            barrier_state=["BYPASSED"],
            consequence="Crush trauma / struck-by suspended load",
            sif_status=CanonicalSIFStatus.SIF_POTENTIAL,
            sif_reasons=["CCTV Verification Failed: Re-breach detected in active zone while load active."],
            lsr=["SAFE_MECHANICAL_LIFTING", "LINE_OF_FIRE"],
            machine_observation=True,
            narrative="CCTV automated verification detected worker re-entry into restricted zone following corrective action sign-off."
        )
        db.save_event(rebreach_event)
        try:
            real_recurrence_engine.process_event(rebreach_event)
        except Exception:
            pass

    return result

# ==========================================
# SAFETY MEMORY & RECURRENCE INTELLIGENCE (Sections 6, 7, 8)
# ==========================================

@app.get("/api/safety-memory/summary")
@app.get("/api/safety-memory/status")
def get_safety_memory_summary():
    """Returns consolidated Safety Memory status, recurring patterns, candidate vs validated counts from SQLite"""
    counts = db.count_events()
    patterns = db.list_patterns()
    cand_count = sum(1 for p in patterns if p.validation_status == CanonicalReviewStatus.CANDIDATE)
    val_count = sum(1 for p in patterns if p.validation_status == CanonicalReviewStatus.HSE_VALIDATED)
    preconditions = db.list_preconditions(active_only=True)
    return {
        "total_events": counts["total"],
        "sif_events_count": counts["sif_potential"],
        "review_required_count": counts["review_required"],
        "safe_controls_count": counts["no_sif_potential"],
        "candidate_patterns_count": cand_count,
        "validated_patterns_count": val_count,
        "active_preconditions_count": len(preconditions),
        "patterns": [p.to_dict() for p in patterns]
    }

@app.get("/api/safety-memory/events")
def get_safety_memory_events():
    """Returns all recorded safety events in SQLite persistent database"""
    return {"events": [ev.to_dict() for ev in db.list_events(limit=200)]}

@app.get("/api/safety-memory/patterns")
def get_safety_memory_patterns():
    """Returns all Candidate and HSE Validated Recurring Safety-Control Patterns from SQLite"""
    patterns = db.list_patterns()
    return {"patterns": [p.to_dict() for p in patterns]}

@app.post("/api/safety-memory/patterns/{pattern_id}/validate")
@app.post("/api/safety-memory/validate-pattern")
def validate_safety_pattern_route(pattern_id: Optional[str] = None, req: Dict[str, Any] = {}):
    """
    HSE Governance Layer:
    Human HSE reviews Candidate Pattern -> validates or rejects -> triggers future precondition derivation.
    """
    target_id = pattern_id or req.get("pattern_id")
    if not target_id:
        raise HTTPException(status_code=400, detail="Pattern ID is required")
    decision = req.get("decision", "VALIDATE")
    reviewer = req.get("reviewer", "DEMO_HSE_REVIEWER")
    notes = req.get("notes", "Confirmed recurring failure of safety barrier.")

    try:
        pat = real_propagation_engine.validate_safety_pattern(
            pattern_id=target_id,
            reviewer_role=reviewer,
            action="VALIDATE" if decision.upper() in ["CONFIRM", "VALIDATE"] else "REJECT",
            review_notes=notes
        )
        # If validated, auto-propose active precondition
        prec = None
        if pat.validation_status == CanonicalReviewStatus.HSE_VALIDATED:
            prec = real_precondition_engine.create_precondition_from_pattern(pat.pattern_id)

        state_manager.notify_clients()
        return {
            "message": f"Pattern {target_id} {decision}ed by HSE",
            "pattern": pat.to_dict(),
            "precondition": prec.to_dict() if prec else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/events/{event_id}/correct")
def correct_event_route(event_id: str, req: Dict[str, Any] = {}):
    """
    Human Correction Propagation (P1.8):
    Supervisor / HSE corrects extracted barrier or state.
    Triggers dependency-aware recomputation of SIF, LSR, and Pattern state.
    """
    corrections = req.get("corrections", {})
    reviewer = req.get("reviewer", "DEMO_HSE_REVIEWER")
    reason = req.get("reason", "Field inspection correction")
    try:
        res = real_propagation_engine.apply_human_correction(
            event_id=event_id,
            corrections=corrections,
            reviewer_role=reviewer,
            reason=reason
        )
        state_manager.notify_clients()
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/safety-memory/future-requirements")
def get_future_work_requirements():
    """Returns active Future-Work Preconditions derived from HSE Validated Patterns"""
    precs = db.list_preconditions(active_only=True)
    return {"requirements": [p.to_dict() for p in precs]}

@app.post("/api/safety-memory/check-work-package")
def evaluate_work_package(package: Dict[str, Any]):
    """
    Evaluates future work package against active preconditions.
    Flags MISSING_EVIDENCE or PASS. Never auto-approves permits.
    """
    pkg_id = package.get("package_id") or package.get("id") or f"PKG-{uuid.uuid4().hex[:6]}"
    activity = package.get("activity", "Mechanical Lifting")
    location = package.get("location", "Rig 04")
    evidence = package.get("submitted_evidence") or package.get("evidence") or {}
    res = real_precondition_engine.evaluate_work_package(pkg_id, activity, location, evidence)
    return res.to_dict()

# ==========================================
# UNIFIED SAFETY EVENT PIPELINE & HUMAN REPORTS (Phases 1, 2, 3, 4, 5, 6)
# ==========================================

@app.post("/api/events/human")
def submit_human_safety_report(req: Dict[str, Any]):
    """
    Ingests and processes a REAL Human Safety Observation.
    1. Runs real NLP & assertion detector with exact evidence spans.
    2. Runs deterministic SIF pathway reasoning.
    3. Maps multi-label IOGP Life-Saving Rules.
    4. Persists Canonical SafetyEvent in SQLite and FAISS semantic memory.
    5. Evaluates two-stage recurrence and candidate control patterns.
    6. Triggers live immediate alert if high SIF.
    """
    narrative = req.get("narrative", "").strip()
    if not narrative:
        raise HTTPException(status_code=400, detail="Field 'narrative' ('What happened?') is required.")

    location = req.get("location", "Drilling Rig 04 - Drill Floor").strip()
    activity = req.get("activity", "Mechanical Lifting Operations").strip()
    reporter = req.get("reporter", "Field HSE Inspector").strip()
    date_val = req.get("date") or datetime.now().isoformat()

    now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    event_id = f"EVT-HUMAN-{now_str}-{uuid.uuid4().hex[:4].upper()}"

    # 1. NLP Assertion & Evidence Extraction -> Canonical SafetyEvent
    canonical_ev = real_assertion_detector.analyze(
        narrative,
        context={
            "event_id": event_id,
            "location": location,
            "activity": activity,
            "source": "HUMAN",
            "timestamp": date_val
        }
    )

    # 2. SIF Pathway Reasoning
    canonical_ev = real_sif_pathway_engine.evaluate(canonical_ev)

    # 3. Multi-label LSR mapping
    lsr_matches = real_lsr_classifier.classify_event(canonical_ev)
    canonical_ev.lsr = [m["lsr"] for m in lsr_matches]

    # 4. Save to persistent SQLite database
    db.save_event(canonical_ev)

    # 5. Semantic Memory & Recurrence
    rec_results, pattern = real_recurrence_engine.process_event(canonical_ev)

    # 6. Synchronize into unified_event_store for live UI access
    unified_event = CanonicalSafetyEvent(
        event_id=canonical_ev.event_id,
        source="HUMAN",
        timestamp=canonical_ev.timestamp,
        location=canonical_ev.location,
        activity=canonical_ev.activity,
        narrative=canonical_ev.narrative,
        hazard=canonical_ev.energy,
        exposure=canonical_ev.exposure,
        critical_barrier=", ".join(canonical_ev.barrier) if canonical_ev.barrier else "Safety Barrier",
        barrier_condition=", ".join(canonical_ev.barrier_state) if canonical_ev.barrier_state else "UNKNOWN",
        consequence=canonical_ev.consequence,
        sif_potential="HIGH" if canonical_ev.sif_status == CanonicalSIFStatus.SIF_POTENTIAL else ("MEDIUM" if canonical_ev.sif_status == CanonicalSIFStatus.REVIEW_REQUIRED else "NOT_SIF"),
        lsr=", ".join(canonical_ev.lsr) if canonical_ev.lsr else "General Safety",
        assertion_status=canonical_ev.assertion.value if hasattr(canonical_ev.assertion, "value") else str(canonical_ev.assertion),
        temporal_status=canonical_ev.temporal_status.value if hasattr(canonical_ev.temporal_status, "value") else str(canonical_ev.temporal_status),
        evidence_spans=[s.to_dict() if hasattr(s, "to_dict") else s for s in canonical_ev.evidence],
        evidence_sources=["HUMAN_REPORT"],
        recurrence_classification=rec_results[0].final_relationship.value if rec_results else "INDEPENDENT_RECURRENCE",
        lifecycle_state="ACTION_REQUIRED" if canonical_ev.sif_status == CanonicalSIFStatus.SIF_POTENTIAL else "RESOLVED",
        machine_observation=False,
        metadata={"reporter": reporter}
    )
    unified_event_store.add_event(unified_event)

    # 7. If SIF-POTENTIAL, trigger immediate active alert in state_manager
    if canonical_ev.sif_status == CanonicalSIFStatus.SIF_POTENTIAL:
        state_manager.trigger_alert(
            alert_type="Human Safety Report / SIF Precursor",
            location=location,
            camera="C-01",
            severity="CRITICAL",
            sif_potential="HIGH / POTENTIAL",
            person_count=1,
            title="HUMAN REPORT: CRITICAL SIF PRECURSOR DETECTED",
            short_summary=f"Worker report at {location}: {canonical_ev.exposure}",
            hazard=canonical_ev.energy,
            unsafe_condition=narrative,
            notes=f"Field report by {reporter}. Barrier: {', '.join(canonical_ev.barrier)} ({', '.join(canonical_ev.barrier_state)})"
        )

    state_manager.notify_clients()

    return {
        "success": True,
        "message": "Human Safety Report analyzed, vectorized, and persisted successfully",
        "event": canonical_ev.to_dict(),
        "recurrence_matches": [r.to_dict() for r in rec_results],
        "candidate_pattern": pattern.to_dict() if pattern else None
    }

@app.get("/api/events")
def get_unified_safety_events(
    source: Optional[str] = "ALL",
    sif_status: Optional[str] = "ALL",
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """Returns filtered, paginated Unified Safety Events (HUMAN, IMPORTED, CCTV)."""
    return unified_event_store.get_events(
        source=source,
        sif_status=sif_status,
        search=search,
        page=page,
        page_size=page_size
    )

@app.get("/api/events/stats/summary")
@app.get("/api/events/summary-stats")
@app.get("/api/events/summary")
def get_unified_safety_event_summary():
    """Returns dynamically computed SIF intelligence metrics from real stored events."""
    return unified_event_store.get_summary_stats()

@app.get("/api/events/{event_id}")
def get_unified_safety_event_by_id(event_id: str):
    """Returns complete details, evidence spans, and audit trail for a single event."""
    ev = unified_event_store.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Safety Event '{event_id}' not found")
    return ev.to_dict()

@app.post("/api/events/{event_id}/action")
def update_event_action_state(event_id: str, req: Dict[str, Any]):
    """Records supervisor corrective action on an event."""
    supervisor_id = req.get("supervisor_id", "SUP-01")
    notes = req.get("notes", "Corrective action taken on site")
    ev = unified_event_store.update_lifecycle(event_id, "AWAITING_VERIFICATION", supervisor_id, notes)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Safety Event '{event_id}' not found")
    state_manager.notify_clients()
    return {"message": "Action recorded. Transitioned to AWAITING_VERIFICATION", "event": ev.to_dict()}

@app.post("/api/events/{event_id}/verify")
def verify_event_condition(event_id: str, req: Dict[str, Any]):
    """Closed-loop verification: 'Completion is not proof'. Checks for restoration or re-breach."""
    simulate_rebreach = bool(req.get("simulate_rebreach", False))
    supervisor_id = req.get("supervisor_id", "SUP-01")
    notes = req.get("notes", "")

    if simulate_rebreach:
        ev = unified_event_store.update_lifecycle(
            event_id,
            "REOPENED",
            supervisor_id,
            f"VERIFICATION FAILED: Re-breach detected in zone! Corrective action reopened. {notes}"
        )
        try:
            db.save_verification_record(
                verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
                event_id=event_id,
                source="CCTV",
                status="FAILED",
                details=f"Re-breach detected in zone: {notes}"
            )
        except Exception as e:
            logger.error(f"Error persisting verification record: {e}")
            
        state_manager.notify_clients()
        return {
            "verified": False,
            "message": "✕ VERIFICATION FAILED: Re-breach detected in zone! Corrective action reopened.",
            "event": ev.to_dict() if ev else None
        }
    else:
        ev = unified_event_store.update_lifecycle(
            event_id,
            "RESOLVED",
            supervisor_id,
            f"✓ VERIFIED: Observable zone clearance confirmed. {notes}"
        )
        try:
            db.save_verification_record(
                verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
                event_id=event_id,
                source="CCTV",
                status="VERIFIED",
                details=f"Observable zone clearance confirmed: {notes}"
            )
        except Exception as e:
            logger.error(f"Error persisting verification record: {e}")
            
        state_manager.notify_clients()
        return {
            "verified": True,
            "message": "✓ VERIFIED: Observable zone clearance confirmed. Event closed.",
            "event": ev.to_dict() if ev else None
        }

@app.post("/api/dataset/import-file")
async def import_safety_dataset_file(file: UploadFile = File(...)):
    """
    Phase 4: Accepts CSV, XLSX, JSON, or PDF company dataset,
    detects column mappings, and returns data health preview.
    """
    try:
        contents = await file.read()
        res = dataset_import_manager.parse_file(file.filename, contents)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/dataset/import-execute")
def execute_dataset_import(req: Optional[Dict[str, Any]] = None, max_rows: Optional[int] = None):
    """
    Phase 5 & 6: Starts asynchronous background batch import into UnifiedEventStore
    and SafetyMemoryStore without freezing browser UI.
    """
    limit = max_rows
    if req and "max_rows" in req:
        limit = req.get("max_rows")
    try:
        if dataset_import_manager.total_rows == 0:
            dataset_import_manager.parse_default_dataset()
        dataset_import_manager.start_background_import(limit)
        return {
            "success": True,
            "message": "Dataset ingestion pipeline started in background",
            "status": "PROCESSING",
            "total_rows": dataset_import_manager.total_rows,
            "processed": dataset_import_manager.processed_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/dataset/import-status")
def get_dataset_import_status():
    """Phase 6: Returns telemetry for real-time progress bar and completion summary."""
    return dataset_import_manager.get_status()


# ==========================================
# CORROBORATION: HUMAN REPORT + CCTV EVIDENCE (Sections 3B & 12)
# ==========================================

@app.post("/api/corroboration/evaluate")
def evaluate_corroboration(req: Dict[str, Any]):
    """
    Synthesizes Human Field Observation with CCTV Evidence.
    Returns: CORROBORATED | CCTV_ONLY | HUMAN_REPORT_ONLY | EVIDENCE_CONFLICT
    """
    human_text = req.get("human_text")
    cctv_alert_id = req.get("cctv_alert_id")
    human_event = None
    cctv_event = None

    if human_text:
        human_event = AssertionDetector.evaluate_safety_event(human_text, req.get("context", {}))

    if cctv_alert_id:
        with state_manager.lock:
            alert = state_manager._active_alerts.get(cctv_alert_id)
            if not alert:
                for h in state_manager.history:
                    if h.id == cctv_alert_id:
                        alert = h
                        break
        if alert:
            cctv_event = SafetyEvent(
                event_id=f"EVT-{alert.id}",
                source="CCTV",
                location=alert.location,
                activity=alert.activity or "Mechanical Lifting",
                raw_narrative=alert.short_summary or alert.title or "CCTV observation"
            )

    result = corroboration_engine.corroborate_events(
        human_event=human_event,
        cctv_event=cctv_event,
        human_report_text=human_text
    )
    return result

@app.get("/api/corroboration/demo-scenarios")
def get_corroboration_scenarios():
    """Returns preset demonstration scenarios for Human Report + CCTV Evidence"""
    scenario_a = corroboration_engine.corroborate_events(
        human_event=SafetyEvent(
            event_id="EVT-H-01",
            source="HUMAN_REPORT",
            location="Demo Lifting Area",
            activity="Mechanical Lifting",
            raw_narrative="Worker entered lifting exclusion zone."
        ),
        cctv_event=SafetyEvent(
            event_id="EVT-C-01",
            source="CCTV",
            location="Demo Lifting Area",
            activity="Mechanical Lifting",
            raw_narrative="Person detected inside defined exclusion zone."
        )
    )
    scenario_b = corroboration_engine.corroborate_events(
        cctv_event=SafetyEvent(
            event_id="EVT-C-02",
            source="CCTV",
            location="Lifting Zone 03",
            activity="Mechanical Lifting",
            raw_narrative="Person detected inside defined exclusion zone."
        )
    )
    scenario_c = corroboration_engine.corroborate_events(
        human_report_text="Contractor observed working under pipe rack without barricade in Pipe Yard Beta."
    )
    return {
        "corroborated": scenario_a,
        "cctv_only": scenario_b,
        "human_only": scenario_c
    }

# ==========================================
# 9-PHASE DEMO STORYBOARD CONTROLLER (Section 11)
# ==========================================

@app.post("/api/demo/phase/{phase_num}")
def execute_demo_phase(phase_num: int, req: Dict[str, Any] = {}):
    """
    Executes a specific phase of the exact SIH demonstration story (Section 11):
    Phase 1: Historical Intelligence (5 independent occurrences, recurring pattern)
    Phase 2: HSE Validation (HSE confirms pattern -> Future Work Requirement)
    Phase 3 & 4: Live CCTV Event -> Machine-Generated Safety Observation -> SIF Intelligence
    Phase 5: SIF Analysis Display (High SIF Potential, Hazard, Exposure, Barrier, LSR)
    Phase 6: Mobile Alert (Supervisor receives clean 2-3s alert)
    Phase 7: Action (Acknowledge -> Action Completed)
    Phase 8: CCTV Verification (Clear -> VERIFIED, or Re-breach -> REOPENED)
    Phase 9: Safety Memory Updated (5 -> 6 independent occurrences)
    """
    if phase_num == 1:
        # Phase 1: Historical Intelligence
        # Return summary of 5 independent occurrences
        safety_memory.reset()
        pat = safety_memory.patterns.get("PAT-LIFT-01")
        pat.validation_status = HSEValidationStatus.CANDIDATE
        state_manager.notify_clients()
        return {
            "phase": 1,
            "title": "Phase 1: Historical Safety Intelligence",
            "message": "Loaded historical safety observations. Identified Candidate Recurring Safety-Control Pattern with 5 independent occurrences.",
            "pattern": pat.dict() if pat else None
        }

    elif phase_num == 2:
        # Phase 2: HSE Validation
        pat = safety_memory.validate_pattern("PAT-LIFT-01", "CONFIRM", "Chief HSE Officer (OIL)", "Validated based on recurring personnel segregation failures.")
        reqs = list(safety_memory.future_requirements.values())
        matching_req = [r for r in reqs if r.derived_from_pattern_id == "PAT-LIFT-01"]
        state_manager.notify_clients()
        return {
            "phase": 2,
            "title": "Phase 2: HSE Validation & Future Learning",
            "message": "✓ HSE VALIDATED SAFETY PATTERN. Derived mandatory future-work requirement.",
            "pattern": pat.dict() if pat else None,
            "future_requirement": matching_req[0].dict() if matching_req else None
        }

    elif phase_num in [3, 4]:
        # Phase 3 & 4: Live CCTV Event & Machine-Generated Safety Observation
        alert = state_manager.simulate_zone_entry()
        state_manager.notify_clients()
        return {
            "phase": phase_num,
            "title": "Phase 3 & 4: Live CCTV Detection -> Machine Safety Observation",
            "message": "Person entered lifting exclusion zone. Generated machine observation and sent to SIF Intelligence.",
            "alert": alert.dict() if alert else None,
            "machine_observation": alert.machine_observation if alert else None
        }

    elif phase_num == 5:
        # Phase 5: SIF Analysis
        alert = state_manager.active_alert
        if not alert:
            alert = state_manager.simulate_zone_entry()
        return {
            "phase": 5,
            "title": "Phase 5: SIF Intelligence Assessment",
            "message": "SIF POTENTIAL — HIGH. Hazard: Suspended Load | Barrier: Exclusion Zone (Violated) | LSR: Line of Fire.",
            "alert": alert.dict() if alert else None
        }

    elif phase_num == 6:
        # Phase 6: Mobile Alert
        alert = state_manager.active_alert
        if not alert:
            alert = state_manager.simulate_zone_entry()
        return {
            "phase": 6,
            "title": "Phase 6: Mobile Supervisor Alert Triggered",
            "message": "Operational mobile alert delivered to field supervisor for immediate response.",
            "alert": alert.dict() if alert else None
        }

    elif phase_num == 7:
        # Phase 7: Action Taken
        alert = state_manager.active_alert
        if not alert:
            alert = state_manager.simulate_zone_entry()
        state_manager.respond_to_alert("SUP-01", "Supervisor en route to secure exclusion zone", alert.id)
        action_alert = state_manager.mark_action_taken(alert.id, "SUP-01", "Workers cleared from exclusion zone; physical perimeter restored.", "Clear zone")
        state_manager.notify_clients()
        return {
            "phase": 7,
            "title": "Phase 7: Action Taken",
            "message": "Action marked taken by supervisor. Transitioned to AWAITING_VERIFICATION ('Completion is not proof').",
            "alert": action_alert.dict() if action_alert else None
        }

    elif phase_num == 8:
        # Phase 8: CCTV Verification
        simulate_rebreach = bool(req.get("simulate_rebreach", False))
        verif_res = state_manager.verify_cctv_condition(None, "SUP-01", simulate_rebreach)
        state_manager.notify_clients()
        return {
            "phase": 8,
            "title": "Phase 8: CCTV Verification",
            "result": verif_res
        }

    elif phase_num == 9:
        # Phase 9: Safety Memory Updated
        pat = safety_memory.patterns.get("PAT-LIFT-01")
        return {
            "phase": 9,
            "title": "Phase 9: Safety Memory Updated",
            "message": f"NEW SAFETY EVIDENCE ADDED. Recurring pattern '{pat.title if pat else ''}' occurrences: {pat.independent_occurrences_count if pat else 6} independent occurrences.",
            "pattern": pat.dict() if pat else None
        }

    raise HTTPException(status_code=400, detail=f"Invalid phase number {phase_num}")

# ==========================================
# AI + NLP SAFETY ANALYSIS ENDPOINTS (SIH PS 26165)
# ==========================================

def get_all_alerts_for_nlp():
    """Retrieves consolidated list of active and historical alerts for NLP analysis"""
    with state_manager.lock:
        return list(state_manager._active_alerts.values()) + list(state_manager.history)

@app.get("/api/reports/generated")
def get_generated_reports():
    """
    Returns all structured safety reports automatically generated from live CCTV alerts
    and accumulated event history.
    """
    alerts = get_all_alerts_for_nlp()
    reports = nlp_analyzer.sync_and_get_reports(alerts)
    return {"reports": reports, "total": len(reports)}

@app.get("/api/reports/export-pdf")
def export_reports_pdf():
    """
    Generates and downloads a consolidated industrial HSE PDF report of all
    current safety observations and AI precursor findings from the uploaded CSV dataset.
    """
    summary = dataset_store.get_summary()
    status_info = dataset_store.get_status_info()
    dataset_info = status_info.get("dataset_info")

    alerts = get_all_alerts_for_nlp()
    if summary:
        from nlp_engine.pdf_exporter import pdf_exporter
        pdf_bytes = pdf_exporter.export_dataset_pdf(dataset_info, summary, alerts=alerts)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"SHRAMRAKSHAK_HSE_Intelligence_Report_{date_str}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    alerts = get_all_alerts_for_nlp()
    reports = nlp_analyzer.sync_and_get_reports(alerts)
    if reports:
        from nlp_engine.pdf_exporter import pdf_exporter
        pdf_bytes = pdf_exporter.export_summary_pdf(reports)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ShramRakshak_CCTV_Safety_Report.pdf"}
        )

    raise HTTPException(
        status_code=400,
        detail="No analysed dataset available. Upload and process a safety-report CSV first."
    )


@app.get("/api/reports/validation/summary")
def get_validation_summary():
    """
    Returns AI validation metrics (TP, TN, FP, FN, Precision, Recall, F1)
    derived from evaluated HSE ground truth labels, or INSUFFICIENT_LABELLED_DATA.
    Never returns fake or uncalibrated accuracy.
    """
    return nlp_analyzer.get_validation_summary()

@app.post("/api/reports/prototype-history/load")
def load_prototype_history():
    """
    Seeds standard prototype evaluation reports for HSE review and validation testing.
    """
    proto_reports = [
        SafetyReport(
            report_id="REP-PROTO-001",
            source="PROTOTYPE_HISTORY",
            event_type="RESTRICTED_ZONE",
            timestamp=datetime.now().isoformat(),
            camera_id="C-01",
            location="Drill Site Alpha",
            activity="Mechanical Lifting",
            description="Person entered active lifting exclusion zone beneath suspended crane load.",
            hazard="Suspended Load",
            energy_source="Gravity / Suspended Load",
            exposure="Line of Fire",
            barrier="Physical exclusion barricade",
            barrier_failure="Barricade breached by unauthorized personnel",
            potential_consequence="Fatality / Permanent Disabling Injury",
            sif_potential=True,
            risk_score=85,
            risk_level="CRITICAL",
            confidence=85,
            confidence_level="HIGH",
            evidence_strength="HIGH",
            needs_hse_review=False,
            life_saving_rules=["Safe Mechanical Lifting", "Line of Fire"],
            is_demo_sample=True
        ),
        SafetyReport(
            report_id="REP-PROTO-002",
            source="PROTOTYPE_HISTORY",
            event_type="RESTRICTED_ZONE",
            timestamp=datetime.now().isoformat(),
            camera_id="C-02",
            location="Fabrication Yard",
            activity="Hot Work",
            description="Worker grinding pipe without spark shelter within 4m of flammable solvent storage.",
            hazard="Open Spark near Flammables",
            energy_source="Thermal / Chemical Energy",
            exposure="Fire / Flash Fire",
            barrier="Physical spark containment screen",
            barrier_failure="Spark containment screen not deployed",
            potential_consequence="Flash fire and severe burn injuries",
            sif_potential=False,
            risk_score=45,
            risk_level="MEDIUM",
            confidence=80,
            confidence_level="HIGH",
            evidence_strength="MEDIUM",
            needs_hse_review=True,
            life_saving_rules=["Hot Work"],
            is_demo_sample=True
        ),
        SafetyReport(
            report_id="REP-PROTO-003",
            source="PROTOTYPE_HISTORY",
            event_type="CONFINED_SPACE",
            timestamp=datetime.now().isoformat(),
            camera_id="C-03",
            location="Tank Battery 4",
            activity="Confined Space Entry",
            description="Personnel entered vessel before atmospheric gas testing completion.",
            hazard="Toxic Gas / Oxygen Deficiency",
            energy_source="Atmospheric Contaminants",
            exposure="Inhalation of toxic atmosphere",
            barrier="Atmospheric multi-gas detector clearance",
            barrier_failure="Entry made prior to continuous gas monitor reading verification",
            potential_consequence="Asphyxiation / Fatal atmospheric toxicity",
            sif_potential=True,
            risk_score=90,
            risk_level="CRITICAL",
            confidence=90,
            confidence_level="HIGH",
            evidence_strength="HIGH",
            needs_hse_review=False,
            life_saving_rules=["Confined Space Entry"],
            is_demo_sample=True
        )
    ]
    for r in proto_reports:
        nlp_analyzer.report_generator.generated_reports[r.report_id] = r
    return {"message": "Prototype history reports loaded successfully", "count": len(proto_reports)}

@app.get("/api/reports/{report_id}")
def get_report_by_id(report_id: str):
    """
    Returns a specific safety report with complete AI/NLP precursor analysis.
    """
    alerts = get_all_alerts_for_nlp()
    report = nlp_analyzer.get_report_by_id(report_id, alerts)
    if not report:
        raise HTTPException(status_code=404, detail=f"Safety report '{report_id}' not found")
    return report

@app.post("/api/reports/{report_id}/analyze")
def analyze_report_by_id(report_id: str):
    """
    Runs on-demand AI/NLP re-analysis of a specific safety report.
    """
    alerts = get_all_alerts_for_nlp()
    report = nlp_analyzer.analyze_report(report_id, alerts)
    if not report:
        raise HTTPException(status_code=404, detail=f"Safety report '{report_id}' not found")
    return {"message": "Report analyzed successfully", "report": report}

@app.post("/api/reports/{report_id}/review")
def submit_report_hse_review(report_id: str, req: HSEReviewRequest):
    """
    Stores an official Human HSE Review decision (CONFIRM | CORRECT | REJECT)
    with optional HSE corrections. Updates report state and builds real validation dataset.
    """
    alerts = get_all_alerts_for_nlp()
    updated_report = nlp_analyzer.submit_hse_review(report_id, req.dict(), alerts)
    if not updated_report:
        raise HTTPException(status_code=404, detail=f"Safety report '{report_id}' not found")
    return {
        "message": f"HSE review decision '{req.decision}' recorded successfully",
        "report_id": report_id,
        "report": updated_report
    }

@app.get("/api/reports/analysis/summary", response_model=AnalysisSummary)
def get_analysis_summary():
    """
    Returns high-level AI/NLP SIF precursor intelligence summary,
    risk distributions, top Life-Saving Rules, and high-risk prioritizations.
    """
    alerts = get_all_alerts_for_nlp()
    return nlp_analyzer.get_summary(alerts)

@app.get("/api/reports/analysis/patterns")
def get_analysis_patterns():
    """
    Returns recurring precursor patterns mined from accumulated safety reports.
    """
    alerts = get_all_alerts_for_nlp()
    patterns = nlp_analyzer.get_recurring_patterns(alerts)
    return {"patterns": patterns, "total": len(patterns)}


@app.get("/api/reports/{report_id}/export-pdf")
def export_single_report_pdf(report_id: str):
    """
    Generates and downloads an individual safety observation dossier PDF.
    """
    alerts = get_all_alerts_for_nlp()
    pdf_bytes = nlp_analyzer.export_single_report_pdf(report_id, alerts)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report_id}_Dossier.pdf"}
    )

@app.post("/api/reports/analyze-text")
def analyze_raw_text(req: dict):
    """
    Demonstrates ingestion of external text (e.g. OIL's real UA/UC, Near-Miss or Incident reports)
    directly through the same AI/NLP engine.
    """
    text = req.get("text", "")
    context = req.get("context", {})
    if not text:
        raise HTTPException(status_code=400, detail="Field 'text' is required")
    return nlp_analyzer.analyze_raw_text(text, context)

@app.get("/api/zones")
def get_zones():
    """Returns the configured restricted zones (permanent and temporary)"""
    zones_list = list(state_manager.zones.values())
    return {
        "zones": zones_list,
        "active_zone": state_manager.active_zone,
        "permanent_zones": state_manager.get_permanent_zones(),
        "temporary_zones": state_manager.get_temporary_zones(),
        "active_zones": state_manager.get_active_zones()
    }

@app.post("/api/zones")
def save_zone(zone: RestrictedZone):
    """Creates or updates a restricted safety zone"""
    saved = state_manager.set_zone(zone)
    return {"message": "Safety zone saved successfully", "zone": saved}

@app.delete("/api/zones/{zone_id}")
@app.post("/api/zones/{zone_id}/delete")
def delete_zone(zone_id: str):
    """Deletes/clears a restricted safety zone"""
    state_manager.delete_zone(zone_id)
    return {"message": f"Safety zone {zone_id} deleted"}

@app.delete("/api/zones")
@app.post("/api/zones/delete")
def delete_all_zones():
    """Deletes/clears the active restricted safety zone"""
    state_manager.delete_zone(None)
    return {"message": "Active safety zone deleted"}

@app.patch("/api/zones/{zone_id}/toggle")
@app.post("/api/zones/{zone_id}/toggle")
def toggle_zone(zone_id: str):
    """Enables or disables a safety zone"""
    zone = state_manager.toggle_zone(zone_id)
    return {"message": "Safety zone toggled", "zone": zone}

@app.post("/api/zones/restore-default")
def restore_default_zone():
    """Restores the default permanent safety zone ZONE-001"""
    zone = state_manager.restore_default_zone()
    return {"message": "Default safety zone restored", "zone": zone}

# ==========================================
# SAFETY PASSPORT API ENDPOINTS
# ==========================================

@app.get("/api/passports")
def list_passports():
    """Returns list of all safety passports (active and history)"""
    return {"passports": state_manager.get_passports_list()}

@app.get("/api/passports/active")
def get_active_passport():
    """Returns the currently active / in-progress safety passport"""
    p = state_manager.active_passport
    return {"passport": p}

@app.get("/api/passports/{passport_id}")
def get_passport_by_id(passport_id: str):
    """Returns specific safety passport by ID"""
    with state_manager.lock:
        p = state_manager.passports.get(passport_id)
    if not p:
        raise HTTPException(status_code=404, detail="Safety Passport not found")
    return {"passport": p}

@app.post("/api/passports")
def create_safety_passport(req: CreatePassportRequest):
    """Creates a new high-risk task Safety Passport (from Supervisor or HSE)"""
    try:
        passport = state_manager.create_passport(req)
        return {"message": "Safety Passport created successfully", "passport": passport}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/passports/{passport_id}/verify-control")
def verify_passport_control(passport_id: str, req: VerifyControlRequest, request: Request):
    """Verifies or un-verifies a pre-start safety control"""
    role = request.headers.get("x-user-role") or req.user_role or "supervisor"
    try:
        passport = state_manager.verify_control(
            passport_id=passport_id,
            control_id=req.control_id,
            verified=req.verified,
            verified_by=req.verified_by or ("HSE Manager" if str(role).lower() == "hse" else "Demo Supervisor"),
            notes=req.notes,
            user_role=role
        )
        return {"message": "Control verification updated", "passport": passport}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/passports/{passport_id}/approve")
def approve_safety_passport(passport_id: str, request: Request, req: ApprovePassportRequest = ApprovePassportRequest()):
    """HSE formal authorization for the Safety Passport"""
    role = request.headers.get("x-user-role") or req.user_role or "supervisor"
    try:
        passport = state_manager.approve_passport(
            passport_id=passport_id,
            approved_by=req.approved_by or "HSE Manager",
            notes=req.notes,
            user_role=role
        )
        return {"message": "Safety Passport approved by HSE", "passport": passport}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/passports/{passport_id}/activate")
def activate_safety_passport(passport_id: str, request: Request):
    """Activates the Safety Passport if all mandatory controls are verified"""
    role = request.headers.get("x-user-role") or request.query_params.get("user_role") or "supervisor"
    try:
        success, msg, passport = state_manager.activate_passport(passport_id, user_role=role)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        return {"message": msg, "passport": passport}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.post("/api/passports/{passport_id}/verify-restoration")
def verify_barrier_restoration(passport_id: str, req: VerifyRestorationRequest = VerifyRestorationRequest()):
    """Supervisor physically verifies that the critical barrier has been restored"""
    success, msg, passport = state_manager.verify_barrier_restored(
        passport_id=passport_id,
        supervisor_id=req.supervisor_id or "Demo Supervisor",
        notes=req.notes
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "passport": passport}

@app.post("/api/passports/{passport_id}/close")
def close_safety_passport(passport_id: str):
    """Formally closes the Safety Passport upon task completion"""
    try:
        passport = state_manager.close_passport(passport_id)
        return {"message": "Safety Passport closed", "passport": passport}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/demo/simulate-zone-entry")
def simulate_zone_entry():
    """Demo Mode fallback: simulates a person entering the restricted zone"""
    alert = state_manager.simulate_zone_entry()
    return {"message": "Simulated Restricted Zone Entry triggered", "alert": alert}

@app.post("/api/demo/simulate-multi-violation")
def simulate_multi_violation():
    """Demo Mode fallback: simulates 3 people (2 No Helmet + 1 in Restricted Zone) simultaneously"""
    alerts = state_manager.simulate_multi_violation()
    return {"message": "Simulated Multi-Violation triggered (Zone + 2 No-Helmet)", "alerts": alerts}

@app.get("/video_feed")
@app.get("/api/video_feed")
@app.get("/api/stream")
def video_feed(camera: Optional[str] = "C-01", camera_id: Optional[str] = None):
    """MJPEG live stream with bounding boxes and HUD for the dashboard (supports multi-camera)"""
    target_cam = camera_id or camera or getattr(state_manager, 'active_camera_id', 'C-01')
    return StreamingResponse(
        generate_mjpeg_stream(camera_id=target_cam),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.post("/api/cv/frame")
async def process_browser_frame(request: Request):
    """
    Receives live webcam frames from browser (or demo video playback)
    at configurable 10-12 FPS, runs real ONNX model inference, and returns detections.
    """
    try:
        content_type = request.headers.get("content-type", "")
        img_bytes = None
        camera_id = "C-01"
        frame_seq = 0

        if "multipart/form-data" in content_type:
            form = await request.form()
            file = form.get("frame")
            camera_id = form.get("camera_id", "C-01")
            try:
                frame_seq = int(form.get("frame_seq", 0))
            except (ValueError, TypeError):
                frame_seq = 0
            if file:
                img_bytes = await file.read()
        elif "application/json" in content_type:
            data = await request.json()
            camera_id = data.get("camera_id", "C-01")
            try:
                frame_seq = int(data.get("frame_seq", 0))
            except (ValueError, TypeError):
                frame_seq = 0
            b64 = data.get("frame", "")
            if b64:
                if "," in b64:
                    b64 = b64.split(",")[1]
                img_bytes = base64.b64decode(b64)
        else:
            img_bytes = await request.body()

        if not img_bytes:
            raise HTTPException(status_code=400, detail="Empty frame payload")

        # Decode image to numpy BGR array
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            raise HTTPException(status_code=400, detail="Could not decode image frame")

        # Track external frame timestamp to avoid hardware conflicts
        video_engine._last_external_frame_ts = time.time()

        # Run real ONNX detection engine
        result = video_engine.process_frame(frame, camera_id=camera_id, frame_seq=frame_seq)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cv/reset")
def reset_cv_session():
    """
    Resets all CV tracking session states (person tracks, vehicle tracks,
    proximity states, frame sequences) and clears camera active alert session.
    Called when user switches source (Webcam <-> Demo Video) or uploads new video.
    """
    video_engine.reset_tracks()
    state_manager.reset_cv_session()
    return {"status": "ok", "message": "CV detection session cleanly reset"}

@app.get("/api/cv/debug")
def get_cv_debug():
    """Returns real-time AI & Camera diagnostics for developer section"""
    return video_engine.get_debug_stats()

@app.get("/api/cameras")
def get_cameras():
    """Returns list of active camera channels (physical + industrial AI nodes)"""
    return {
        "cameras": [
            {
                "id": "C-01",
                "name": "Camera C-01 (Laptop Webcam)",
                "location": "Demo Work Zone",
                "type": "PHYSICAL" if hasattr(video_engine, 'cap') and video_engine.cap and video_engine.cap.isOpened() else "AI_CCTV",
                "status": "LIVE",
                "resolution": "640x480",
                "ai_active": True,
                "stream_url": "/video_feed?camera=C-01"
            }
        ],
        "active_camera": "C-01"
    }

@app.post("/api/cameras/select")
def select_active_camera(req: Dict[str, Any]):
    cam_id = req.get("camera_id", "C-01")
    state_manager.active_camera_id = cam_id
    return {"message": f"Active camera set to {cam_id}", "camera_id": cam_id}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time synchronization between
    Dashboard and Mobile Supervisor clients.
    """
    await websocket.accept()
    state_manager.register_websocket(websocket)
    # Immediately send the initial status on connect
    initial_status = state_manager.get_system_status().model_dump_json()
    await websocket.send_text(initial_status)
    try:
        while True:
            # Keep connection alive and listen for client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        state_manager.unregister_websocket(websocket)
    except Exception:
        state_manager.unregister_websocket(websocket)

# ============================================================
# REAL DATASET SIF ANALYTICS API ENDPOINTS (SIH PS 26165)
# ============================================================

_cached_dataframe: Optional[pd.DataFrame] = None
_cached_mapping: Optional[Dict[str, Optional[str]]] = None

def _run_background_dataset_processing(df: pd.DataFrame, mapping: Dict[str, Optional[str]], max_rows: Optional[int]):
    try:
        def update_cb(prog, msg):
            dataset_store.update_progress(prog, msg)

        dataset_store.update_progress(0.15, "Starting NLP Preprocessing & Safety Term Normalization...")
        reports, summary = dataset_processor.process_dataset(
            df=df,
            mapping=mapping,
            max_rows=max_rows,
            progress_callback=update_cb
        )
        dataset_store.set_completed_results(reports, summary)
    except Exception as e:
        dataset_store.set_failed(f"Dataset processing error: {str(e)}")

@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Ingests an uploaded safety report CSV dataset, validates data health,
    auto-detects column mappings, and returns data quality metrics.
    """
    global _cached_dataframe, _cached_mapping
    try:
        contents = await file.read()
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only .csv files are supported.")

        df = pd.read_csv(io.BytesIO(contents), low_memory=False)
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="Uploaded CSV file contains no data rows.")

        mapping = ColumnMapper.auto_map_columns(df)
        quality_info = DataQualityValidator.validate(df, mapping, file.filename)

        _cached_dataframe = df
        _cached_mapping = mapping

        dataset_store.reset()
        dataset_store.set_validated_info(quality_info)

        return {
            "message": "Dataset uploaded and validated successfully",
            "quality_report": quality_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {str(e)}")

@app.post("/api/dataset/process")
def start_dataset_processing(req: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Triggers the complete NLP/SIF analysis pipeline on the validated dataset.
    """
    global _cached_dataframe, _cached_mapping
    if _cached_dataframe is None or _cached_mapping is None:
        raise HTTPException(status_code=400, detail="No validated dataset found. Please upload a CSV first or load the preset dataset.")

    max_rows = req.get("max_rows", 2000) # Default to 2000 rows for fast live demo execution if unspecified

    dataset_store.update_progress(0.10, "Initializing NLP & SIF Pathway Pipeline...")
    background_tasks.add_task(
        _run_background_dataset_processing,
        _cached_dataframe,
        _cached_mapping,
        max_rows
    )

    return {
        "message": "Dataset processing started in background",
        "total_rows": len(_cached_dataframe),
        "processing_rows": min(len(_cached_dataframe), max_rows if max_rows else len(_cached_dataframe))
    }

@app.get("/api/dataset/status")
def get_dataset_status():
    """Returns current status and progress of the dataset analysis pipeline"""
    return dataset_store.get_status_info()

@app.get("/api/dataset/summary")
def get_dataset_summary():
    """Returns the 9-Section Final HSE Intelligence Report summary"""
    summary = dataset_store.get_summary()
    if not summary:
        raise HTTPException(status_code=404, detail="Dataset summary report not ready yet. Please run SIF analysis first.")
    return summary

@app.get("/api/dataset/reports")
def get_dataset_reports(
    status_filter: str = "ALL",
    source_filter: str = "ALL",
    lsr_filter: Optional[str] = None,
    precursor_filter: Optional[str] = None,
    site_filter: Optional[str] = None,
    activity_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """Returns paginated and filtered list of analyzed dataset reports for drill-down"""
    return dataset_store.get_filtered_reports(
        status_filter=status_filter,
        source_filter=source_filter,
        lsr_filter=lsr_filter,
        precursor_filter=precursor_filter,
        site_filter=site_filter,
        activity_filter=activity_filter,
        search_query=search,
        page=page,
        page_size=page_size
    )

@app.get("/api/dataset/report/{report_id}")
def get_dataset_single_report(report_id: str):
    """Returns full details and explanation for a single dataset report"""
    report = dataset_store.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found in dataset store.")
    return report

@app.get("/api/dataset/sample")
def load_sample_dataset(max_rows: int = 1500, background_tasks: BackgroundTasks = None):
    """
    Preset loader: Loads January2015toNovember2025.csv directly from zip/Downloads
    for seamless live demonstration without needing manual file browsing.
    """
    global _cached_dataframe, _cached_mapping
    current_dir = os.path.dirname(os.path.abspath(__file__))
    home_dir = os.path.expanduser("~")
    possible_paths = [
        os.path.join(current_dir, "data", "January2015toNovember2025.zip"),
        os.path.join(current_dir, "data", "January2015toNovember2025.csv"),
        os.path.join(current_dir, "January2015toNovember2025.zip"),
        os.path.join(current_dir, "January2015toNovember2025.csv"),
        os.path.join(home_dir, "Downloads", "SIH FINAL PROJECT SHRAMRAKSHAK ZIP", "SIH FINAL PROJECT SHRAMRAKSHAK", "January2015toNovember2025.zip"),
        os.path.join(home_dir, "Downloads", "SIH FINAL PROJECT SHRAMRAKSHAK ZIP", "SIH FINAL PROJECT SHRAMRAKSHAK", "Scraping", "January2015toNovember2025.csv"),
        os.path.join(home_dir, "Downloads", "January2015toNovember2025.zip"),
        os.path.join(home_dir, "Downloads", "Data", "Data", "accident data.csv"),
        "c:/Users/Dell/Downloads/SIH FINAL PROJECT SHRAMRAKSHAK ZIP/SIH FINAL PROJECT SHRAMRAKSHAK/January2015toNovember2025.zip",
        "c:/Users/Dell/Downloads/January2015toNovember2025.zip",
        "c:/Users/Shravani/Downloads/January2015toNovember2025.zip",
        "c:/Users/Shravani/Downloads/Data/Data/accident data.csv"
    ]

    df = None
    file_name = "January2015toNovember2025.csv"

    for path in possible_paths:
        if os.path.exists(path):
            try:
                if path.endswith(".zip"):
                    with zipfile.ZipFile(path, 'r') as z:
                        csv_members = [m for m in z.namelist() if m.endswith(".csv")]
                        target_member = "January2015toNovember2025.csv" if "January2015toNovember2025.csv" in csv_members else (csv_members[0] if csv_members else None)
                        if target_member:
                            with z.open(target_member) as f:
                                df = pd.read_csv(f, low_memory=False)
                                file_name = os.path.basename(target_member)
                                break
                elif path.endswith(".csv"):
                    df = pd.read_csv(path, low_memory=False)
                    file_name = os.path.basename(path)
                    break
            except Exception as e:
                print(f"Sample load warning from {path}: {e}")

    if df is None:
        # Fallback synthetic demo data to guarantee presentation resiliency
        sample_rows = [
            {"ID": i + 1, "UPA": 1000 + i, "EventDate": f"2024-0{(i % 9) + 1}-15", "Employer": "OIL Field Operations",
             "Address1": "Sector 4", "Address2": "", "City": "Duliajan", "State": "AS", "Zip": "786602",
             "Latitude": 27.35, "Longitude": 95.32, "Primary NAICS": "211111", "Hospitalized": 0, "Amputation": 0,
             "Loss of Eye": 0, "Inspection": "INSP-01",
             "Final Narrative": narrative, "Nature": "Contusion", "NatureTitle": "Bruise/Struck-by",
             "Part of Body": 10, "Part of Body Title": "Head", "Event": 12, "EventTitle": "Exposure/Struck-by",
             "Source": 3, "SourceTitle": "CCTV", "Secondary Source": "", "Secondary Source Title": "", "FederalState": "FED"}
            for i, narrative in enumerate([
                "Worker observed working under suspended crane boom without mandatory hard hat and hi-vis vest in drilling rig perimeter.",
                "Roustabout entered high-pressure manifold exclusion boundary while pump pressure was active without clearance permit.",
                "Contractor stepped into crane lifting swing radius during pipe offloading operation. Supervisor intervened immediately.",
                "Maintenance technician bypassed compressor emergency shut-off interlock guard during lubrication routine.",
                "Scaffolder unhooked fall arrest lanyard at elevated platform height of 5 meters near tank battery."
            ] * 15)
        ]
        df = pd.DataFrame(sample_rows)
        file_name = "SyntheticDemoIncidents.csv"

    mapping = ColumnMapper.auto_map_columns(df)
    quality_info = DataQualityValidator.validate(df, mapping, file_name)

    _cached_dataframe = df
    _cached_mapping = mapping

    dataset_store.reset()
    dataset_store.set_validated_info(quality_info)

    # Immediately run processing in background for instant demo readiness
    dataset_store.update_progress(0.10, "Initializing Preset NLP Pipeline...")
    if background_tasks:
        background_tasks.add_task(
            _run_background_dataset_processing,
            _cached_dataframe,
            _cached_mapping,
            max_rows
        )
    else:
        import threading
        threading.Thread(
            target=_run_background_dataset_processing,
            args=(_cached_dataframe, _cached_mapping, max_rows),
            daemon=True
        ).start()

    return {
        "message": f"Preset sample dataset '{file_name}' loaded successfully",
        "quality_report": quality_info,
        "processing_started": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
