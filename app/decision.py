"""Three-layer governance decision for the LOGOSECO service.

Layer 1 — ConstitutionalGate (deterministic hard boundary).
Layer 2 — Governance Floor certification (no dimension compensates for another).
Layer 3 — Deliberative layer (v1: recorded upstream, non-overriding; reimplemented in Stage 3).

The binding result is the MOST RESTRICTIVE across layers. A floor-certification
failure cannot be out-voted by a permissive gate verdict: it forces at least
human approval. Only a GRANT outcome ever produces a signed grant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .governance.governance import (
    ConstitutionalGate,
    GovernanceVerdict,
    GovernanceAssessment,
)
from .floor import GovernanceVector, evaluate, CertificationResult

_EXECUTABLE = {
    GovernanceVerdict.ALLOW: "ALLOW",
    GovernanceVerdict.ALLOW_WITH_LIMITS: "ALLOW_WITH_LIMITS",
}


@dataclass(frozen=True)
class DecisionResult:
    outcome: str                      # GRANT | PENDING_HUMAN | BLOCKED
    grant_verdict: Optional[str]      # executable verdict to mint, when outcome == GRANT
    reason: str
    limits: dict = field(default_factory=dict)
    gate_verdict: str = ""
    floor_certified: Optional[bool] = None
    floor_reason: str = ""
    risks: tuple = ()


def decide(*, capability, plan, context_snapshot="", reversible=False,
           governance_vector: Optional[GovernanceVector] = None) -> DecisionResult:
    # Layer 1 — deterministic gate
    a: GovernanceAssessment = ConstitutionalGate().assess(
        capability=capability, plan=plan,
        context_snapshot=context_snapshot, reversible=reversible,
    )
    verdict = a.verdict
    reasons = [a.reason]

    # Layer 2 — governance floor (only when a vector is supplied)
    floor: Optional[CertificationResult] = None
    if governance_vector is not None:
        floor = evaluate(governance_vector)
        if not floor.certified:
            reasons.append("floor: " + floor.reason)
            if verdict in (GovernanceVerdict.ALLOW, GovernanceVerdict.ALLOW_WITH_LIMITS):
                verdict = GovernanceVerdict.REQUIRE_HUMAN_APPROVAL  # floor cannot be out-voted

    # Layer 3 — deliberative (v1 stub: recorded upstream; does not override here)

    if verdict == GovernanceVerdict.BLOCK:
        outcome, gv = "BLOCKED", None
    elif verdict == GovernanceVerdict.REQUIRE_HUMAN_APPROVAL:
        outcome, gv = "PENDING_HUMAN", None
    else:
        outcome, gv = "GRANT", _EXECUTABLE[verdict]

    return DecisionResult(
        outcome=outcome,
        grant_verdict=gv,
        reason="; ".join(r for r in reasons if r),
        limits=dict(a.limits or {}),
        gate_verdict=verdict.value,
        floor_certified=(floor.certified if floor else None),
        floor_reason=(floor.reason if floor else ""),
        risks=tuple(a.risks or ()),
    )
