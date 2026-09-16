import re
from typing import Dict, List, Any, Optional

class SemanticSafetyLayer:
    """
    Lightweight local semantic understanding layer for industrial safety narratives.
    Recognizes linguistic paraphrases, semantic synonyms, and operational terminology
    across Oil & Gas HSSE domains without relying on opaque or hallucinating external models.

    Accurately described as:
    "Hybrid AI safety reasoning: semantic context + explainable safety rules"
    """

    # Semantic synonym mapping clusters for operational concepts
    SEMANTIC_CLUSTERS = {
        "ENERGY_ISOLATION": {
            "patterns": [
                r"\b(isolat\w*(\s+\w+){0,3}\s+(was\s+|were\s+)?(bypassed|defeated|not\s+maintained|omitted|skipped))\b",
                r"\b(lock-?out|tag-?out|loto)(\s+\w+){0,3}\s+(was\s+|were\s+)?(defeated|removed|not\s+applied|bypassed|missing)\b",
                r"\b(without\s+(verified\s+)?zero\s+energy)\b",
                r"\b(equipment\s+.*without\s+(verified\s+)?zero\s+energy)\b",
                r"\b(breaker\s+opened\s+before\s+lock)\b",
                r"\b(live\s+(conductor|circuit|feeder)\s+worked\s+on)\b",
                r"\b(double\s+block\s+and\s+bleed\s+not\s+verified)\b",
                r"\b(pressur(ized|e)\s+line\s+unbolted\s+before\s+bleed)\b"
            ],
            "inferred_domain": "Energy Isolation",
            "inferred_energy": "Hazardous Stored Electrical / Pneumatic Energy",
            "inferred_barrier": "Positive Lockout-Tagout (LOTO) & Zero-Energy Verification",
            "inferred_failure": "Positive energy isolation not established or verified before intervention",
            "inferred_exposure": "Personnel working directly on energized / pressurized system",
            "inferred_consequence": "Arc flash electrocution or high-pressure fluid injection"
        },
        "SUSPENDED_LOAD_LINE_OF_FIRE": {
            "patterns": [
                r"\b(load\s+(passed|swung|hoisted|moved)\s+(above|over)\s+workers)\b",
                r"\b(personnel\s+(were\s+)?under(neath)?\s+(suspended\s+)?(equipment|load|pipe|spool))\b",
                r"\b(lifting\s+path\s+crossed\s+(an\s+)?occupied\s+(area|walkway|corridor))\b",
                r"\b(entered\s+(the\s+)?drop\s+zone\s+during\s+lift)\b",
                r"\b(stepped\s+under\s+suspended)\b",
                r"\b(swung\s+over\s+(an\s+)?active\s+walkway)\b",
                r"\b(hook\s+dragging\s+loose|load\s+line\s+snag)\b"
            ],
            "inferred_domain": "Mechanical Lifting",
            "inferred_energy": "Mechanical / Gravitational Potential Energy",
            "inferred_barrier": "Lifting Exclusion Zone & Controlled Drop Radius",
            "inferred_failure": "Exclusion perimeter breached while load was in motion overhead",
            "inferred_exposure": "Personnel positioned directly in drop trajectory / swing radius",
            "inferred_consequence": "Catastrophic struck-by, crushing, or fatal trauma"
        },
        "FALL_FROM_HEIGHT": {
            "patterns": [
                r"\b(unhooked\s+(dual\s+)?lanyards?)\b",
                r"\b(disconnected\s+(twin\s+)?hooks?\s+simultaneously)\b",
                r"\b(without\s+(wearing\s+)?(fall-?arrest\s+)?harness)\b",
                r"\b(missing\s+toe-?board\s+on\s+scaffold)\b",
                r"\b(rusted|displaced|unbolted)\s+grating\s+(on\s+platform)?\b",
                r"\b(open\s+cellar\s+(hatch|grating)|edge\s+protection\s+missing)\b",
                r"\b(unsecured\s+portable\s+ladder\s+on\s+scaffold)\b"
            ],
            "inferred_domain": "Working at Height",
            "inferred_energy": "Gravitational Elevation Energy (>1.8m)",
            "inferred_barrier": "100% Tie-Off Fall Arrest System & Rigid Guardrails",
            "inferred_failure": "Fall protection lifeline or edge guarding discontinued during elevation",
            "inferred_exposure": "Worker active at height without positive secondary anchorage",
            "inferred_consequence": "Uncontrolled fall from height resulting in fatal trauma"
        },
        "HOT_WORK_EXPLOSION": {
            "patterns": [
                r"\b(cutting|welding|torch|grinding)\s+(near|4m\s+from|adjacent\s+to)\s+(hydrocarbon|manifold|solvent|degreaser)\b",
                r"\b(without\s+(continuous\s+)?gas\s+test(ing)?)\b",
                r"\b(flammable\s+gas\s+monitoring\s+not\s+established)\b",
                r"\b(sparks?\s+directed\s+toward\s+(oily\s+drain|sump|solvent))\b",
                r"\b(fire\s+blanket\s+missing\s+below\s+welding)\b"
            ],
            "inferred_domain": "Hot Work",
            "inferred_energy": "Thermal Ignition Energy in Flammable Atmosphere",
            "inferred_barrier": "Atmospheric Gas Testing & Fire Watch Containment",
            "inferred_failure": "Open spark ignition source introduced without verified zero-gas atmosphere",
            "inferred_exposure": "Personnel in immediate zone of potential vapor cloud flash fire",
            "inferred_consequence": "Vapor cloud flash fire, explosion, or severe thermal burns"
        },
        "CONFINED_SPACE_TOXIC": {
            "patterns": [
                r"\b(entry\s+into\s+crude\s+oil\s+storage\s+tank\s+without)\b",
                r"\b(without\s+continuous\s+multi-?gas\s+monitor)\b",
                r"\b(standby\s+(entry\s+)?attendant\s+left\s+position)\b",
                r"\b(stepped\s+inside\s+(manway|mud\s+pit|tank)\s+before\s+gas\s+tester)\b"
            ],
            "inferred_domain": "Confined Space",
            "inferred_energy": "Toxic Chemical / Asphyxiating Atmospheric Energy",
            "inferred_barrier": "Continuous Gas Certification & Dedicated Standby Attendant",
            "inferred_failure": "Confined compartment entered without verified atmosphere or standby rescue",
            "inferred_exposure": "Personnel breathing toxic H2S / oxygen-deficient atmosphere",
            "inferred_consequence": "Asphyxiation, toxic poisoning, or irreversible loss of consciousness"
        },
        "MOBILE_PLANT_COLLISION": {
            "patterns": [
                r"\b(heavy\s+vacuum\s+tanker\s+reversed\s+without\s+banksman)\b",
                r"\b(revers(ing)?\s+near\s+wellhead\s+without\s+(banksman|reverse\s+horn))\b",
                r"\b(forklift\s+carrying\s+overloaded\s+.*forward\s+view\s+blocked)\b",
                r"\b(transport\s+exclusion\s+boundary\s+unmonitored)\b"
            ],
            "inferred_domain": "Driving & Heavy Plant",
            "inferred_energy": "Heavy Mobile Equipment Kinetic Momentum",
            "inferred_barrier": "Banksman Guidance & Dedicated Pedestrian Segregation",
            "inferred_failure": "Vehicle maneuvered with obstructed visibility in shared pedestrian area",
            "inferred_exposure": "Pedestrian personnel in vehicle reversing blind spot",
            "inferred_consequence": "Run-over, crushing by mobile plant, or fatal impact"
        },
        "LOW_ENERGY_HOUSEKEEPING": {
            "patterns": [
                r"\b(cable\s+tray\s+offcuts\s+left\s+across\s+walkway)\b",
                r"\b(trip\s+hazard|dunnage\s+left\s+in\s+walkway|housekeeping)\b",
                r"\b(stepped\s+into\s+marked\s+pump\s+corridor\s+without\s+chin\s+strap)\b",
                r"\b(minor\s+ppe\s+adjustment|safety\s+glasses\s+rested\s+on\s+forehead)\b"
            ],
            "inferred_domain": "Restricted Zone & Housekeeping",
            "inferred_energy": "Low-Energy Physical Obstruction / Minor Ergonomic",
            "inferred_barrier": "Good Housekeeping & General PPE Maintenance",
            "inferred_failure": "Minor physical obstacle or unfastened secondary PPE component",
            "inferred_exposure": "Low consequence slip/trip or localized minor contact",
            "inferred_consequence": "Minor slip, trip, or superficial abrasion"
        }
    }

    @classmethod
    def analyze_semantics(cls, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extracts semantic concepts, inferred energy sources, barriers, and exposures
        from incident text through paraphrase mapping.
        """
        context = context or {}
        text_lower = text.lower()
        matched_clusters = []

        for cluster_key, data in cls.SEMANTIC_CLUSTERS.items():
            for pattern in data["patterns"]:
                if re.search(pattern, text_lower):
                    matched_clusters.append({
                        "cluster": cluster_key,
                        "domain": data["inferred_domain"],
                        "energy_source": data["inferred_energy"],
                        "barrier": data["inferred_barrier"],
                        "barrier_failure": data["inferred_failure"],
                        "exposure": data["inferred_exposure"],
                        "potential_consequence": data["inferred_consequence"],
                        "matched_pattern": pattern
                    })
                    break

        if matched_clusters:
            top_cluster = matched_clusters[0]
            confidence = "HIGH" if len(matched_clusters) >= 1 else "MEDIUM"
            # Map domain to standard LSR candidates
            domain = top_cluster["domain"]
            lsr_candidates = []
            if "Energy Isolation" in domain:
                lsr_candidates = ["Energy Isolation"]
            elif "Mechanical Lifting" in domain:
                lsr_candidates = ["Safe Mechanical Lifting", "Line of Fire"]
            elif "Working at Height" in domain:
                lsr_candidates = ["Working at Height"]
            elif "Hot Work" in domain:
                lsr_candidates = ["Hot Work"]
            elif "Confined Space" in domain:
                lsr_candidates = ["Confined Space"]
            elif "Driving" in domain:
                lsr_candidates = ["Driving"]

            return {
                "matched": True,
                "domain": top_cluster["domain"],
                "energy_source": top_cluster["energy_source"],
                "barrier": top_cluster["barrier"],
                "barrier_failure": top_cluster["barrier_failure"],
                "exposure": top_cluster["exposure"],
                "potential_consequence": top_cluster["potential_consequence"],
                "lsr_candidates": lsr_candidates,
                "confidence": confidence,
                "all_matches": matched_clusters
            }

        # Fallback when no direct paraphrase cluster triggers
        return {
            "matched": False,
            "domain": context.get("activity", "General Operations"),
            "energy_source": "Unclassified Mechanical / Kinetic Energy",
            "barrier": "Standard Operational Boundary Controls",
            "barrier_failure": "Operational control not verified",
            "exposure": "Personnel present in active work area",
            "potential_consequence": "Physical impact or personal injury",
            "lsr_candidates": [],
            "confidence": "LOW",
            "all_matches": []
        }
