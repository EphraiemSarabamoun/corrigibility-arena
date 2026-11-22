"""Write the dev split's episodes to data/dev/ as JSON lines, one file per (setting, mode).

The committed files are exactly what the generator makes for the config's
settings, modes, seed and n (tests/test_manifest_and_data.py checks this), so a reader can see every dev
episode without running anything, and training code can read them directly.
The test split is never exported.

    .venv/bin/python -m arena.export
"""

from __future__ import annotations

import json
from pathlib import Path

from arena import config, splits, generator

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_DIR = REPO_ROOT / "data" / "dev"


def lines(setting: str, mode: str, n: int, seed: int) -> list[str]:
    """The JSON lines of one dev file."""
    return [json.dumps(e.to_dict(), sort_keys=True, ensure_ascii=False) for e in generator.episodes("dev", setting, mode, n, seed)]


def main() -> int:
    cfg = config.load()
    DEV_DIR.mkdir(parents=True, exist_ok=True)
    for setting in cfg.settings:
        for mode in cfg.modes:
            if not splits.supports(setting, mode):
                continue  # a mode built only for some settings (modes.SETTING_ONLY)
            path = DEV_DIR / f"{setting}_{mode}.jsonl"
            path.write_text("\n".join(lines(setting, mode, cfg.n, cfg.seed)) + "\n")
            print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
