from dataclasses import dataclass, field
from enum import Enum
import re


class GovernanceVerdict(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_LIMITS = "ALLOW_WITH_LIMITS"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class GovernanceAssessment:
    verdict: GovernanceVerdict
    reason: str
    risks: tuple[str, ...] = field(default_factory=tuple)
    limits: dict = field(default_factory=dict)


class ConstitutionalGate:
    """Hard pre-execution governance boundary; model judgement is advisory only."""

    HUMAN_APPROVAL_CAPABILITIES = frozenset({
        "purchase", "approve", "delegate", "create_agent", "destroy_agent",
        "communicate", "send", "message", "publish",
    })

    def assess(self, *, capability, plan, context_snapshot="", reversible=False):
        capability = str(capability)
        normalized = re.sub(r"[^a-z0-9]+", "_", capability.casefold()).strip("_")
        tokens = set(normalized.split("_")) if normalized else set()
        capability_leaf = normalized.split("_")[-1] if normalized else ""
        sensitive_tokens = {
            "purchase", "approve", "approval", "delegate", "communicate",
            "send", "message", "publish", "delete", "destroy", "terminate",
            "revoke", "transfer", "withdraw", "charge", "dispatch", "deliver",
        }
        # Inspect the executable plan too: a benign capability name must not
        # launder a consequential operation embedded in a step or nested argument.
        plan_text = re.sub(r"[^a-z0-9]+", "_", repr(plan).casefold())
        plan_tokens = set(plan_text.split("_"))
        sensitive_action = (
            capability_leaf in self.HUMAN_APPROVAL_CAPABILITIES
            or bool(tokens & sensitive_tokens)
            or ({"create", "agent"} <= tokens)
            or ({"destroy", "agent"} <= tokens)
            or bool(plan_tokens & sensitive_tokens)
            or ({"create", "agent"} <= plan_tokens)
            or ({"destroy", "agent"} <= plan_tokens)
        )
        if not plan:
            return GovernanceAssessment(GovernanceVerdict.BLOCK, "empty executable plan")

        if sensitive_action:
            return GovernanceAssessment(
                GovernanceVerdict.REQUIRE_HUMAN_APPROVAL,
                f"capability '{capability}' is consequential and requires explicit human approval",
                ("external_or_irreversible_consequence",),
            )

        if not context_snapshot:
            return GovernanceAssessment(
                GovernanceVerdict.ALLOW_WITH_LIMITS,
                "bounded execution permitted, but universal context is incomplete",
                ("incomplete_context",),
                {"context_required_for_future_escalation": True},
            )

        return GovernanceAssessment(
            GovernanceVerdict.ALLOW,
            "bounded plan passed the deterministic constitutional pre-execution gate",
        )
