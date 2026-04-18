"""
config/loader.py
Load and expose the YAML config. Single source of truth for all settings.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict[str, Any]:
    """Return the full parsed config dict."""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_crew_model(config: dict, crew_name: str) -> str:
    """
    Return the configured model for a given crew name.

    Lookup order:
      1. config["crew_models"][crew_name]  — per-crew assignment in config.yaml
      2. config["llm_fallback"]["model"]   — fallback if crew not mapped
      3. "llama3.1:8b"                     — hard default if config is missing keys

    This is the single point used by all crew builders and the web UI endpoint.
    CLI --model overrides this value after it is resolved.
    """
    crew_models = config.get("crew_models", {})
    if crew_name in crew_models:
        return crew_models[crew_name]
    fallback = config.get("llm_fallback", {})
    return fallback.get("model", "llama3.1:8b")


def get_target_repo(config: dict) -> str | None:
    """
    Return the resolved absolute path to the target repo, or None if not set.

    Lookup order:
      1. config["_target_repo"]       — set by CLI --target-repo at runtime
      2. config["crew"]["target_repo"] — from config.yaml (null by default)
    """
    runtime = config.get("_target_repo")
    if runtime:
        return str(Path(runtime).expanduser().resolve())
    yaml_val = config.get("crew", {}).get("target_repo")
    if yaml_val:
        return str(Path(yaml_val).expanduser().resolve())
    return None


def get_agent_model(config: dict, agent_name: str) -> str:
    """
    Return the configured model for a specific agent.

    Lookup order:
      1. config["agent_models"][agent_name]  — per-agent assignment in config.yaml
      2. config["llm_fallback"]["model"]     — fallback if agent not mapped
      3. "llama3.1:8b"                       — hard default if config is missing keys
    """
    agent_models = config.get("agent_models", {})
    if agent_name in agent_models:
        return agent_models[agent_name]
    return config.get("llm_fallback", {}).get("model", "llama3.1:8b")
