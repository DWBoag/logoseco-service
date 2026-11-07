"""Padawan side of the LOGOSECO Approver (install as app/core/signed_approver.py).

Padawan holds only the Approver's PUBLIC key. It asks the Approver for a
decision over the request socket, verifies the returned grant, records single
use, and imports it into LiveAuthorityEngine. It cannot approve anything
itself: the request socket offers no approve operation and Padawan has no
signing key.
"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

GRANT_VERSION = 1
BOUND_FIELDS = ("capability", "application", "plan_sha256", "execution_target",
                "session_id", "principal_id", "action_id")
SIGNED_FIELDS = ("grant_version", "grant_id", "nonce", *BOUND_FIELDS, "approved_by",
                 "verdict", "limits", "policy_version", "issued_at", "expires_at")
EXECUTABLE_VERDICTS = ("ALLOW", "ALLOW_WITH_LIMITS", "HUMAN_APPROVED")


class GrantRejected(PermissionError):
    pass


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _now():
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ApproverOutcome:
    status: str            # GRANTED | PENDING_HUMAN | BLOCKED | UNAVAILABLE
    detail: str
    grant: dict | None = None
    pending_id: str | None = None


class SignedApproverClient:
    def __init__(self, socket_path, public_key_path, used_ledger_path, timeout=10.0):
        self.socket_path = str(socket_path)
        key = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("Approver public key must be Ed25519")
        self.public_key = key
        self.used_path = Path(used_ledger_path)
        self.used_path.parent.mkdir(parents=True, exist_ok=True)
        self.used_path.touch(exist_ok=True)
        self.timeout = timeout

    # transport -------------------------------------------------------
    def _call(self, message: dict) -> dict:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)
            s.connect(self.socket_path)
            s.sendall((json.dumps(message) + "\n").encode("utf-8"))
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        reply = json.loads(buf)
        if not isinstance(reply, dict):
            raise ValueError("Approver reply must be an object")
        return reply

    def healthy(self) -> bool:
        """Require a healthy policy and verifiable audit-log metadata, not just a socket reply."""
        try:
            reply = self._call({"op": "health"})
            return (
                reply.get("status") == "OK"
                and reply.get("policy_intact") is True
                and isinstance(reply.get("policy_version"), str)
                and bool(reply.get("policy_version"))
                and type(reply.get("log_records")) is int
                and reply["log_records"] >= 0
            )
        except (OSError, ValueError, TypeError):
            return False

    # verification ----------------------------------------------------
    def verify_signature(self, grant) -> bool:
        """True only for an unmodified grant signed by the Approver's key."""
        if not isinstance(grant, dict) or set(grant) != set(SIGNED_FIELDS) | {"signature"}:
            return False
        try:
            sig = base64.b64decode(grant["signature"], validate=True)
            self.public_key.verify(sig, _canonical({f: grant[f] for f in SIGNED_FIELDS}).encode("utf-8"))
            return True
        except (ValueError, TypeError, InvalidSignature):
            return False

    def check(self, grant: dict, expected: dict) -> dict:
        if not isinstance(grant, dict) or set(grant) != set(SIGNED_FIELDS) | {"signature"}:
            raise GrantRejected("grant has missing or unexpected fields")
        if not self.verify_signature(grant):
            raise GrantRejected("grant signature invalid")
        if grant["grant_version"] != GRANT_VERSION:
            raise GrantRejected("unsupported grant version")
        if grant["verdict"] not in EXECUTABLE_VERDICTS:
            raise GrantRejected("grant verdict does not permit execution")
        try:
            expiry = datetime.fromisoformat(grant["expires_at"])
            if expiry.tzinfo is None:
                raise ValueError
        except (TypeError, ValueError):
            raise GrantRejected("grant expiry invalid")
        if expiry <= _now():
            raise GrantRejected("grant expired")
        mismatches = [f for f in BOUND_FIELDS if grant[f] != expected.get(f)]
        if mismatches:
            raise GrantRejected("grant binding mismatch: " + ", ".join(sorted(mismatches)))
        if self._is_used(grant["grant_id"]):
            raise GrantRejected("grant already used")
        return grant

    def _is_used(self, grant_id):
        """Fail closed when the single-use grant ledger cannot be trusted."""
        try:
            lines = self.used_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (not isinstance(record, dict)
                        or not isinstance(record.get("grant_id"), str)):
                    raise ValueError("invalid used-grant ledger record")
                if record["grant_id"] == grant_id:
                    return True
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise GrantRejected("used-grant ledger unreadable or corrupt") from exc
        return False

    def consume(self, grant: dict, expected: dict) -> dict:
        with self.used_path.open("a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                self.check(grant, expected)
                fh.write(json.dumps({"grant_id": grant["grant_id"], "used_at": _now().isoformat()}) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return grant

    # decisions -------------------------------------------------------
    def obtain(self, *, plan, context_snapshot="", advisory=None, **binding) -> ApproverOutcome:
        expected = {f: binding.get(f) for f in BOUND_FIELDS}
        request = {**expected, "plan": list(plan), "context_snapshot": context_snapshot}
        if advisory:
            request["advisory"] = advisory
        try:
            reply = self._call({"op": "decide", "request": request})
        except (OSError, ValueError) as exc:
            return ApproverOutcome("UNAVAILABLE", "LOGOSECO Approver unreachable: " + type(exc).__name__)
        return self._outcome(reply, expected)

    def collect(self, pending_id: str, **binding) -> ApproverOutcome:
        expected = {f: binding.get(f) for f in BOUND_FIELDS}
        try:
            reply = self._call({"op": "collect", "pending_id": pending_id})
        except (OSError, ValueError) as exc:
            return ApproverOutcome("UNAVAILABLE", "LOGOSECO Approver unreachable: " + type(exc).__name__)
        return self._outcome(reply, expected, pending_id)

    def _outcome(self, reply, expected, pending_id=None):
        status = reply.get("status")
        if status == "GRANTED":
            try:
                grant = self.consume(reply.get("grant"), expected)
            except GrantRejected as exc:
                return ApproverOutcome("BLOCKED", "grant rejected: " + str(exc))
            return ApproverOutcome("GRANTED", reply.get("reason", "granted"), grant=grant)
        if status == "PENDING_HUMAN":
            return ApproverOutcome("PENDING_HUMAN",
                                   "waiting for human approval in the LOGOSECO Approver",
                                   pending_id=reply.get("pending_id"))
        if status == "PENDING":
            return ApproverOutcome("PENDING_HUMAN", "still waiting for human approval", pending_id=pending_id)
        return ApproverOutcome("BLOCKED", str(reply.get("reason") or status or "blocked"))
