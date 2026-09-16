import re
from typing import List, Dict, Any, Optional

# Official 9 IOGP Life-Saving Rules (IOGP Report 459 standard)
LSR_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Safe Mechanical Lifting": {
        "why": "Personnel or load were involved in mechanical lifting without controlled path or integrity.",
        "keywords": [
            "lifting", "crane", "hoist", "suspended load", "rigging", "sling",
            "mechanical lifting", "lifting exclusion zone", "lift plan", "winch", "boom"
        ],
        "patterns": [
            r"\blift(ing)?\b",
            r"\bcrane\b",
            r"\bsuspended\s+load\b",
            r"\brigg(ing)?\b",
            r"\bhoist\b"
        ]
    },
    "Line of Fire": {
        "why": "Personnel were positioned directly in the trajectory, drop radius, or swing path of hazardous equipment.",
        "keywords": [
            "line of fire", "suspended load", "falling object", "underneath load",
            "exclusion zone", "moving machinery", "swing radius", "struck by",
            "pinch point", "drop hazard", "crush hazard", "trajectory", "recoil"
        ],
        "patterns": [
            r"\bline\s+of\s+fire\b",
            r"\bsuspended\s+load\b",
            r"\bunder(neath)?\s+(the\s+)?load\b",
            r"\bexclusion\s+zone\b",
            r"\bcrush(ing)?\b",
            r"\bstruck\s+by\b",
            r"\bswing\s+radius\b"
        ]
    },
    "Bypassing Safety Controls": {
        "why": "Safety critical barrier, physical exclusion perimeter, or procedure was compromised or overridden.",
        "keywords": [
            "bypass", "override", "barrier breached", "barrier failed", "interlock",
            "safety device disabled", "boundary breached", "perimeter breached",
            "disregarded control", "unauthorized entry into restricted"
        ],
        "patterns": [
            r"\bbypass(ing)?\b",
            r"\bbarrier\s+(breach(ed)?|fail(ed)?|restor(ed)?)\b",
            r"\bperimeter\s+breach(ed)?\b",
            r"\bcontrol\s+breach(ed)?\b",
            r"\boverrid(e|ing)\b"
        ]
    },
    "Work Authorisation": {
        "why": "Task executed without required permit to work, authorization verification, or formal clearance.",
        "keywords": [
            "permit to work", "ptw", "safety passport", "authorization", "permit",
            "pre-start check", "unauthorized task", "toolbox talk", "isolation permit"
        ],
        "patterns": [
            r"\bpermit\b",
            r"\bpassport\b",
            r"\bauthoris(ation|ed)\b",
            r"\bauthoriz(ation|ed)\b",
            r"\bptw\b"
        ]
    },
    "Energy Isolation": {
        "why": "Stored electrical, hydraulic, or pneumatic energy was not positively isolated and verified zero energy.",
        "keywords": [
            "lockout", "tagout", "loto", "energy isolation", "de-energized",
            "stored energy", "pressurized line", "zero energy", "electrical isolation"
        ],
        "patterns": [
            r"\bloto\b",
            r"\blockout\b",
            r"\btagout\b",
            r"\benergy\s+isolation\b",
            r"\bde-?energiz\b"
        ]
    },
    "Working at Height": {
        "why": "Work performed at elevation (>1.8m) without 100% continuous fall protection anchorage.",
        "keywords": [
            "working at height", "scaffold", "fall protection", "safety harness",
            "ladder", "elevated platform", "leading edge", "manlift", "fall hazard"
        ],
        "patterns": [
            r"\bheight\b",
            r"\bscaffold(ing)?\b",
            r"\bharness\b",
            r"\bfall\s+(protection|hazard)\b",
            r"\belevated\b"
        ]
    },
    "Hot Work": {
        "why": "Open flame, sparks, or thermal ignition source operated without continuous gas testing.",
        "keywords": [
            "hot work", "welding", "cutting", "grinding", "spark", "open flame",
            "explosive atmosphere", "gas test", "fire watch"
        ],
        "patterns": [
            r"\bhot\s+work\b",
            r"\bweld(ing)?\b",
            r"\bflame\b",
            r"\bgrind(ing)?\b",
            r"\bspark\b"
        ]
    },
    "Confined Space": {
        "why": "Enclosed or oxygen-deficient compartment entered without atmosphere certification or standby attendant.",
        "keywords": [
            "confined space", "vessel entry", "tank", "pit", "manhole",
            "toxic atmosphere", "oxygen deficiency", "enclosed chamber"
        ],
        "patterns": [
            r"\bconfined\s+space\b",
            r"\bvessel\b",
            r"\bmanhole\b",
            r"\btank\s+entry\b"
        ]
    },
    "Driving": {
        "why": "Heavy plant or vehicle maneuvered without banksman, seatbelt, or pedestrian segregation.",
        "keywords": [
            "driving", "seatbelt", "vehicle", "speeding", "forklift transit",
            "collision", "mobile equipment transit", "rollover"
        ],
        "patterns": [
            r"\bdriv(ing|e)?\b",
            r"\bvehicle\b",
            r"\bseatbelt\b",
            r"\bforklift\b"
        ]
    }
}

class LSRClassifier:
    """
    Multi-label IOGP Life-Saving Rules Classifier.
    Maps event descriptions, hazards, activities, and barrier failures
    to applicable official IOGP rules without forcing rules where none apply.
    """

    def classify(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Classifies input incident text and context to applicable IOGP Life-Saving Rules.
        Returns a list of matched rule names (multi-label, capped to maximum 3).
        """
        details = self.classify_detailed(text, context)
        # Cap to maximum 3 rules to prevent over-classification
        return [d["rule"] for d in details[:3]]

    def classify_detailed(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Returns structured IOGP Life-Saving Rule mappings with confidence and evidence.
        """
        if not text:
            return []

        # Combine text and contextual fields
        corpus = [text.lower()]
        if context:
            for k in ["activity", "hazard", "barrier_failure", "unsafe_condition", "event_type"]:
                val = context.get(k)
                if val:
                    corpus.append(str(val).lower())
        full_text = " ".join(corpus)

        matched_items = []

        for rule_name, rule_data in LSR_DEFINITIONS.items():
            evidence_snippets = []
            confidence = "LOW"

            # Check regex patterns
            for pattern in rule_data["patterns"]:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    evidence_snippets.append(f"Pattern matched: '{match.group(0)}'")
                    confidence = "HIGH"
                    break

            # Check keyword presence
            if not evidence_snippets:
                for kw in rule_data["keywords"]:
                    if kw in full_text:
                        evidence_snippets.append(f"Keyword observed: '{kw}'")
                        confidence = "MEDIUM"
                        break

            if evidence_snippets:
                matched_items.append({
                    "rule": rule_name,
                    "confidence": confidence,
                    "why": rule_data["why"],
                    "evidence": evidence_snippets
                })

        # Return max 3 most relevant rules
        return matched_items[:3]
