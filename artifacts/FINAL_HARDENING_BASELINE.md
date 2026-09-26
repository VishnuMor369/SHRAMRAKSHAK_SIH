# SHRAMRAKSHAK: Phase 0 Forensic Inspection & Hardening Baseline

**Project**: SHRAMRAKSHAK  
**Problem Statement**: SIH26165 — AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in OIL's Unsafe-Act/Unsafe-Condition and Near-Miss Reports  
**Date of Baseline**: 2026-09-26  
**Auditor**: Senior Systems Validation & Safety-NLP Architecture Agent  

---

## 1. Git State Baseline

| Field | Value |
|---|---|
| **Branch** | `main` |
| **Commit Hash** | `a02ba42` |
| **Commit Message** | `feat(safety-memory): implement closed-loop operational pattern workflow with CCTV verification and history` |
| **Working Tree** | Clean (`nothing to commit, working tree clean`) |
| **Remote Sync** | Up to date with `origin/main` |

---

## 2. Production Storage Hashes & Physical Metrics

Before executing any phase modifications, all production persistent data files were hashed and inventoried.

| File Path | SHA256 Hash | Size (Bytes) | Status |
|---|---|---|---|
| `backend/data/shramrakshak.db` | `6b76a63489b5897b67fb7fe1189396b06d3b554dc3777470eaac8b5e8f065c1d` | 417,792 | **LOCKED & VERIFIED** |
| `backend/data/e5_faiss.index` | `2f58231da3c1776318684017d2d6c67e93d2df3304952de9dc6a418e5ce4fd35` | 145,965 | **LOCKED & VERIFIED** |
| `backend/data/e5_faiss_mapping.json` | `6c6ad53ff0c3fbf4f98a20584fa5918d16456b59de1d51e29fd9fc3db4785aeb` | 6,471 | **LOCKED & VERIFIED** |

---

## 3. SQLite Production Table Counts

Exact row counts retrieved directly from `backend/data/shramrakshak.db`:

| Table Name | Row Count | Invariant Notes |
|---|---|---|
| `events` | **103** | Canonical SafetyEvent master records |
| `evidence_spans` | **157** | Character-offset verified text spans |
| `embeddings` | **35** | E5 passage records logged individually via `add_event` |
| `patterns` | **11** | Recurrence clusters (8 HSE_VALIDATED, 2 CANDIDATE, 1 REOPENED, 1 REJECTED) |
| `pattern_members` | **32** | Event-to-pattern associative linkages |
| `reviews` | **26** | Audit trail of human HSE governance decisions |
| `preconditions` | **15** | Safety preconditions (9 ACTIVE, 6 CHALLENGED) |
| `future_work_checks` | **30** | Pre-work package evidence validation logs |
| `verification_records` | **2** | Closed-loop on-site / CCTV verification audit records |
| `run_manifests` | **3** | Reproducible batch run audit records |
| `reports` | **60** | Ingested raw human reports |
| `sqlite_sequence` | **2** | Internal autoincrement sequence counters |

---

## 4. FAISS Vector & Mapping Inspection

Using the forensic diagnostic tool (`tools/check_memory_integrity.py`):

| Metric | Measured Value | Verification Result |
|---|---|---|
| **FAISS Model** | `intfloat/e5-small-v2` | Real transformer model verified |
| **FAISS Index Type** | `IndexFlatIP` | Inner Product on L2-normalized vectors (= Cosine Similarity) |
| **FAISS Dimension (`d`)** | `384` | Exact match to E5-small-v2 dimension |
| **FAISS Total Vectors (`ntotal`)** | `95` | Indexed vectors present in binary index |
| **Mapping Total Keys (`id_to_event`)** | `95` | Keys 0 to 94 mapped |
| **Mapping Total Reverse (`event_to_id`)** | `95` | Bidirectional reverse mapping intact |
| **Next ID Counter** | `95` | Consistent with vector index length |
| **Valid Mappings (in SQLite)** | **93** | 93 vector IDs point to valid rows in `events` |
| **Orphan Mappings (missing in SQLite)** | **2** | Vector 0 (`EVT-TEST-E5`) & Vector 93 (`EVT-E2E-6b586f`) |
| **Missing Embeddings in SQLite** | **60** | Batch-ingested events were added to FAISS but omitted from `embeddings` table |
| **Unindexed Events in SQLite** | **10** | 10 ad-hoc test rows exist in DB without vector index |
| **Memory Integrity Status** | **FAIL** | `REPAIR_REQUIRED` (Preserved without silent mutation) |

---

## 5. Existing Test Suite Execution Results

All existing project-specific test suites were executed BEFORE modifying any application code. All tests ran under hermetic isolation (`test_isolation.py`) and did NOT alter production hashes:

| Test Suite | Execution Command | Result | Pass Rate | Key Verification Points |
|---|---|---|---|---|
| **Adversarial Assertion (8 Cases)** | `python tests/test_assertion_8_cases.py` | **PASS** | 8/8 (100%) | Affirmed, negated, hypothetical, post-event, double negation ambiguity |
| **Recurrence Reasoning (Events A, B, C)** | `python tests/test_recurrence_cases.py` | **PASS** | 3/3 (100%) | Independent recurrence vs related-but-different polarity conflict |
| **Precondition FK Bug Regression** | `python tests/test_precondition_fk_regression.py` | **PASS** | 1/1 (100%) | NULL FK persisted cleanly for non-applicable standard work |
| **True Closed-Loop Pipeline E2E** | `python tests/test_true_closed_loop_e2e.py` | **PASS** | 10/10 (100%) | Raw report -> SIF -> E5 -> Recurrence -> HSE -> Precondition -> Future-work |
| **Operational Closed-Loop Workflow** | `python tests/test_pattern_operational_closed_loop.py` | **PASS** | 1/1 (100%) | Pattern -> Assign Action -> Complete -> Re-breach -> Reopen -> Clear -> Close |
| **Master 15-Step Acceptance** | `python tests/test_master_closed_loop_acceptance.py` | **PASS** | 15/15 (100%) | Full end-to-end multi-agent governance and CCTV verification |
| **Full Architecture 28-Step Verification** | `python tests/test_full_architecture_e2e.py` | **PASS** | 28/28 (100%) | Complete 28-requirement verification suite |
| **Pytest Runner** | `pytest -q tests/` | **PASS** | 4/4 (100%) | Automated discovery runner |

---

## 6. Frontend Build & API Surface Inspection

- **Frontend Build**: Executed `npm run build` using Vite 5.4.21. Built `dist/` in 4.85 seconds with 0 errors.
- **Frontend Views**: 8 active views:
  1. `OverviewView.jsx` (Overview)
  2. `ReportsView.jsx` (Reports)
  3. `SafetyIntelligenceView.jsx` (Safety Intelligence)
  4. `SafetyMemoryView.jsx` (Safety Memory)
  5. `LiveSafetyView.jsx` (Live Safety / CCTV)
  6. `ActionsVerificationView.jsx` (Actions)
  7. `ImportDataView.jsx` (Import Data)
  8. `SettingsDemoView.jsx` (Settings/Demo)
- **Backend API Surface**: 50+ FastAPI REST endpoints in `backend/main.py` covering all views.
