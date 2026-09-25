# SHRAMRAKSHAK — FINAL FORENSIC HARDENING CHECKLIST

Project: **SHRAMRAKSHAK**  
SIH Problem Statement: **SIH26165** — *“AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in OIL's Unsafe-Act/Unsafe-Condition and Near-Miss Reports.”*

Status Indicators:
- `[ ] NOT STARTED`
- `[~] IN PROGRESS`
- `[x] VERIFIED COMPLETE`
- `[!] BLOCKED`

---

## 1. Absolute Rules & Governance Foundations

- [x] **R1: Checklist First**
  - **Status:** VERIFIED COMPLETE
  - **File(s) Changed:** `docs/FINAL_HARDENING_CHECKLIST.md`
  - **Observed Result:** Checklist created covering all 37 mission gates.
  - **Artifact/Evidence:** `docs/FINAL_HARDENING_CHECKLIST.md`

- [x] **R2: Baseline Capture Before Modification**
  - **Status:** VERIFIED COMPLETE
  - **File(s) Changed:** `docs/BASELINE_VALIDATION.md`, `artifacts/environment_versions.txt`
  - **Command/Test Executed:** Ran `tests/test_assertion_8_cases.py`, `tests/test_recurrence_cases.py`, `tests/test_full_architecture_e2e.py`, `tests/test_true_closed_loop_e2e.py`
  - **Observed Result:** Captured exact baseline pass/fail counts, execution traces, and environment versions.
  - **Artifact/Evidence:** `docs/BASELINE_VALIDATION.md`

- [~] **R3: Architecture Preservation**
  - **Status:** IN PROGRESS
  - **Scope:** Preserve working canonical SafetyEvent, E5 embeddings, FAISS, SQLite, 2-stage recurrence, HSE review, preconditions, CCTV without wholesale rewrites.

- [~] **R4: Authoritative Single Production Pipeline**
  - **Status:** IN PROGRESS
  - **Scope:** Ensure `POST /api/events/report` and main pipelines route strictly through canonical SafetyEvent. Audit legacy modules and mark `ACTIVE`, `LEGACY`, `TEST-ONLY`, `DEPRECATED`.

- [~] **R5: No Fake Results Enforcement**
  - **Status:** IN PROGRESS
  - **Scope:** Zero simulated similarity, zero fabricated embeddings, zero dummy SIF scores, zero synthetic OIL ground truth claims.

- [~] **R6: No Self-Certification**
  - **Status:** IN PROGRESS
  - **Scope:** All tests must execute real application NLP, extraction, E5 inference, and FAISS indexing paths.

- [~] **R7: Strict Provenance & Non-OIL Labeling**
  - **Status:** IN PROGRESS
  - **Scope:** External dataset `January2015toNovember2025.csv` explicitly tagged `is_oil_data=False`, `has_sif_ground_truth=False`, `label_status=UNLABELED_FOR_SIF`.

---

## 2. Priority 0 (P0) Requirements

- [ ] **P0-1: SIF Human-Exposure Gate Implementation**
  - **Status:** NOT STARTED
  - **States:** `HUMAN_EXPOSURE_CONFIRMED`, `HUMAN_EXPOSURE_NEGATED`, `HUMAN_EXPOSURE_POSSIBLE`, `HUMAN_EXPOSURE_UNKNOWN`
  - **Cases:**
    - Case A: Suspended load moving + barrier failed + NO workers inside area -> `NO_SIF_POTENTIAL_IDENTIFIED` (exposure NEGATED)
    - Case B: Suspended load moving + barrier failed + location unknown -> `REVIEW_REQUIRED` (exposure UNKNOWN)
    - Case C: Worker entered exclusion zone while suspended load moving -> `SIF-POTENTIAL` (exposure CONFIRMED)
  - **File(s) Changed:** `backend/models_canonical.py`, `backend/nlp_engine/sif_pathway_engine.py`, `backend/nlp_engine/preprocessor.py`
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [x] **P0-2: Backend / Vite Proxy Connectivity & Health**
  - **Status:** VERIFIED COMPLETE
  - **File(s) Changed:** `backend/main.py`, `frontend/vite.config.js`
  - **Command/Test Executed:** FastAPI Uvicorn listener check, curl/requests to 13 `/api/*` endpoints via Vite proxy `http://localhost:5173` and backend `http://0.0.0.0:8000`.
  - **Observed Result:** Reordered FastAPI static route definitions ahead of parameterized routes. All 13 core endpoints returned `200 OK`.
  - **Artifact/Evidence:** Verified in baseline and server health check logs.

---

## 3. Priority 1 (P1) Requirements

