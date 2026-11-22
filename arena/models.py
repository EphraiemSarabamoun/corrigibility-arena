"""Build the Inspect model a run talks to: scripted, OpenAI-compatible, or local on CPU.

local    Inspect's Hugging Face provider on CPU. The source is resolved to a
         directory first (arena/hub.py): a pinned Hub snapshot in cache/hub, or
         a checkpoint directory as is. Greedy decoding (do_sample False), the
         configured dtype, torch limited to the configured thread count, one
         request at a time.
openai   any OpenAI-compatible server (a vLLM server, for example), through
         Inspect's openai-api provider, temperature 0. The key is read from
         <SERVICE>_API_KEY if set, else a placeholder, since local servers ignore it.
scripted a policy from arena/policies.py, for tests and for the foil runs.

model_facts() returns what the run manifest records about the model.
"""

from __future__ import annotations

import os
from pathlib import Path

from inspect_ai.model import GenerateConfig, Model, get_model

from arena import hub
from arena.config import Config, ModelSpec

THREAD_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")


def limit_threads(threads: int) -> None:
    """Cap CPU threads for torch and its math libraries; call before torch is imported."""
    for var in THREAD_VARS:
        os.environ[var] = str(threads)


def build_scripted(policy: str) -> Model:
    import arena.policies  # noqa: F401  registers the scripted provider

    return get_model(f"scripted/{policy}")


def build_openai(spec: ModelSpec, cfg: Config) -> Model:
    key_var = f"{spec.service.upper()}_API_KEY"
    return get_model(
        f"openai-api/{spec.service}/{spec.name}",
        base_url=spec.base_url,
        api_key=os.environ.get(key_var, "placeholder"),
        config=GenerateConfig(temperature=0.0, max_tokens=cfg.max_tokens),
    )


def local_dir(spec: ModelSpec) -> Path:
    """The directory a local model loads from."""
    return hub.resolve(spec.source, spec.revision or None)


def build_local(spec: ModelSpec, cfg: Config) -> Model:
    limit_threads(cfg.threads)
    hub.apply_hub_env()
    import torch

    torch.set_num_threads(cfg.threads)
    path = local_dir(spec)
    label = spec.source if not hub.is_local_dir(spec.source) else f"local/{path.name}"
    return get_model(
        f"hf/{label}",
        config=GenerateConfig(max_tokens=cfg.max_tokens, max_connections=cfg.requests_at_once),
        model_path=str(path),
        device="cpu",
        do_sample=False,
        dtype=cfg.dtype,
    )


def build(spec: ModelSpec | None, cfg: Config, scripted: str | None = None) -> Model:
    """The model for a run: a scripted policy if named, else the config entry."""
    if scripted:
        return build_scripted(scripted)
    assert spec is not None
    if spec.kind == "local":
        return build_local(spec, cfg)
    return build_openai(spec, cfg)


def model_facts(spec: ModelSpec | None, cfg: Config, scripted: str | None = None) -> dict:
    """What the manifest records about the model and how it was run."""
    if scripted:
        return {"kind": "scripted", "policy": scripted}
    assert spec is not None
    facts = {"key": spec.key, "kind": spec.kind}
    if spec.kind == "local":
        facts.update(source=spec.source, revision=spec.revision, dtype=cfg.dtype, threads=cfg.threads,
                     requests_at_once=cfg.requests_at_once, decoding="greedy", device="cpu")
    else:
        facts.update(service=spec.service, name=spec.name, base_url=spec.base_url, temperature=0.0)
    return facts
