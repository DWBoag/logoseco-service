"""
governance_floor_standard/certification.py

The two-gate certification rule, and the hash-chain mechanics that make
a sequence of certification records tamper-evident.

Pure, dependency-free (stdlib only: hashlib, json, dataclasses, typing).
This module never calls out to any implementer's servers, judge models,
or databases -- everything here operates only on numbers and records you
already have. That is the point: a third party (an insurer, a court, a
competing auditor, a customer's own compliance team) can run this same
code themselves and reach the same conclusion, without trusting any one
implementer's internals.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .vector import GovernanceVector

DIMENSION_FLOOR_DEFAULT = 0.5
BLENDED_THRESHOLD_DEFAULT = 0.7


@dataclass
class CertificationResult:
    certified: bool
    dimension_floor: float
    blended_threshold: float
    floor_failures: Dict[str, float]
    blended_score: float
    dimensions: Dict[str, float]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certified": self.certified,
            "dimension_floor": self.dimension_floor,
            "blended_threshold": self.blended_threshold,
            "floor_failures": self.floor_failures,
            "blended_score": self.blended_score,
            "dimensions": self.dimensions,
            "reason": self.reason,
        }


def evaluate(
    vector: GovernanceVector,
    dimension_floor: float = DIMENSION_FLOOR_DEFAULT,
    blended_threshold: float = BLENDED_THRESHOLD_DEFAULT,
) -> CertificationResult:
    """
    Evaluate a GovernanceVector against the two independent gates:

    1. DIMENSION FLOOR -- every one of the five dimensions must
       individually clear dimension_floor. A single dimension below the
       floor voids certification regardless of the other four or of the
       blended score.
    2. BLENDED THRESHOLD -- the harmonic-mean blended score must
       separately clear blended_threshold, even after gate 1 passes.

    Never accepts pre-computed dimension scores as an override -- the
    caller must supply a real GovernanceVector built from their own
    actual audit evidence, never numbers asserted after the fact.
    """
    dims = vector.dimensions
    floor_failures = {name: score for name, score in dims.items() if score < dimension_floor}

    if floor_failures:
        worst = min(floor_failures, key=floor_failures.get)
        return CertificationResult(
            certified=False,
            dimension_floor=dimension_floor,
            blended_threshold=blended_threshold,
            floor_failures=floor_failures,
            blended_score=vector.blended_score,
            dimensions=dims,
            reason=(
                f"Dimension floor failure: {worst}={floor_failures[worst]:.4f} is below the "
                f"required floor of {dimension_floor}. Certification is void regardless of "
                f"the other four dimensions or the blended score."
            ),
        )

    if vector.blended_score < blended_threshold:
        return CertificationResult(
            certified=False,
            dimension_floor=dimension_floor,
            blended_threshold=blended_threshold,
            floor_failures={},
            blended_score=vector.blended_score,
            dimensions=dims,
            reason=(
                f"All five dimensions clear the {dimension_floor} floor, but the blended "
                f"score {vector.blended_score:.4f} is below the {blended_threshold} "
                f"certification threshold."
            ),
        )

    return CertificationResult(
        certified=True,
        dimension_floor=dimension_floor,
        blended_threshold=blended_threshold,
        floor_failures={},
        blended_score=vector.blended_score,
        dimensions=dims,
        reason="All five dimensions clear the floor and the blended score clears the certification threshold.",
    )


def compute_record_hash(record: Dict[str, Any], prev_hash: Optional[str]) -> str:
    """
    SHA-256 over the record's own content plus the previous record's
    hash, so altering any past record breaks every hash computed after
    it. Used when issuing a new certification record.
    """
    payload = json.dumps(record, sort_keys=True) + "|" + (prev_hash or "GENESIS")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ChainVerificationResult:
    valid: bool
    records_checked: int
    broken_at_index: Optional[int] = None
    reason: str = ""
    failures: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "records_checked": self.records_checked,
            "broken_at_index": self.broken_at_index,
            "reason": self.reason,
            "failures": self.failures,
        }


_RECORD_FIELDS = (
    "org_id", "certified", "honesty", "fairness", "consistency", "learning",
    "impact", "blended_score", "dimension_floor", "blended_threshold",
    "floor_failures", "reason",
)


def verify_chain(records: List[Dict[str, Any]]) -> ChainVerificationResult:
    """
    Independently verify a sequence of certification records, oldest
    first, by recomputing each record_hash from its own content plus the
    previous record's hash and confirming it matches what's stored.

    This is the function a third party actually runs: given the raw
    records an implementer returns (e.g. from a certification-history
    API), confirm the chain hasn't been tampered with -- without
    trusting the implementer's own verification of itself.

    Records must contain, at minimum: the fields in _RECORD_FIELDS,
    plus record_hash and prev_hash. Extra fields are ignored; this
    function only recomputes the hash over the canonical field set so
    an implementer's own bookkeeping fields (ids, timestamps, etc.)
    don't need to match exactly, only the substantive content.
    """
    if not records:
        return ChainVerificationResult(valid=True, records_checked=0, reason="No records to verify.")

    failures = []
    prev_hash = None
    for i, rec in enumerate(records):
        content = {k: rec.get(k) for k in _RECORD_FIELDS}
        expected_hash = compute_record_hash(content, prev_hash)
        actual_prev = rec.get("prev_hash")
        actual_hash = rec.get("record_hash")

        if actual_prev != prev_hash:
            failures.append({
                "index": i,
                "issue": "prev_hash mismatch",
                "expected_prev_hash": prev_hash,
                "actual_prev_hash": actual_prev,
            })
        if actual_hash != expected_hash:
            failures.append({
                "index": i,
                "issue": "record_hash does not match recomputed hash -- content or chain has been altered",
                "expected_record_hash": expected_hash,
                "actual_record_hash": actual_hash,
            })

        if failures and failures[-1]["index"] == i:
            return ChainVerificationResult(
                valid=False,
                records_checked=i + 1,
                broken_at_index=i,
                reason=f"Chain verification failed at record index {i} (org_id={rec.get('org_id')!r}).",
                failures=failures,
            )

        prev_hash = actual_hash

    return ChainVerificationResult(
        valid=True,
        records_checked=len(records),
        reason=f"All {len(records)} records verified: each record_hash correctly chains from the previous.",
    )