- [ ] **P1-01: Assertion / Temporal Benchmark (8 + 3 = 11 Cases)**
  - **Status:** NOT STARTED
  - **Scope:** Original 8 cases + 3 human exposure gate cases.
  - **File(s) Changed:** `tests/test_assertion_8_cases.py` (updated to 11 cases)
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-02: Silent Failure Elimination & Telemetry Manifests**
  - **Status:** NOT STARTED
  - **Scope:** Audit repository for `except Exception: pass`. Record stage failure states: `SUCCESS`, `PREPROCESSING_FAILED`, `ASSERTION_FAILED`, `EXTRACTION_FAILED`, `SIF_FAILED`, `LSR_FAILED`, `EMBEDDING_FAILED`, `FAISS_FAILED`, `RECURRENCE_FAILED`, `PERSISTENCE_FAILED`.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-03: FAISS / SQLite Consistency & 1-to-1 Mapping Invariant**
  - **Status:** NOT STARTED
  - **Scope:** Every active FAISS vector maps to exactly 1 persisted embedding metadata record in SQLite and vice versa.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-04: Real E5 Retrieval Validation Benchmark (40 Pairs)**
  - **Status:** NOT STARTED
  - **Scope:** 20 positive paraphrase pairs + 20 negative/hard-negative pairs across 8 core safety domains. Measure Recall@1, Recall@3, Recall@5.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** `artifacts/semantic_retrieval_benchmark.json`

- [ ] **P1-05: Two-Stage Recurrence Validation (Cases 1-4)**
  - **Status:** NOT STARTED
  - **Scope:** Raw text -> SafetyEvent -> E5 embedding -> FAISS retrieval -> structured compatibility -> relationship (`DUPLICATE`, `INDEPENDENT_RECURRENCE`, `RELATED_BUT_DIFFERENT`, `REVIEW_REQUIRED`).
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** `artifacts/recurrence_benchmark.json`

- [ ] **P1-06: Recurrence Cross-Domain Generalization**
  - **Status:** NOT STARTED
  - **Scope:** Lifting, energy isolation, confined space, work at height, hot work, process safety.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-07: Recurrence Auditability & Plain-Language Explanation**
  - **Status:** NOT STARTED
  - **Scope:** Expose candidate, similarity, matching/conflicting structured fields, time/site relationship, assertion compatibility, plain-language reason.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-08: Human Review Propagation Across State Graph**
  - **Status:** NOT STARTED
  - **Scope:** Human correction (`FAILED` -> `EFFECTIVE_VERIFIED`) recomputes downstream SafetyEvent, SIF pathway, LSR, pattern membership/count, control signals, preconditions. Provenance tag `REAL_HSE_REVIEW` vs `DEMO_HSE_REVIEW`.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-09: Precondition Lifecycle & Human Acceptance Governance**
  - **Status:** NOT STARTED
  - **Scope:** Lifecycle: `CANDIDATE_PATTERN` -> `HSE_VALIDATED` -> `PRECONDITION_PROPOSED` -> `HSE_ACCEPTED / HSE_EDITED / HSE_REJECTED` -> `ACTIVE`. Only `ACTIVE` preconditions evaluated.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-10: Multi-Precondition Complete Independent Evaluation**
  - **Status:** NOT STARTED
  - **Scope:** Evaluate ALL applicable preconditions independently. Output exactly which requirement failed/required review without early exit.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-11: Automatic Pattern Reopening on Downstream Recurrence**
  - **Status:** NOT STARTED
  - **Scope:** New independent recurrence breaches challenge previously validated pattern and shift active precondition to `CHALLENGED`, requiring human re-validation.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-12: Provenance Safe Defaults**
  - **Status:** NOT STARTED
  - **Scope:** Constructors default `is_oil_data=False`, `has_sif_ground_truth=False`, `label_status=UNLABELED_FOR_SIF`.
  - **File(s) Changed:** `backend/models_canonical.py`
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-13: Confidence Semantics Audit**
  - **Status:** NOT STARTED
  - **Scope:** Clearly label rule/heuristic confidence as `HEURISTIC` / `RULE-BASED` / `UNCALIBRATED`. UI never claims calibrated fatality probability.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-14: IOGP Life-Saving Rules Multi-Label Mapping**
  - **Status:** NOT STARTED
  - **Scope:** Derived strictly from canonical SafetyEvent. No fabricated/combined rule names. Evidence-backed or `REVIEW_REQUIRED`.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-15: CCTV Safety Boundary & Visual Observability Limits**
  - **Status:** NOT STARTED
  - **Scope:** CCTV produces canonical SafetyEvent for visual breach/clear zone. Explicitly disclaim non-observable states (zero-energy, gas testing, certification). Marked `prototype / integration-ready`.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [x] **P1-16: Global Modal / Drawer / Overlay Viewport Architecture**
  - **Status:** VERIFIED COMPLETE
  - **File(s) Changed:** `frontend/src/components/common/OverlayPortal.jsx`, `frontend/src/components/common/UnifiedDrawer.jsx`, `frontend/src/components/common/UnifiedModal.jsx`, `frontend/src/hooks/useOverlayLock.js`, `frontend/src/index.css`, `frontend/src/components/safety-intelligence/EvidenceDetailDrawer.jsx`, `frontend/src/components/dashboard/AlertDetailModal.jsx`, `frontend/src/components/dashboard/MobileAccessModal.jsx`, `frontend/src/components/reports/SafetyReportDetailModal.jsx`, `frontend/src/components/views/ReportsView.jsx`, `frontend/src/components/views/SafetyPassportView.jsx`
  - **Command/Test Executed:** Vite build (`npm run build`) succeeded in 4.99s. Full audit of all 6 modal/drawer components.
  - **Observed Result:** Root cause identified (drawer rendered inside nested relative flex container with `overflow-hidden` causing half-screen clip). Resolved via Portal to `document.body`, fixed viewport backdrops at `z-[60]` and responsive drawers at `z-[70]`.
  - **Artifact/Evidence:** Git commit `9e5098e` and clean build output.

