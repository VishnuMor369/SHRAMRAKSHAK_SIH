# SHRAMRAKSHAK: Forensic Implementation & Architecture Audit
**Audit Date**: September 25, 2026  
**Auditor**: Principal ML/NLP Engineer & Safety Systems Architect  
**Objective**: Forensic evaluation of existing codebase against enterprise requirements (SIH Problem Statement SIH26165).

---

## 1. Executive Summary

This forensic audit evaluates the actual code, running services, data pipelines, model weights, and persistence guarantees in the SHRAMRAKSHAK repository.
The audit operates under **Directives 1 & 3**: Zero tolerance for dummy outputs, placeholder AI scores, fake persistence, or unverified claims.

---

## 2. Current Architecture & Data Flow

### 2.1 High-Level Flow
Currently, the system operates three separate ingestion pathways that were recently unified at the interface layer:
1. **Human Safety Reports**: Submitted via `POST /api/events/human`, parsed with regex/heuristics, and saved to `UnifiedEventStore`.
2. **Batch Company Dataset**: Uploaded or preloaded via `POST /api/dataset/import-execute`, parsed with pandas, normalized, and saved to `UnifiedEventStore`.
3. **CCTV Vision Engine**: Evaluates person bounding boxes and pose keypoints against floor polygons with 5-frame confirmation and exit debouncing, generating active alerts and `SafetyEvent` records.

### 2.2 Forensic Inspection of Existing Components

| Component | Physical File | Reality Status | Inspection Finding |
| :--- | :--- | :--- | :--- |
| **Event Schema** | `unified_event_store.py` | Partially Conforming | Dataclass `SafetyEvent` has 24 fields, but downstream components (`nlp_engine/sif_pathway_engine.py`, `safety_memory.py`) still use legacy schemas or independent dataclasses. |
| **NLP Preprocessing** | Missing | **Absent** | No dedicated preprocessor. Texts are passed directly to regex matchers without tokenization, sentence splitting, or clause segmentation. |
| **Assertion & Modality** | `assertion_detector.py` | Partially Working | Rule-based regexes handle key phrases, but lack systematic clause segmentation and fail on subtle double-negation ambiguities (e.g., *"It is not true that no barrier was present"*). |
| **Safety Ontology** | Scattered | Needs Centralization | Ontology terms are scattered across Python constants in `assertion_detector.py`, `analyzer.py`, and `sif_pathway_engine.py`. YAML definitions absent. |
| **Evidence Spans** | `assertion_detector.py` | Fragile | Spans are extracted via regex matches, but offsets are not systematically verified against original character indices across tokenizers. |
| **SIF Pathway** | `sif_pathway_engine.py` | Partially Working | Deterministic rule tree exists, but confidence calculations previously fell back to static numbers (e.g. 95) rather than evidence counts. |
| **LSR Mapping** | `lsr_classifier.py` | Keyword-Biased | Uses regex dictionaries; does not directly take `SafetyEvent` as canonical input. |
| **Semantic Memory** | `safety_memory.py` | Heuristic / Fake Vectors | Word-overlap and token matching used; real E5 embedding transformer and FAISS vector index were absent. |
| **Recurrence Reasoning** | `safety_memory.py` | Basic | Checks activity/hazard matching and time deltas, but does not use two-stage vector + structured multi-attribute compatibility. |
| **Persistence Layer** | `safety_events.json` | Fragile JSON | Uses single flat JSON file. Subject to concurrent write issues and Windows file-locking. SQLite is missing. |
| **CCTV Detection** | `detection.py` | **GENUINE & WORKING** | Real ONNX runtime with `yolov8n.onnx`, `ppe_safety.onnx`, `fire_detection.onnx`. Floor polygon keypoint logic (feet in polygon, perspective rejection, 5-frame temporal smoothing) is solid and passes tests. |
| **Supervisor Flow** | `Supervisor.jsx` | Solid | Mobile UI handles acknowledge, take action, awaiting verification, and CCTV re-verification. |

---

## 3. Dangerous Assumptions & Fake/Mock Logic Found

1. **Embedding & Vector Memory Absence**:
   - Previous components claimed "Semantic Safety Memory" but actually computed word-overlap ratios or placeholder similarity. Real transformer embeddings (`intfloat/e5-small-v2`) and FAISS vector indexes were not installed.
2. **Dataset Outcome Fields Confused with Precursors**:
   - In older dataset processing scripts, injury severity outcomes (`Hospitalized`, `Amputation`, `NatureTitle`) were used as proxies for SIF precursor presence. This is an invalid HSE assumption: a fatal precursor (e.g., rigger under suspended load) can occur with zero injury.
3. **JSON File Persistence as "Database"**:
   - Relying on `safety_events.json` across concurrent asynchronous tasks led to file-locking conflicts (`[WinError 5] Access is denied` on Windows). SQLite relational database is required.
4. **HSE Governance Claim vs. Implementation**:
   - Pattern review was a single toggle without an immutable audit trail (`reviewer_role`, `previous_value`, `new_value`, dependency-aware recomputation).

