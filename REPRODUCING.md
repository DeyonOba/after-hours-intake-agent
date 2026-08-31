# Reproduction Guide

Everything below assumes a clean machine with git and either `uv`
([install](https://docs.astral.sh/uv/)) or Python 3.12.

Tested with: Python 3.12, `anthropic==1.2.0`, `scikit-learn==1.9.0` (pinned in
`requirements.txt`). OS: macOS (any platform with Python 3.12 should work).

## 1. Setup (≈2 minutes)

```bash
git clone <this-repo> && cd frontier_engineering_challenge_2026

# with uv (recommended):
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# or with plain python 3.12:
#   python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt

cp .env.example .env      # then paste your Anthropic API key into .env
```

Both Console API keys (`sk-ant-api...`) and OAuth tokens (`sk-ant-oat...`)
work; the client factory routes each correctly. Note: subscription OAuth
tokens may not have access to Opus-class models — a Console key with credits
is the reliable path.

## 2. Verify the data & harness without spending anything

```bash
.venv/bin/python -m eval.run_eval --selfcheck
# -> SELFCHECK OK: 18 cases consistent with price book, playbook, calendar.

.venv/bin/python -m eval.run_eval --config configs/rung0.yaml --dry-run
# -> prints config flags + prompt stats, runs selfcheck, no API calls
```

`--selfcheck` recomputes every answer key's quote total, playbook refs, and
slot assignment from the source data and fails on any inconsistency — the
answer keys cannot silently drift from the price book.

The two model artifacts are regenerated deterministically (fixed seeds):

```bash
.venv/bin/python scripts/train_duration_model.py   # rebuilds data/historical_jobs.csv + models/duration_model.joblib
.venv/bin/python scripts/fetch_seeds.py            # optional: re-pins dataset rows (network); committed copies already in data/seeds/
```

## 3. Reproduce the main result

Baseline and final, 18 cases each:

```bash
.venv/bin/python -m eval.run_eval --config configs/rung0.yaml   # baseline
.venv/bin/python -m eval.run_eval --config configs/rung6.yaml   # final
```

Any intermediate changelog row is the same command with that rung's config
(`configs/rung1.yaml` … `rung5.yaml`).

**Expected output per run:** a per-case progress line
(`OK/MISS sev=... turns=... $...`), an aggregate metrics block, and files
under `results/<rung>/`:

- `results.json` — config, aggregate metrics, per-case scores and tickets
- `summary.md` — the same as a table
- `trajectories/<case>.json` — every message, tool call, tool result, safety
  override, and verifier issue for every conversation
- `case_scores/<case>.json` — incremental per-case saves; if a run is
  interrupted, add `--resume` to continue without re-spending

**Approximate runtime & cost per 18-case run** (Claude Opus 5 agent + Haiku
4.5 simulator, prices of 2026-08): rung0 ≈ 15 min / ~$1.4 · rung1–2 ≈ 15–30
min / ~$1.5 each · rung3–6 ≈ 10–30 min / ~$2.7–4.5 each. Full 7-rung program:
~$15–20.

What the numbers should look like: within a few percent of the tables in
`CHANGELOG.md` and `README.md` (LLM sampling varies slightly run to run; the
qualitative deltas between rungs — escalation recall, hallucinated codes,
quote accuracy — are stable).

## 4. Judge shortcuts (no API needed)

Committed outputs from our runs are in `results/` — every aggregate in the
README/CHANGELOG traces to a `results/<rung>/results.json`, and every claim
about agent behavior to a file in `results/<rung>/trajectories/`.

To spot-check scoring logic without any API calls:

```bash
.venv/bin/python - <<'EOF'
import json
from types import SimpleNamespace
from agent_core import config
from eval import scoring
case = [c for c in config.load_cases() if c["id"] == "c05_no_hot_water_returning"][0]
rec = json.load(open("results/rung6/case_scores/c05_no_hot_water_returning.json"))
shim = SimpleNamespace(ticket=rec["ticket"], parse_ok=True, refusal=False, turns=4, safety_overrides=[])
print(scoring.score_case(case, shim))
EOF
```

## 5. Optional: live Discord demo

The eval never touches Discord; this is demo-only. Create a bot at
discord.com/developers, put `DISCORD_BOT_TOKEN` in `.env`, install
`discord.py`, and run the adapter in `adapters/discord_bot/` (see its README).
