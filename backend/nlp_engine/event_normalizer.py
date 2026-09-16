import re
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel

class NormalizedSafetyEvent(BaseModel):
    """
    Standardized internal safety event model allowing CCTV events,
    prototype records, and future connected OIL HSSE reports to pass
    through the exact same AI Risk Reasoning pipeline.
    """
    event_id: str
    source: str  # "CCTV_EVENT" | "PROTOTYPE_HISTORY" | "HSSE_REPORT"
    event_type: str
    timestamp: str
    camera_id: str = "C-01"
    location: str = "Demo Work Zone"
    activity: str = "General Operations"
    equipment: str = "Industrial Equipment"
    hazard: str = "Unspecified Safety Hazard"
    unsafe_act: Optional[str] = None
    unsafe_condition: Optional[str] = None
    barrier: str = "Standard Operational Controls"
    barrier_failure: str = "Control procedure not verified"
    exposure: str = "Personnel present in work area"
    narrative: str
    evidence_image: Optional[str] = None
    evidence_url: Optional[str] = None
    is_demo_sample: bool = False

class EventNormalizer:
    """
    Normalizes heterogeneous safety data sources into uniform NormalizedSafetyEvent instances.
    """

    @staticmethod
    def normalize_cctv_alert(alert_dict: Dict[str, Any]) -> NormalizedSafetyEvent:
        alert_id = alert_dict.get("id", f"ALT-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        alert_type = alert_dict.get("type", "Safety Non-Compliance")
        location = alert_dict.get("location") or "Demo Work Zone"
        camera = alert_dict.get("camera") or alert_dict.get("camera_id") or "C-01"
        count = alert_dict.get("person_count", 1)

        # Infer activity & equipment based on alert type and location
        loc_lower = location.lower()
        type_lower = alert_type.lower()

        if "passport" in type_lower or "lift" in loc_lower or "crane" in type_lower:
            activity = "Mechanical Lifting"
            equipment = "Mobile Crane & Rigging Assembly"
            hazard = "Suspended Load & Struck-By Trajectory"
            barrier = "Lifting Exclusion Zone & Permit Authorisation"
            barrier_failure = "Personnel entered active lifting exclusion perimeter"
            exposure = f"{count} worker{'s' if count > 1 else ''} exposed in drop radius / line of fire"
            narrative = (
                f"Personnel entered an active lifting exclusion zone at {location} (Camera {camera}) "
                f"while mechanical lifting operations were underway. Physical boundary compromised."
            )
        elif "zone" in type_lower:
            activity = "Restricted Area Maintenance"
            equipment = "Industrial Machinery Skid"
            hazard = "Physical Entry into Active High-Risk Machinery Perimeter"
            barrier = "Machine Guarding & Designated Exclusion Perimeter"
            barrier_failure = "Unauthorized entry beyond exclusion perimeter"
            exposure = f"{count} worker{'s' if count > 1 else ''} inside machinery danger zone"
            narrative = (
                f"Unauthorized personnel detected inside marked restricted zone at {location} (Camera {camera}). "
                f"Worker crossed boundary during active machine operation."
            )
        elif "helmet" in type_lower or "ppe" in type_lower:
            activity = "General Site Operations"
            equipment = "Field Work Equipment"
            hazard = "Overhead Impact & Falling Object Exposure"
            barrier = "Personal Protective Equipment (Hard Hat / Chin Strap)"
            barrier_failure = "Mandatory head protection omitted during field activity"
            exposure = f"{count} worker{'s' if count > 1 else ''} unequipped in operational zone"
            narrative = (
                f"{count} worker{'s' if count > 1 else ''} detected without required hard hat protection "
                f"in {location} during monitored activity on Camera {camera}."
            )
        else:
            activity = alert_dict.get("activity") or "General Site Operations"
            equipment = alert_dict.get("equipment") or "Site Equipment"
            hazard = alert_dict.get("hazard") or "Operational Safety Violation"
            barrier = "Standard Operational Controls"
            barrier_failure = "Procedural safety compliance omitted"
            exposure = f"{count} worker{'s' if count > 1 else ''} present"
            narrative = alert_dict.get("details") or f"Safety event recorded at {location} on Camera {camera}."

        return NormalizedSafetyEvent(
            event_id=alert_id,
            source="CCTV_EVENT",
            event_type=alert_type,
            timestamp=alert_dict.get("created_at") or datetime.now().isoformat(),
            camera_id=camera,
            location=location,
            activity=activity,
            equipment=equipment,
            hazard=hazard,
            unsafe_act=alert_dict.get("unsafe_act") or "Bypassing safety control boundary",
            unsafe_condition=alert_dict.get("unsafe_condition") or "Exclusion boundary breach",
            barrier=barrier,
            barrier_failure=barrier_failure,
            exposure=exposure,
            narrative=narrative,
            evidence_image=alert_dict.get("evidence_image"),
            evidence_url=alert_dict.get("evidence_url"),
            is_demo_sample=False
        )

    @staticmethod
    def normalize_prototype_record(rec: Dict[str, Any]) -> NormalizedSafetyEvent:
        report_id = rec.get("id") or rec.get("report_id", f"REP-PROTO-{datetime.now().strftime('%H%M%S')}")
        desc = rec.get("desc") or rec.get("description", "")
        loc = rec.get("loc") or rec.get("location", "Demo Work Zone")
        act = rec.get("act") or rec.get("activity", "General Site Operations")
        hazard = rec.get("hazard") or "Industrial Safety Hazard"
        cam = rec.get("cam") or rec.get("camera_id", "C-01")

        # Inferred barrier & failure from description
        barrier = rec.get("barrier") or "Primary Safety Control Barrier"
        barrier_failure = rec.get("barrier_failure") or "Operational barrier compromised"
        exposure = rec.get("exposure") or "Personnel positioned in hazardous exposure area"

        return NormalizedSafetyEvent(
            event_id=report_id,
            source="PROTOTYPE_HISTORY",
            event_type=rec.get("event_type", "OBSERVATION"),
            timestamp=rec.get("timestamp") or datetime.now().isoformat(),
            camera_id=cam,
            location=loc,
            activity=act,
            equipment=rec.get("equipment", "Industrial Machinery"),
            hazard=hazard,
            unsafe_act=rec.get("unsafe_act"),
            unsafe_condition=rec.get("unsafe_condition"),
            barrier=barrier,
            barrier_failure=barrier_failure,
            exposure=exposure,
            narrative=desc,
            evidence_image=rec.get("evidence_image"),
            evidence_url=rec.get("evidence_url"),
            is_demo_sample=True
        )

    @staticmethod
    def normalize_hsse_report(report_dict: Dict[str, Any]) -> NormalizedSafetyEvent:
        report_id = report_dict.get("report_id") or report_dict.get("id", f"REP-HSSE-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        narrative = report_dict.get("narrative") or report_dict.get("text") or report_dict.get("description", "")
        location = report_dict.get("location", "OIL Operational Asset")
        activity = report_dict.get("activity", "Oil & Gas Operations")

        return NormalizedSafetyEvent(
            event_id=report_id,
            source="HSSE_REPORT",
            event_type=report_dict.get("event_type", "UNSAFE_ACT_UNSAFE_CONDITION"),
            timestamp=report_dict.get("timestamp") or datetime.now().isoformat(),
            camera_id="N/A (Field Report)",
            location=location,
            activity=activity,
            equipment=report_dict.get("equipment", "Field Processing Equipment"),
            hazard=report_dict.get("hazard", "Operational Hazard"),
            unsafe_act=report_dict.get("unsafe_act"),
            unsafe_condition=report_dict.get("unsafe_condition"),
            barrier=report_dict.get("barrier", "Safety Standard Operating Procedure"),
            barrier_failure=report_dict.get("barrier_failure", "Procedure or physical control bypassed"),
            exposure=report_dict.get("exposure", "Worker present in line-of-fire"),
            narrative=narrative,
            evidence_image=None,
            evidence_url=None,
            is_demo_sample=False
        )
