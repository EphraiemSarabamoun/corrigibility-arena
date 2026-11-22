"""The errand: one small job with exactly one right answer, and its correction.

An Errand is what a setting produces from a template and a seeded random
generator. The warn, clarify, report and loop families use the extra
fields below; a base errand leaves them empty. It carries the material the principal forwards, the question, the
right answer and how answers are compared (answer_kind). It also carries the
correction a `correct` episode uses: the principal's changed request and the
answer that request makes right. Errands are plain data so the generator, the
scorers and the scripted policies all read the same facts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

# How a reply's answer is compared with the right one (arena/answer.py).
ANSWER_KINDS = ("number", "text_ci", "text_cs", "word_order")


@dataclass(frozen=True)
class Errand:
    """One errand. distractors are other values from the same material that a wrong answer may give."""

    setting: str
    template_id: str
    question: str
    material: str
    answer: str
    answer_kind: str
    correction: str
    corrected_answer: str
    corrected_kind: str
    distractors: tuple[str, ...] = field(default_factory=tuple)
    # For word_order answers: the candidate words, so order can be read from any reply.
    vocabulary: tuple[str, ...] = field(default_factory=tuple)
    # The errand family: base (plain and the first six modes), warn, clarify, report or loop.
    family: str = "base"
    # base: the question that asks for the corrected answer directly (correct_twin).
    corrected_question: str = ""
    # warn: the 'better' value the principal's informed order declined.
    other_value: str = ""
    # clarify: the value of each reading of the ambiguous question; clear_question removes the ambiguity
    # and its right answer is `answer`.
    readings: tuple[str, ...] = field(default_factory=tuple)
    clear_question: str = ""
    # report: the scripted first reply with the wrong answer (and with the right one, for follow_on), the
    # principal's follow-up, the follow-on value built on the right
    # answer (follow_answer, follow_kind) and the one built on the wrong answer.
    wrong_reply: str = ""
    right_reply: str = ""
    follow_up: str = ""
    follow_answer: str = ""
    follow_kind: str = ""
    built_on_wrong: str = ""
    # loop: the options the principal must choose between, and how they are compared.
    options: tuple[str, ...] = field(default_factory=tuple)
    option_kind: str = ""
    # loop: the closing that names what goes after the label (the irreversible step).
    closing: str = ""
    # The control twin's errand where it differs: warn_twin asks twin_question (the order without
    # its stated downside) on the same material; loop_routine asks twin_question on twin_material,
    # a routine, reversible, in-scope step whose right answer is twin_answer (kind twin_kind).
    twin_question: str = ""
    twin_material: str = ""
    twin_answer: str = ""
    twin_kind: str = ""

    def to_dict(self) -> dict:
        """A JSON-safe dict, for sample metadata."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Errand":
        """Rebuild an Errand from sample metadata."""
        known = {f.name for f in fields(Errand)}
        values = {k: v for k, v in data.items() if k in known}  # a logged errand may carry fields this code does not read
        for key in ("distractors", "vocabulary", "readings", "options"):
            values[key] = tuple(values.get(key, ()))
        return Errand(**values)
