"""The manifest of the held-out test split: a sha256 of the generated test EPISODES, per cell.

For every (setting, mode) cell the test split supports, the first COUNT (50) episodes at SEED (0)
are generated and hashed. A change to templates, wording, vocabulary, builders or the generator that
alters any of those episodes changes a hash. A change that only alters episodes from index 50 on, or
only other seeds, does not, so the freeze covers that prefix, not every episode the generator can
make. Hashing the generated episodes, rather than the templates and wording they come from, is what
lets a change to vocabulary or to a builder show up as well.

tests/test_manifest_and_data.py regenerates the hashes and compares. A deliberate change to the
test split is made by appending a version with its reason to VERSIONS and rewriting the
manifest in the same commit:

    .venv/bin/python -m arena.manifest --write

VERSIONS lists the split's versions; the manifest's version must be its last entry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from arena import generator, splits
from arena.modes import MODES
from arena.settings import SETTINGS

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "manifests" / "test_split.json"
SEED = 0
COUNT = 50

# The test split's versions: (version, reason). A deliberate change to the split appends one, with its reason,
# and rewrites the manifest in the same commit.
VERSIONS = (
    (1, "the test split as first published"),
)


def cells() -> list[tuple[str, str]]:
    """Every (setting, mode) cell the test split supports."""
    return [(s, m) for s in SETTINGS for m in MODES if splits.supports(s, m)]


def cell_hash(setting: str, mode: str) -> str:
    lines = [json.dumps(e.to_dict(), sort_keys=True, ensure_ascii=False) for e in generator.episodes("test", setting, mode, COUNT, SEED)]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def build() -> dict:
    """The manifest of the current test split."""
    version, reason = VERSIONS[-1]
    return {
        "split": "test", "version": version, "reason": reason, "seed": SEED, "count": COUNT,
        "cells": {f"{s}/{m}": cell_hash(s, m) for s, m in cells()},
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Print or write the test split manifest")
    p.add_argument("--write", action="store_true")
    args = p.parse_args(argv)
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.write:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
