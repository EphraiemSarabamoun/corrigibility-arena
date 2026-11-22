"""Run the arena: one model over a grid of (setting, mode) cells, writing Inspect .eval logs.

Execution starts here. Examples:

    .venv/bin/python run_eval.py --scripted ideal --run-id smoke --n 4
    .venv/bin/python run_eval.py --model olmo2_1b_instruct --run-id pilot --modes plain
    .venv/bin/python run_eval.py --model vllm_server --run-id v1 --split dev

Logs go to logs/<run-id>/<model>/, beside a manifest.json that records the
config, the model facts, the versions and the wall time. summarize.py turns
that folder into tables. Thread limits are applied before torch is imported.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

from arena import config as config_mod
from arena.models import limit_threads
from arena import splits

REPO_ROOT = Path(__file__).resolve().parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    who = p.add_mutually_exclusive_group(required=True)
    who.add_argument("--model", help="a [models.<key>] entry of config.toml")
    who.add_argument("--scripted", help="a scripted policy: ideal, always_answer, always_stop, obey_last")
    p.add_argument("--run-id", required=True)
    p.add_argument("--config", default=str(config_mod.DEFAULT_PATH))
    p.add_argument("--split")
    p.add_argument("--settings", nargs="+")
    p.add_argument("--modes", nargs="+")
    p.add_argument("--n", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--log-root", default=str(REPO_ROOT / "logs"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = config_mod.load(Path(args.config))
    limit_threads(cfg.threads)

    from inspect_ai import eval as inspect_eval

    from arena import models
    from arena.task import corrigibility_task

    split = args.split or cfg.split
    settings = tuple(args.settings or cfg.settings)
    modes = tuple(args.modes or cfg.modes)
    n = args.n or cfg.n
    seed = cfg.seed if args.seed is None else args.seed
    spec = cfg.models[args.model] if args.model else None
    model_tag = args.model or f"scripted_{args.scripted}"
    log_dir = Path(args.log_root) / args.run_id / model_tag
    log_dir.mkdir(parents=True, exist_ok=True)

    model = models.build(spec, cfg, scripted=args.scripted)
    # A mode built only for some settings (modes.SETTING_ONLY) is skipped elsewhere.
    tasks = [corrigibility_task(split=split, setting=s, mode=m, n=n, seed=seed, max_tokens=cfg.max_tokens)
             for s in settings for m in modes if splits.supports(s, m)]
    started = time.time()
    logs = inspect_eval(tasks, model=model, log_dir=str(log_dir), display="plain", max_tasks=1, max_samples=cfg.requests_at_once if spec and spec.kind == "local" else None, fail_on_error=False)
    manifest = {
        "run_id": args.run_id,
        "model_tag": model_tag,
        "model": models.model_facts(spec, cfg, scripted=args.scripted),
        "split": split,
        "settings": list(settings),
        "modes": list(modes),
        "n": n,
        "seed": seed,
        "max_tokens": cfg.max_tokens,
        "wall_time_s": round(time.time() - started, 1),
        "python": platform.python_version(),
        "logs": [{"task": log.eval.task, "status": log.status, "file": Path(log.location).name} for log in logs],
    }
    try:
        import inspect_ai

        manifest["inspect_ai"] = inspect_ai.__version__
    except Exception:  # pragma: no cover
        pass
    (log_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    failed = [log.eval.task for log in logs if log.status != "success"]
    print(json.dumps({"log_dir": str(log_dir), "failed_tasks": failed, "wall_time_s": manifest["wall_time_s"]}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
