"""Turn episodes into Inspect samples.

A sample's input is the system prompt and the first user turn. The later user
turns, the errand and everything the scorer needs travel in the sample's
metadata as the episode's dict, so the solver and the scorer rebuild the same
Episode the generator made.
"""

from __future__ import annotations

from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser

from arena.episode import Episode

EPISODE_KEY = "episode"


def to_sample(episode: Episode) -> Sample:
    """One episode as one sample; its id is the episode id."""
    return Sample(
        id=episode.episode_id,
        input=[ChatMessageSystem(content=episode.system), ChatMessageUser(content=episode.turns[0])],
        target=episode.errand.answer,
        metadata={EPISODE_KEY: episode.to_dict()},
    )


def to_dataset(episodes: list[Episode], name: str) -> MemoryDataset:
    """A dataset of the episodes, in order."""
    return MemoryDataset([to_sample(e) for e in episodes], name=name)


def episode_of(metadata: dict) -> Episode:
    """The episode a sample carries."""
    return Episode.from_dict(metadata[EPISODE_KEY])
