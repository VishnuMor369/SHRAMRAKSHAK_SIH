import io
import re
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from nlp_engine.event_normalizer import EventNormalizer
from nlp_engine.lsr_classifier import LSRClassifier
from nlp_engine.sif_classifier import SIFClassifier
from nlp_engine.precursor_extractor import PrecursorExtractor
from nlp_engine.sif_pathway_engine import SIFPathwayEngine

class ColumnMapper:
    """
    Auto-detects and maps dataset columns dynamically for any uploaded CSV layout.
    """

    NARRATIVE_CANDIDATES = [
        "final narrative", "narrative", "description", "incident_description",
        "report_text", "details", "unsafe_act_description", "observation", "summary"
    ]
    DATE_CANDIDATES = [
        "eventdate", "date", "incident_date", "report_date", "created_at", "timestamp"
    ]
    LOCATION_CANDIDATES = [
        "employer", "location", "site", "plant", "facility", "address1", "city", "state", "department"
    ]
    ACTIVITY_CANDIDATES = [
        "eventtitle", "activity", "operation", "category", "job_type", "task_type", "event"
    ]
    HAZARD_CANDIDATES = [
        "naturetitle", "nature", "source title", "sourcetitle", "hazard", "risk_type"
    ]
    GROUND_TRUTH_CANDIDATES = [
        "hospitalized", "amputation", "loss of eye", "sif_potential", "severity", "is_sif"
    ]

    @classmethod
    def auto_map_columns(cls, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        cols = {c: str(c).strip().lower() for c in df.columns}
        
        narrative_col = None
        for cand in cls.NARRATIVE_CANDIDATES:
            match = [orig for orig, lwr in cols.items() if cand in lwr]
            if match:
                narrative_col = match[0]
                break

        date_col = None
        for cand in cls.DATE_CANDIDATES:
            match = [orig for orig, lwr in cols.items() if cand in lwr]
            if match:
                date_col = match[0]
                break

        location_col = None
        for cand in cls.LOCATION_CANDIDATES:
            match = [orig for orig, lwr in cols.items() if cand in lwr]
            if match:
                location_col = match[0]
                break

        activity_col = None
        for cand in cls.ACTIVITY_CANDIDATES:
            match = [orig for orig, lwr in cols.items() if cand in lwr]
            if match:
                activity_col = match[0]
                break

        hazard_col = None
        for cand in cls.HAZARD_CANDIDATES:
            match = [orig for orig, lwr in cols.items() if cand in lwr]
            if match:
                hazard_col = match[0]
                break

        ground_truth_cols = []
        for cand in cls.GROUND_TRUTH_CANDIDATES:
            match = [orig for orig, lwr in cols.items() if cand in lwr]
            if match:
                ground_truth_cols.append(match[0])

        return {
            "narrative_col": narrative_col or (df.columns[0] if len(df.columns) > 0 else None),
            "date_col": date_col,
            "location_col": location_col,
            "activity_col": activity_col,
            "hazard_col": hazard_col,
            "ground_truth_cols": ground_truth_cols
        }

class DataQualityValidator:
    """
    Validates uploaded dataset health, missing values, duplicates, and usable rows.
    """

    @staticmethod
    def validate(df: pd.DataFrame, mapping: Dict[str, Optional[str]], file_name: str = "uploaded_dataset.csv") -> Dict[str, Any]:
        total_rows = len(df)
        narrative_col = mapping.get("narrative_col")

        missing_narratives = df[narrative_col].isnull().sum() if narrative_col in df else total_rows
        empty_text_rows = df[df[narrative_col].astype(str).str.strip() == ""].shape[0] if narrative_col in df else 0

        # Duplicate check on narrative text
        duplicate_rows = df.duplicated(subset=[narrative_col]).sum() if narrative_col in df else 0

        # Usable records
        usable_df = df.dropna(subset=[narrative_col]) if narrative_col in df else pd.DataFrame()
        if narrative_col in usable_df:
            usable_df = usable_df[usable_df[narrative_col].astype(str).str.strip() != ""]
        
        usable_count = len(usable_df)
        invalid_count = total_rows - usable_count

        date_col = mapping.get("date_col")
        missing_dates = df[date_col].isnull().sum() if date_col and date_col in df else total_rows

        location_col = mapping.get("location_col")
        missing_locations = df[location_col].isnull().sum() if location_col and location_col in df else total_rows

        activity_col = mapping.get("activity_col")
        missing_activities = df[activity_col].isnull().sum() if activity_col and activity_col in df else total_rows

        # Calculate Data Health Score (0 - 100%)
        health_score = 100.0
        if total_rows > 0:
            health_score -= (invalid_count / total_rows) * 50.0
            health_score -= (duplicate_rows / total_rows) * 20.0
            health_score -= (missing_locations / total_rows) * 15.0
            health_score -= (missing_dates / total_rows) * 15.0
        health_score = max(10.0, round(health_score, 1))

        warnings = []
        if duplicate_rows > 0:
            warnings.append(f"Found {duplicate_rows} duplicate report narratives.")
        if missing_locations > 0:
            warnings.append(f"{missing_locations} records are missing explicit site/location fields.")
        if missing_dates > 0:
            warnings.append(f"{missing_dates} records are missing incident dates.")
        if usable_count == 0:
            warnings.append("CRITICAL: No usable report narratives found in the uploaded file.")

        return {
            "file_name": file_name,
            "total_rows": total_rows,
            "usable_records": usable_count,
            "invalid_rows": invalid_count,
            "duplicate_rows": int(duplicate_rows),
            "missing_text_count": int(missing_narratives + empty_text_rows),
            "missing_location_count": int(missing_locations),
            "missing_activity_count": int(missing_activities),
            "missing_date_count": int(missing_dates),
            "detected_columns": mapping,
            "health_score": health_score,
            "warnings": warnings,
            "all_columns": df.columns.tolist()
        }

class DatasetProcessor:
    """
    Batch processes dataset reports through the SHRAMRAKSHAK NLP/SIF Analytics Pipeline.
    """

    def __init__(self):
        self.normalizer = EventNormalizer()
        self.lsr_classifier = LSRClassifier()
        self.sif_classifier = SIFClassifier()
        self.precursor_extractor = PrecursorExtractor()
        self.pathway_engine = SIFPathwayEngine()

    def process_dataset(
        self,
        df: pd.DataFrame,
        mapping: Dict[str, Optional[str]],
        max_rows: Optional[int] = None,
        progress_callback=None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:

        narrative_col = mapping["narrative_col"]
        date_col = mapping.get("date_col")
        location_col = mapping.get("location_col")
        activity_col = mapping.get("activity_col")
        hazard_col = mapping.get("hazard_col")
        ground_truth_cols = mapping.get("ground_truth_cols", [])

        # Filter valid rows
        usable_df = df.dropna(subset=[narrative_col]).copy()
        usable_df = usable_df[usable_df[narrative_col].astype(str).str.strip() != ""]

        if max_rows and len(usable_df) > max_rows:
            usable_df = usable_df.head(max_rows)

        total_to_process = len(usable_df)
        processed_reports: List[Dict[str, Any]] = []

        actual_ground_truths = []
        predicted_sif_labels = []

        start_time = time.time()

        for idx, (_, row) in enumerate(usable_df.iterrows()):
            raw_text = str(row[narrative_col]).strip()
            report_id = f"REP-DATA-{str(row.get('ID', row.get('UPA', idx + 1))).split('.')[0]}"

            # Parse date
            date_val = str(row[date_col]) if date_col and date_col in row and pd.notnull(row[date_col]) else "Unknown Date"

            # Parse location & employer
            loc_val = str(row[location_col]) if location_col and location_col in row and pd.notnull(row[location_col]) else "Oil Field Site"
            city_val = str(row.get("City", "")) if "City" in row and pd.notnull(row["City"]) else ""
            state_val = str(row.get("State", "")) if "State" in row and pd.notnull(row["State"]) else ""
            full_location = f"{loc_val} ({city_val}, {state_val})".strip(" (,) ") if (city_val or state_val) else loc_val

            # Parse activity & hazard
            act_val = str(row[activity_col]) if activity_col and activity_col in row and pd.notnull(row[activity_col]) else ""
            haz_val = str(row[hazard_col]) if hazard_col and hazard_col in row and pd.notnull(row[hazard_col]) else ""

            # Check ground truth severity if available
            ground_truth_sif = None
            if ground_truth_cols:
                is_severe = False
                for gt_col in ground_truth_cols:
                    val = row.get(gt_col, 0)
                    if pd.notnull(val) and (str(val).strip() in ['1', '1.0', 'True', 'true', 'YES', 'yes'] or (isinstance(val, (int, float)) and val > 0)):
                        is_severe = True
                        break
                ground_truth_sif = is_severe
                actual_ground_truths.append(ground_truth_sif)

            # 1. NLP Preprocessing & Entity Extraction
            context = {
                "event_type": "DATASET_INCIDENT",
                "location": full_location,
                "activity": act_val or "Industrial Operation",
                "hazard": haz_val or "Operational Hazard"
            }
            extracted = self.precursor_extractor.extract(raw_text, context)
            context.update(extracted)

            # 2. Multi-Label IOGP Life-Saving Rules
            lsr_detailed = self.lsr_classifier.classify_detailed(raw_text, context)
            lsr_rules = [item["rule"] for item in lsr_detailed]

            # 3. Explainable SIF Classification
            sif_pot, risk_score, risk_lvl, reason, why_flagged = self.sif_classifier.classify(raw_text, context)
            predicted_sif_labels.append(sif_pot)

            # 4. Deterministic SIF Pathway Generation
            norm_ev = self.normalizer.normalize_hsse_report({
                "id": report_id,
                "description": raw_text,
                "location": full_location,
                "activity": extracted["activity"],
                "hazard": extracted["hazard"],
                "barrier_failure": extracted["barrier_failure"]
            })
            pathway = self.pathway_engine.analyze_event(norm_ev, {"activity": extracted["activity"], "location": full_location, "life_saving_rules": lsr_rules})

            # Construct final report item
            report_item = {
                "report_id": report_id,
                "source": "DATASET_REPORT",
                "event_type": "SAFETY_INCIDENT",
                "timestamp": date_val,
                "location": full_location,
                "employer": loc_val,
                "activity": extracted["activity"],
                "description": raw_text,
                "hazard": extracted["hazard"],
                "energy_source": pathway.get("energy_source"),
                "exposure": pathway.get("exposure"),
                "barrier": pathway.get("barrier"),
                "unsafe_act": extracted.get("unsafe_act"),
                "unsafe_condition": extracted.get("unsafe_condition"),
                "barrier_failure": extracted.get("barrier_failure"),
                "potential_consequence": pathway.get("potential_consequence"),
                "sif_pathway": pathway.get("sif_pathway"),
                "sif_potential": sif_pot,
                "ground_truth_sif": ground_truth_sif,
                "risk_score": risk_score,
                "risk_level": risk_lvl,
                "confidence": 85 if len(why_flagged) > 1 else 70,
                "confidence_level": "HIGH" if len(why_flagged) > 1 else "MEDIUM",
                "evidence_strength": "HIGH",
                "needs_hse_review": (risk_score >= 60 and not sif_pot),
                "life_saving_rules": lsr_rules,
                "lsr_evidence": lsr_detailed,
                "precursor": extracted["precursor"],
                "reason": reason,
                "why_flagged": why_flagged,
                "ai_recommendation": extracted["ai_recommendation"],
                "recommended_action": pathway.get("recommended_action") or pathway.get("corrective_action"),
                "is_demo_sample": False
            }

            processed_reports.append(report_item)

            # Progress callback
            if progress_callback and (idx % 50 == 0 or idx == total_to_process - 1):
                prog = 0.1 + (0.8 * ((idx + 1) / total_to_process))
                progress_callback(prog, f"Processed {idx + 1} of {total_to_process} safety reports...")

        elapsed_sec = round(time.time() - start_time, 2)

        # Evaluate ML performance metrics if ground truth labels exist
        model_metrics = None
        if len(actual_ground_truths) == len(predicted_sif_labels) and len(actual_ground_truths) > 0:
            tp = sum(1 for a, p in zip(actual_ground_truths, predicted_sif_labels) if a and p)
            fp = sum(1 for a, p in zip(actual_ground_truths, predicted_sif_labels) if not a and p)
            fn = sum(1 for a, p in zip(actual_ground_truths, predicted_sif_labels) if a and not p)
            tn = sum(1 for a, p in zip(actual_ground_truths, predicted_sif_labels) if not a and not p)

            precision = round((tp / (tp + fp)) * 100, 1) if (tp + fp) > 0 else 0.0
            recall = round((tp / (tp + fn)) * 100, 1) if (tp + fn) > 0 else 0.0
            f1 = round((2 * precision * recall / (precision + recall)), 1) if (precision + recall) > 0 else 0.0
            accuracy = round(((tp + tn) / len(actual_ground_truths)) * 100, 1)

            model_metrics = {
                "has_ground_truth": True,
                "total_evaluated": len(actual_ground_truths),
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "confusion_matrix": {"TP": tp, "FP": fp, "FN": fn, "TN": tn}
            }
        else:
            model_metrics = {
                "has_ground_truth": False,
                "note": "Domain-rule + Semantic NLP Hybrid Model evaluated without pre-existing SIF labels."
            }

        # Build 9-Section Final HSE Intelligence Report
        summary_report = self._build_9_section_report(processed_reports, model_metrics, elapsed_sec)

        return processed_reports, summary_report

    def _build_9_section_report(
        self,
        reports: List[Dict[str, Any]],
        model_metrics: Optional[Dict[str, Any]],
        elapsed_sec: float
    ) -> Dict[str, Any]:

        total_reports = len(reports)
        sif_reports = [r for r in reports if r["sif_potential"]]
        sif_count = len(sif_reports)
        non_sif_count = total_reports - sif_count
        sif_density_pct = round((sif_count / total_reports) * 100, 1) if total_reports > 0 else 0.0

        # Risk distribution
        risk_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for r in reports:
            risk_dist[r.get("risk_level", "MEDIUM")] = risk_dist.get(r.get("risk_level", "MEDIUM"), 0) + 1

        # Section 3: IOGP Life-Saving Rules breakdown
        lsr_counts: Dict[str, Dict[str, Any]] = {}
        for r in reports:
            for rule in r.get("life_saving_rules", []):
                if rule not in lsr_counts:
                    lsr_counts[rule] = {"rule": rule, "count": 0, "sif_count": 0, "activities": set(), "locations": set()}
                lsr_counts[rule]["count"] += 1
                if r["sif_potential"]:
                    lsr_counts[rule]["sif_count"] += 1
                if r.get("activity"):
                    lsr_counts[rule]["activities"].add(r["activity"])
                if r.get("location"):
                    lsr_counts[rule]["locations"].add(r["location"])

        lsr_list = []
        for rule, data in lsr_counts.items():
            density = round((data["sif_count"] / data["count"]) * 100, 1) if data["count"] > 0 else 0.0
            lsr_list.append({
                "rule": rule,
                "count": data["count"],
                "sif_count": data["sif_count"],
                "sif_density_pct": density,
                "top_activities": list(data["activities"])[:3],
                "top_locations": list(data["locations"])[:3]
            })
        lsr_list.sort(key=lambda x: x["sif_count"], reverse=True)

        # Section 4: Recurring SIF Precursor Patterns (Activity + Location + Barrier Failure)
        pattern_groups: Dict[str, Dict[str, Any]] = {}
        for r in reports:
            act = r.get("activity", "General Operations")
            loc = r.get("location", "Site Area")
            bar_fail = r.get("barrier_failure") or r.get("precursor") or "Unverified Safety Control"
            
            key = f"{act} | {bar_fail}"
            if key not in pattern_groups:
                pattern_groups[key] = {
                    "pattern_id": f"PAT-DATA-{len(pattern_groups)+1:03d}",
                    "title": f"{bar_fail} during {act}",
                    "activity": act,
                    "location": loc,
                    "locations": set([loc]),
                    "barrier_failure": bar_fail,
                    "occurrences": 0,
                    "sif_potential_count": 0,
                    "related_lsr": set(r.get("life_saving_rules", []))
                }
            pattern_groups[key]["occurrences"] += 1
            pattern_groups[key]["locations"].add(loc)
            if r["sif_potential"]:
                pattern_groups[key]["sif_potential_count"] += 1
            pattern_groups[key]["related_lsr"].update(r.get("life_saving_rules", []))

        recurring_patterns = []
        for data in pattern_groups.values():
            density = round((data["sif_potential_count"] / data["occurrences"]) * 100, 1) if data["occurrences"] > 0 else 0.0
            recurring_patterns.append({
                "pattern_id": data["pattern_id"],
                "title": data["title"],
                "activity": data["activity"],
                "location": list(data["locations"])[0] if data["locations"] else data["location"],
                "locations": list(data["locations"])[:5],
                "barrier_failure": data["barrier_failure"],
                "occurrences": data["occurrences"],
                "sif_potential_count": data["sif_potential_count"],
                "sif_density_pct": density,
                "risk_level": "CRITICAL" if density >= 60 else "HIGH" if density >= 35 else "MEDIUM",
                "related_lsr": list(data["related_lsr"])[:3]
            })
        recurring_patterns.sort(key=lambda x: (x["sif_potential_count"], x["occurrences"]), reverse=True)

        # Section 5: Site Analysis & Priority Ranking
        site_groups: Dict[str, Dict[str, Any]] = {}
        for r in reports:
            site = r.get("employer") or r.get("location") or "Main Field Site"
            if site not in site_groups:
                site_groups[site] = {
                    "site_name": site,
                    "total_reports": 0,
                    "sif_count": 0,
                    "precursors": set(),
                    "activities": set(),
                    "lsr_set": set()
                }
            site_groups[site]["total_reports"] += 1
            if r["sif_potential"]:
                site_groups[site]["sif_count"] += 1
            if r.get("precursor"):
                site_groups[site]["precursors"].add(r["precursor"])
            if r.get("activity"):
                site_groups[site]["activities"].add(r["activity"])
            site_groups[site]["lsr_set"].update(r.get("life_saving_rules", []))

        site_rankings = []
        for site, data in site_groups.items():
            density = round((data["sif_count"] / data["total_reports"]) * 100, 1) if data["total_reports"] > 0 else 0.0
            site_rankings.append({
                "site_name": site,
                "total_reports": data["total_reports"],
                "sif_count": data["sif_count"],
                "sif_density_pct": density,
                "dominant_precursor": list(data["precursors"])[0] if data["precursors"] else "Unverified Barrier",
                "dominant_activity": list(data["activities"])[0] if data["activities"] else "Mechanical Lifting",
                "top_lsr": list(data["lsr_set"])[:2],
                "priority_label": "CRITICAL" if density >= 50 else "HIGH" if density >= 25 else "MEDIUM"
            })
        site_rankings.sort(key=lambda x: (x["sif_density_pct"], x["sif_count"]), reverse=True)

        # Section 6: Activity Analysis & Priority Ranking
        act_groups: Dict[str, Dict[str, Any]] = {}
        for r in reports:
            act = r.get("activity") or "General Operations"
            if act not in act_groups:
                act_groups[act] = {
                    "activity_name": act,
                    "total_reports": 0,
                    "sif_count": 0,
                    "barriers_failed": set()
                }
            act_groups[act]["total_reports"] += 1
            if r["sif_potential"]:
                act_groups[act]["sif_count"] += 1
            if r.get("barrier_failure"):
                act_groups[act]["barriers_failed"].add(r["barrier_failure"])

        activity_rankings = []
        for act, data in act_groups.items():
            density = round((data["sif_count"] / data["total_reports"]) * 100, 1) if data["total_reports"] > 0 else 0.0
            activity_rankings.append({
                "activity_name": act,
                "total_reports": data["total_reports"],
                "sif_count": data["sif_count"],
                "sif_density_pct": density,
                "main_barrier_failed": list(data["barriers_failed"])[0] if data["barriers_failed"] else "Exclusion Zone Control",
                "priority_label": "CRITICAL" if density >= 50 else "HIGH" if density >= 25 else "MEDIUM"
            })
        activity_rankings.sort(key=lambda x: (x["sif_density_pct"], x["sif_count"]), reverse=True)

        # Section 7: Barrier Failure Analysis
        barrier_counts: Dict[str, Dict[str, Any]] = {}
        for r in reports:
            b = r.get("barrier_failure") or r.get("barrier") or "Safety Control Unverified"
            if b not in barrier_counts:
                barrier_counts[b] = {"barrier": b, "count": 0, "sif_count": 0}
            barrier_counts[b]["count"] += 1
            if r["sif_potential"]:
                barrier_counts[b]["sif_count"] += 1

        barrier_analysis = []
        for b, data in barrier_counts.items():
            density = round((data["sif_count"] / data["count"]) * 100, 1) if data["count"] > 0 else 0.0
            barrier_analysis.append({
                "barrier": b,
                "occurrence_count": data["count"],
                "sif_count": data["sif_count"],
                "sif_density_pct": density
            })
        barrier_analysis.sort(key=lambda x: x["sif_count"], reverse=True)

        # Section 8: Trend Analysis (Monthly breakdown)
        monthly_trend: Dict[str, Dict[str, int]] = {}
        for r in reports:
            date_str = r.get("timestamp", "")
            month_key = "2025-Overall"
            try:
                dt = pd.to_datetime(date_str, errors='coerce')
                if pd.notnull(dt):
                    month_key = dt.strftime("%Y-%m")
            except Exception:
                pass

            if month_key not in monthly_trend:
                monthly_trend[month_key] = {"total": 0, "sif": 0}
            monthly_trend[month_key]["total"] += 1
            if r["sif_potential"]:
                monthly_trend[month_key]["sif"] += 1

        trend_list = [
            {"period": m, "total_reports": data["total"], "sif_reports": data["sif"], "sif_density_pct": round((data["sif"]/data["total"])*100, 1) if data["total"] > 0 else 0}
            for m, data in sorted(monthly_trend.items())
        ]

        # Section 9: Prescriptive HSE Action Priorities
        top_site = site_rankings[0]["site_name"] if site_rankings else "High-Risk Field Sites"
        top_act = activity_rankings[0]["activity_name"] if activity_rankings else "Mechanical Lifting & Work at Height"
        top_precursor = recurring_patterns[0]["title"] if recurring_patterns else "Energy Isolation & Exclusion Zone Failures"

        action_priorities = [
            {
                "priority_rank": 1,
                "category": "Immediate Field Intervention",
                "title": f"Mandatory Safety Audits at {top_site}",
                "description": f"Based on analyzed reports, {top_site} exhibits a high SIF precursor density ({site_rankings[0]['sif_density_pct'] if site_rankings else 'high'}%). Audit all active isolation permits and high-energy barriers."
            },
            {
                "priority_rank": 2,
                "category": "Activity Stand-Down",
                "title": f"Pre-Job Briefing Focus on {top_act}",
                "description": f"{top_act} accounted for the highest concentration of potential fatal precursors ({activity_rankings[0]['sif_count'] if activity_rankings else 'multiple'} SIF events). Mandate double-verifier signoffs before task initiation."
            },
            {
                "priority_rank": 3,
                "category": "Barrier Restoration",
                "title": f"Eliminate Recurring Precursor: {top_precursor}",
                "description": f"Enforce physical interlocks and positive barrier verifications to address recurring precursor pathways identified across the dataset."
            }
        ]

        return {
            "section_1_executive_summary": {
                "reports_analyzed": total_reports,
                "sif_potential_count": sif_count,
                "non_sif_count": non_sif_count,
                "sif_density_pct": sif_density_pct,
                "processing_time_sec": elapsed_sec,
                "risk_distribution": risk_dist,
                "top_site": top_site,
                "top_activity": top_act,
                "top_precursor": top_precursor
            },
            "section_2_sif_analysis": {
                "model_metrics": model_metrics,
                "sif_count": sif_count,
                "non_sif_count": non_sif_count,
                "sample_high_priority_reports": reports[:5]
            },
            "section_3_life_saving_rules": lsr_list[:8],
            "section_4_recurring_precursors": recurring_patterns[:10],
            "section_5_site_rankings": site_rankings[:10],
            "section_6_activity_rankings": activity_rankings[:10],
            "section_7_barrier_analysis": barrier_analysis[:10],
            "section_8_trend_analysis": trend_list[:12],
            "section_9_action_priorities": action_priorities
        }

dataset_processor = DatasetProcessor()