- [ ] **P1-17: Frontend Default Landing View**
  - **Status:** NOT STARTED
  - **Scope:** Landing page opens directly on `SAFETY INTELLIGENCE`.
  - **File(s) Changed:** `frontend/src/pages/Dashboard.jsx`
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-18: Large-Scale Dataset Stress Test (1,000+ Records)**
  - **Status:** NOT STARTED
  - **Scope:** Ingest and process 1,000+ records (or full dataset if capped) from `January2015toNovember2025.csv`. Record stage metrics and runtime.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** `artifacts/stress_run_<run_id>.json`

- [ ] **P1-19: Adversarial Robustness Benchmark (100+ Cases)**
  - **Status:** NOT STARTED
  - **Scope:** 10 categories (direct affirmed, negation, safe control, hypothetical, post-event, double negation, red herrings, barrier states, paraphrases, duplicates).
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** `artifacts/adversarial_benchmark.json`

- [ ] **P1-20: Unseen Live Input API Validation (10+ Narratives)**
  - **Status:** NOT STARTED
  - **Scope:** 10 un-registered narratives submitted via `POST /api/events/report`.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P1-21: Subprocess Restart Persistence Proof**
  - **Status:** NOT STARTED
  - **Scope:** Real process restart test script `scripts/verify_restart_persistence.py`. Ingest -> embed -> FAISS -> SQLite -> exit process -> restart process -> reload -> verify 100% correspondence.
  - **File(s) Changed:** `scripts/verify_restart_persistence.py`
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** `artifacts/restart_persistence_result.json`

- [ ] **P1-22: Reproducibility & Dependency Documentation**
  - **Status:** NOT STARTED
  - **Scope:** Create `docs/REPRODUCIBILITY.md` and capture exact pinned versions.
  - **File(s) Changed:** `docs/REPRODUCIBILITY.md`, `artifacts/environment_versions.txt`
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** `docs/REPRODUCIBILITY.md`

- [ ] **P1-23: Legacy NLP & Model Architecture Audit**
  - **Status:** NOT STARTED
  - **Scope:** Audit legacy vs active modules (`analyzer.py`, `sif_classifier.py`, `precursor_extractor.py`, `event_normalizer.py`, `pattern_miner.py`, `semantic_layer.py`, `safety_memory.py`).
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** Documented in Final Hardening Report.

- [ ] **P1-24: Clean Failure Handling & Input Boundary Testing**
  - **Status:** NOT STARTED
  - **Scope:** Empty reports, 10k-char inputs, malformed CSV, invalid JSON, missing IDs. System fails gracefully with explicit error responses.
  - **File(s) Changed:** 
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

---

## 4. Priority 2 (P2) Requirements

- [ ] **P2-1: Website Forensic Regression Across All 8 Views**
  - **Status:** NOT STARTED
  - **Views:** Overview, Reports, Safety Intelligence, Safety Memory, Live Safety, Actions, Import Data, Settings/Demo.
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

- [ ] **P2-2: Full 13-Step Closed-Loop Demonstration**
  - **Status:** NOT STARTED
  - **Steps:** Human Report -> SafetyEvent -> SIF -> LSR -> Evidence -> Safety Memory -> Recurring Pattern -> HSE Validation -> Precondition -> Action -> CCTV Verification -> State Feed back into Memory.
  - **Command/Test Executed:** 
  - **Observed Result:** 
  - **Artifact/Evidence:** 

---

## 5. Final Acceptance & Release Package

- [ ] **Final Clean-Room Validation Execution**
- [ ] **Artifacts Directory Generation** (`artifacts/*.json`, `artifacts/*.txt`)
- [ ] **Final Hardening Report** (`docs/FINAL_HARDENING_REPORT.md` - 26 sections)
