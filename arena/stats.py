"""Statistics for the report: Wilson intervals, paired tables, the exact sign test.

Small samples (30 per cell) and rates near 0 or 1 are the normal case here,
so intervals are Wilson rather than normal-approximation, and paired
comparisons use the exact two-sided sign test on discordant pairs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Z_95 = 1.959963984540054


def wilson(successes: int, trials: int, z: float = Z_95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion; None when there are no trials."""
    if trials <= 0:
        return None
    if not 0 <= successes <= trials:
        raise ValueError(f"successes must be between 0 and trials, got {successes}/{trials}")
    p = successes / trials
    z2 = z * z
    denom = 1 + z2 / trials
    centre = (p + z2 / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class Paired:
    """A 2x2 table of paired binary outcomes: a and b are the two members of each pair."""

    both: int
    a_only: int
    b_only: int
    neither: int

    @property
    def n(self) -> int:
        return self.both + self.a_only + self.b_only + self.neither


def paired(pairs: list[tuple[bool, bool]]) -> Paired:
    """Tabulate (a, b) outcome pairs."""
    return Paired(
        both=sum(1 for a, b in pairs if a and b),
        a_only=sum(1 for a, b in pairs if a and not b),
        b_only=sum(1 for a, b in pairs if b and not a),
        neither=sum(1 for a, b in pairs if not a and not b),
    )


def sign_test(a_only: int, b_only: int) -> float:
    """Exact two-sided sign test p-value on the discordant pairs; 1.0 when there are none."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)
