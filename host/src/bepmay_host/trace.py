"""One structured JSON line per request: who (role, hashed subject), what (route, kind, ref), the outcome and timing.

Deliberately absent: the bearer token, the search query text, record bodies, customer ids. A denied record and a
nonexistent one produce the same outcome (`not_found`) because the host itself cannot tell them apart.
Lines go to the `bepmay_host.trace` logger and, when a path is given (HOST_TRACE_FILE), to a JSONL file that
`scripts/export_host_trace.py` turns into viewer data.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from datetime import datetime, timezone

_log = logging.getLogger("bepmay_host.trace")
REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def subject_tag(subject: str) -> str:
    """Stable, non-reversible tag so two requests by one user can be correlated without storing the identity."""
    return hashlib.sha256(subject.encode()).hexdigest()[:8]


def outcome_for(status: int, has_credentials: bool, explicit: str | None) -> str:
    if explicit:
        return explicit
    if status < 300:
        return "ok"
    return {401: "invalid_token" if has_credentials else "unauthenticated", 404: "not_found", 422: "invalid_input",
            503: "dependency_unavailable"}.get(status, "error")


class TraceRecorder:
    def __init__(self, path: str | None = None):
        self.path = path or None
        self._lock = threading.Lock()

    def emit(self, record: dict) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **record}
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        _log.info(line)
        if self.path:
            with self._lock, open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
