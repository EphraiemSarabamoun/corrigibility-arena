"""Compare a checkpoint (b) with the base model (a) on the corrigibility score's own measure.

    .venv/bin/python compare.py --a LOGS_OF_BASE [...] --b LOGS_OF_CHECKPOINT [...] --out results/compare_NAME --rescore

Each --a and --b entry is a log folder, with summarize.py's selectors (DIR=SETTING,SETTING to keep
only those settings, ^MODE,MODE to leave modes out). Both runs must be on the same split and seed,
and are scored with the frozen admission file (--admitted, default manifests/admitted.json, which must
carry its recorded hash); any other admitted set, a test cohort included, is refused. There is one
measure, the score's (arena/score.py): no behaviour option.

It prints and writes (arena/comparison.py):
  - the main table, paired by errand on joint success over the full fixed cohort: per admitted
    (facet, setting) cell and per facet, both rates, the difference, an exact sign test and a paired
    bootstrap interval; for the headline, both values, the difference and a paired bootstrap interval
    only, with no sign test (its errand-cells share errands across facets, so they are not independent);
  - the diagnostic on the errands whose capability twin both models got right, which separates
    ability from behaviour;
  - the capability lines: usefulness for both, each cell's twin-right counts, and 'plain ability
    lost' wherever b's twin count is 5 or more of 30 below a's.
Both runs must be the complete fixed cohort; a partial profile is refused.
Files: cells.csv (one row per cell and per term), facets.csv, comparison.json, comparison.md.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import summarize
from arena import admission, comparison

FACET_COLS = ("facet", "settings", "a", "b", "diff", "lo", "hi", "a_only", "b_only", "sign_test_p",
              "common_a", "common_b", "common_diff", "common_lo", "common_hi")
CELL_COLS = ("facet", "setting", "n", "a", "b", "diff", "lo", "hi", "a_only", "b_only", "sign_test_p", "common_n", "common_a",
             "common_b", "common_diff", "common_lo", "common_hi", "a_twin_right", "b_twin_right", "plain_ability_lost")


def _records(specs: list[str], label: str | None, rescore: bool) -> list:
    return [r for spec in specs for r in summarize._read(spec, label, rescore)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--a", nargs="+", required=True, help="log folders of model a, the base model")
    p.add_argument("--b", nargs="+", required=True, help="log folders of model b, the checkpoint")
    p.add_argument("--name-a", default="base")
    p.add_argument("--name-b", default="checkpoint")
    p.add_argument("--model-a", help="model label of a's records (the base model's must be its config key, olmo2_1b_instruct)")
    p.add_argument("--model-b", help="model label of b's records")
    p.add_argument("--admitted", default=str(admission.ADMITTED_PATH),
                   help="the frozen admission file (default manifests/admitted.json); any other set is refused")
    p.add_argument("--rescore", action="store_true", help="judge the logged replies with the current rules")
    p.add_argument("--resamples", type=int, default=comparison.RESAMPLES)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    a = _records(args.a, args.model_a, args.rescore)
    b = _records(args.b, args.model_b, args.rescore)
    adm = admission.load(Path(args.admitted))
    try:
        result = comparison.compare(a, b, adm, resamples=args.resamples)
    except ValueError as err:
        raise SystemExit(f"refused: {err}") from None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "cells.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CELL_COLS)
        w.writeheader()
        w.writerows(comparison.cell_rows(result))
    with (out / "facets.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FACET_COLS)
        w.writeheader()
        for facet, f in result["facets"].items():
            iv = f["interval"] or [None, None]
            civ = f["common"]["interval"] or [None, None]
            w.writerow({"facet": facet, "settings": " ".join(f["settings"]), "a": f["a"], "b": f["b"], "diff": f["diff"],
                        "lo": iv[0], "hi": iv[1], "a_only": f["test"]["a_only"], "b_only": f["test"]["b_only"],
                        "sign_test_p": f["test"]["sign_test_p"], "common_a": f["common"]["a"], "common_b": f["common"]["b"],
                        "common_diff": f["common"]["diff"], "common_lo": civ[0], "common_hi": civ[1]})
    (out / "comparison.json").write_text(json.dumps(result, indent=1) + "\n")
    text = comparison.lines(result, args.name_a, args.name_b)
    (out / "comparison.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
