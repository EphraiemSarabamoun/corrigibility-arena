"""The episode solver: play the principal's scripted turns, one model reply after each.

Turn 1 is already in the sample input. After each reply the solver appends the
next scripted user turn, whatever the model said; the principal does not adapt.
Where the episode holds a fixed assistant reply for a turn (report_error and
follow_on), the solver inserts it, marked in its metadata, instead of asking the
model; the scorer and the log reader skip such messages.
Before every call it puts the episode and the turn number in the sample store,
which is how the scripted policies (arena/policies.py) know what they are
answering. A real model never reads the store.
"""

from __future__ import annotations

from inspect_ai.model import ChatMessageAssistant, ChatMessageUser
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import store

from arena.dataset import EPISODE_KEY, episode_of

STORE_EPISODE = "arena_episode"
STORE_TURN = "arena_turn"
# Metadata key marking an assistant message the solver inserted rather than the model wrote.
SCRIPTED = "arena_scripted"


@solver
def episode_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        episode = episode_of(state.metadata)
        store().set(STORE_EPISODE, state.metadata[EPISODE_KEY])
        for turn, text in enumerate(episode.turns):
            if turn > 0:
                state.messages.append(ChatMessageUser(content=text))
            if turn in episode.scripted:
                # A fixed earlier assistant answer (report_error, follow_on): shown, never generated.
                state.messages.append(ChatMessageAssistant(content=episode.scripted[turn], metadata={SCRIPTED: True}))
                continue
            store().set(STORE_TURN, turn)
            state = await generate(state)
            if state.output is not None and state.output.error:
                break
        return state

    return solve
