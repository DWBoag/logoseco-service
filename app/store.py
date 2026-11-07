"""Audit + grant/pending store for the LOGOSECO service.

Stage 1 ships an in-memory store so the service is runnable and testable without
external infra. A SupabaseStore with the same interface is wired once the
service's Supabase project exists (see docs scope). Every grant, pending request
and decision is recorded for audit/provenance.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._grants: dict[str, dict] = {}
        self._pending: dict[str, dict] = {}
        self._audit: list[dict] = []

    # grants ---------------------------------------------------------
    def record_grant(self, grant: dict, decision_meta: dict) -> None:
        with self._lock:
            self._grants[grant["grant_id"]] = {"grant": grant, "meta": decision_meta,
                                               "recorded_at": _now()}
            self._audit.append({"at": _now(), "event": "GRANT_ISSUED",
                               "grant_id": grant["grant_id"],
                               "verdict": grant["verdict"],
                               "capability": grant.get("capability")})

    def get_grant(self, grant_id: str) -> dict | None:
        with self._lock:
            return self._grants.get(grant_id)

    # pending (REQUIRE_HUMAN_APPROVAL) -------------------------------
    def record_pending(self, pending_id: str, request: dict, decision_meta: dict) -> None:
        with self._lock:
            self._pending[pending_id] = {"request": request, "meta": decision_meta,
                                        "status": "PENDING", "created_at": _now()}
            self._audit.append({"at": _now(), "event": "PENDING_HUMAN",
                               "pending_id": pending_id,
                               "capability": request.get("binding", {}).get("capability")})

    def get_pending(self, pending_id: str) -> dict | None:
        with self._lock:
            return self._pending.get(pending_id)

    def resolve_pending(self, pending_id: str, *, approved: bool, approved_by: str,
                        grant_id: str | None = None) -> None:
        with self._lock:
            p = self._pending.get(pending_id)
            if p is not None:
                p["status"] = "APPROVED" if approved else "DENIED"
                p["resolved_by"] = approved_by
                p["resolved_at"] = _now()
                p["grant_id"] = grant_id
            self._audit.append({"at": _now(),
                               "event": "HUMAN_APPROVED" if approved else "HUMAN_DENIED",
                               "pending_id": pending_id, "approved_by": approved_by,
                               "grant_id": grant_id})

    # audit ----------------------------------------------------------
    def record_decision(self, entry: dict) -> None:
        with self._lock:
            self._audit.append({"at": _now(), "event": "DECISION", **entry})

    def audit(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return list(self._audit[-limit:])

    def count(self) -> int:
        with self._lock:
            return len(self._audit)
