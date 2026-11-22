"""Load and check config.toml.

Returns plain dataclasses so the runner and the report never index raw dicts.
The checks are the ones a wrong config would otherwise turn into a silently
different run: unknown settings or modes, a Hub source without a pinned
revision, more than eight CPU threads.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from arena.modes import MODES
from arena.settings import SETTINGS

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO_ROOT / "config.toml"
MAX_THREADS = 8
MODEL_KINDS = ("local", "openai")


@dataclass(frozen=True)
class ModelSpec:
    key: str
    kind: str
    source: str = ""
    revision: str = ""
    service: str = ""
    name: str = ""
    base_url: str = ""


@dataclass(frozen=True)
class Config:
    split: str
    seed: int
    n: int
    max_tokens: int
    settings: tuple[str, ...]
    modes: tuple[str, ...]
    keep_threshold: float
    threads: int
    dtype: str
    requests_at_once: int
    models: dict[str, ModelSpec] = field(default_factory=dict)


def _check(cfg: Config) -> None:
    bad = [s for s in cfg.settings if s not in SETTINGS]
    if bad:
        raise ValueError(f"unknown settings {bad}; known {SETTINGS}")
    bad = [m for m in cfg.modes if m not in MODES]
    if bad:
        raise ValueError(f"unknown modes {bad}; known {MODES}")
    from arena import splits

    from arena.modes import SETTING_ONLY

    for setting in cfg.settings:
        for mode in cfg.modes:
            if not splits.supports(setting, mode) and mode not in SETTING_ONLY:
                raise ValueError(f"mode {mode!r} has no templates for setting {setting!r} (the warn, clarify, report and loop families cover sums and extract)")
    if not 1 <= cfg.threads <= MAX_THREADS:
        raise ValueError(f"local threads must be 1 to {MAX_THREADS}, got {cfg.threads}")
    for spec in cfg.models.values():
        if spec.kind not in MODEL_KINDS:
            raise ValueError(f"model {spec.key}: kind must be one of {MODEL_KINDS}")
        if spec.kind == "local" and not spec.source:
            raise ValueError(f"model {spec.key}: a local model needs a source")
        if spec.kind == "openai" and not (spec.service and spec.name and spec.base_url):
            raise ValueError(f"model {spec.key}: an openai model needs service, name and base_url")


def load(path: Path = DEFAULT_PATH) -> Config:
    """Read and check the config file."""
    raw = tomllib.loads(Path(path).read_text())
    run, pilot, local = raw["run"], raw["pilot"], raw["local"]
    models = {key: ModelSpec(key=key, **values) for key, values in raw.get("models", {}).items()}
    cfg = Config(
        split=run["split"],
        seed=int(run["seed"]),
        n=int(run["n"]),
        max_tokens=int(run["max_tokens"]),
        settings=tuple(run["settings"]),
        modes=tuple(run["modes"]),
        keep_threshold=float(pilot["keep_threshold"]),
        threads=int(local["threads"]),
        dtype=str(local["dtype"]),
        requests_at_once=int(local["requests_at_once"]),
        models=models,
    )
    _check(cfg)
    return cfg
