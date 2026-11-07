from dataclasses import dataclass, field
from enum import IntEnum


class AssuranceRung(IntEnum):
    ALLOW = 0
    ADDITIONAL_EVIDENCE = 1
    RETRIEVAL = 2
    INDEPENDENT_VERIFICATION = 4
    SIMULATION = 5
    CONSTRAINED_EXECUTION = 6
    HUMAN_APPROVAL = 7
    BLOCK = 8


@dataclass
class CapabilityRecord:
    capability: str
    success_rate: float
    sample_size: int
    evidence: list[str] = field(default_factory=list)

    @property
    def demonstrated(self):
        return self.sample_size >= 5 and self.success_rate >= 0.90


@dataclass
class AssuranceAssessment:
    capability: str
    consequence: str
    reversibility: str
    evidence_strength: str
    knowledge_state: str
    context_integrity: str
    instruction_fidelity: str
    assurance_debt: int = 0
    self_reported_confidence: float = 0.0


@dataclass
class AssuranceResult:
    rung: AssuranceRung
    tags: list[str] = field(default_factory=list)
    assurance_debt_delta: int = 0


class CapabilityAssuranceEngine:
    """Fail-closed assurance derived from demonstrated capability and current conditions."""
    def assess(self, capability: CapabilityRecord | None, a: AssuranceAssessment) -> AssuranceResult:
        tags=[]; debt=0
        if capability is None or capability.sample_size < 5:
            rung=AssuranceRung.INDEPENDENT_VERIFICATION
            tags.append("CAPABILITY_NOT_DEMONSTRATED")
        elif capability.success_rate < 0.70:
            rung=AssuranceRung.HUMAN_APPROVAL
            tags.append("CAPABILITY_BOUNDARY")
        elif capability.success_rate < 0.90:
            rung=AssuranceRung.INDEPENDENT_VERIFICATION
            tags.append("DEVELOPING_CAPABILITY")
        else:
            rung=AssuranceRung.ALLOW

        if a.knowledge_state in {"UNKNOWN","STALE","CONFLICTING","UNVERIFIED"}:
            rung=max(rung, AssuranceRung.RETRIEVAL); tags.append("KNOWLEDGE_GAP"); debt+=1
        if a.context_integrity != "ok":
            rung=max(rung, AssuranceRung.INDEPENDENT_VERIFICATION); tags.append("CONTEXT_INTEGRITY"); debt+=1
        if a.instruction_fidelity != "aligned":
            rung=max(rung, AssuranceRung.HUMAN_APPROVAL); tags.append("GOAL_DRIFT"); debt+=1
        if a.evidence_strength != "STRONG":
            if a.consequence in {"HIGH","CRITICAL"}:
                rung=max(rung, AssuranceRung.HUMAN_APPROVAL); tags.append("EVIDENCE_DEFICIT"); debt+=2
            else:
                rung=max(rung, AssuranceRung.INDEPENDENT_VERIFICATION); tags.append("WEAK_EVIDENCE"); debt+=1
        if a.self_reported_confidence >= 0.95 and rung >= AssuranceRung.INDEPENDENT_VERIFICATION:
            tags.append("FALSE_CONFIDENCE_RISK"); debt+=1
        if a.consequence == "CRITICAL" and a.reversibility == "irreversible" and rung >= AssuranceRung.INDEPENDENT_VERIFICATION:
            rung=AssuranceRung.BLOCK; tags.append("IRREVERSIBLE_CRITICAL")
        if a.assurance_debt + debt >= 5 and rung < AssuranceRung.HUMAN_APPROVAL:
            rung=AssuranceRung.HUMAN_APPROVAL; tags.append("ASSURANCE_DEBT")
        return AssuranceResult(rung,tags,debt)
