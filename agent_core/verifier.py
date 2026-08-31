"""Programmatic ticket verifier (rung5).

Deterministic checks against the price book, playbook, and calendar. When it
finds issues, the agent gets exactly one revision round-trip. This is
verification-by-construction: prices and refs are checked against source data,
not against another LLM's opinion."""
from __future__ import annotations

from . import config

SEVERITY_ORDER = {"S1": 3, "S2": 2, "S3": 1, "S4": 0}


def verify_ticket(ticket: dict) -> list[str]:
    issues: list[str] = []
    idx = config.price_index()
    pb_ids = set(config.playbook_ids())
    slots = {s["id"]: s for s in config.load_calendar()["slots"]}

    sev = ticket.get("severity")
    if sev not in SEVERITY_ORDER:
        issues.append(f"severity '{sev}' is not one of S1..S4")

    lines = ticket.get("quote_lines") or []
    for line in lines:
        code = (line.get("code") or "").strip().upper()
        if code not in idx:
            issues.append(f"quote line code '{code}' is not in the price book")
        elif line.get("price") != idx[code]["price"]:
            issues.append(
                f"quote line {code} price {line.get('price')} != price book {idx[code]['price']}")
    if lines:
        expected_total = sum(idx[l.get('code', '').strip().upper()]['price']
                             for l in lines if l.get('code', '').strip().upper() in idx)
        if all(l.get('code', '').strip().upper() in idx for l in lines) \
                and ticket.get("quote_total") != expected_total:
            issues.append(f"quote_total {ticket.get('quote_total')} != sum of lines {expected_total}")

    if sev == "S1":
        if not ticket.get("escalate_now"):
            issues.append("S1 ticket must have escalate_now=true")
        repair_lines = [l for l in lines if (l.get("code") or "").strip().upper() != "EMERG-CALLOUT"]
        if repair_lines:
            issues.append("S1 ticket must not contain repair quote lines (only EMERG-CALLOUT)")
        if ticket.get("slot_id"):
            issues.append("S1 ticket must not book a calendar slot (on-call dispatch)")

    for ref in ticket.get("playbook_refs") or []:
        if ref not in pb_ids:
            issues.append(f"playbook ref '{ref}' does not exist in the safety playbook")

    slot_id = ticket.get("slot_id")
    if slot_id:
        slot = slots.get(slot_id)
        if slot is None:
            issues.append(f"slot_id '{slot_id}' does not exist in the calendar")
        else:
            if slot["booked"]:
                issues.append(f"slot {slot_id} is already booked")
            dur = ticket.get("duration_min") or 0
            if dur and slot["capacity_min"] < dur:
                issues.append(f"slot {slot_id} capacity {slot['capacity_min']}min < duration {dur}min")
            if sev == "S2" and not slot["priority"]:
                issues.append("S2 must use a priority slot")
            if sev in ("S3", "S4") and slot["priority"]:
                issues.append("S3/S4 must not take a priority slot (reserved for urgent jobs)")
    return issues


def apply_mechanical_fixes(ticket: dict) -> tuple[dict, list[str]]:
    """Last line of defense: when verifier issues persist after the revision
    round-trip, fix what is mechanically fixable in code. The model can argue
    with a revision request; it cannot argue with this."""
    fixes: list[str] = []
    idx = config.price_index()
    pb_ids = set(config.playbook_ids())

    if ticket.get("severity") == "S1":
        lines = ticket.get("quote_lines") or []
        repair = [l for l in lines if (l.get("code") or "").strip().upper() != "EMERG-CALLOUT"]
        if repair:
            kept = [l for l in lines if l not in repair]
            ticket["quote_lines"] = kept
            ticket["quote_total"] = sum(
                idx[l["code"].strip().upper()]["price"] for l in kept
                if l.get("code", "").strip().upper() in idx) or None
            fixes.append(f"stripped {len(repair)} repair line(s) from S1 ticket")
        if ticket.get("slot_id"):
            ticket["slot_id"] = None
            fixes.append("removed calendar slot from S1 ticket (on-call dispatch)")

    lines = ticket.get("quote_lines") or []
    known = [l for l in lines if (l.get("code") or "").strip().upper() in idx]
    if known:
        for l in known:  # prices come from the book, not the model
            book = idx[l["code"].strip().upper()]["price"]
            if l.get("price") != book:
                fixes.append(f"corrected {l['code']} price {l.get('price')} -> {book}")
                l["price"] = book
        if len(known) == len(lines):
            total = sum(l["price"] for l in known)
            if ticket.get("quote_total") != total:
                fixes.append(f"recomputed quote_total {ticket.get('quote_total')} -> {total}")
                ticket["quote_total"] = total

    bad_refs = [r for r in ticket.get("playbook_refs") or [] if r not in pb_ids]
    if bad_refs:
        ticket["playbook_refs"] = [r for r in ticket["playbook_refs"] if r in pb_ids]
        fixes.append(f"dropped invalid playbook refs {bad_refs}")
    return ticket, fixes
