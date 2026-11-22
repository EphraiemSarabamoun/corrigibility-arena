"""The episode: an errand wrapped in a mode, as the model will see it.

An Episode is plain data: the system prompt, the principal's user turns in
order, the errand, and what the mode adds (a marker, an injected or forged
line). `instructions` lists every directive in the episode in the order a
reader meets it, with who gave it; the scripted policies read it, the scorers
do not. `errand_id` is shared by every mode built on the same errand, which is
how a mode episode finds its plain twin.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from arena.errand import Errand


@dataclass(frozen=True)
class Directive:
    """One directive: the user turn it sits in (0-based), who gave it, and what it asks for.

    source is principal or other. act is answer, plan, stop, go, correct, marker or drop, and for the
    other families ask (clarify), report (report_error) or loop (loop_in), and follow (correct_twin's
    separate follow-on request).
    Answer-format lines are part of the directive they close, not directives of their own.
    """

    turn: int
    source: str
    act: str


@dataclass(frozen=True)
class Episode:
    episode_id: str
    errand_id: str
    split: str
    setting: str
    mode: str
    seed: int
    index: int
    principal: str
    system: str
    turns: tuple[str, ...]
    errand: Errand
    instructions: tuple[Directive, ...]
    inject_variant: str = ""
    marker: str = ""
    other: str = ""
    planted_line: str = ""
    extra: dict = field(default_factory=dict)
    # Fixed assistant replies, keyed by the user turn they follow. The solver inserts each one
    # as an assistant message instead of asking the model (report_error and follow_on).
    scripted: dict = field(default_factory=dict)

    def generated_turns(self) -> list[int]:
        """The user turns after which the model replies, in order."""
        return [i for i in range(len(self.turns)) if i not in self.scripted]

    def to_dict(self) -> dict:
        """A JSON-safe dict for Inspect sample metadata."""
        data = asdict(self)
        data["turns"] = list(self.turns)
        data["instructions"] = [asdict(d) for d in self.instructions]
        data["scripted"] = {str(k): v for k, v in self.scripted.items()}
        return data

    @staticmethod
    def from_dict(data: dict) -> "Episode":
        """Rebuild an Episode from sample metadata."""
        values = dict(data)
        values["errand"] = Errand.from_dict(values["errand"])
        values["turns"] = tuple(values["turns"])
        values["instructions"] = tuple(Directive(**d) for d in values["instructions"])
        values["scripted"] = {int(k): v for k, v in values.get("scripted", {}).items()}
        return Episode(**values)
