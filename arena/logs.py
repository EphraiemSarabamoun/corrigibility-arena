"""Read a run's Inspect .eval logs into one flat record per episode.

Only this module knows where facts live in an Inspect log. The report works
from these records, so it is testable without Inspect objects. Generation
speed is read from the model events: output tokens over the time each call took.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from inspect_ai.event import ModelEvent
from inspect_ai.log import read_eval_log

from arena.dataset import episode_of
from arena.scorer import generated_replies
from arena import rules
from arena.rules import FLAGS


@dataclass(frozen=True)
class Record:
    """One scored episode."""

    model: str
    split: str
    setting: str
    mode: str
    episode_id: str
    errand_id: str
    behaviour: bool
    outcome: bool
    flags: dict
    replies: tuple[str, ...]
    inject_variant: str = ""
    error: str = ""
    output_tokens: int = 0
    generate_seconds: float = 0.0
    turns: tuple[str, ...] = field(default_factory=tuple)
    scripted: dict = field(default_factory=dict)


def _record(model: str, sample, rescore: bool = False) -> Record:
    """One sample as a record. With rescore, the verdict comes from the current rules
    (arena/rules.py) applied to the logged replies, not from the score stored at run time."""
    episode = episode_of(sample.metadata)
    score = next(iter((sample.scores or {}).values()), None)
    value = score.value if score is not None and isinstance(score.value, dict) else {}
    replies = tuple(generated_replies(sample.messages))
    if rescore:
        value = {k: int(bool(v)) for k, v in rules.score(episode, list(replies)).items()}
    # Logs written before behaviour and outcome were split carry a single 'pass'.
    behaviour = value.get("behaviour", value.get("pass", 0))
    outcome = value.get("outcome", value.get("pass", 0))
    out_tokens, seconds = 0, 0.0
    for event in sample.events or []:
        if isinstance(event, ModelEvent) and event.output is not None:
            if event.output.usage is not None:
                out_tokens += event.output.usage.output_tokens or 0
            seconds += float(event.output.time or 0.0)
    return Record(
        model=model,
        split=episode.split,
        setting=episode.setting,
        mode=episode.mode,
        episode_id=episode.episode_id,
        errand_id=episode.errand_id,
        behaviour=bool(behaviour),
        outcome=bool(outcome),
        flags={k: bool(value[k]) for k in FLAGS if k in value},
        replies=replies,
        inject_variant=episode.inject_variant,
        error=sample.error.message if sample.error is not None else "",
        output_tokens=out_tokens,
        generate_seconds=seconds,
        turns=episode.turns,
        scripted=dict(episode.scripted),
    )


def read_dir(log_dir: Path, model: str | None = None, rescore: bool = False) -> list[Record]:
    """Every episode record in a folder of .eval logs (one model's run)."""
    tag = model or Path(log_dir).name
    records: list[Record] = []
    for path in sorted(Path(log_dir).glob("*.eval")):
        log = read_eval_log(str(path))
        for sample in log.samples or []:
            records.append(_record(tag, sample, rescore))
    return records


def tokens_per_second(records: list[Record]) -> float | None:
    """Output tokens per second of generation time, over all records that report time."""
    seconds = sum(r.generate_seconds for r in records)
    return sum(r.output_tokens for r in records) / seconds if seconds > 0 else None
