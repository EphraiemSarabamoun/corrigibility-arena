"""Generate episodes deterministically from (split, setting, mode, seed, index).

Three random streams, each seeded from a hash of its key, keep twins exact:
the errand stream depends only on (split, setting, seed, index), so every mode
gets the same errand; the frame stream (principal, system prompt, greeting,
intro, closings) is likewise mode-free; only the mode stream (which third
party, which marker) depends on the mode. Templates rotate by index so each
template is used equally often.
"""

from __future__ import annotations

import hashlib
import random

from arena import modes, settings, splits, vocab
from arena.settings import families
from arena.episode import Episode
from arena.errand import Errand
from arena.modes import Frame


def stream(*key: object) -> random.Random:
    """A random generator seeded from a stable hash of the key (Python's hash() is salted per process)."""
    digest = hashlib.sha256("|".join(str(k) for k in key).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _key(split: str, setting: str, family: str) -> tuple:
    """The stream key prefix: base errands keep the key they had before the families existed."""
    return (split, setting) if family == "base" else (split, setting, family)


def errand_id(split: str, setting: str, seed: int, index: int, family: str = "base") -> str:
    """The pairing key shared by an errand's episodes in every mode built on its family."""
    return "-".join(_key(split, setting, family)) + f"-s{seed}-{index:03d}"


def make_errand(split_name: str, setting: str, seed: int, index: int, family: str = "base") -> Errand:
    """The errand at one index: template by rotation, contents from the errand stream."""
    split = splits.get(split_name)
    templates = split.templates(setting, family)
    template = templates[index % len(templates)]
    rng = stream(*_key(split_name, setting, family), seed, index, "errand")
    pools = vocab.POOLS[split_name]
    if family == "base":
        return settings.BUILDERS[setting](rng, template, pools)
    return families.make_errand(rng, template, pools)


def make_frame(split_name: str, setting: str, seed: int, index: int, family: str = "base") -> Frame:
    """The mode-free frame of one errand's episodes."""
    wording = splits.get(split_name).wording
    rng = stream(*_key(split_name, setting, family), seed, index, "frame")
    principal = rng.choice(wording.principals)
    return Frame(
        principal=principal,
        system=rng.choice(wording.system).format(principal=principal),
        greeting=rng.choice(wording.greetings).format(principal=principal),
        intro=rng.choice(wording.intros),
        answer_format=rng.choice(wording.answer_format),
        plan_request=rng.choice(wording.plan_request),
        turn2_index=rng.randrange(1000),
    )


def make_episode(split_name: str, setting: str, mode: str, seed: int, index: int) -> Episode:
    """One episode."""
    family = modes.MODE_FAMILY[mode]
    errand = make_errand(split_name, setting, seed, index, family)
    frame = make_frame(split_name, setting, seed, index, family)
    wording = splits.get(split_name).wording
    built = modes.build(mode, wording, frame, errand, stream(*_key(split_name, setting, family), seed, index, "mode", mode))
    eid = errand_id(split_name, setting, seed, index, family)
    return Episode(
        episode_id=f"{eid}-{mode}",
        errand_id=eid,
        split=split_name,
        setting=setting,
        mode=mode,
        seed=seed,
        index=index,
        principal=frame.principal,
        system=frame.system,
        turns=built.turns,
        errand=errand,
        instructions=built.instructions,
        inject_variant=built.inject_variant,
        marker=built.marker,
        other=built.other,
        planted_line=built.planted_line,
        scripted=dict(built.scripted),
    )


def episodes(split_name: str, setting: str, mode: str, n: int, seed: int, start: int = 0) -> list[Episode]:
    """n consecutive episodes from index `start`."""
    return [make_episode(split_name, setting, mode, seed, i) for i in range(start, start + n)]
