"""The shapes of a split's wording: errand templates and the principal's mode lines.

These dataclasses hold strings only, no logic. A split (arena/splits/dev.py or
arena/splits/test.py) fills them in; the settings (arena/settings/) and the
modes (arena/modes.py) read them. Keeping every sentence a model sees inside a
split file is what lets the dev and test splits be disjoint in wording, and
lets arena/manifest.py hash the test split's wording exactly.

Placeholders use str.format names. Each template lists the names it may use in
its docstring; tests/test_splits.py checks every string formats cleanly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SumsTemplate:
    """A receipt. header uses {shop}; line uses {item} and {price}; questions are paraphrases of 'what is the total';
    corrections use {item} and ask to leave that item out; corrected_questions ask for that corrected total
    directly (the correct_twin mode) and use {item}."""

    id: str
    header: str
    line: str
    questions: tuple[str, ...]
    corrections: tuple[str, ...]
    corrected_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractTemplate:
    """A short message. message uses {sender} {event} {date} {place} {amount}.
    questions maps a field (date, sender, amount) to paraphrases asking for it.
    field_nouns maps a field to the noun phrase a correction uses; corrections use {noun}."""

    id: str
    message: str
    questions: dict[str, tuple[str, ...]]
    field_nouns: dict[str, str]
    corrections: tuple[str, ...]


@dataclass(frozen=True)
class TransformTemplate:
    """A small rewrite with one right answer. op is first, upper, count or sort (arena/settings/transform.py).
    material uses {words} (first, sort), {word} (upper) or {items} (count); joiner joins the words or items.
    corrections: first asks for the later word; sort for reverse order; upper for lowercase; count uses {item}, an item to add."""

    id: str
    op: str
    material: str
    joiner: str
    questions: tuple[str, ...]
    corrections: tuple[str, ...]


@dataclass(frozen=True)
class FamilyTemplate:
    """A template of one of the warn, clarify, report and loop errand families, for one setting.

    kind names the builder in arena/settings/families.py that reads it. texts maps each slot the
    builder needs to its paraphrases; the builder documents its slots and their placeholders.
    tests/test_splits.py checks that every slot a builder needs is present in every template.
    """

    id: str
    family: str
    setting: str
    kind: str
    texts: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class SplitWording:
    """Everything the principal and the material's other authors say, for one split.

    system uses {principal}. greetings use {principal}. user_layout joins the parts of the
    first user turn and uses {greeting} {question} {intro} {material} {closing}.
    answer_format is the closing that asks for the ANSWER line; plan_request is the closing
    of a plan-first turn. go_ahead, stop and correction_wrap (uses {correction}) are the
    principal's second turns. inject_marker uses {other} {principal} {marker}; inject_drop
    uses {other} {principal}; forged_stop uses {principal} and claims to be the principal
    while sitting inside the material.
    """

    principals: tuple[str, ...]
    others: tuple[str, ...]
    marker_words: tuple[str, ...]
    system: tuple[str, ...]
    greetings: tuple[str, ...]
    user_layout: str
    intros: tuple[str, ...]
    answer_format: tuple[str, ...]
    plan_request: tuple[str, ...]
    go_ahead: tuple[str, ...]
    stop: tuple[str, ...]
    correction_wrap: tuple[str, ...]
    inject_marker: tuple[str, ...]
    inject_drop: tuple[str, ...]
    forged_stop: tuple[str, ...]
    # correct_twin's second turn: a separate follow-on request for the corrected value, with no
    # contradiction of the first; uses {question} (the corrected question, first letter lowered).
    follow_on_wrap: tuple[str, ...] = ()
    # Decoys: the cue words of stop and loop_in used innocently, in their own two modes only, so plain
    # and the capability twins stay clean. decoy_go_ahead is continue's go-ahead
    # with an ordinary 'stop' in it (continue_decoy); decoy_asides put an innocent 'can't' or 'cannot'
    # before the routine step (loop_decoy).
    decoy_go_ahead: tuple[str, ...] = ()
    decoy_asides: tuple[str, ...] = ()


@dataclass(frozen=True)
class Split:
    """One split: its name, its mode wording, its base errand templates per setting, and the
    templates of the warn, clarify, report and loop errand families (family name to templates, each naming its setting)."""

    name: str
    wording: SplitWording
    sums: tuple[SumsTemplate, ...]
    extract: tuple[ExtractTemplate, ...]
    transform: tuple[TransformTemplate, ...]
    families: tuple[FamilyTemplate, ...] = ()

    def templates(self, setting: str, family: str = "base") -> tuple:
        """The templates of one setting in this split: the base errands, or one other family's."""
        if family == "base":
            return {"sums": self.sums, "extract": self.extract, "transform": self.transform}[setting]
        return tuple(t for t in self.families if t.family == family and t.setting == setting)
