"""Deterministic safety rule layer (rung2+).

LLM judgment is not allowed to be the last line of defense for life-safety
signals. These rules scan the CUSTOMER's own words and enforce a severity
floor on the final ticket. Rules only ever raise severity, never lower it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SEVERITY_ORDER = {"S1": 3, "S2": 2, "S3": 1, "S4": 0}

# Phrases that neutralize a trigger ("no gas smell", "don't smell gas", ...)
NEGATION_PATTERNS = [
    r"\bno (?:gas|sewage|smell of gas)\b[^.!?\n]*",
    r"\b(?:don't|do not|can't|cannot|doesn't|does not) smell\b[^.!?\n]*",
    r"\bno smell\b[^.!?\n]*",
    r"\bnot (?:a )?gas\b[^.!?\n]*",
]

@dataclass
class Trigger:
    name: str
    pattern: str
    floor: str
    required_ref: str
    strip_quote: bool = False

TRIGGERS = [
    Trigger("gas_smell", r"\b(gas smell|gas leak|smell[a-z]*[^.!?\n]{0,30}\bgas\b|rotten eggs?|sulfur|sulphur)\b",
            "S1", "PB-06", strip_quote=True),
    Trigger("sewage", r"\b(sewage|sewer (?:is )?back|sewage back|waste water coming up)\b",
            "S1", "PB-05"),
    Trigger("uncontained_water", r"\b(spraying|gushing|pouring|burst|flooding|water(?:'s| is)? (?:going )?everywhere)\b",
            "S1", "PB-02"),
]


@dataclass
class SafetyFinding:
    floor: str = "S4"
    fired: list = field(default_factory=list)          # trigger names
    required_refs: list = field(default_factory=list)  # playbook ids
    strip_quote: bool = False


def scan_customer_text(texts: list[str]) -> SafetyFinding:
    joined = "\n".join(texts).lower()
    for neg in NEGATION_PATTERNS:
        joined = re.sub(neg, " ", joined)
    finding = SafetyFinding()
    for trig in TRIGGERS:
        if re.search(trig.pattern, joined):
            finding.fired.append(trig.name)
            finding.required_refs.append(trig.required_ref)
            finding.strip_quote = finding.strip_quote or trig.strip_quote
            if SEVERITY_ORDER[trig.floor] > SEVERITY_ORDER[finding.floor]:
                finding.floor = trig.floor
    return finding


def enforce(ticket: dict, finding: SafetyFinding) -> tuple[dict, list[str]]:
    """Apply the severity floor to a parsed ticket. Returns (ticket, overrides)."""
    overrides: list[str] = []
    if not finding.fired:
        return ticket, overrides

    sev = ticket.get("severity") or "S4"
    if SEVERITY_ORDER.get(sev, 0) < SEVERITY_ORDER[finding.floor]:
        overrides.append(f"severity {sev} -> {finding.floor} (rules: {finding.fired})")
        ticket["severity"] = finding.floor

    if finding.floor == "S1" and not ticket.get("escalate_now"):
        overrides.append("escalate_now forced true")
        ticket["escalate_now"] = True

    refs = set(ticket.get("playbook_refs") or [])
    missing = [r for r in finding.required_refs if r not in refs]
    if missing:
        overrides.append(f"playbook refs added: {missing}")
        ticket["playbook_refs"] = sorted(refs | set(missing))

    if finding.strip_quote and ticket.get("quote_lines"):
        overrides.append("quote stripped (gas emergency: no quoting)")
        ticket["quote_lines"] = []
        ticket["quote_total"] = None
        ticket["slot_id"] = None
    return ticket, overrides
