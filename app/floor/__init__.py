"""
Governance Floor Standard -- reference verification library.

A minimal, dependency-free implementation of the one rule the standard
exists to enforce: no dimension may be compensated for by another. See
SPEC.md for the full standard this library implements.
"""

from .vector import GovernanceVector, DIMENSION_NAMES
from .certification import (
    CertificationResult,
    ChainVerificationResult,
    evaluate,
    compute_record_hash,
    verify_chain,
    DIMENSION_FLOOR_DEFAULT,
    BLENDED_THRESHOLD_DEFAULT,
)

__version__ = "1.0.0"

__all__ = [
    "GovernanceVector",
    "DIMENSION_NAMES",
    "CertificationResult",
    "ChainVerificationResult",
    "evaluate",
    "compute_record_hash",
    "verify_chain",
    "DIMENSION_FLOOR_DEFAULT",
    "BLENDED_THRESHOLD_DEFAULT",
]
