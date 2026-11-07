"""LOGOSECO service — the independent signed-grant authority (HTTP transport).

Horus asks this service to govern a capability. The service runs the three-layer
decision (gate + floor + deliberation) and, only for executable outcomes, mints
an Ed25519-signed grant in the format the existing Horus-side verifier accepts.
The private signing key lives only here. REQUIRE_HUMAN outcomes become pending
requests a human resolves; BLOCK outcomes mint nothing.
"""
from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .approver import Approver, plan_sha256
from .decision import decide
from .floor import GovernanceVector
from .store import InMemoryStore

POLICY_VERSION = os.environ.get("LOGOSECO_POLICY_VERSION", "v1")
APPROVER_TOKEN = os.environ.get("LOGOSECO_APPROVER_TOKEN", "")

_pem = os.environ.get("LOGOSECO_PRIVATE_KEY_PEM", "")
if _pem:
    APPROVER = Approver.from_pem(_pem.encode("utf-8"), POLICY_VERSION)
    _EPHEMERAL = False
else:
    APPROVER = Approver.generate(POLICY_VERSION)  # dev only — key is lost on restart
    _EPHEMERAL = True

STORE = InMemoryStore()
app = FastAPI(title="LOGOSECO Service", version="1.0.0")


class Binding(BaseModel):
    capability: str
    application: str
    plan_sha256: str
    execution_target: str
    session_id: str
    principal_id: str
    action_id: str


class GovernVector(BaseModel):
    honesty: float
    fairness: float
    consistency: float
    learning: float
    impact: float


class GovernRequest(BaseModel):
    plan: list[str]
    binding: Binding
    context_snapshot: str = ""
    reversible: bool = False
    governance_vector: Optional[GovernVector] = None
    ttl_seconds: int = Field(default=300, ge=10, le=3600)


@app.get("/status")
def status():
    return {
        "status": "OK",
        "service": "logoseco",
        "mode": "LIVE_SERVICE",
        "policy_intact": True,
        "policy_version": POLICY_VERSION,
        "log_records": STORE.count(),
        "ephemeral_key": _EPHEMERAL,
        "public_key_pem": APPROVER.public_key_pem().decode("ascii"),
    }


@app.post("/govern")
def govern(req: GovernRequest):
    b = req.binding
    # integrity: the plan and its bound hash must agree
    if b.plan_sha256 != plan_sha256(req.plan):
        raise HTTPException(status_code=400, detail="binding.plan_sha256 does not match plan")

    vec = None
    if req.governance_vector is not None:
        vec = GovernanceVector(**req.governance_vector.model_dump())

    d = decide(capability=b.capability, plan=req.plan,
               context_snapshot=req.context_snapshot, reversible=req.reversible,
               governance_vector=vec)

    meta = {"gate_verdict": d.gate_verdict, "floor_certified": d.floor_certified,
            "floor_reason": d.floor_reason, "reason": d.reason, "risks": list(d.risks)}
    STORE.record_decision({"capability": b.capability, "outcome": d.outcome, **meta})

    if d.outcome == "GRANT":
        grant = APPROVER.mint_grant(verdict=d.grant_verdict, limits=d.limits,
                                    binding=b.model_dump(),
                                    approved_by=f"logoseco:{POLICY_VERSION}",
                                    ttl_seconds=req.ttl_seconds)
        STORE.record_grant(grant, meta)
        return {"status": "GRANTED", "reason": d.reason, "grant": grant}

    if d.outcome == "PENDING_HUMAN":
        pending_id = secrets.token_hex(16)
        STORE.record_pending(pending_id, req.model_dump(), meta)
        return {"status": "PENDING_HUMAN", "pending_id": pending_id, "reason": d.reason}

    return JSONResponse(status_code=200,
                        content={"status": "BLOCKED", "reason": d.reason})


@app.post("/pending/{pending_id}/approve")
def approve(pending_id: str, authorization: str = Header(default="")):
    # Minimal human-approval auth (Stage-1b will harden: per-approver identity + signed input).
    if not APPROVER_TOKEN:
        raise HTTPException(status_code=503, detail="human approval endpoint disabled (no APPROVER_TOKEN set)")
    if authorization != f"Bearer {APPROVER_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")
    p = STORE.get_pending(pending_id)
    if p is None:
        raise HTTPException(status_code=404, detail="pending request not found")
    if p["status"] != "PENDING":
        raise HTTPException(status_code=409, detail=f"already {p['status']}")
    binding = p["request"]["binding"]
    grant = APPROVER.mint_grant(verdict="HUMAN_APPROVED", limits={},
                                binding=binding, approved_by="human:approver")
    STORE.record_grant(grant, p["meta"])
    STORE.resolve_pending(pending_id, approved=True, approved_by="human:approver",
                          grant_id=grant["grant_id"])
    return {"status": "GRANTED", "grant": grant}


@app.get("/grants/{grant_id}")
def get_grant(grant_id: str):
    g = STORE.get_grant(grant_id)
    if g is None:
        raise HTTPException(status_code=404, detail="grant not found")
    return g


@app.get("/audit")
def audit(limit: int = 100):
    return {"records": STORE.audit(limit=min(max(limit, 1), 500))}
