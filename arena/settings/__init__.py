"""The registry of settings: each name maps to the function that builds one errand from a template.

A setting is an errand family, the main task of an episode (ControlArena's sense
of the word). Which settings a run uses is a config choice (config.toml), not a
code change; config.toml says which settings are kept and why.
"""

from __future__ import annotations

from arena.settings import extract, sums, transform

BUILDERS = {
    "sums": sums.make_errand,
    "extract": extract.make_errand,
    "transform": transform.make_errand,
}

SETTINGS = tuple(BUILDERS)
