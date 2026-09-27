# SHRAMRAKSHAK: Final Reproducibility & Environment Specification
**SIH 2026 Problem Statement:** SIH26165  
**System:** SHRAMRAKSHAK HSE Intelligence System  
**Date:** 2026-09-27  

---

## 1. Environment & Dependency Specifications

All components of the SHRAMRAKSHAK system have been verified and frozen against the following runtime environment:

### Host Operating System
- **OS:** Microsoft Windows 11 Enterprise (64-bit)
- **Shell:** PowerShell 7 / Windows PowerShell

### Python Environment
- **Python Version:** 3.11.9 (tags/v3.11.9:de542f0, Apr 2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
- **Key Python Packages:**
  - `fastapi` == 0.115.6
  - `uvicorn` == 0.34.0
  - `torch` == 2.2.0+cpu
  - `torchvision` == 0.17.0+cpu
  - `onnxruntime` == 1.20.1
  - `opencv-python` == 4.10.0.84
  - `faiss-cpu` == 1.10.0
  - `sentence-transformers` == 3.4.1
  - `reportlab` == 4.2.5
  - `pytest` == 9.1.1
  - `httpx` == 0.28.1

### Node.js & Frontend Environment
- **Node.js:** v20+
- **Vite:** 5.4.21
- **React:** 18.3.1
- **TailwindCSS:** 3.4.17
- **Lucide Icons:** 1.16.0

---

## 2. Step-by-Step Reproduction Guide

To independently reproduce the entire test suite and verify 100% of all metrics:

### Step 1: Verify Production Storage Baseline
Execute from workspace root:
```powershell
python tools/check_memory_integrity.py
```
**Expected Output:**
```json
{
  "status": "PASS",
  "counts": {
    "events": 314,
    "embedding_rows": 314,
    "faiss_vectors": 314,
    "mappings": 314
  },
  "orphan_vectors": [],
  "orphan_mappings": [],
  "unindexed_events": [],
  "persistence_state": "CLEAN"
}
```

### Step 2: Run Adversarial NLP Validation Suite
Execute:
```powershell
python tests/run_adversarial_nlp_validation.py
```
**Expected Output:**
- Total Cases: 168
- Correct: 168 (100.00%)
- Unsafe False Negatives: 0
- Unsafe False Positives: 0
- Incorrect Review Ambiguities: 0

### Step 3: Run Full Phase 43 Automated Pytest Suite
Execute:
```powershell
pytest tests/test_single_authoritative_sif_pipeline.py `
       tests/test_sih_density_consistency.py `
       tests/test_hse_correction_propagation_final.py `
       tests/test_pdf_data_consistency_final.py `
       tests/test_memory_reconciliation_final.py `
       tests/test_cctv_nlp_independence_final.py `
       tests/test_rebreach_memory_final.py `
       tests/test_api_contracts_final.py `
       tests/test_test_isolation_final.py -v
```
**Expected Output:**
- 30 passed in < 15.0 seconds
- 0 failures, 0 errors

### Step 4: Verify Frontend Build
Execute from `frontend/`:
```powershell
npm run build
```
**Expected Output:**
- `built in ~5s`
- Zero TypeScript / Rollup errors.

### Step 5: Verify Live System End-to-End
With backend running on port 8000 and frontend on port 5173, execute:
```powershell
python backend/verify_live_system.py
```
**Expected Output:**
- `*** ALL SYSTEM VERIFICATION CHECKS COMPLETED SUCCESSFULLY! ***`

---

## 3. Cryptographic Storage Hashes (Frozen Baseline)

The production storage baseline comprises 314 canonical events with verified bijective alignment:

| File Path | Description | SHA-256 Hash |
|---|---|---|
| `backend/data/shramrakshak.db` | Canonical SQLite Database (314 events, 314 embeddings) | `dac39fd190b76e7cb74734cd329ff0be3549dd5d2321c6f363793c0d730db2c2` |
| `backend/data/e5_faiss.index` | E5-small-v2 384-dim IndexFlatIP Binary (314 vectors) | `ae210bc1068876a8611c414766892778961513ec3fc0bf6abce561669c07b9f1` |
| `backend/data/e5_faiss_mapping.json` | Vector ID to Event ID Bijective Mapping (314 entries) | `a20c82a4776a19342d95ece4f6103fc590641cb687f0335a96af4cfb25b497ea` |

Any test run executing via `isolated_test_environment` guarantees that these hashes remain identical with 0 bits altered.
