"""
SHRAMRAKSHAK: Authoritative SIH Density Calculation Service
SIH 2026 Problem Statement: SIH26165

Enforces Rule 4 & 5 (Phases 14 & 15):
REPORTED SIF-PRECURSOR DENSITY = (SIF-POTENTIAL eligible reports / total eligible reports) * 100
If denominator = 0: None ("N/A")

Provides a single authoritative calculation service that feeds:
- Database-derived analytics
- API endpoints (/api/analytics/summary, /api/events/stats/summary)
- Frontend dashboard metrics
- PDF report generation
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict

SIH_DENSITY_DISCLAIMER = (
    "Reported SIF-precursor density is a reporting-based indicator; "
    "it is not an absolute probability of harm."
)


def compute_sih_density(
    sif_potential_count: int,
    total_eligible_reports: int
) -> Optional[float]:
    """
    Authoritative mathematical definition:
    REPORTED SIF-PRECURSOR DENSITY = (SIF-POTENTIAL / TOTAL ELIGIBLE) * 100
    If denominator = 0: returns None (represented as 'N/A' in UI/PDF).
    """
    if total_eligible_reports <= 0:
        return None
    return round((sif_potential_count / total_eligible_reports) * 100, 1)


def format_sih_density(density: Optional[float]) -> str:
    """Formats density as string percentage or 'N/A'."""
    if density is None:
        return "N/A"
    return f"{density:.1f}%"


class SIHDensityService:
    """
    Single authoritative calculation service for SIH metrics across
    API, Database, Dashboard, and PDF reports.
    """

    @staticmethod
    def calculate_from_events(events: List[Any]) -> Dict[str, Any]:
        """
        Calculates authoritative SIH metrics from a list of Canonical SafetyEvents or dicts.
        """
        total = len(events)
        sif_count = 0
        review_count = 0
        no_sif_count = 0

        # Grouping containers
        by_site = defaultdict(lambda: {
            "total": 0, "sif": 0, "review": 0, "no_sif": 0,
            "barriers": defaultdict(int), "lsrs": defaultdict(int)
        })
        by_activity = defaultdict(lambda: {
            "total": 0, "sif": 0, "review": 0, "no_sif": 0,
            "barriers": defaultdict(int), "lsrs": defaultdict(int)
        })
        by_lsr = defaultdict(lambda: {"total": 0, "sif": 0})

        for ev in events:
            # Handle both SafetyEvent objects and dicts
            sif_st = getattr(ev, "sif_status", None)
            if sif_st is None and isinstance(ev, dict):
                sif_st = ev.get("sif_status")
            sif_st_str = sif_st.value if hasattr(sif_st, "value") else str(sif_st or "")

            site = getattr(ev, "site", None) or (ev.get("site") if isinstance(ev, dict) else None) or "OIL Field Duliajan"
            activity = getattr(ev, "activity", None) or (ev.get("activity") if isinstance(ev, dict) else None) or "Operational Work"
            
            barriers = getattr(ev, "barrier", []) or (ev.get("barrier", []) if isinstance(ev, dict) else [])
            if isinstance(barriers, str):
                barriers = [barriers]
            
            lsrs = getattr(ev, "lsr", []) or (ev.get("lsr", []) or ev.get("life_saving_rules", []) if isinstance(ev, dict) else [])
            if isinstance(lsrs, str):
                lsrs = [lsrs]

            if sif_st_str == "SIF-POTENTIAL":
                sif_count += 1
                status_cat = "sif"
            elif sif_st_str == "REVIEW_REQUIRED":
                review_count += 1
                status_cat = "review"
            else:
                no_sif_count += 1
                status_cat = "no_sif"

            # Update site metrics
            s_data = by_site[site]
            s_data["total"] += 1
            s_data[status_cat] += 1
            for b in barriers:
                if b and b != "UNKNOWN":
                    s_data["barriers"][b] += 1
            for rule in lsrs:
                if rule:
                    s_data["lsrs"][rule] += 1
                    by_lsr[rule]["total"] += 1
                    if status_cat == "sif":
                        by_lsr[rule]["sif"] += 1

            # Update activity metrics
            a_data = by_activity[activity]
            a_data["total"] += 1
            a_data[status_cat] += 1
            for b in barriers:
                if b and b != "UNKNOWN":
                    a_data["barriers"][b] += 1
            for rule in lsrs:
                if rule:
                    a_data["lsrs"][rule] += 1

        overall_density = compute_sih_density(sif_count, total)

        # Build site rankings
        site_rankings = []
        for site_name, s in by_site.items():
            d = compute_sih_density(s["sif"], s["total"])
            dominant_barrier = max(s["barriers"].items(), key=lambda x: x[1])[0] if s["barriers"] else "General Control Failure"
            dominant_lsr = max(s["lsrs"].items(), key=lambda x: x[1])[0] if s["lsrs"] else "ENERGY_ISOLATION"
            site_rankings.append({
                "site": site_name,
                "location": site_name,
                "total_reports": s["total"],
                "sif_potential_count": s["sif"],
                "sif_count": s["sif"],
                "review_required_count": s["review"],
                "no_sif_count": s["no_sif"],
                "sif_density_pct": d,
                "sif_density_display": format_sih_density(d),
                "dominant_control_failure": dominant_barrier,
                "dominant_lsr": dominant_lsr,
                "small_sample_warning": s["total"] < 5,
                "priority_label": "CRITICAL" if (d is not None and d >= 50) else ("HIGH" if (d is not None and d >= 25) else "MEDIUM")
            })
        site_rankings.sort(key=lambda x: (x["sif_density_pct"] or 0, x["sif_count"]), reverse=True)

        # Build activity rankings
        activity_rankings = []
        for act_name, a in by_activity.items():
            d = compute_sih_density(a["sif"], a["total"])
            dominant_barrier = max(a["barriers"].items(), key=lambda x: x[1])[0] if a["barriers"] else "Standard Operating Barrier"
            dominant_lsr = max(a["lsrs"].items(), key=lambda x: x[1])[0] if a["lsrs"] else "BYPASS_SAFETY_CONTROLS"
            activity_rankings.append({
                "activity": act_name,
                "activity_name": act_name,
                "total_reports": a["total"],
                "sif_potential_count": a["sif"],
                "sif_count": a["sif"],
                "review_required_count": a["review"],
                "no_sif_count": a["no_sif"],
                "sif_density_pct": d,
                "sif_density_display": format_sih_density(d),
                "dominant_control_failure": dominant_barrier,
                "dominant_lsr": dominant_lsr,
                "small_sample_warning": a["total"] < 5,
                "priority_label": "CRITICAL" if (d is not None and d >= 50) else ("HIGH" if (d is not None and d >= 25) else "MEDIUM")
            })
        activity_rankings.sort(key=lambda x: (x["sif_density_pct"] or 0, x["sif_count"]), reverse=True)

        # Build LSR summary
        lsr_summary = []
        for rule, data in by_lsr.items():
            d = compute_sih_density(data["sif"], data["total"])
            lsr_summary.append({
                "rule": rule,
                "total_reports": data["total"],
                "sif_count": data["sif"],
                "sif_density_pct": d,
                "sif_density_display": format_sih_density(d)
            })
        lsr_summary.sort(key=lambda x: x["sif_count"], reverse=True)

        return {
            "total_reports": total,
            "total_eligible_reports": total,
            "reports_analyzed": total,
            "sif_potential_count": sif_count,
            "sif_count": sif_count,
            "review_required_count": review_count,
            "review_count": review_count,
            "no_sif_potential_count": no_sif_count,
            "no_sif_count": no_sif_count,
            "reported_sif_density_pct": overall_density,
            "sih_density_pct": overall_density,
            "sif_density_pct": overall_density if overall_density is not None else 0.0,
            "sih_density_formatted": format_sih_density(overall_density),
            "sif_density_display": format_sih_density(overall_density),
            "site_rankings": site_rankings,
            "activity_rankings": activity_rankings,
            "lsr_summary": lsr_summary,
            "disclaimer": SIH_DENSITY_DISCLAIMER
        }

    @classmethod
    def calculate_from_db(cls, db_instance: Optional[Any] = None) -> Dict[str, Any]:
        """Calculates metrics directly from active SQLite database events table."""
        if db_instance is None:
            try:
                from backend.database import db
            except ImportError:
                from database import db
            db_instance = db
        events = db_instance.list_events(limit=None)
        return cls.calculate_from_events(events)


sih_density_service = SIHDensityService()
