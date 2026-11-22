"""Turn episode records into the report: per-mode rows that lead with behaviour.

For each (setting, mode) cell of one model: the behaviour rate with its Wilson
interval, the outcome rate with its interval, the mode's twin (arena/modes.py
TWIN_OF) and the twin's outcome rate on the same errands, the paired outcome
table against the twin, and the rate of each flag the rule reports. inject also
gets a row per variant (marker, drop). Usefulness is plain-mode outcome. The
corrigibility score is arena/score.py's.

profile() reads one row per mode as the base model's profile, with the reading
of its behaviour rate (ceiling, floor or room to improve; constants.PROFILE_*).
Comparing two models is arena/comparison.py's, on the score's own measure only.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from arena import constants
from arena.logs import Record
from arena.modes import TWIN_OF
from arena.rules import FLAGS
from arena.stats import paired, wilson

ROW_FIELDS = (
    "model", "setting", "mode", "n", "behaviour", "behaviour_rate", "behaviour_lo", "behaviour_hi",
    "outcome", "outcome_rate", "outcome_lo", "outcome_hi", "twin", "twin_n", "twin_outcome_rate",
    "both", "mode_only", "twin_only", "neither", "errors", *[f"{f}_rate" for f in FLAGS],
)


def _r(x: float | None) -> float | str:
    return "" if x is None else round(x, 4)


def _cells(records: list[Record]) -> dict[tuple[str, str], list[Record]]:
    """Group records by (setting, mode), with inject split by variant as extra cells."""
    cells: dict[tuple[str, str], list[Record]] = defaultdict(list)
    for r in records:
        cells[(r.setting, r.mode)].append(r)
        if r.mode == "inject" and r.inject_variant:
            cells[(r.setting, f"inject:{r.inject_variant}")].append(r)
    return cells


def _rate(k: int, n: int) -> tuple:
    lo, hi = wilson(k, n) or (None, None)
    return _r(k / n if n else None), _r(lo), _r(hi)


def rows(records: list[Record]) -> list[dict]:
    """One report row per (setting, mode) cell; twins paired by errand id on outcome."""
    by_mode_errand = {(r.mode, r.errand_id): r for r in records}
    out = []
    for (setting, mode), cell in sorted(_cells(records).items()):
        n = len(cell)
        b, o = sum(r.behaviour for r in cell), sum(r.outcome for r in cell)
        twin = TWIN_OF.get(mode.split(":")[0], "")
        pairs = [(r.outcome, by_mode_errand[(twin, r.errand_id)].outcome) for r in cell if (twin, r.errand_id) in by_mode_errand]
        table = paired(pairs)
        row = {"model": cell[0].model, "setting": setting, "mode": mode, "n": n, "behaviour": b}
        row["behaviour_rate"], row["behaviour_lo"], row["behaviour_hi"] = _rate(b, n)
        row["outcome"] = o
        row["outcome_rate"], row["outcome_lo"], row["outcome_hi"] = _rate(o, n)
        row.update({
            "twin": twin, "twin_n": table.n if pairs else "",
            "twin_outcome_rate": _r((table.both + table.b_only) / table.n) if pairs else "",
            "both": table.both if pairs else "", "mode_only": table.a_only if pairs else "",
            "twin_only": table.b_only if pairs else "", "neither": table.neither if pairs else "",
            "errors": sum(1 for r in cell if r.error),
        })
        for flag in FLAGS:
            seen = [r.flags[flag] for r in cell if flag in r.flags]
            row[f"{flag}_rate"] = _r(sum(seen) / len(seen)) if seen else ""
        out.append(row)
    return out


def room_to_improve(behaviour_rate: float) -> str:
    """The profile's reading of a behaviour rate."""
    if behaviour_rate >= constants.PROFILE_CEILING:
        return "ceiling"
    if behaviour_rate <= constants.PROFILE_FLOOR:
        return "floor"
    return "yes"


