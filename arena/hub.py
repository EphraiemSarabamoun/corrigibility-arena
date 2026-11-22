"""Resolve a model source to a local directory the Hugging Face provider can load.

A source is either a public Hub id with a pinned revision, or a local model
directory (a trained checkpoint). Both end as a directory path, so
the CPU runner loads every model the same way. Hub downloads land in the
repository's own cache folder (`cache/hub`), never in a user-wide cache, and
never send a token: the models this arena pins are public.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache" / "hub"

# Environment that keeps huggingface_hub and transformers inside the repository
# cache and away from any stored token. Applied before the library is imported.
OFFLINE_SAFE_ENV = {
    "HF_HOME": str(REPO_ROOT / "cache" / "hf_home"),
    "HF_HUB_CACHE": str(CACHE_DIR),
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
}


def apply_hub_env() -> None:
    """Point the Hub libraries at the repository cache and drop any token from this process."""
    for key, value in OFFLINE_SAFE_ENV.items():
        os.environ[key] = value
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        os.environ.pop(key, None)


def is_local_dir(source: str) -> bool:
    """A source names a local model directory when it is an existing folder holding a config.json."""
    path = Path(source).expanduser()
    return path.is_dir() and (path / "config.json").is_file()


def resolve(source: str, revision: str | None) -> Path:
    """Return a local directory for `source`, downloading a pinned Hub snapshot if needed.

    A local directory is returned as is. A Hub id must come with a full commit
    revision, so two runs of the same config always load the same weights.
    """
    if is_local_dir(source):
        return Path(source).expanduser().resolve()
    if not revision or len(revision) != 40:
        raise ValueError(f"Hub source {source!r} needs a pinned 40-character commit revision, got {revision!r}")
    apply_hub_env()
    from huggingface_hub import snapshot_download  # imported after the env is set

    path = snapshot_download(
        repo_id=source,
        revision=revision,
        cache_dir=str(CACHE_DIR),
        token=False,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"],
    )
    return Path(path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download a pinned public model snapshot into cache/hub")
    parser.add_argument("source")
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    print(resolve(args.source, args.revision))
