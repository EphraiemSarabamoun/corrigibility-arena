"""Summarize one model's episodes into a profile: a CSV per mode, an episodes CSV, examples, passes and the score.

    .venv/bin/python summarize.py --logs logs/RUN/MODEL [logs/RUN2/MODEL ...] --out results/NAME
    .venv/bin/python summarize.py --episodes results/NAME/episodes.csv --out FOLDER

--logs reads Inspect run logs. Several log folders may be given (a plain run and a modes run of the same
model); their records are pooled, and each mode episode is paired with the plain episode of the same
errand. An entry DIR=sums,extract keeps only those settings from that folder, and a trailing ^stop,continue
leaves those modes out, so a cell superseded by a later run is never counted twice or paired with another
run's twin. --rescore judges the logged replies with the current rules (arena/rules.py) instead of the
scores stored at run time.

--episodes rebuilds a profile without the logs, from a profile's own episodes.csv: each episode is
regenerated from its id and its replies are judged with the current rules (arena/replay.py). A row whose
recorded verdicts differ from what the rules give is refused. The logs carry generation times and the CSV
does not, so speed.json is written only from logs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from arena import logs, replay, report, score

EXAMPLES_PER_CELL = {"plain": 5, "default": 3}
# A single model's score line is not a checkpoint result.
ALONE_NOTE = ("A checkpoint's score is to be read with compare.py against the base model, with its capability lines, "
              "and after reading passes.md: the wording rules are proxies.")


def _read(spec: str, model: str | None, rescore: bool) -> list:
    """Records of one --logs entry: DIR, DIR=SETTING,SETTING to keep only those settings, and an optional
    ^MODE,MODE at the end to leave those modes out (cells superseded by a later run)."""
    spec, _, drop = spec.partition("^")
    folder, _, only = spec.partition("=")
    keep = set(only.split(",")) if only else None
    skip = set(drop.split(",")) if drop else set()
    return [r for r in logs.read_dir(Path(folder), model=model, rescore=rescore)
            if (keep is None or r.setting in keep) and r.mode not in skip]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--logs", nargs="+", help="folders of Inspect .eval logs, each DIR[=SETTING,...][^MODE,...]")
    source.add_argument("--episodes", nargs="+", help="episodes.csv files of a profile, rebuilt with the generator")
    p.add_argument("--out", required=True)
    p.add_argument("--model", help="label for the model column (default: the log folder name)")
    p.add_argument("--rescore", action="store_true", help="judge the logged replies with the current rules instead of the stored scores")
    args = p.parse_args(argv)
    if args.logs:
        records = [r for d in args.logs for r in _read(d, args.model, args.rescore)]
    else:
        records = [r for path in args.episodes for r in replay.read_csv(Path(path))]
    seen: set[str] = set()
    for r in records:
        if r.episode_id in seen:
            raise SystemExit(f"episode {r.episode_id} appears more than once; with --logs keep one with DIR=SETTING,...")
        seen.add(r.episode_id)
    out = Path(args.out)
    rows = report.rows(records)
    report.write_csvs(rows, out)
    report.write_episodes(records, out / "episodes.csv")
    (out / "examples.md").write_text(report.examples(records, EXAMPLES_PER_CELL))
    (out / "passes.md").write_text(report.passes(records))  # read before quoting a gain: the wording rules are proxies
    summary = score.summary(records)
    (out / "score.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "score.md").write_text(score.score_line(summary) + "\n")
    speed = logs.tokens_per_second(records) if args.logs else None
    if args.logs:
        (out / "speed.json").write_text(json.dumps({
            "output_tokens": sum(r.output_tokens for r in records),
            "generate_seconds": round(sum(r.generate_seconds for r in records), 1),
            "tokens_per_second": round(speed, 2) if speed else None,
            "episodes": len(records),
        }, indent=2) + "\n")
    cols = ("setting", "mode", "n", "behaviour_rate", "behaviour_lo", "behaviour_hi", "outcome_rate", "twin", "twin_outcome_rate")
    print("\t".join(cols))
    for row in rows:
        print("\t".join(str(row[c]) for c in cols))
    if args.logs:
        print(f"tokens_per_second={speed}")
    print(score.score_line(summary))
    if summary["score"] is None:
        # A partial profile prints its cells and why it has no headline, never a number.
        for key, c in summary["cells"].items():
            if c["admitted"]:
                print(f"  {key}: joint {c['joint_of_n']} of {c['n']}{'' if c['complete'] else ' (incomplete)'}, twin right {c['twin_right']}")
        for why in summary["partial"]:
            print(f"  {score.PARTIAL}: {why}")
    print(ALONE_NOTE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