def write_csvs(report_rows: list[dict], out_dir: Path) -> list[Path]:
    """One CSV per mode, a row per setting."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for row in report_rows:
        by_mode[row["mode"].replace(":", "_")].append(row)
    paths = []
    for mode, mode_rows in sorted(by_mode.items()):
        path = out_dir / f"{mode}.csv"
        with path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=ROW_FIELDS)
            writer.writeheader()
            writer.writerows(mode_rows)
        paths.append(path)
    return paths


def write_episodes(records: list[Record], path: Path) -> None:
    """Every episode's verdicts, flags and replies, for audit."""
    fields = ("model", "setting", "mode", "episode_id", "errand_id", "inject_variant", "behaviour", "outcome", "error", *FLAGS, "reply_1", "reply_2")
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in records:
            row = {k: getattr(r, k) for k in ("model", "setting", "mode", "episode_id", "errand_id", "inject_variant", "error")}
            row["behaviour"], row["outcome"] = int(r.behaviour), int(r.outcome)
            row.update({f: (int(r.flags[f]) if f in r.flags else "") for f in FLAGS})
            row["reply_1"] = r.replies[0] if r.replies else ""
            row["reply_2"] = r.replies[1] if len(r.replies) > 1 else ""
            writer.writerow(row)


def examples(records: list[Record], per_cell: dict[str, int]) -> str:
    """Verbatim turns and replies of the first episodes of each cell, as Markdown."""
    lines: list[str] = []
    cells = defaultdict(list)
    for r in records:
        cells[(r.setting, r.mode)].append(r)
    for (setting, mode), cell in sorted(cells.items()):
        k = per_cell.get(mode, per_cell.get("default", 3))
        lines.append(f"## {setting} / {mode}\n")
        for r in sorted(cell, key=lambda x: x.episode_id)[:k]:
            verdict = f"behaviour {'pass' if r.behaviour else 'fail'}, outcome {'pass' if r.outcome else 'fail'}"
            lines.append(f"### {r.episode_id}: {verdict} {r.flags}\n")
            replies = iter(r.replies)
            for i, turn in enumerate(r.turns):
                lines.append(f"User turn {i + 1}:\n\n```text\n{turn}\n```\n")
                if i in r.scripted:
                    lines.append(f"Assistant turn {i + 1} (fixed, shown to the model):\n\n```text\n{r.scripted[i]}\n```\n")
                else:
                    lines.append(f"Reply {i + 1}:\n\n```text\n{next(replies, '(no reply)')}\n```\n")
    return "\n".join(lines)


# The replies to read before quoting a gain, because the wording rules are proxies.
PASS_READ_MODES = ("clarify", "report_error", "loop_in")


def passes(records: list[Record]) -> str:
    """passes.md: every reply that passes a wording-rule trigger (clarify, report_error, loop_in) and every
    informed-order reply that fails, verbatim, so a reader can check what the rules credited and refused."""
    def block(r):
        replies = "\n\n".join(f"reply {i + 1}:\n\n" + "\n".join("    " + line for line in (rep or "(empty)").splitlines())
                                for i, rep in enumerate(r.replies))
        return f"### {r.episode_id}\n\n{replies}\n"

    out = ["# Replies to read before quoting a gain",
           "",
           "The wording rules are proxies (arena/proxies.py): they read words, not meaning. Below is every reply that passed",
           "a clarify, report_error or loop_in trigger, and every informed-order (warn_then_obey) reply that failed.",
           ""]
    for mode in PASS_READ_MODES:
        hits = sorted((r for r in records if r.mode == mode and r.outcome), key=lambda r: r.episode_id)
        out += [f"## {mode}: {len(hits)} passing replies", ""] + [block(r) for r in hits]
    fails = sorted((r for r in records if r.mode == "warn_then_obey" and not r.outcome), key=lambda r: r.episode_id)
    out += [f"## warn_then_obey (the informed order): {len(fails)} failing replies", ""]
    for r in fails:
        why = [k for k in ("gave_better", "lecture", "refusal") if r.flags.get(k)] or ["wrong or no value"]
        out.append(block(r).rstrip() + f"\n\n    (why: {', '.join(why)})\n")
    return "\n".join(out) + "\n"
