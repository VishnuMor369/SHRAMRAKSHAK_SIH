"""
SHRAMRAKSHAK: Persistent SQLite Safety Memory & Storage Engine
SIH 2026 Problem Statement: SIH26165

Implements P1.5 Persistent Safety Memory.
Target: backend/data/shramrakshak.db
Ensures complete persistence across process restarts.
Uses WAL journal mode with busy_timeout for resilient concurrent operations.
"""

import os
import json
import sqlite3
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from datetime import datetime

try:
    from .models_canonical import (
        SafetyEvent, EvidenceSpan, SafetyPattern, RecurrenceResult,
        WorkPrecondition, WorkCheckResult, RunManifest,
        AssertionStatus, TemporalStatus, BarrierState, SIFStatus, ReviewStatus, RecurrenceRelationship,
        ExposureStatus
    )
except ImportError:
    from models_canonical import (
        SafetyEvent, EvidenceSpan, SafetyPattern, RecurrenceResult,
        WorkPrecondition, WorkCheckResult, RunManifest,
        AssertionStatus, TemporalStatus, BarrierState, SIFStatus, ReviewStatus, RecurrenceRelationship,
        ExposureStatus
    )

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "shramrakshak.db")


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                raw_text TEXT NOT NULL,
                source TEXT,
                site TEXT,
                location TEXT,
                reporter TEXT,
                timestamp TEXT,
                metadata_json TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                report_id TEXT,
                source TEXT,
                timestamp TEXT,
                site TEXT,
                location TEXT,
                activity TEXT,
                energy TEXT,
                exposure TEXT,
                barrier TEXT,
                barrier_state TEXT,
                consequence TEXT,
                assertion TEXT,
                temporal_status TEXT,
                sif_status TEXT,
                sif_reasons TEXT,
                lsr TEXT,
                uncertainty TEXT,
                confidence REAL,
                review_status TEXT,
                embedding_id TEXT,
                pattern_id TEXT,
                provenance TEXT,
                lifecycle_state TEXT,
                machine_observation INTEGER,
                narrative TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (report_id) REFERENCES reports(report_id)
            );

            CREATE TABLE IF NOT EXISTS evidence_spans (
                span_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                value TEXT NOT NULL,
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                text TEXT NOT NULL,
                confidence REAL,
                source TEXT,
                FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                embedding_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                dim INTEGER NOT NULL,
                passage_text TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS patterns (
                pattern_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                activity TEXT,
                energy TEXT,
                exposure TEXT,
                barrier TEXT,
                occurrence_count INTEGER DEFAULT 1,
                duplicate_count INTEGER DEFAULT 0,
                validation_status TEXT DEFAULT 'CANDIDATE',
                reviewer_role TEXT,
                reviewed_at TEXT,
                review_notes TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS pattern_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                similarity REAL,
                reason TEXT,
                added_at TEXT,
                FOREIGN KEY (pattern_id) REFERENCES patterns(pattern_id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_value TEXT,
                new_value TEXT,
                reason TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS preconditions (
                precondition_id TEXT PRIMARY KEY,
                pattern_id TEXT,
                title TEXT NOT NULL,
                required_barrier TEXT NOT NULL,
                required_evidence_types TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT,
                FOREIGN KEY (pattern_id) REFERENCES patterns(pattern_id)
            );

            CREATE TABLE IF NOT EXISTS future_work_checks (
                check_id TEXT PRIMARY KEY,
                package_id TEXT NOT NULL,
                activity TEXT NOT NULL,
                location TEXT NOT NULL,
                precondition_id TEXT,
                status TEXT NOT NULL,
                findings TEXT,
                missing_evidence TEXT,
                evaluated_at TEXT,
                FOREIGN KEY (precondition_id) REFERENCES preconditions(precondition_id)
            );

            CREATE TABLE IF NOT EXISTS verification_records (
                verification_id TEXT PRIMARY KEY,
                event_id TEXT,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                timestamp TEXT,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            );

            CREATE TABLE IF NOT EXISTS run_manifests (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT,
                dataset_name TEXT,
                dataset_hash TEXT,
                code_version TEXT,
                model_name TEXT,
                model_version TEXT,
                ontology_version TEXT,
                config_hash TEXT,
                records_seen INTEGER,
                records_processed INTEGER,
                records_failed INTEGER,
                events_created INTEGER,
                patterns_created INTEGER,
                reviews_executed INTEGER,
                embeddings_created INTEGER,
                execution_time_seconds REAL,
                metadata_json TEXT
            );

            -- Indexes for fast candidate lookups and joins
            CREATE INDEX IF NOT EXISTS idx_events_sif ON events(sif_status);
            CREATE INDEX IF NOT EXISTS idx_events_activity ON events(activity);
            CREATE INDEX IF NOT EXISTS idx_events_site ON events(site);
            CREATE INDEX IF NOT EXISTS idx_events_pattern ON events(pattern_id);
            CREATE INDEX IF NOT EXISTS idx_spans_event ON evidence_spans(event_id);
            CREATE INDEX IF NOT EXISTS idx_pattern_members_pattern ON pattern_members(pattern_id);
            CREATE INDEX IF NOT EXISTS idx_pattern_members_event ON pattern_members(event_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_target ON reviews(target_id);
            """)

    # -------------------------------------------------------------
    # Report CRUD
    # -------------------------------------------------------------
    def insert_report(self, report_id: str, raw_text: str, source: str = "HUMAN",
                      site: str = "OIL Field Duliajan", location: str = "Rig 04",
                      reporter: str = "Staff", metadata: Optional[Dict[str, Any]] = None) -> str:
        with self.get_connection() as conn:
            now = datetime.now().isoformat()
            conn.execute("""
            INSERT OR REPLACE INTO reports
            (report_id, raw_text, source, site, location, reporter, timestamp, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (report_id, raw_text, source, site, location, reporter, now,
                  json.dumps(metadata or {}), now))
        return report_id

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata_json"] = json.loads(d["metadata_json"] or "{}")
            return d

    # -------------------------------------------------------------
    # Event CRUD (Canonical SafetyEvent)
    # -------------------------------------------------------------
    def save_event(self, event: SafetyEvent) -> SafetyEvent:
        with self.get_connection() as conn:
            if event.report_id:
                conn.execute("""
                INSERT OR IGNORE INTO reports (report_id, raw_text, source, site, location, reporter, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (event.report_id, event.narrative or "Auto-generated report header", event.source, event.site, event.location, "System", event.created_at))

            conn.execute("""
            INSERT OR REPLACE INTO events
            (event_id, report_id, source, timestamp, site, location,
             activity, energy, exposure, barrier, barrier_state, consequence,
             assertion, temporal_status, sif_status, sif_reasons, lsr,
             uncertainty, confidence, review_status, embedding_id, pattern_id,
             provenance, lifecycle_state, machine_observation, narrative, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.report_id,
                event.source,
                event.timestamp,
                event.site,
                event.location,
                event.activity,
                event.energy,
                event.exposure,
                json.dumps(event.barrier),
                json.dumps(event.barrier_state),
                event.consequence,
                event.assertion.value if isinstance(event.assertion, AssertionStatus) else str(event.assertion),
                event.temporal_status.value if isinstance(event.temporal_status, TemporalStatus) else str(event.temporal_status),
                event.sif_status.value if isinstance(event.sif_status, SIFStatus) else str(event.sif_status),
                json.dumps(event.sif_reasons),
                json.dumps(event.lsr),
                json.dumps(event.uncertainty),
                event.confidence,
                event.review_status.value if isinstance(event.review_status, ReviewStatus) else str(event.review_status),
                event.embedding_id,
                event.pattern_id,
                json.dumps(event.provenance),
                event.lifecycle_state,
                1 if event.machine_observation else 0,
                event.narrative,
                event.created_at,
                datetime.now().isoformat()
            ))

            # Store evidence spans
            conn.execute("DELETE FROM evidence_spans WHERE event_id = ?", (event.event_id,))
            for sp in event.evidence:
                span_dict = sp.to_dict() if hasattr(sp, "to_dict") else sp
                conn.execute("""
                INSERT INTO evidence_spans (event_id, field_name, value, start_offset, end_offset, text, confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    span_dict.get("field", ""),
                    span_dict.get("value", ""),
                    span_dict.get("start_offset", 0),
                    span_dict.get("end_offset", 0),
                    span_dict.get("text", ""),
                    span_dict.get("confidence", 1.0),
                    span_dict.get("source", "TEXT_EXTRACTION")
                ))
        return event

    def get_event(self, event_id: str) -> Optional[SafetyEvent]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_event(conn, row)

    def list_events(self, limit: int = 100, sif_filter: Optional[str] = None) -> List[SafetyEvent]:
        with self.get_connection() as conn:
            if sif_filter:
                cur = conn.execute("SELECT * FROM events WHERE sif_status = ? ORDER BY timestamp DESC LIMIT ?",
                                   (sif_filter, limit))
            else:
                cur = conn.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            return [self._row_to_event(conn, r) for r in rows]

    def count_events(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            sif = conn.execute("SELECT COUNT(*) FROM events WHERE sif_status = 'SIF-POTENTIAL'").fetchone()[0]
            review = conn.execute("SELECT COUNT(*) FROM events WHERE sif_status = 'REVIEW_REQUIRED'").fetchone()[0]
            no_sif = conn.execute("SELECT COUNT(*) FROM events WHERE sif_status = 'NO_SIF_POTENTIAL_IDENTIFIED'").fetchone()[0]
            return {
                "total": total,
                "sif_potential": sif,
                "review_required": review,
                "no_sif_potential": no_sif
            }

    def _row_to_event(self, conn: sqlite3.Connection, row: sqlite3.Row) -> SafetyEvent:
        d = dict(row)
        # Fetch spans
        cur = conn.execute("SELECT * FROM evidence_spans WHERE event_id = ?", (d["event_id"],))
        spans_rows = cur.fetchall()
        spans = [
            EvidenceSpan(
                field=s["field_name"],
                value=s["value"],
                start_offset=s["start_offset"],
                end_offset=s["end_offset"],
                text=s["text"],
                confidence=s["confidence"],
                source=s["source"]
            ) for s in spans_rows
        ]

        # Safely resolve Enums by either value or name
        as_val = d["assertion"]
        assertion_enum = AssertionStatus(as_val) if as_val in [a.value for a in AssertionStatus] else (
            AssertionStatus[as_val] if as_val in AssertionStatus.__members__ else AssertionStatus.AFFIRMED
        )

        ts_val = d["temporal_status"]
        temporal_enum = TemporalStatus(ts_val) if ts_val in [t.value for t in TemporalStatus] else (
            TemporalStatus[ts_val] if ts_val in TemporalStatus.__members__ else TemporalStatus.DURING_EVENT
        )

        sif_val = d["sif_status"]
        sif_enum = SIFStatus(sif_val) if sif_val in [s.value for s in SIFStatus] else (
            SIFStatus[sif_val] if sif_val in SIFStatus.__members__ else SIFStatus.SIF_POTENTIAL
        )

        rev_val = d["review_status"]
        review_enum = ReviewStatus(rev_val) if rev_val in [r.value for r in ReviewStatus] else (
            ReviewStatus[rev_val] if rev_val in ReviewStatus.__members__ else ReviewStatus.CANDIDATE
        )

        exp_val = (d["exposure"] or "").upper()
        if "NO_HUMAN_EXPOSURE" in exp_val or "OUTSIDE" in exp_val or "SAFE BOUNDARY" in exp_val:
            exp_status = ExposureStatus.NEGATED
        elif "UNKNOWN" in exp_val or "NOT RECORDED" in exp_val:
            exp_status = ExposureStatus.UNKNOWN
        elif "POSSIBLE" in exp_val or "SUSPECTED" in exp_val:
            exp_status = ExposureStatus.POSSIBLE
        elif "INSIDE" in exp_val or "ENTERED" in exp_val or "CROSSED" in exp_val:
            exp_status = ExposureStatus.CONFIRMED
        else:
            exp_status = ExposureStatus.UNKNOWN

        return SafetyEvent(
            event_id=d["event_id"],
            report_id=d["report_id"],
            source=d["source"],
            timestamp=d["timestamp"],
            site=d["site"],
            location=d["location"],
            activity=d["activity"],
            energy=d["energy"],
            exposure=d["exposure"],
            exposure_status=exp_status,
            barrier=json.loads(d["barrier"] or "[]"),
            barrier_state=json.loads(d["barrier_state"] or "[]"),
            consequence=d["consequence"],
            assertion=assertion_enum,
            temporal_status=temporal_enum,
            sif_status=sif_enum,
            sif_reasons=json.loads(d["sif_reasons"] or "[]"),
            lsr=json.loads(d["lsr"] or "[]"),
            evidence=spans,
            uncertainty=json.loads(d["uncertainty"] or "[]"),
            confidence=d["confidence"],
            review_status=review_enum,
            embedding_id=d["embedding_id"],
            pattern_id=d["pattern_id"],
            provenance=json.loads(d["provenance"] or "{}"),
            lifecycle_state=d["lifecycle_state"],
            machine_observation=bool(d["machine_observation"]),
            narrative=d["narrative"] or "",
            created_at=d["created_at"],
            updated_at=d["updated_at"]
        )

    # -------------------------------------------------------------
    # Pattern CRUD
    # -------------------------------------------------------------
    def save_pattern(self, pattern: SafetyPattern) -> SafetyPattern:
        with self.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO patterns
            (pattern_id, title, activity, energy, exposure, barrier,
             occurrence_count, duplicate_count, validation_status,
             reviewer_role, reviewed_at, review_notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.title,
                pattern.activity,
                pattern.energy,
                pattern.exposure,
                pattern.barrier,
                pattern.occurrence_count,
                pattern.duplicate_count,
                pattern.validation_status.value if isinstance(pattern.validation_status, ReviewStatus) else str(pattern.validation_status),
                pattern.reviewer_role,
                pattern.reviewed_at,
                pattern.review_notes,
                pattern.created_at,
                datetime.now().isoformat()
            ))
        return pattern

    def get_pattern(self, pattern_id: str) -> Optional[SafetyPattern]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM patterns WHERE pattern_id = ?", (pattern_id,))
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            return SafetyPattern(
                pattern_id=d["pattern_id"],
                title=d["title"],
                activity=d["activity"],
                energy=d["energy"],
                exposure=d["exposure"],
                barrier=d["barrier"],
                occurrence_count=d["occurrence_count"],
                duplicate_count=d["duplicate_count"],
                validation_status=ReviewStatus(d["validation_status"]) if d["validation_status"] in ReviewStatus.__members__ else ReviewStatus.CANDIDATE,
                reviewer_role=d["reviewer_role"],
                reviewed_at=d["reviewed_at"],
                review_notes=d["review_notes"],
                created_at=d["created_at"],
                updated_at=d["updated_at"]
            )

    def list_patterns(self) -> List[SafetyPattern]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM patterns ORDER BY occurrence_count DESC")
            rows = cur.fetchall()
            return [
                SafetyPattern(
                    pattern_id=d["pattern_id"],
                    title=d["title"],
                    activity=d["activity"],
                    energy=d["energy"],
                    exposure=d["exposure"],
                    barrier=d["barrier"],
                    occurrence_count=d["occurrence_count"],
                    duplicate_count=d["duplicate_count"],
                    validation_status=ReviewStatus(d["validation_status"]) if d["validation_status"] in ReviewStatus.__members__ else ReviewStatus.CANDIDATE,
                    reviewer_role=d["reviewer_role"],
                    reviewed_at=d["reviewed_at"],
                    review_notes=d["review_notes"],
                    created_at=d["created_at"],
                    updated_at=d["updated_at"]
                ) for d in [dict(r) for r in rows]
            ]

    def add_pattern_member(self, pattern_id: str, event_id: str, relationship: str, similarity: float, reason: str):
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO pattern_members (pattern_id, event_id, relationship, similarity, reason, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (pattern_id, event_id, relationship, similarity, reason, datetime.now().isoformat()))

    def get_pattern_members(self, pattern_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM pattern_members WHERE pattern_id = ?", (pattern_id,))
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------
    # Reviews & Human Audit Logging
    # -------------------------------------------------------------
    def log_review(self, review_id: str, target_type: str, target_id: str,
                   reviewer_role: str, action: str, previous_value: Any,
                   new_value: Any, reason: str):
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO reviews (review_id, target_type, target_id, reviewer_role, action, previous_value, new_value, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review_id,
                target_type,
                target_id,
                reviewer_role,
                action,
                json.dumps(previous_value) if previous_value is not None else None,
                json.dumps(new_value) if new_value is not None else None,
                reason,
                datetime.now().isoformat()
            ))

    def list_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM reviews ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                if r["previous_value"]:
                    r["previous_value"] = json.loads(r["previous_value"])
                if r["new_value"]:
                    r["new_value"] = json.loads(r["new_value"])
            return rows

    # -------------------------------------------------------------
    # Future-Work Preconditions & Checks
    # -------------------------------------------------------------
    def save_precondition(self, prec: WorkPrecondition) -> WorkPrecondition:
        with self.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO preconditions
            (precondition_id, pattern_id, title, required_barrier, required_evidence_types, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                prec.precondition_id,
                prec.pattern_id,
                prec.title,
                prec.required_barrier,
                json.dumps(prec.required_evidence_types),
                prec.status,
                prec.created_at
            ))
        return prec

    def get_precondition(self, precondition_id: str) -> Optional[WorkPrecondition]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM preconditions WHERE precondition_id = ?", (precondition_id,))
            r = cur.fetchone()
            if not r:
                return None
            return WorkPrecondition(
                precondition_id=r["precondition_id"],
                pattern_id=r["pattern_id"],
                title=r["title"],
                required_barrier=r["required_barrier"],
                required_evidence_types=json.loads(r["required_evidence_types"] or "[]"),
                status=r["status"],
                created_at=r["created_at"]
            )

    def list_preconditions(self, active_only: bool = True) -> List[WorkPrecondition]:
        with self.get_connection() as conn:
            if active_only:
                cur = conn.execute("SELECT * FROM preconditions WHERE status = 'ACTIVE' ORDER BY created_at DESC")
            else:
                cur = conn.execute("SELECT * FROM preconditions ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [
                WorkPrecondition(
                    precondition_id=r["precondition_id"],
                    pattern_id=r["pattern_id"],
                    title=r["title"],
                    required_barrier=r["required_barrier"],
                    required_evidence_types=json.loads(r["required_evidence_types"] or "[]"),
                    status=r["status"],
                    created_at=r["created_at"]
                ) for r in rows
            ]

    def deactivate_preconditions_for_pattern(self, pattern_id: str) -> None:
        with self.get_connection() as conn:
            conn.execute("UPDATE preconditions SET status = 'INACTIVE' WHERE pattern_id = ?", (pattern_id,))

    def save_work_check(self, check: WorkCheckResult) -> WorkCheckResult:
        with self.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO future_work_checks
            (check_id, package_id, activity, location, precondition_id, status, findings, missing_evidence, evaluated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                check.check_id,
                check.package_id,
                check.activity,
                check.location,
                check.precondition_id,
                check.status,
                json.dumps(check.findings),
                json.dumps(check.missing_evidence),
                check.evaluated_at
            ))
        return check

    def list_work_checks(self, limit: int = 50) -> List[WorkCheckResult]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM future_work_checks ORDER BY evaluated_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            return [
                WorkCheckResult(
                    check_id=r["check_id"],
                    package_id=r["package_id"],
                    activity=r["activity"],
                    location=r["location"],
                    precondition_id=r["precondition_id"],
                    status=r["status"],
                    findings=json.loads(r["findings"] or "[]"),
                    missing_evidence=json.loads(r["missing_evidence"] or "[]"),
                    evaluated_at=r["evaluated_at"]
                ) for r in rows
            ]

    # -------------------------------------------------------------
    # Verification Records (CCTV & Audits)
    # -------------------------------------------------------------
    def save_verification(self, verification_id: str, event_id: Optional[str],
                          source: str, status: str, details: Any):
        with self.get_connection() as conn:
            # Validate foreign key reference if event_id is supplied
            actual_event_id = event_id
            if actual_event_id:
                exists = conn.execute("SELECT 1 FROM events WHERE event_id = ?", (actual_event_id,)).fetchone()
                if not exists:
                    actual_event_id = None

            details_json = json.dumps(details, default=str) if isinstance(details, (dict, list)) else json.dumps({"note": str(details)})
            conn.execute("""
            INSERT OR REPLACE INTO verification_records (verification_id, event_id, source, status, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                verification_id,
                actual_event_id,
                source,
                status,
                details_json,
                datetime.now().isoformat()
            ))

    def list_verifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM verification_records ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                if r["details"]:
                    try:
                        r["details"] = json.loads(r["details"])
                    except Exception:
                        pass
            return rows

    save_verification_record = save_verification
    get_verification_records = list_verifications

    # -------------------------------------------------------------
    # Run Manifests
    # -------------------------------------------------------------
    def save_manifest(self, manifest: RunManifest):
        with self.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO run_manifests
            (run_id, timestamp, dataset_name, dataset_hash, code_version, model_name,
             model_version, ontology_version, config_hash, records_seen, records_processed,
             records_failed, events_created, patterns_created, reviews_executed,
             embeddings_created, execution_time_seconds, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                manifest.run_id,
                manifest.timestamp,
                manifest.dataset_name,
                manifest.dataset_hash,
                manifest.code_version,
                manifest.model_name,
                manifest.model_version,
                manifest.ontology_version,
                manifest.config_hash,
                manifest.records_seen,
                manifest.records_processed,
                manifest.records_failed,
                manifest.events_created,
                manifest.patterns_created,
                manifest.reviews_executed,
                manifest.embeddings_created,
                manifest.execution_time_seconds,
                json.dumps(manifest.to_dict())
            ))

    def get_latest_manifest(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM run_manifests ORDER BY timestamp DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            if d["metadata_json"]:
                d["metadata_json"] = json.loads(d["metadata_json"])
            return d


# Global singleton instance
db = DatabaseManager()
