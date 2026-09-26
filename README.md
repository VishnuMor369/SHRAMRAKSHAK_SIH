# 🛡️ SHRAMRAKSHAK: Industrial AI Safety Intelligence & Closed-Loop SIF Prevention
> **Smart India Hackathon (SIH 2024 Finalist Platform — Problem Statement SIH26165)**  
> *Autonomous SIF Precondition Detection • Semantic Recurrence Memory • Verified Closed-Loop Resolution*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Uvicorn-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-cyan.svg)](https://react.dev/)
[![Vector Memory](https://img.shields.io/badge/Vector%20Memory-FAISS%20E5--Small-orange.svg)](https://github.com/facebookresearch/faiss)
[![Tests: 15/15 Passing](https://img.shields.io/badge/Acceptance%20Suite-15%2F15%20Passing-brightgreen.svg)](tests/)

---

## 📌 Executive Summary

**SHRAMRAKSHAK** is an enterprise-grade industrial safety intelligence platform engineered to eliminate Serious Injury & Fatality (**SIF**) events in high-hazard environments (construction, manufacturing, heavy industrial plants).

Unlike traditional safety dashboards that merely record lagging incident metrics, SHRAMRAKSHAK creates a **continuous, 7-stage closed-loop safety ecosystem**:
1. **Multimodal Incident Ingestion**: Batch normalization of industrial logs (OSHA, HSE, manual forms) with streaming NLP assertion detection.
2. **Deterministic & Semantic Classification**: Dual-layer Life Saving Rules (LSR) and SIF potential scoring (High / Medium / Low).
3. **Safety Memory & Recurrence**: Dense semantic vector indexing (FAISS E5) with dynamic safety barrier extraction.
4. **HSE Expert Validation**: Transparent pattern lifecycle (`CANDIDATE` ➔ `VALIDATED` ➔ `REJECTED`) with automated barrier precondition enforcement.
5. **Future Work Assurance**: Pre-task verification matching planned hazardous operations against active plant preconditions.
6. **Live CCTV Observation & Action State Machine**: Real-time YOLO-powered computer vision violation detection paired with transactional response SLAs and post-resolution verification windows.
7. **Human-in-the-Loop Resolution & Closed-Loop Auditing**: Verification tracking, re-breach detection, and immutable tamper-resistant audit logs.

---

## 🏗️ End-to-End System Architecture

```mermaid
flowchart TD
    subgraph INGESTION["Stage 1 & 2: Ingestion & Classification"]
        A[Historical OSHA / Plant Incident Data] --> B[Dataset Importer & Stream Parser]
        B --> C[Assertion & Negation Detector]
        C --> D[LSR Classifier & SIF Engine]
        D --> E[Canonical SafetyEvent Database (SQLite)]
    end

    subgraph MEMORY["Stage 3 & 4: Safety Memory & HSE Validation"]
        E --> F[Semantic Vector Index (FAISS E5)]
        F --> G[Recurrence Pattern Engine]
        G --> H{HSE Expert Review}
        H -->|Validated| I[Active Precondition Store]
        H -->|Rejected| J[Deactivated Precondition Store]
    end

    subgraph OPERATIONS["Stage 5 & 6: Operations & Edge Verification"]
        K[Planned High-Hazard Permit / Work] --> L[Future Work Assurance Engine]
        I --> L
        L --> M[Field Work Clearance]
        N[CCTV Stream / RTSP / Edge YOLO] --> O[Live Violation Debounce Engine]
        O --> P[Transactional Action State Machine]
        P -->|20s Supervisor SLA| Q[Mobile Field Supervisor UI]
    end

    subgraph CLOSURE["Stage 7: Closed-Loop Human Verification"]
        Q --> R{Supervisor Action}
        R -->|Fixed & Resolved| S[Awaiting Verification Window (60s)]
        S -->|CCTV Re-Breach Detected| P
        S -->|Clearance Confirmed| T[Tamper-Proof Audit Record]
        T --> E
    end
```

---

## ⚙️ Core Technical Capabilities

### 1. Batch NLP Streaming Pipeline
- High-throughput streaming chunk processor in `backend/dataset_importer.py`.
- Immediate UI responsiveness with debounced stage updates (`Parsing` ➔ `LSR Classification` ➔ `SIF Scoring` ➔ `Vector Memory Indexing`).
- Medical/historical negation detection to avoid false-positive hazard triggers (`backend/nlp_engine/assertion_detector.py`).
- Transparent OSHA historical incident dataset disclaimer for auditability.

### 2. Canonical SIF & LSR Classification
- Aligned High / Medium / Low SIF potential scoring across canonical data models, SQLite storage, and React UI components.
- Zero-drift guarantee: consistent risk badges across reports, live drawers, and intelligence views.

### 3. Safety Memory & Recurrence Engine
- Dynamic barrier condition extraction eliminating hardcoded heuristic fallbacks.
- Strictly scoped cross-site recurrence pattern identification.
- Clean-room test isolation ensuring production FAISS vectors (`backend/data/e5_faiss.index`) and SQLite records (`backend/data/shramrakshak.db`) remain byte-for-byte immutable during automated testing.

### 4. Robust Action State Machine & Verification Loop
- Transactional state transitions: `OPEN` ➔ `RESPONDING` ➔ `AWAITING_VERIFICATION` ➔ `RESOLVED`.
- Direct Human Resolution endpoint (`POST /api/alerts/{alert_id}/resolve`) with supervisor name and resolution notes.
- Post-resolution verification window: if edge CCTV detects another violation before the verification timer expires, the action is automatically reopened as a `RE-BREACH`.
- Full persistent verification records saved to SQLite (`verification_records` table) and visualized without missing timestamps.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.11 & 3.12)
- **Node.js v18+** and `npm`
- Laptop with webcam or RTSP/synthetic camera stream

---

### Step 1: Clone & Install Dependencies

```powershell
# Clone the repository
git clone https://github.com/preetmutha24-lang/RESEARCH-BASIS-ONLY-.git
cd "RESEARCH-BASIS-ONLY-"

# Backend dependencies
pip install fastapi "uvicorn[standard]" websockets opencv-python ultralytics qrcode pillow pydantic numpy faiss-cpu sentence-transformers

# Frontend dependencies
cd frontend
npm install
cd ..
```

---

### Step 2: Run Backend & Frontend

#### Terminal 1 — Backend:
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*API docs available at: `http://localhost:8000/docs`*

#### Terminal 2 — Frontend:
```powershell
cd frontend
npm run dev
```
*HSE Dashboard available at: `http://localhost:5173`*

---

### Step 3: Run Full Master Regression Suite

Execute the clean-room, end-to-end acceptance suite verifying all 7 stages of the safety loop:

```powershell
python -m pytest tests/test_master_closed_loop_acceptance.py -v
```

**Results:**
```text
tests/test_master_closed_loop_acceptance.py::test_master_closed_loop_15_step_acceptance PASSED [100%]
============================== 1 passed in 4.88s ==============================
```

---

## 📊 Verification Matrix & Test Coverage

| Test Step | Verification Domain | Validation Criterion | Status |
|:---:|:---|:---|:---:|
| **01** | Database Hash Protection | Production SQLite byte-hash unchanged | ✅ PASSED |
| **02** | FAISS Vector Isolation | Vector count and memory mapping intact | ✅ PASSED |
| **03** | Batch NLP Import | Clean-room ingestion of historical incidents | ✅ PASSED |
| **04** | Assertion & Negation | Correct handling of negated hazards | ✅ PASSED |
| **05** | LSR Rule Engine | Zero-drift rule and high-risk classification | ✅ PASSED |
| **06** | Canonical SIF Consistency | Unified SIF severity across all models | ✅ PASSED |
| **07** | Barrier Extraction | Dynamic barrier conditions derived accurately | ✅ PASSED |
| **08** | HSE Pattern Workflow | Precondition state toggled on validation/rejection | ✅ PASSED |
| **09** | Rejection Safety | Rejected patterns deactivate active preconditions | ✅ PASSED |
| **10** | Precondition Enforcement | Matching permits flag required safety barriers | ✅ PASSED |
| **11** | Action State Transition | Transactional state machine progression | ✅ PASSED |
| **12** | Direct Human Resolution | API endpoint resolves action with audit note | ✅ PASSED |
| **13** | Verification Window | Action transitions to AWAITING_VERIFICATION | ✅ PASSED |
| **14** | CCTV Re-Breach Detection | Immediate re-opening of action on re-breach | ✅ PASSED |
| **15** | Post-Validation Audit | Zero mutations to production state files | ✅ PASSED |

---

## 👥 Hackathon Team & Problem Details

- **Hackathon:** Smart India Hackathon (SIH 2024)
- **Problem Statement ID:** SIH26165
- **Team:** BRAINSTACK
- **Domain:** AI & Robotics for Workplace Safety and Industrial Health
- **Lead Developer & Maintainer:** Vishnu Mor (`vishnumor369@gmail.com`)
- **Repository:** [preetmutha24-lang/RESEARCH-BASIS-ONLY-](https://github.com/preetmutha24-lang/RESEARCH-BASIS-ONLY-)

---

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
