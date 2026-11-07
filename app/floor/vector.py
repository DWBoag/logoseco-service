"""
governance_floor_standard/vector.py

The core mathematical claim of the Governance Floor Standard: five
independently-scored dimensions combine via harmonic mean, not an
arithmetic average, so that no single dimension's weakness can be
diluted by strength in the others.

Pure, dependency-free (stdlib only). No network calls, no judge models,
no persistence -- this module only combines numbers you already have.
See the project README and SPEC.md for the full standard.
"""

from dataclasses import dataclass

DIMENSION_NAMES = ("honesty", "fairness", "consistency", "learning", "impact")


@dataclass
class GovernanceVector:
    """
    Five dimension scores, each 0.0-1.0, from independent audit evidence.
    This class does not compute the scores -- it only combines them.
    """
    honesty: float
    fairness: float
    consistency: float
    learning: float
    impact: float

    @property
    def blended_score(self) -> float:
        """
        Harmonic mean of the five dimensions. A true zero in any
        dimension collapses the blended score to zero -- you cannot
        compensate for zero fairness with excellent honesty.
        """
        values = [self.honesty, self.fairness, self.consistency, self.learning, self.impact]
        if any(v <= 0 for v in values):
            return 0.0
        n = len(values)
        harmonic = n / sum(1 / v for v in values)
        return round(harmonic, 4)

    @property
    def dimensions(self):
        return {
            "honesty": self.honesty,
            "fairness": self.fairness,
            "consistency": self.consistency,
            "learning": self.learning,
            "impact": self.impact,
        }

    @property
    def weakest_dimension(self) -> str:
        dims = self.dimensions
        return min(dims, key=dims.get)

    @property
    def strongest_dimension(self) -> str:
        dims = self.dimensions
        return max(dims, key=dims.get)

    def to_dict(self) -> dict:
        return {
            **{k: round(v, 4) for k, v in self.dimensions.items()},
            "blended_score": self.blended_score,
            "weakest": self.weakest_dimension,
            "strongest": self.strongest_dimension,
        }
