"""The Inspect scorer: collect the assistant replies and apply the mode's rule.

The score's value is the rule's dict of facts (behaviour, outcome and flags), so
every flag is in the .eval log. The metrics are the means of behaviour and
outcome with their standard errors; intervals and paired comparisons are
computed later from the logs (arena/report.py), not here.
"""

from __future__ import annotations

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState

from arena import rules
from arena.dataset import episode_of
from arena.solver import SCRIPTED


def generated_replies(messages) -> list[str]:
    """The text of every assistant message the model wrote, in order (scripted turns skipped)."""
    return [m.text for m in messages if isinstance(m, ChatMessageAssistant) and not (m.metadata or {}).get(SCRIPTED)]


@scorer(metrics={"behaviour": [mean(), stderr()], "outcome": [mean(), stderr()]})
def rule_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        episode = episode_of(state.metadata)
        replies = generated_replies(state.messages)
        facts = rules.score(episode, replies)
        value = {k: (1 if v else 0) for k, v in facts.items()}
        answer = replies[-1] if replies else ""
        return Score(value=value, answer=answer, explanation=episode.mode)

    return score
