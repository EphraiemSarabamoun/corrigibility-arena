"""The two splits and a lookup by name.

dev may be read, tuned on and trained on. test is held out: its templates and
wording are disjoint from dev's, and its content is frozen by
manifests/test_split.json. See README.md, "Splits, and what must stay out of training data".
"""

from __future__ import annotations

from arena.splits import dev, test
from arena.templates import Split

SPLITS: dict[str, Split] = {"dev": dev.SPLIT, "test": test.SPLIT}


def get(name: str) -> Split:
    """The split of that name, or a clear error."""
    if name not in SPLITS:
        raise ValueError(f"unknown split {name!r}; choose from {sorted(SPLITS)}")
    return SPLITS[name]


def supports(setting: str, mode: str) -> bool:
    """Whether both splits have templates for the mode's errand family in this setting."""
    from arena.modes import MODE_FAMILY

    family = MODE_FAMILY[mode]
    from arena.modes import SETTING_ONLY

    if mode == "correct_twin" and setting == "transform":
        return False  # transform errands carry no corrected question
    if mode in SETTING_ONLY and setting not in SETTING_ONLY[mode]:
        return False
    return all(split.templates(setting, family) for split in SPLITS.values())
