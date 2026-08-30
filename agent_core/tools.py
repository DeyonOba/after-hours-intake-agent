"""Agent tools (rung3+): price book lookup, ML duration prediction, slots,
and (rung6) customer memory lookup. Pure implementations live beside their
@beta_tool wrappers so they stay unit-testable without the SDK loop."""
from __future__ import annotations

import json
from pathlib import Path

from anthropic import beta_tool

from . import config, memory

_DURATION_MODEL = None  # lazy cache: {"model": estimator, "codes": [...]}


def _price_items() -> list[dict]:
    return config.load_price_book()["items"]


def price_book_lookup_impl(query: str) -> str:
    q = query.lower()
    words = [w for w in q.replace("/", " ").split() if len(w) > 2]
    hits = []
    for item in _price_items():
        hay = f"{item['code']} {item['name']}".lower()
        score = sum(1 for w in words if w in hay)
        if score:
            hits.append((score, item))
    hits.sort(key=lambda t: -t[0])
    if not hits:
        return "No price-book match. Try get_price with an exact code, or different keywords."
    return json.dumps([h[1] for h in hits[:5]])


def get_price_impl(code: str) -> str:
    item = config.price_index().get(code.strip().upper())
    return json.dumps(item) if item else f"Unknown code '{code}'. Codes must come from price_book_lookup."


def predict_duration_impl(job_code: str, old_fixture: bool = False,
                          recurring: bool = False, multi_fixture: bool = False) -> str:
    global _DURATION_MODEL
    code = job_code.strip().upper()
    idx = config.price_index()
    if code not in idx:
        return f"Unknown job code '{code}'."
    model_path = config.MODELS_DIR / "duration_model.joblib"
    if _DURATION_MODEL is None and model_path.exists():
        import joblib
        _DURATION_MODEL = joblib.load(model_path)
    if _DURATION_MODEL is None:
        return "Duration model not trained. Run scripts/train_duration_model.py first."
    codes = _DURATION_MODEL["codes"]
    feats = [[1.0 if code == c else 0.0 for c in codes]
             + [float(old_fixture), float(recurring), float(multi_fixture)]]
    minutes = int(round(float(_DURATION_MODEL["model"].predict(feats)[0])))
    return json.dumps({"job_code": code, "predicted_duration_min": minutes})


def get_available_slots_impl(duration_min: int, priority: bool = False) -> str:
    slots = [
        s for s in config.load_calendar()["slots"]
        if not s["booked"] and s["capacity_min"] >= duration_min and s["priority"] == priority
    ]
    if not slots:
        return "No slots fit. Try priority=false, a shorter duration, or tell the customer the office will call."
    return json.dumps(slots)


def lookup_customer_impl(phone: str) -> str:
    record = memory.lookup(phone)
    return json.dumps(record) if record else "No record for this phone number (new customer)."


# --- @beta_tool wrappers (schemas generated from signatures/docstrings) -----

@beta_tool
def price_book_lookup(query: str) -> str:
    """Search the flat-rate price book by keywords (e.g. 'toilet clog', 'water heater replace').

    Args:
        query: Keywords describing the job.
    """
    return price_book_lookup_impl(query)


@beta_tool
def get_price(code: str) -> str:
    """Get one price-book line by its exact code (e.g. 'TOILET-REBUILD').

    Args:
        code: Exact price-book code.
    """
    return get_price_impl(code)


@beta_tool
def predict_duration(job_code: str, old_fixture: bool = False,
                     recurring: bool = False, multi_fixture: bool = False) -> str:
    """Predict on-site duration in minutes for a job using the trained ML model.

    Args:
        job_code: Price-book code of the job.
        old_fixture: True if the fixture/equipment is old (15+ years or customer says so).
        recurring: True if this same problem was serviced before at this address.
        multi_fixture: True if multiple fixtures are affected.
    """
    return predict_duration_impl(job_code, old_fixture, recurring, multi_fixture)


@beta_tool
def get_available_slots(duration_min: int, priority: bool = False) -> str:
    """List open calendar slots that fit a job duration.

    Args:
        duration_min: Predicted job duration in minutes.
        priority: True only for S2 urgent jobs (priority slots are reserved for them).
    """
    return get_available_slots_impl(duration_min, priority)


@beta_tool
def lookup_customer(phone: str) -> str:
    """Look up a customer's record (equipment, service history) by phone number.

    Args:
        phone: Customer phone number, e.g. '+1-555-0105'.
    """
    return lookup_customer_impl(phone)


def toolset(cfg) -> list:
    tools = [price_book_lookup, get_price, predict_duration, get_available_slots]
    if cfg.memory:
        tools.append(lookup_customer)
    return tools
