"""The Inspect task: one (split, setting, mode) cell of n episodes.

`corrigibility_task` is also registered with Inspect, so a run can be started
with `inspect eval arena/task.py -T split=dev -T setting=sums -T mode=stop`;
the repository's runner (run_eval.py) builds the same tasks in Python.
"""

from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig

from arena import generator
from arena.dataset import to_dataset
from arena.scorer import rule_scorer
from arena.solver import episode_solver


def task_name(split: str, setting: str, mode: str) -> str:
    """The task's name in logs and file names."""
    return f"{split}_{setting}_{mode}"


@task
def corrigibility_task(split: str = "dev", setting: str = "sums", mode: str = "plain", n: int = 30, seed: int = 0, max_tokens: int = 128) -> Task:
    episodes = generator.episodes(split, setting, mode, n, seed)
    return Task(
        dataset=to_dataset(episodes, name=task_name(split, setting, mode)),
        solver=episode_solver(),
        scorer=rule_scorer(),
        config=GenerateConfig(max_tokens=max_tokens),
        name=task_name(split, setting, mode),
        metadata={"split": split, "setting": setting, "mode": mode, "n": n, "seed": seed},
    )
