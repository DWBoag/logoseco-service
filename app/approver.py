"""LOGOSECO Approver — the SIGNING side.

Holds the Ed25519 PRIVATE key and mints grants in the exact format that
app/governance/signed_approver.py (the client verifier) accepts. The client
holds only the PUBLIC key and can never sign — authority lives here, not in the
intelligence that asks for it.

Grant format and signature are byte-compatible with the existing verifier:
constants (SIGNED_FIELDS, BOUND_FIELDS, GRANT_VERSION, _canonical) are imported
from signed_approver so the two can never drift.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from .governance.signed_approver import (
    SIGNED_FIELDS,
    BOUND_FIELDS,
    GRANT_VERSION,
    EXECUTABLE_VERDICTS,
    _canonical,
    _now,
)

DEFAULT_TTL_SECONDS = 300


class ApproverKeyError(RuntimeError):
    pass


def plan_sha256(plan) -> str:
    """Deterministic hash of a plan, bound into the grant so a grant for one plan
    cannot be replayed against a different one."""
    return hashlib.sha256(_canonical(list(plan)).encode("utf-8")).hexdigest()


class Approver:
    def __init__(self, private_key: Ed25519PrivateKey, policy_version: str):
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ApproverKeyError("private key must be Ed25519")
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise ApproverKeyError("policy_version is required")
        self._sk = private_key
        self.policy_version = policy_version

    @classmethod
    def from_pem(cls, pem: bytes, policy_version: str) -> "Approver":
        key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ApproverKeyError("PEM did not contain an Ed25519 private key")
        return cls(key, policy_version)

    @classmethod
    def generate(cls, policy_version: str) -> "Approver":
        return cls(Ed25519PrivateKey.generate(), policy_version)

    def public_key_pem(self) -> bytes:
        return self._sk.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def private_key_pem(self) -> bytes:
        return self._sk.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def mint_grant(self, *, verdict: str, limits: dict, binding: dict,
                   approved_by: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict:
        """Mint a signed grant. Only EXECUTABLE verdicts are ever minted; a
        REQUIRE_HUMAN_APPROVAL or BLOCK decision never produces a grant here."""
        if verdict not in EXECUTABLE_VERDICTS:
            raise ApproverKeyError(
                f"verdict {verdict!r} is not executable; grants are only minted for {EXECUTABLE_VERDICTS}")
        missing = [f for f in BOUND_FIELDS if binding.get(f) in (None, "")]
        if missing:
            raise ApproverKeyError("binding is missing required fields: " + ", ".join(missing))
        now = _now()
        grant = {
            "grant_version": GRANT_VERSION,
            "grant_id": secrets.token_hex(16),
            "nonce": secrets.token_hex(16),
            **{f: binding[f] for f in BOUND_FIELDS},
            "approved_by": approved_by,
            "verdict": verdict,
            "limits": dict(limits or {}),
            "policy_version": self.policy_version,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        payload = _canonical({f: grant[f] for f in SIGNED_FIELDS}).encode("utf-8")
        grant["signature"] = base64.b64encode(self._sk.sign(payload)).decode("ascii")
        return grant