---

## 4. Reusable vs. Refactor vs. Replace Matrix

### 4.1 Reusable Components (Keep & Integrate)
- **CCTV Floor Polygon & Keypoint Occupancy Engine** (`detection.py`, `test_zone.py`): Proven perspective-rejection logic, temporal smoothing (5 frames), and exit debouncing.
- **REST API Scaffolding & FastAPI App** (`main.py`): Lifespan handlers, CORS middleware, WebSocket broadcast primitives.
- **Supervisor Mobile & Dashboard UI** (`Supervisor.jsx`, `Dashboard.jsx`, `ReportsView.jsx`): Responsive views with clear visual hierarchy.

### 4.2 Components Requiring Refactoring
- **`UnifiedEventStore`**: Must migrate backend storage from JSON files to a robust SQLite database schema (`shramrakshak.db`) with complete table normalization.
- **`AssertionDetector`**: Must integrate with a real tokenizer and clause preprocessor to handle clause-level assertions and double-negation ambiguities safely.
- **`SafetyMemory`**: Must replace token-set recurrence with Two-Stage E5 + FAISS + Structured Multi-Attribute Reasoning.

### 4.3 Components Requiring Replacement / New Creation
- **`backend/nlp_engine/preprocessor.py`**: Brand new module for character-offset preserving normalization, clause segmentation, modal/conditional/negation tagging.
- **`ontology/`**: Brand new directory with YAML files for activities, energies, exposures, barriers, barrier states, consequences, LSR rules, uncertainty.
- **`backend/nlp_engine/semantic_memory.py`**: Brand new module loading `intfloat/e5-small-v2`, embedding generation with `passage:`/`query:` prefixes, FAISS index management, persistence, and reload.
- **`dataset_pipeline/`**: Refactored modular pipeline with validation, normalization, provenance tracking, and deterministic run manifests.

---

## 5. Architectural Gap Analysis Against Prompt

| Prompt Requirement | Current Status | Remediation Plan |
| :--- | :--- | :--- |
| **P0.1 Canonical SafetyEvent** | Partial | Define definitive model in `backend/models_canonical.py` consumed by all modules. |
| **P0.2 NLP Preprocessor** | Absent | Implement `backend/nlp_engine/preprocessor.py` with offset preservation. |
| **P0.3 Assertion Reasoning** | Partial | Pass all 8 mandatory adversarial test cases at canonical event level. |
| **P0.4 Central Safety Ontology** | Scattered | Create `ontology/*.yaml` and ontology validator. |
| **P0.5 Traceable Evidence Spans** | Partial | Enforce character-exact verification against raw input strings. |
| **P0.6 Real SIF Pathway** | Partial | Implement evidence-based equation: Hazard + Exposure + Failed Control + Consequence. |
| **P0.7 Structured IOGP LSR** | Partial | Multi-label mapper consuming `SafetyEvent`. |
| **P1.1 Data Ingestion Pipeline** | Partial | Create modular `dataset_pipeline/` supporting CSV, JSON, JSONL. |
| **P1.2 Dataset Provenance** | Partial | Enforce provenance flags (`is_oil_data=False`, `UNLABELED_FOR_SIF`). |
| **P1.3 Real E5 Embeddings** | Absent | Load `intfloat/e5-small-v2`, compute embeddings, build FAISS index. |
| **P1.4 Two-Stage Recurrence** | Absent | Stage 1 (FAISS cosine) + Stage 2 (Multi-attribute structured match). |
| **P1.5 SQLite Persistent Memory** | Absent | Implement `backend/data/shramrakshak.db` with 11 relational tables. |
| **P1.6 Run Manifest Logging** | Absent | Generate deterministic run manifest per pipeline execution. |
| **P1.7 Pattern Governance** | Basic | Enforce `CANDIDATE` default, explicit HSE review, immutable audit log. |
| **P1.8 Correction Propagation** | Absent | Implement dependency-aware recomputation cascade upon human edits. |
| **P2.1 Precondition Engine** | Basic | Formulate safety preconditions from HSE-validated recurring patterns. |
| **P2.2 Future Work Evidence** | Basic | Verify structured evidence against required preconditions. |
| **P2.3 CCTV Event Integration** | Working | CCTV breaches generate canonical `SafetyEvent`. |
| **P2.5 CCTV Verification** | Working | Closed-loop verification with re-breach detection. |
| **P4 Evaluation & Metrics** | Absent | Create evaluation dataset and compute precision, recall, F1, false negatives. |

---

## 6. Audit Conclusion & Next Steps

The repository has genuine Computer Vision primitives and a clean frontend framework, but lacks the core ML/NLP engineering rigor demanded for an enterprise safety intelligence system: real transformer embeddings, FAISS vector search, SQLite state persistence, structured ontology configurations, and dependency-aware human correction propagation.

Execution will proceed sequentially through Phases 4–17 without shortcuts.
