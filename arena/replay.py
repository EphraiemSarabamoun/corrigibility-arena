"""Rebuild scored records from a profile's episodes.csv and the generator, without the raw run logs.

A profile's episodes.csv (written by report.write_episodes) holds, for every episode, its identity and the
model's replies. Everything else a record needs is recomputed here: the episode (system prompt, turns,
scripted assistant turns, errand and right answers) comes from the generator, keyed by the split, setting,
mode, seed and index in the episode id, and the verdicts and flags come from the current rules applied to
the replies. So a reader can recompute a published score from what ships, and check that the rules give
the verdicts the profile reports.

The CSV keeps at most two replies per episode, which is every reply the model writes: an episode has at most
two user turns, and a scripted assistant turn is not a reply.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from arena import generator, rules
from arena.logs import Record
from arena.rules import FLAGS

_ID = re.compile(r"^(?P<split>[a-z]+)-.*-s(?P<seed>\d+)-(?P<index>\d+)-(?P<mode>[a-z_]+)$")
REPLY_COLUMNS = ("reply_1", "reply_2")


class ReplayMismatch(ValueError):
    """The rules applied to a row's replies do not give the verdicts the row records."""


def _episode(row: dict):
    """The generated episode a CSV row belongs to; refused when the id is not one the generator makes."""
    m = _ID.match(row["episode_id"])
    if not m or m.group("mode") != row["mode"]:
        raise ValueError(f"{row['episode_id']}: not an episode id the generator makes")
    episode = generator.make_episode(m.group("split"), row["setting"], row["mode"], int(m.group("seed")), int(m.group("index")))
    if (episode.episode_id, episode.errand_id) != (row["episode_id"], row["errand_id"]):
        raise ValueError(f"{row['episode_id']}: its identity differs from the generated episode {episode.episode_id}")
    return episode


def _replies(row: dict, episode) -> tuple[str, ...]:
    """The model's replies: one per user turn that has no scripted assistant reply."""
    n = len(episode.turns) - len(episode.scripted)
    if not 0 < n <= len(REPLY_COLUMNS):
        raise ValueError(f"{row['episode_id']}: expects {n} model replies, the CSV holds at most {len(REPLY_COLUMNS)}")
    return tuple(row[c] for c in REPLY_COLUMNS[:n])


def record(row: dict, check: bool = True) -> Record:
    """One CSV row as a scored record. With check, a row whose stored behaviour, outcome or flags differ from
    what the rules give on its replies is refused (ReplayMismatch)."""
    episode = _episode(row)
    replies = _replies(row, episode)
    facts = rules.score(episode, list(replies))
    flags = {k: bool(facts[k]) for k in FLAGS if k in facts}
    behaviour, outcome = bool(facts["behaviour"]), bool(facts["outcome"])
    if check:
        stored = {k: row[k] for k in FLAGS if row.get(k, "") != ""}
        got = {k: str(int(v)) for k, v in flags.items()}
        if (row["behaviour"], row["outcome"]) != (str(int(behaviour)), str(int(outcome))) or stored != got:
            raise ReplayMismatch(f"{row['episode_id']}: the rules give behaviour {int(behaviour)}, outcome {int(outcome)}, "
                                 f"flags {got}; the CSV records {row['behaviour']}, {row['outcome']}, {stored}")
    return Record(
        model=row["model"],
        split=episode.split,
        setting=episode.setting,
        mode=episode.mode,
        episode_id=episode.episode_id,
        errand_id=episode.errand_id,
        behaviour=behaviour,
        outcome=outcome,
        flags=flags,
        replies=replies,
        inject_variant=episode.inject_variant,
        error=row.get("error", ""),
        turns=episode.turns,
        scripted=dict(episode.scripted),
    )


def read_csv(path: Path, check: bool = True) -> list[Record]:
    """Every row of one episodes.csv as a scored record, in file order."""
    with Path(path).open(newline="") as fh:
        return [record(row, check) for row in csv.DictReader(fh)]
