from collections import Counter, defaultdict
from typing import List, Dict, Any
from models import SafetyReport, RecurringPattern

class PatternMiner:
    """
    Recurring Precursor Pattern Miner & Risk Prioritizer.
    Analyzes historical safety reports to detect systemic SIF precursor clusters,
    quantify high-risk locations/activities, and prioritize interventions.
    """

    def mine_patterns(self, reports: List[SafetyReport]) -> List[RecurringPattern]:
        """
        Groups repeated hazard, activity, location, and barrier combinations.
        Only reports with >= 2 occurrences are considered valid recurring patterns.
        """
        if not reports or len(reports) < 2:
            return []

        # Group by composite key: (location, activity)
        clusters = defaultdict(list)
        for r in reports:
            loc = r.location or "General Area"
            act = r.activity or "General Site Operations"
            key = (loc, act)
            clusters[key].append(r)

        patterns: List[RecurringPattern] = []
        for idx, (key, cluster_reports) in enumerate(clusters.items(), 1):
            count = len(cluster_reports)
            if count < 2:
                continue # Insufficient occurrences for a recurring pattern

            location, activity = key
            sif_count = sum(1 for r in cluster_reports if r.sif_potential)
            all_lsrs = set()
            for r in cluster_reports:
                all_lsrs.update(r.life_saving_rules)

            # Determine aggregate pattern risk
            if sif_count >= 2 or any(r.risk_level == "CRITICAL" for r in cluster_reports):
                pattern_risk = "CRITICAL"
            elif sif_count >= 1 or any(r.risk_level == "HIGH" for r in cluster_reports):
                pattern_risk = "HIGH"
            else:
                pattern_risk = "MEDIUM"

            # Dominant precursor and hazard
            precursor_counts = Counter([r.precursor for r in cluster_reports if r.precursor])
            dominant_precursor = precursor_counts.most_common(1)[0][0] if precursor_counts else "Systemic barrier failure"

            hazard_counts = Counter([r.hazard for r in cluster_reports if r.hazard])
            dominant_hazard = hazard_counts.most_common(1)[0][0] if hazard_counts else "Operational hazard"

            title = f"{activity} in {location}: {dominant_precursor}"

            patterns.append(RecurringPattern(
                pattern_id=f"PAT-{idx:03d}",
                title=title,
                occurrences=count,
                risk_level=pattern_risk,
                related_lsr=sorted(list(all_lsrs)),
                related_precursor=dominant_precursor,
                location=location,
                activity=activity
            ))

        # Sort patterns highest occurrences first
        patterns.sort(key=lambda p: (p.occurrences, p.risk_level == "CRITICAL"), reverse=True)
        return patterns

    def calculate_prioritization(self, reports: List[SafetyReport]) -> Dict[str, Any]:
        """
        Calculates transparent risk prioritization rankings based on SIF precursor density.
        
        Formula:
          SIF Precursor Density Score = min(100, int((sif_count * 25 + total_events * 8) * weight))
          where weight reflects concentration of high-risk events over total area activity.
        """
        if not reports:
            return {
                "high_risk_locations": [],
                "high_risk_activities": [],
                "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
                "top_life_saving_rules": []
            }

        # 1. Location Prioritization
        loc_stats = defaultdict(lambda: {"total": 0, "sif": 0, "high_risk": 0})
        for r in reports:
            stats = loc_stats[r.location]
            stats["total"] += 1
            if r.sif_potential:
                stats["sif"] += 1
            if r.risk_level in ["HIGH", "CRITICAL"]:
                stats["high_risk"] += 1

        high_risk_locations = []
        for loc, stats in loc_stats.items():
            # Transparent scoring: SIF occurrences carry 4x weight of standard observations
            density_score = min(100, (stats["sif"] * 35) + (stats["high_risk"] * 15) + (stats["total"] * 5))
            high_risk_locations.append({
                "location": loc,
                "score": density_score,
                "total_events": stats["total"],
                "sif_precursors": stats["sif"],
                "risk_category": "HIGH" if density_score >= 60 else ("MEDIUM" if density_score >= 35 else "LOW")
            })
        high_risk_locations.sort(key=lambda x: x["score"], reverse=True)

        # 2. Activity Prioritization
        act_stats = defaultdict(lambda: {"total": 0, "sif": 0})
        for r in reports:
            act_stats[r.activity]["total"] += 1
            if r.sif_potential:
                act_stats[r.activity]["sif"] += 1

        high_risk_activities = []
        for act, stats in act_stats.items():
            density_score = min(100, (stats["sif"] * 40) + (stats["total"] * 10))
            high_risk_activities.append({
                "activity": act,
                "score": density_score,
                "total_events": stats["total"],
                "sif_precursors": stats["sif"],
                "risk_category": "CRITICAL" if density_score >= 75 else ("HIGH" if density_score >= 50 else "MEDIUM")
            })
        high_risk_activities.sort(key=lambda x: x["score"], reverse=True)

        # 3. Risk Level Distribution
        risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for r in reports:
            if r.risk_level in risk_dist:
                risk_dist[r.risk_level] += 1

        # 4. Top Life-Saving Rules
        lsr_counter = Counter()
        for r in reports:
            for rule in r.life_saving_rules:
                lsr_counter[rule] += 1

        top_lsrs = [
            {"rule": rule, "count": count}
            for rule, count in lsr_counter.most_common(5)
        ]

        return {
            "high_risk_locations": high_risk_locations,
            "high_risk_activities": high_risk_activities,
            "risk_distribution": risk_dist,
            "top_life_saving_rules": top_lsrs
        }
