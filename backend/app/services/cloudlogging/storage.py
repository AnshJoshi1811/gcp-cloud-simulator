"""In-memory storage for Cloud Logging entries and sinks."""

from typing import Dict, List, Optional, Any
from collections import deque
import re
import threading

from .models import LogEntry, LogSink, Severity

MAX_ENTRIES_PER_PROJECT = 10000


class LoggingStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.entries: Dict[str, deque] = {}  # project_id -> deque[LogEntry]
        self.sinks: Dict[str, Dict[str, LogSink]] = {}  # project_id -> sink_id -> LogSink

    def write_entry(
        self, project_id: str, log_name: str, severity: str = Severity.DEFAULT,
        text_payload: Optional[str] = None, json_payload: Optional[Dict[str, Any]] = None,
        resource_type: str = "global", labels: Optional[Dict[str, str]] = None,
    ) -> LogEntry:
        entry = LogEntry(
            project_id=project_id, log_name=log_name, severity=severity,
            text_payload=text_payload, json_payload=json_payload,
            resource_type=resource_type, labels=labels or {},
        )
        with self._lock:
            bucket = self.entries.setdefault(project_id, deque(maxlen=MAX_ENTRIES_PER_PROJECT))
            bucket.append(entry)
        return entry

    def list_entries(
        self, project_ids: List[str], filter_str: str = "", page_size: int = 100,
        order_by: str = "timestamp desc",
    ) -> List[LogEntry]:
        all_entries: List[LogEntry] = []
        for pid in project_ids:
            all_entries.extend(self.entries.get(pid, []))

        all_entries = self._apply_filter(all_entries, filter_str)

        reverse = "desc" in order_by
        all_entries.sort(key=lambda e: e.timestamp, reverse=reverse)
        return all_entries[:page_size]

    def _apply_filter(self, entries: List[LogEntry], filter_str: str) -> List[LogEntry]:
        """Supports a practical subset of the Cloud Logging query language:
        severity>=X / severity=X, logName=X (substring), resource.type=X.
        Unrecognized clauses are ignored rather than erroring, since the full
        grammar is large and callers mostly need these three in practice.
        """
        if not filter_str.strip():
            return entries

        clauses = [c.strip() for c in re.split(r"\bAND\b", filter_str, flags=re.IGNORECASE) if c.strip()]
        result = entries
        for clause in clauses:
            m = re.match(r'severity\s*(>=|=)\s*"?(\w+)"?', clause, re.IGNORECASE)
            if m:
                op, value = m.groups()
                value = value.upper()
                if op == ">=":
                    result = [e for e in result if Severity.rank(e.severity) >= Severity.rank(value)]
                else:
                    result = [e for e in result if e.severity == value]
                continue
            m = re.match(r'logName\s*=\s*"?([^"]+)"?', clause, re.IGNORECASE)
            if m:
                value = m.group(1)
                result = [e for e in result if value in e.log_name]
                continue
            m = re.match(r'resource\.type\s*=\s*"?([^"]+)"?', clause, re.IGNORECASE)
            if m:
                value = m.group(1)
                result = [e for e in result if e.resource_type == value]
                continue
        return result

    def create_sink(self, project_id: str, sink_id: str, destination: str, filter_str: str = "") -> LogSink:
        with self._lock:
            project_sinks = self.sinks.setdefault(project_id, {})
            if sink_id in project_sinks:
                raise ValueError(f"Sink '{sink_id}' already exists")
            sink = LogSink(project_id=project_id, sink_id=sink_id, destination=destination, filter=filter_str)
            project_sinks[sink_id] = sink
            return sink

    def get_sink(self, project_id: str, sink_id: str) -> Optional[LogSink]:
        return self.sinks.get(project_id, {}).get(sink_id)

    def list_sinks(self, project_id: str) -> List[LogSink]:
        return list(self.sinks.get(project_id, {}).values())

    def delete_sink(self, project_id: str, sink_id: str) -> bool:
        with self._lock:
            if sink_id in self.sinks.get(project_id, {}):
                del self.sinks[project_id][sink_id]
                return True
            return False

    def get_stats(self) -> Dict[str, int]:
        return {
            "entries": sum(len(e) for e in self.entries.values()),
            "sinks": sum(len(s) for s in self.sinks.values()),
        }


storage = LoggingStorage()
