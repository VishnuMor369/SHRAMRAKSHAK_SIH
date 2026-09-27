# SHRAMRAKSHAK: Final SIH Requirement Traceability Matrix
**SIH 2026 Problem Statement:** SIH26165  
**System:** SHRAMRAKSHAK HSE Intelligence System  
**Date:** 2026-09-27  

---

## 1. Traceability Overview

This matrix maps every functional and non-functional requirement specified by Oil India Limited (OIL) for Problem Statement **SIH26165** to its exact implementing source files, algorithms, and verifying test suites in the SHRAMRAKSHAK codebase.

---

## 2. Requirement-to-Code Traceability Matrix

| SIH26165 Requirement | Core Implementing Modules | Verifying Test Suites | Acceptance Gate | Status |
|---|---|---|---|---|
| **R01: Unification of Multi-Source Safety Data** (Human reports, imported CSV/PDF records, CCTV observations) | `backend/unified_event_store.py`<br>`backend/models_canonical.py` | `tests/test_cctv_nlp_independence_final.py`<br>`tests/test_single_authoritative_sif_pipeline.py` | G10, G11 | **VERIFIED** |
| **R02: Single Authoritative SIF Precursor Engine** (Strict SIF-Potential, Review-Required, No-SIF) | `backend/nlp_engine/sif_pathway_engine.py` | `tests/test_single_authoritative_sif_pipeline.py`<br>`tests/run_adversarial_nlp_validation.py` | G01, G02, G03 | **VERIFIED** |
| **R03: Linguistic Negation & Assertion Modeling** (Distinguish actual incidents from hypothetical safety talks & post-event fixes) | `backend/nlp_engine/assertion_detector.py`<br>`backend/nlp_engine/preprocessor.py` | `tests/run_adversarial_nlp_validation.py` (168 cases) | G04, G05 | **VERIFIED** |
| **R04: IOGP Life-Saving Rules Classification** (Automated mapping to 9 core IOGP LSR standards) | `backend/nlp_engine/lsr_classifier.py`<br>`backend/nlp_engine/ontology.py` | `tests/test_single_authoritative_sif_pipeline.py`<br>`tests/run_adversarial_nlp_validation.py` | G06 | **VERIFIED** |
| **R05: Bijective Semantic Memory & Vector Search** (E5-small-v2 embeddings + FlatIP FAISS indexing) | `backend/nlp_engine/semantic_memory.py`<br>`tools/check_memory_integrity.py` | `tests/test_memory_reconciliation_final.py`<br>`tests/test_test_isolation_final.py` | G07, G08, G09 | **VERIFIED** |
| **R06: Two-Stage Recurrence Mining** (Distinguish genuine independent recurrences from duplicate incident reports) | `backend/nlp_engine/recurrence_engine.py` | `tests/test_rebreach_memory_final.py` | G14, G15 | **VERIFIED** |
| **R07: Closed-Loop Reopening on Re-Breach (Rule 20)** (Reopen closed patterns and escalate when controls fail again) | `backend/nlp_engine/recurrence_engine.py`<br>`backend/state.py` | `tests/test_rebreach_memory_final.py` | G16, G17 | **VERIFIED** |
| **R08: Human-in-the-Loop Review & Audit Logging** (Formal HSE review, correction propagation, immutable logging) | `backend/nlp_engine/propagation.py`<br>`backend/database.py` | `tests/test_hse_correction_propagation_final.py` | G11, G12, G13 | **VERIFIED** |
| **R09: Objective CCTV Verification ("Completion is not proof")** (Camera verification of physical barrier conditions) | `backend/main.py` (`/api/alert/cctv-verify`)<br>`backend/state.py` | `tests/test_cctv_nlp_independence_final.py`<br>`tests/test_api_contracts_final.py` | G18, G19 | **VERIFIED** |
| **R10: SIF Precursor Density Metric** (Formula: `(SIF-Potential / Total Eligible) * 100` + regulatory disclaimer) | `backend/nlp_engine/sih_density.py`<br>`backend/main.py` (`/api/density`) | `tests/test_sih_density_consistency.py`<br>`tests/test_api_contracts_final.py` | G20, G21 | **VERIFIED** |
| **R11: Multi-Zone CCTV Computer Vision** (YOLOv8 ONNX PPE detection, exclusion polygons, 15s debounce) | `backend/detection.py`<br>`backend/state.py` | `backend/test_targeted_cctv_fixes.py`<br>`backend/test_stale_detection_lifecycle.py` | G24, G25, G26 | **VERIFIED** |
| **R12: Safety Passport & Digital PTW** (4-stage PTW lifecycle, mobile supervisor QR sign-off) | `backend/main.py`<br>`backend/state.py`<br>`frontend/src/` | `backend/test_safety_passport.py`<br>`backend/verify_live_system.py` | G27, G28, G29 | **VERIFIED** |
| **R13: Industrial HSE PDF Report Generation** (Formatted executive summary and individual dossiers with density) | `backend/nlp_engine/pdf_exporter.py` | `tests/test_pdf_data_consistency_final.py`<br>`backend/verify_live_system.py` | G30, G31, G32 | **VERIFIED** |
| **R14: Zero Production Storage Test Mutation** (Hermetic clean-room test harness for ephemeral runs) | `tests/test_isolation.py` | `tests/test_test_isolation_final.py` | G33, G34 | **VERIFIED** |
| **R15: End-to-End Enterprise Web Interface** (Dark mode, glassmorphism, responsive live telemetry) | `frontend/src/App.jsx`<br>`frontend/src/` | `npm run build`<br>`backend/verify_live_system.py` | G35–G42 | **VERIFIED** |

---

## 3. Regulatory & Domain Standards Compliance

1. **IOGP Report 459:** Standardized 9 Life-Saving Rules strictly encoded into ontology and classification pipelines.
2. **Campbell Institute / DEKRA SIF Paradigm:** SIF Precursor concept strictly implemented (High-Energy Hazard + Broken/Absent Barrier + Confirmed Exposure).
3. **DGMS (Directorate General of Mines Safety, India):** Near-miss reporting, high-pressure line-of-fire protection, and crane exclusion zone enforcement.
4. **OSHA 1910.147 / 1910.1200:** Lockout/Tagout (LOTO) energy isolation and hazardous chemical handling.
