import threading
from typing import Dict, List, Optional, Any

class DatasetStore:
    """
    In-memory storage and indexing manager for uploaded CSV dataset processing results.
    Provides fast, thread-safe pagination, filtering, and metric lookups.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._current_dataset_info: Optional[Dict[str, Any]] = None
        self._processed_reports: List[Dict[str, Any]] = []
        self._reports_by_id: Dict[str, Dict[str, Any]] = {}
        self._summary_report: Optional[Dict[str, Any]] = None
        self._progress: float = 0.0
        self._status: str = "IDLE" # "IDLE" | "VALIDATED" | "PROCESSING" | "COMPLETED" | "FAILED"
        self._error_message: Optional[str] = None

    def reset(self):
        with self._lock:
            self._current_dataset_info = None
            self._processed_reports = []
            self._reports_by_id = {}
            self._summary_report = None
            self._progress = 0.0
            self._status = "IDLE"
            self._error_message = None

    def set_validated_info(self, info: Dict[str, Any]):
        with self._lock:
            self._current_dataset_info = info
            self._status = "VALIDATED"
            self._progress = 0.1
            self._error_message = None

    def update_progress(self, progress: float, status_text: str = "PROCESSING"):
        with self._lock:
            self._progress = min(1.0, max(0.0, progress))
            self._status = status_text

    def set_completed_results(self, reports: List[Dict[str, Any]], summary: Dict[str, Any]):
        with self._lock:
            self._processed_reports = reports
            self._reports_by_id = {r["report_id"]: r for r in reports}
            self._summary_report = summary
            self._progress = 1.0
            self._status = "COMPLETED"
            self._error_message = None

    def set_failed(self, error: str):
        with self._lock:
            self._status = "FAILED"
            self._error_message = error
            self._progress = 0.0

    def get_status_info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "progress": self._progress,
                "dataset_info": self._current_dataset_info,
                "error": self._error_message,
                "total_processed": len(self._processed_reports),
                "has_summary": self._summary_report is not None
            }

    def get_summary(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._summary_report

    def get_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._reports_by_id.get(report_id)

    def get_filtered_reports(
        self,
        status_filter: str = "ALL",
        source_filter: str = "ALL",
        lsr_filter: Optional[str] = None,
        precursor_filter: Optional[str] = None,
        site_filter: Optional[str] = None,
        activity_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        with self._lock:
            filtered = list(self._processed_reports)

            # SIF / Risk status filter
            if status_filter == "SIF_POTENTIAL":
                filtered = [r for r in filtered if r.get("sif_potential") is True]
            elif status_filter == "HIGH_RISK":
                filtered = [r for r in filtered if r.get("risk_score", 0) >= 60]
            elif status_filter == "NEEDS_REVIEW":
                filtered = [r for r in filtered if r.get("needs_hse_review") is True or r.get("confidence", 100) < 70]

            # Source filter
            if source_filter != "ALL":
                filtered = [r for r in filtered if r.get("source") == source_filter]

            # Specific drill-down filters
            if lsr_filter:
                lsr_lower = lsr_filter.lower()
                filtered = [r for r in filtered if any(lsr_lower in str(rule).lower() for rule in r.get("life_saving_rules", []))]

            if precursor_filter:
                prec_lower = precursor_filter.lower()
                filtered = [
                    r for r in filtered
                    if prec_lower in str(r.get("precursor", "")).lower()
                    or prec_lower in str(r.get("barrier_failure", "")).lower()
                ]

            if site_filter:
                site_lower = site_filter.lower()
                filtered = [r for r in filtered if site_lower in str(r.get("location", "")).lower() or site_lower in str(r.get("employer", "")).lower()]

            if activity_filter:
                act_lower = activity_filter.lower()
                filtered = [r for r in filtered if act_lower in str(r.get("activity", "")).lower()]

            if search_query:
                q_lower = search_query.lower()
                filtered = [
                    r for r in filtered
                    if q_lower in str(r.get("description", "")).lower()
                    or q_lower in str(r.get("report_id", "")).lower()
                    or q_lower in str(r.get("hazard", "")).lower()
                ]

            total_count = len(filtered)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_items = filtered[start_idx:end_idx]

            return {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                "reports": page_items
            }

dataset_store = DatasetStore()
