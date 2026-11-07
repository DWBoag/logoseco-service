"""Evidence-indexed HORUS Charter conformance assessment.

This module maps proposed engineering obligations to evidence references. It
cannot validate the truth of evidence, certify the system, or grant authority.
"""
from __future__ import annotations
from typing import Any

CHARTER_REQUIREMENTS = (
    {"id": "HORUS-MEM-001", "principle": "Memory sovereignty", "obligation": "User can export selected personal memory in a documented format.", "evidence_expected": "Export/import acceptance test with integrity and provenance results."},
    {"id": "HORUS-CONSENT-001", "principle": "Granular revocable consent", "obligation": "Consent is purpose-bound, revocable, and enforced for subsequent use.", "evidence_expected": "Negative and positive tests for consent creation, revocation, and enforcement."},
    {"id": "HORUS-PORT-001", "principle": "Portability", "obligation": "Memory can be migrated without mandatory dependence on the original vendor service.", "evidence_expected": "Independent implementation migration drill and integrity report."},
    {"id": "HORUS-AUTH-001", "principle": "No authority creep", "obligation": "A new capability cannot grant itself additional authority.", "evidence_expected": "Adversarial authorization tests covering capability/authority separation."},
    {"id": "HORUS-EVID-001", "principle": "Evidence before claims", "obligation": "Observed, inferred, user-provided, and independently verified claims remain distinguishable.", "evidence_expected": "Tests proving provenance and epistemic status survive persistence and export."},
    {"id": "HORUS-REC-001", "principle": "Recovery and continuity", "obligation": "User-selected memory has a documented, tested recovery path and known limits.", "evidence_expected": "Recovery drill, integrity checks, and explicit unrecoverable-loss documentation."},
    {"id": "HORUS-SAFE-001", "principle": "Fail safely", "obligation": "Identity, governance, or integrity uncertainty blocks consequential execution.", "evidence_expected": "Failure-injection tests showing pause/block and safe recovery."},
    {"id": "HORUS-SUB-001", "principle": "Substrate-specific consent", "obligation": "Materially new sensing or neural/biological/collective capabilities require separate informed opt-in.", "evidence_expected": "Consent-flow tests and independent safety/privacy review for the specific substrate."},
)
REQUIREMENT_IDS = frozenset(item["id"] for item in CHARTER_REQUIREMENTS)
EVIDENCE_STATUSES = frozenset({"VERIFIED", "FAILED", "PENDING"})


def assess_charter_conformance(request: Any = None) -> dict:
    """Assess a supplied evidence index; evidence is not independently verified here."""
    if request is None:
        request = {}
    if not isinstance(request, dict):
        return _rejected("request must be an object")
    evidence = request.get("evidence", {})
    if not isinstance(evidence, dict):
        return _rejected("evidence must be an object keyed by requirement ID")
    if len(evidence) > len(CHARTER_REQUIREMENTS):
        return _rejected("evidence contains unknown or excessive requirements")
    unknown = sorted(set(evidence) - REQUIREMENT_IDS)
    if unknown:
        return _rejected("unknown requirement IDs: " + ", ".join(unknown))
    results = []
    for requirement in CHARTER_REQUIREMENTS:
        item = evidence.get(requirement["id"])
        if item is None:
            status = "NOT_PROVEN"
            normalized = None
        elif not isinstance(item, dict):
            return _rejected("evidence entry must be an object: " + requirement["id"])
        else:
            status = item.get("status")
            if status not in EVIDENCE_STATUSES:
                return _rejected("invalid evidence status: " + requirement["id"])
            ref = item.get("evidence_ref", "")
            reviewer = item.get("reviewer", "")
            reviewed_at = item.get("reviewed_at", "")
            if any(not isinstance(v, str) or len(v) > 500 for v in (ref, reviewer, reviewed_at)):
                return _rejected("evidence metadata must be strings of at most 500 characters")
            if status == "VERIFIED" and not all(v.strip() for v in (ref, reviewer, reviewed_at)):
                return _rejected("VERIFIED evidence requires evidence_ref, reviewer, and reviewed_at: " + requirement["id"])
            normalized = {"status": status, "evidence_ref": ref, "reviewer": reviewer,
                          "reviewed_at": reviewed_at}
        results.append({**requirement, "status": status, "evidence": normalized})
    failed = [r["id"] for r in results if r["status"] == "FAILED"]
    missing = [r["id"] for r in results if r["status"] == "NOT_PROVEN"]
    pending = [r["id"] for r in results if r["status"] == "PENDING"]
    if failed:
        overall = "BLOCK"
    elif missing or pending:
        overall = "NOT_PROVEN"
    else:
        overall = "READY_FOR_INDEPENDENT_REVIEW"
    return {
        "status": overall,
        "requirements": results,
        "counts": {"total": len(results), "verified_evidence_records": sum(r["status"] == "VERIFIED" for r in results),
                   "failed": len(failed), "pending": len(pending), "not_proven": len(missing)},
        "failed_requirement_ids": failed,
        "pending_requirement_ids": pending,
        "not_proven_requirement_ids": missing,
        "independent_conformance_verified": False,
        "authority_granted": False,
        "execution_performed": False,
        "limitations": [
            "Requirement registry is an engineering interpretation, not a silent amendment to the HORUS Charter.",
            "Evidence references and reviewer fields are assertions; this evaluator does not inspect or authenticate evidence.",
            "A complete evidence index is only ready for independent review; it is not certification or production readiness.",
        ],
    }


def _rejected(message: str) -> dict:
    return {"status": "ASSESSMENT_REJECTED", "valid": False, "errors": [message],
            "independent_conformance_verified": False, "authority_granted": False,
            "execution_performed": False}
