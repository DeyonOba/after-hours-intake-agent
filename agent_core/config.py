"""Configuration: rung feature flags, data loading, .env handling."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"
MODELS_DIR = REPO_ROOT / "models"

# $/MTok (input, output) — verified 2026-08-30
MODEL_PRICES = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def load_dotenv() -> None:
    """Minimal .env loader (repo root). Existing env vars win."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class RungConfig:
    name: str
    label: str = ""
    # capability flags (the changelog ladder)
    context_docs: bool = False      # rung1: price book + playbook pasted into context
    safety_rules: bool = False      # rung2: deterministic severity floor + policy text
    tools: bool = False             # rung3: price lookup, slots, ML duration model
    question_policy: bool = False   # rung4: info threshold before quoting
    verifier: bool = False          # rung5: programmatic ticket verification + one revision
    memory: bool = False            # rung6: customer lookup by phone (contact ID)
    # models
    agent_model: str = "claude-opus-5"
    sim_model: str = "claude-haiku-4-5"
    max_agent_turns: int = 8
    # Opus 5 adaptive thinking spends from the same budget; keep headroom
    max_tokens: int = 8192


def load_rung_config(path: str | Path) -> RungConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return RungConfig(**raw)


def load_price_book() -> dict:
    return json.loads((DATA_DIR / "price_book.json").read_text())


def price_index(price_book: dict | None = None) -> dict[str, dict]:
    pb = price_book or load_price_book()
    return {item["code"]: item for item in pb["items"]}


def load_playbook_text() -> str:
    return (DATA_DIR / "safety_playbook.md").read_text()


def playbook_ids() -> list[str]:
    import re
    return re.findall(r"\bPB-\d{2}\b", load_playbook_text())


def load_calendar() -> dict:
    return json.loads((DATA_DIR / "calendar.json").read_text())


def load_cases() -> list[dict]:
    return json.loads((DATA_DIR / "cases" / "cases.json").read_text())["cases"]


def load_memory_store() -> dict:
    return json.loads((DATA_DIR / "memory_store.json").read_text())["customers"]


def make_client():
    """Anthropic client that accepts either credential type in ANTHROPIC_API_KEY:
    a Console API key (sk-ant-api...) or an OAuth access token (sk-ant-oat...,
    which must be sent as a Bearer auth_token)."""
    import anthropic
    load_dotenv()
    cred = os.environ.get("ANTHROPIC_API_KEY", "")
    if cred.startswith("sk-ant-oat"):
        return anthropic.Anthropic(api_key=None, auth_token=cred)
    return anthropic.Anthropic()


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = MODEL_PRICES.get(model, (0.0, 0.0))
    return (input_tokens * inp + output_tokens * out) / 1_000_000
