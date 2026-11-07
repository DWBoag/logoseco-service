"""Explicit LOGOSECO governance boundary for Padawan.

This local facade is NOT evidence of a live remote LOGOSECO service connection.
It routes assessments through the local deterministic policy kernel and labels
that deployment mode honestly until a verified LOGOSECO service adapter exists.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from .governance import ConstitutionalGate, GovernanceAssessment


@dataclass(frozen=True)
class GovernanceDecisionRecord:
    decision_id: str
    decided_at: str
    mode: str
    remote_service_connected: bool
    assessment: GovernanceAssessment


class LogosecoGovernanceSubstrate:
    """Mandatory governance facade; never confuses local policy with live service."""

    mode = "LOCAL_POLICY_KERNEL"
    remote_service_connected = False

    def __init__(self, policy_kernel=None):
        self.policy_kernel = policy_kernel or ConstitutionalGate()
        self.decisions = []

    def assess(self, *, capability, plan, context_snapshot="", reversible=False):
        assessment = self.policy_kernel.assess(
            capability=capability,
            plan=plan,
            context_snapshot=context_snapshot,
            reversible=reversible,
        )
        record = GovernanceDecisionRecord(
            decision_id="lgd-" + str(len(self.decisions) + 1).zfill(8),
            decided_at=datetime.now(timezone.utc).isoformat(),
            mode=self.mode,
            remote_service_connected=self.remote_service_connected,
            assessment=assessment,
        )
        self.decisions.append(record)
        return assessment
