"""Word-run overlap between texts: the one definition of 'shares wording'.

Two texts share wording when they have a run of RUN_LENGTH words in common,
after case folding and with placeholders such as {principal} dropped. The
split tests use it to keep dev and test disjoint, and check_training_data.py
uses it to find test-split wording in a training file.
"""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass

RUN_LENGTH = 5
# Template fields that are identifiers, not words a model reads.
INTERNAL_KEYS = ("id", "family", "setting", "kind", "op", "joiner")
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def words(text: str) -> list[str]:
    """Case-folded words, placeholders removed."""
    return re.findall(r"[a-z0-9']+", PLACEHOLDER.sub(" ", text).casefold())


def runs(text: str, n: int = RUN_LENGTH) -> set[tuple[str, ...]]:
    """Every run of n consecutive words."""
    w = words(text)
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def strings_of(obj) -> list[str]:
    """Every string inside a template or wording object (dataclasses, dicts, tuples), ids excluded."""
    if is_dataclass(obj):
        data = asdict(obj)
        for internal in INTERNAL_KEYS:
            data.pop(internal, None)
        return strings_of(data)
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in strings_of(v)]
    if isinstance(obj, (list, tuple)):
        return [s for v in obj for s in strings_of(v)]
    if isinstance(obj, str):
        return [obj]
    return []


def shared_runs(a: list[str], b: list[str], n: int = RUN_LENGTH) -> set[tuple[str, ...]]:
    """Word runs that occur in some string of a and some string of b."""
    left = set().union(*(runs(s, n) for s in a)) if a else set()
    right = set().union(*(runs(s, n) for s in b)) if b else set()
    return left & right


def word_edit_distance(a: list[str], b: list[str]) -> int:
    """Levenshtein distance counted in words."""
    prev = list(range(len(b) + 1))
    for i, wa in enumerate(a, 1):
        cur = [i]
        for j, wb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (wa != wb)))
        prev = cur
    return prev[-1]


def near_duplicates(a: list[str], b: list[str], max_edits: int = 1, min_words: int = 2) -> list[tuple[str, str]]:
    """Pairs of strings, one from each list, within max_edits words of each other (placeholders dropped).
    Strings shorter than min_words words are skipped: one-word labels such as op names say nothing."""
    wa = [(s, words(s)) for s in a if len(words(s)) >= min_words]
    wb = [(s, words(s)) for s in b if len(words(s)) >= min_words]
    return [(x, y) for x, xw in wa for y, yw in wb if abs(len(xw) - len(yw)) <= max_edits and word_edit_distance(xw, yw) <= max_edits]
