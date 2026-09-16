import re
from typing import Dict, Optional

class PrecursorExtractor:
    """
    Extracts structured industrial HSSE entities from incident narratives:
    activity, location, equipment, hazard, unsafe act, unsafe condition,
    barrier failure, SIF precursor description, and AI recommendation.
    """

    def extract(self, text: str, context: Optional[Dict] = None) -> Dict[str, str]:
        context = context or {}
        full_text = f"{text} {context.get('location', '')} {context.get('hazard', '')} {context.get('activity', '')}".lower()

        # 1. Activity Extraction
        if re.search(r"\b(driving|vehicle|truck|forklift|revers(ing)?|traffic)\b", full_text):
            activity = "Driving & Plant Movement"
        elif re.search(r"\b(isolat(ion)?|loto|lockout|tagout|breaker|zero\s+energy)\b", full_text):
            activity = "Energy Isolation"
        elif re.search(r"\b(confined|manway|tank\s+t-|culvert|interceptor\s+pit)\b", full_text):
            activity = "Confined Space Entry"
        elif re.search(r"\b(weld(ing)?|hot\s+work|torch|cutting|flame)\b", full_text):
            activity = "Hot Work & Fabrication"
        elif re.search(r"\b(height|scaffold(ing)?|ladder|elevat(ed|ion)|lanyard)\b", full_text):
            activity = "Working at Height"
        elif re.search(r"\b(lift(ing)?|crane|hoist|rigging|spool|spreader)\b", full_text):
            activity = "Mechanical Lifting"
        elif re.search(r"\b(dunnage|housekeeping|storage\s+bay|trip\s+hazard)\b", full_text):
            activity = "Housekeeping & Storage"
        elif re.search(r"\b(compressor|gas\s+compression|pump)\b", full_text):
            activity = "Compressor & Rotating Machinery Operations"
        elif re.search(r"\b(maintenance|repair|inspection|tool-crib)\b", full_text):
            activity = "Routine Maintenance & Inspection"
        else:
            activity = context.get("activity") or "General Site Operations"

        # 2. Location Extraction
        if context.get("location"):
            location = context["location"]
        elif re.search(r"\b(lifting\s+area|lifting\s+zone)\b", full_text):
            location = "Demo Lifting Area"
        elif re.search(r"\b(compressor\s+area|compressor\s+house)\b", full_text):
            location = "Compressor Area (Zone C-01)"
        elif re.search(r"\b(pipe\s*rack|manifold)\b", full_text):
            location = "Main Pipe Rack"
        elif re.search(r"\b(tank\s+t-104|storage\s+tank)\b", full_text):
            location = "Storage Tank T-104"
        elif re.search(r"\b(interceptor\s+pit|drainage)\b", full_text):
            location = "Drainage Interceptor Pit"
        elif re.search(r"\b(logistics|yard\s+b)\b", full_text):
            location = "Logistics Yard B"
        elif re.search(r"\b(pipe\s+yard|yard\s+north)\b", full_text):
            location = "Pipe Yard North"
        elif re.search(r"\b(wellhead|cellar)\b", full_text):
            location = "Wellhead Structure B"
        elif re.search(r"\b(workshop|machine\s+shop)\b", full_text):
            location = "Maintenance Workshop"
        else:
            location = "Demo Work Zone"

        act_lower = activity.lower()

        # 3. Equipment Extraction
        if "driving" in act_lower:
            equipment = "Heavy Plant & Logistics Transport Vehicles"
        elif "isolation" in act_lower:
            equipment = "Electrical Breaker & Isolation Lockout Station"
        elif "confined" in act_lower:
            equipment = "Confined Space Access & Ventilation Equipment"
        elif "hot work" in act_lower:
            equipment = "Oxy-Fuel Torch & Arc Welding Rig"
        elif "height" in act_lower:
            equipment = "Scaffolding & Work Platform"
        elif "lifting" in act_lower:
            equipment = "Mobile Crane & Rigging Assembly"
        elif "compressor" in act_lower:
            equipment = "Centrifugal Gas Compressor"
        elif "housekeeping" in act_lower:
            equipment = "Material Stacking Dunnage & Racks"
        else:
            equipment = "Industrial Work Equipment"

        # 4. Hazard Extraction
        if context.get("hazard"):
            hazard = context["hazard"]
        elif "driving" in act_lower:
            hazard = "Heavy Vehicle Reversing Blind Spot & Pedestrian Collision"
        elif "isolation" in act_lower:
            hazard = "High-Voltage Electrical Arc & Residual Stored Pressure"
        elif "confined" in act_lower:
            hazard = "Oxygen Deficiency & Hazardous Atmospheric Ingress"
        elif "hot work" in act_lower:
            hazard = "Thermal Ignition of Flammables & Uncontrolled Sparks"
        elif "height" in act_lower:
            hazard = "Fall From Height Exposure (>1.8m)"
        elif "lifting" in act_lower:
            hazard = "Suspended Load & Struck-By Trajectory"
        elif "housekeeping" in act_lower:
            hazard = "Walkway Obstruction & Trip Exposure"
        elif "zone" in full_text:
            hazard = "Unauthorized Entry into High-Hazard Exclusion Area"
        elif "helmet" in full_text or "ppe" in full_text:
            hazard = "Impact & Head Trauma from Dropped Objects"
        else:
            hazard = "Workplace Physical Exposure"

        # 5. Unsafe Act, Unsafe Condition, Barrier Failure, Precursor, Recommendation
        if "isolation" in act_lower:
            unsafe_act = "Personnel commenced mechanical/electrical work prior to proving positive isolation"
            unsafe_condition = "Unverified energy state with potential residual line pressure or live circuits"
            barrier_failure = "Lockout-Tagout (LOTO) verification and zero-energy test omitted"
            precursor = "Catastrophic release of stored hazardous electrical / pneumatic energy"
            ai_recommendation = "Enforce mandatory Lockout/Tagout protocol. Execute zero-energy test and affix physical padlocks before opening any enclosure."
        elif "confined" in act_lower:
            unsafe_act = "Worker entered confined space compartment without active gas test certification"
            unsafe_condition = "Unventilated enclosed volume with potential toxic or oxygen-deficient atmosphere"
            barrier_failure = "Confined space entry control barrier and continuous gas monitoring bypassed"
            precursor = "Atmospheric asphyxiation or toxic gas exposure in enclosed compartment"
            ai_recommendation = "Evacuate space immediately. Perform continuous 4-gas testing, establish forced mechanical ventilation, and station dedicated standby sentry."
        elif "driving" in act_lower:
            unsafe_act = "Vehicle operated in pedestrian zone without banksman guide or reversing signal"
            unsafe_condition = "Shared vehicle-pedestrian transit corridor without physical segregation"
            barrier_failure = "Pedestrian-vehicle segregation control and banksman guidance protocol absent"
            precursor = "Vehicle line-of-fire struck-by collision in shared corridor"
            ai_recommendation = "Halt vehicle motion. Deploy certified banksman for all reversing maneuvers and erect physical pedestrian segregation barricades."
        elif "hot work" in act_lower:
            unsafe_act = "Spark-producing task initiated in proximity to combustible materials without fire watch"
            unsafe_condition = "Unshielded flammable vapor / combustible source within spark trajectory radius"
            barrier_failure = "Combustible clearance radius and dedicated fire watch barrier not established"
            precursor = "Thermal ignition of combustible hydrocarbons or flammable solvent vapors"
            ai_recommendation = "Extinguish open flame/arc. Maintain 10m combustible clearance, deploy certified fire watch with extinguisher, and verify continuous gas monitoring."
        elif "height" in act_lower:
            unsafe_act = "Worker transitioned across elevated structure without 100% continuous tie-off"
            unsafe_condition = "Unprotected leading edge or unanchored temporary work platform"
            barrier_failure = "100% fall protection tie-off and edge barricade barrier breached"
            precursor = "Fall from height (>1.8m) without secondary arrest anchorage"
            ai_recommendation = "Direct worker to attach lanyard to certified anchor immediately. Inspect personal fall-arrest system and install static lifeline before continuing."
        elif "housekeeping" in act_lower:
            unsafe_act = "Material placed protruding beyond designated storage bay boundaries"
            unsafe_condition = "Low-level walkway obstruction in designated personnel transit lane"
            barrier_failure = "Walkway clearance demarcation standard not maintained"
            precursor = "Low-energy slip, trip or fall in personnel walkway"
            ai_recommendation = "Relocate protruding dunnage and materials into marked storage bays to maintain clear 1-meter minimum walkway."
        elif re.search(r"\b(zone|entered|stepped|radius|perimeter|lift(ing)?|crane|breach)\b", full_text):
            unsafe_act = "Personnel entered demarcated exclusion boundary during active operation"
            unsafe_condition = "Uncontrolled personnel presence within active machinery operating radius"
            barrier_failure = "Physical / visual perimeter exclusion barrier breached"
            precursor = "Potential line-of-fire / struck-by exposure during mechanical lifting"
            ai_recommendation = "Immediately halt lifting activity. Sound audible exclusion alarm, evacuate all personnel from the zone perimeter, and verify human physical barrier restoration."
        elif re.search(r"\b(helmet|hard\s*hat|ppe|head\s+protection)\b", full_text):
            unsafe_act = "Personnel commenced task without donning mandatory Type-II industrial safety helmet"
            unsafe_condition = "Unprotected cranial exposure in an active industrial operational perimeter"
            barrier_failure = "Administrative PPE compliance check and pre-task donning verification failed"
            precursor = "Absence of personal impact protection against secondary dropped objects"
            ai_recommendation = "Direct worker to step out of active perimeter immediately to don compliant helmet with fastened chin strap. Conduct pre-task safety briefing before resuming."
        else:
            unsafe_act = "Non-adherence to documented safe work procedure"
            unsafe_condition = "Operating without validated barrier safeguards"
            barrier_failure = "Primary operational control barrier failed"
            precursor = "Uncontrolled operational risk exposure"
            ai_recommendation = "Pause operation and re-verify pre-start controls before continuing work."

        return {
            "activity": activity,
            "location": location,
            "equipment": equipment,
            "hazard": hazard,
            "unsafe_act": unsafe_act,
            "unsafe_condition": unsafe_condition,
            "barrier_failure": barrier_failure,
            "precursor": precursor,
            "ai_recommendation": ai_recommendation
        }
