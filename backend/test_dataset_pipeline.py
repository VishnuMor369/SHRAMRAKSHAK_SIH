import os
import sys
import unittest
import pandas as pd
from fastapi.testclient import TestClient

from main import app
from nlp_engine import (
    ColumnMapper, DataQualityValidator, dataset_processor, dataset_store, EventNormalizer, SIFClassifier, LSRClassifier
)

client = TestClient(app)

class TestDatasetPipeline(unittest.TestCase):
    """
    Test suite for Real Data-Driven SIF Analytics Engine (SIH PS 26165).
    """

    def setUp(self):
        self.sample_df = pd.DataFrame([
            {
                "ID": 101,
                "EventDate": "01/15/2025",
                "Employer": "Oil India Digboi Refinery",
                "City": "Digboi",
                "State": "Assam",
                "EventTitle": "Mechanical Lifting",
                "Final Narrative": "Rigging assistant walked directly beneath a 5-ton suspended pipe bundle without verified exclusion zone barriers.",
                "Hospitalized": 1.0,
                "Amputation": 0.0
            },
            {
                "ID": 102,
                "EventDate": "02/10/2025",
                "Employer": "Oil India Duliajan Wellhead",
                "City": "Duliajan",
                "State": "Assam",
                "EventTitle": "Working at Height",
                "Final Narrative": "Scaffolder working at 4.5m elevation on pipe rack without safety harness unclipped and no gas test performed prior to entry.",
                "Hospitalized": 1.0,
                "Amputation": 0.0
            },
            {
                "ID": 103,
                "EventDate": "03/05/2025",
                "Employer": "Oil India Moran Hub",
                "City": "Moran",
                "State": "Assam",
                "EventTitle": "General Housekeeping",
                "Final Narrative": "Worker tripped over loose cable in office hallway and sustained minor knee sprain.",
                "Hospitalized": 0.0,
                "Amputation": 0.0
            }
        ])

    def test_column_auto_mapper(self):
        mapping = ColumnMapper.auto_map_columns(self.sample_df)
        self.assertEqual(mapping["narrative_col"], "Final Narrative")
        self.assertEqual(mapping["date_col"], "EventDate")
        self.assertEqual(mapping["location_col"], "Employer")
        self.assertEqual(mapping["activity_col"], "EventTitle")
        self.assertIn("Hospitalized", mapping["ground_truth_cols"])

    def test_data_quality_validator(self):
        mapping = ColumnMapper.auto_map_columns(self.sample_df)
        quality = DataQualityValidator.validate(self.sample_df, mapping, "test_oil.csv")
        self.assertEqual(quality["total_rows"], 3)
        self.assertEqual(quality["usable_records"], 3)
        self.assertEqual(quality["missing_text_count"], 0)
        self.assertGreaterEqual(quality["health_score"], 80.0)

    def test_safety_term_preservation(self):
        norm = EventNormalizer()
        raw_text = "Vessel entry done with no gas test and LOTO not applied."
        norm_ev = norm.normalize_hsse_report({"description": raw_text})
        self.assertIn("no gas test", norm_ev.narrative.lower())

    def test_sif_classifier_explainability(self):
        clf = SIFClassifier()
        context = {"activity": "Working at Height", "location": "Duliajan Rig"}
        text = "Scaffolder fell from 6m platform due to missing handrails."
        sif_pot, score, lvl, reason, why = clf.classify(text, context)
        self.assertTrue(sif_pot)
        self.assertGreaterEqual(score, 60)
        self.assertIn(lvl, ["HIGH", "CRITICAL"])
        self.assertTrue(len(why) > 0)

    def test_iogp_lsr_mapping(self):
        lsr_clf = LSRClassifier()
        context = {"activity": "Confined Space Entry"}
        text = "Entered storage vessel without gas testing and without energy isolation tag."
        lsr_list = lsr_clf.classify(text, context)
        self.assertTrue(len(lsr_list) > 0)

    def test_dataset_processor_batch_execution(self):
        mapping = ColumnMapper.auto_map_columns(self.sample_df)
        reports, summary = dataset_processor.process_dataset(self.sample_df, mapping)
        self.assertEqual(len(reports), 3)
        self.assertIn("section_1_executive_summary", summary)
        self.assertIn("section_3_life_saving_rules", summary)
        self.assertIn("section_4_recurring_precursors", summary)
        self.assertIn("section_5_site_rankings", summary)
        self.assertIn("section_6_activity_rankings", summary)
        self.assertIn("section_9_action_priorities", summary)

    def test_end_to_end_api_routes(self):
        # 1. Test sample loader API
        res_sample = client.get("/api/dataset/sample?max_rows=50")
        self.assertEqual(res_sample.status_code, 200)
        data = res_sample.json()
        self.assertIn("quality_report", data)

        # 2. Test status API
        res_status = client.get("/api/dataset/status")
        self.assertEqual(res_status.status_code, 200)

        # Wait for background processing or check report endpoints
        dataset_store.set_completed_results(
            [
                {
                    "report_id": "REP-DATA-999",
                    "source": "DATASET_REPORT",
                    "timestamp": "2025-01-01",
                    "location": "Digboi Refinery",
                    "activity": "Mechanical Lifting",
                    "description": "Suspended load dropped near personnel.",
                    "sif_potential": True,
                    "risk_score": 85,
                    "risk_level": "CRITICAL",
                    "life_saving_rules": ["Safe Mechanical Lifting"],
                    "precursor": "Suspended Load Exposure",
                    "barrier_failure": "Exclusion Zone Failure"
                }
            ],
            {"section_1_executive_summary": {"reports_analyzed": 1, "sif_potential_count": 1, "sif_density_pct": 100.0, "processing_time_sec": 0.5, "risk_distribution": {"CRITICAL": 1}, "top_site": "Digboi Refinery", "top_activity": "Mechanical Lifting", "top_precursor": "Suspended Load Exposure"}}
        )

        # 3. Test summary API
        res_sum = client.get("/api/dataset/summary")
        self.assertEqual(res_sum.status_code, 200)

        # 4. Test reports list API
        res_reps = client.get("/api/dataset/reports?status_filter=ALL")
        self.assertEqual(res_reps.status_code, 200)
        self.assertEqual(res_reps.json()["total"], 1)

        # 5. Test single report drill-down API
        res_single = client.get("/api/dataset/report/REP-DATA-999")
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(res_single.json()["report_id"], "REP-DATA-999")

if __name__ == "__main__":
    unittest.main()
