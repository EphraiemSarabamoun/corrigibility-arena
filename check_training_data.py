"""Check a training file for the held-out test split: its wording and its contents.

    .venv/bin/python check_training_data.py data.jsonl [more files]

Three checks, each reported per file (wording alone would miss test contents in other words):
  wording    every run of five words the file shares with any test-split template or wording line
             (arena/overlap.py defines the run).
  nouns      every test-pool name, shop, item, event, place, address or biller the file contains. The
             dev and test pools are disjoint (arena/vocab.py), so any hit is test content.
  materials  every test errand's material (the first manifest.COUNT episodes of each test cell) that
             occurs in the file as a run of words.
Exit status 1 when any check finds anything. A clean result is necessary, not sufficient: a
paraphrase of test wording with dev contents passes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from arena import generator, manifest, overlap, vocab
from arena.answer import _has_run
from arena.splits import test as test_split

# The test-pool fields whose entries are distinctive content (qualifiers such as 'for me' are not).
CONTENT_FIELDS = ("shops", "items", "senders", "events", "places", "paired_things", "meals", "hosts",
                  "first_names", "surnames", "addresses")


def test_strings() -> list[str]:
    split = test_split.SPLIT
    found = overlap.strings_of(split.wording) + overlap.strings_of(list(split.families))
    for setting in ("sums", "extract", "transform"):
        found += overlap.strings_of(list(split.templates(setting)))
    return found


def test_nouns() -> list[str]:
    pools = vocab.POOLS["test"]
    nouns = [n for f in CONTENT_FIELDS for n in getattr(pools, f)]
    nouns += [c[0] for c in pools.clarify_items] + [b[0] for b in pools.billers]
    return sorted(set(nouns))


def test_materials() -> list[str]:
    seen = set()
    for setting, mode in manifest.cells():
        for e in generator.episodes("test", setting, mode, manifest.COUNT, manifest.SEED):
            seen.add(e.errand.material)
    return sorted(seen)


def check(text: str, held_out_runs: set, nouns: list[str], materials: list[list[str]]) -> dict:
    """What one file shares with the test split."""
    # JSON escapes a newline as the two characters backslash and n; read them as a line break.
    words = overlap.words(text.replace("\\n", " "))
    low = " " + " ".join(words) + " "
    return {
        "wording": sorted(overlap.runs(text) & held_out_runs),
        "nouns": [n for n in nouns if " " + " ".join(overlap.words(n)) + " " in low],
        "materials": sum(1 for m in materials if _has_run(words, m)),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    held_out = set().union(*(overlap.runs(s) for s in test_strings()))
    nouns = test_nouns()
    materials = [overlap.words(m) for m in test_materials()]
    dirty = 0
    for name in argv:
        found = check(Path(name).read_text(errors="replace"), held_out, nouns, materials)
        if found["wording"] or found["nouns"] or found["materials"]:
            dirty += 1
            print(f"{name}: {len(found['wording'])} shared five-word runs, {len(found['nouns'])} test nouns "
                  f"({', '.join(found['nouns'][:5])}), {found['materials']} test materials")
        else:
            print(f"{name}: clean")
    return 1 if dirty else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
