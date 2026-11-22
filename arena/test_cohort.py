"""Scoring a test cohort: for tests and research only, never the benchmark's headline.

The public functions in arena/score.py and arena/comparison.py score only the frozen admission file
(manifests/admitted.json). Tests of scripted policies need other cohorts: a 100-errand cohort with every
cell admitted, a one-errand cohort, a set with some cells left out. Such an admitted set says
"test_contract": true, the boolean and nothing else, and is scored with the functions here. They check the
set exactly as the public path does (whole, and still matching the generator's items) and then run the same
private computations, so a test measures the code the benchmark runs.

Their results are marked so that they cannot pass for the benchmark's number: a summary or comparison dict
carries "test_cohort": true, and score.score_line and comparison.lines start every line they print from one
with MARKER. A bare headline or interval is a number and carries no mark, so it is not to be quoted as a score.

Data flow: a test builds records and a test admitted set -> contract() -> score._headline,
score._bootstrap_interval, score._summary or comparison._compare -> the result, marked where it is a dict.
"""

from __future__ import annotations

from arena import comparison, score
from arena.logs import Record

MARKER = score.TEST_COHORT_MARKER


def contract(admitted: dict) -> dict:
    """A test cohort's admitted set, checked: it must say "test_contract": true, the boolean (a string such
    as "false", or any other value, is refused), and be whole and match the generator's items."""
    flag = admitted.get("test_contract") if isinstance(admitted, dict) else None
    if flag is not True:
        raise ValueError(f'a test cohort must carry "test_contract": true, the boolean; this set has {flag!r}')
    return score._validated(admitted)


def headline(records: list[Record], admitted: dict) -> float:
    """The headline computation on a test cohort: 100 times the mean facet over its complete fixed cohort."""
    return score._headline(records, contract(admitted))


def bootstrap_interval(records: list[Record], admitted: dict, resamples: int = score.BOOTSTRAP_RESAMPLES,
                       seed: int = score.BOOTSTRAP_SEED) -> list[float]:
    """The headline's 95 percent bootstrap interval on a test cohort."""
    return score._bootstrap_interval(records, contract(admitted), resamples, seed)


def summary(records: list[Record], admitted: dict) -> dict:
    """The score summary of a test cohort, carrying "test_cohort": true, so its score line is marked."""
    return {"test_cohort": True, **score._summary(records, contract(admitted))}


def compare(a: list[Record], b: list[Record], admitted_a: dict, admitted_b: dict | None = None,
            resamples: int = comparison.RESAMPLES, seed: int = comparison.SEED) -> dict:
    """The paired comparison of two runs on one test cohort (b defaults to a's set, and both must be test
    cohorts), carrying "test_cohort": true, so every line comparison.lines prints for it is marked."""
    admitted_a = contract(admitted_a)
    admitted_b = admitted_a if admitted_b is None else contract(admitted_b)
    return {"test_cohort": True, **comparison._compare(a, b, admitted_a, admitted_b, resamples, seed)}
