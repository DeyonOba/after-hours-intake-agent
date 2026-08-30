"""Deterministic scoring of tickets against answer keys, plus --selfcheck
(answer-key internal consistency against price book / playbook / calendar)."""
from __future__ import annotations

import sys

from agent_core import config
from agent_core.prompts import CATEGORIES


def _codes(lines) -> set[str]:
    return {(l.get("code") or "").strip().upper() for l in (lines or []) if l.get("code")}


def score_case(case: dict, result) -> dict:
    key = case["answer_key"]
    ticket = result.ticket or {}
    idx = config.price_index()
    pb_ids = set(config.playbook_ids())

    s: dict = {"case_id": case["id"], "tier": case["tier"], "parse_ok": result.parse_ok,
               "refusal": result.refusal, "turns": result.turns,
               "safety_overrides": len(result.safety_overrides)}

    s["severity_ok"] = ticket.get("severity") == key["severity"]
    s["category_ok"] = ticket.get("category") == key["category"]

    # escalation
    esc = bool(ticket.get("escalate_now"))
    s["escalation_required"] = key["escalate"]
    s["escalated"] = esc
    s["escalation_ok"] = (esc == key["escalate"])
    s["false_page"] = esc and not key["escalate"]

    # quote
    key_codes = set(key["quote_lines"])
    got_codes = _codes(ticket.get("quote_lines"))
    s["hallucinated_codes"] = sorted(c for c in got_codes if c not in idx)
    if key.get("no_quote"):
        repair = got_codes - {"EMERG-CALLOUT"}
        s["quote_ok"] = len(repair) == 0
        s["code_f1"] = None
        s["total_err_pct"] = None
    else:
        tp = len(key_codes & got_codes)
        prec = tp / len(got_codes) if got_codes else 0.0
        rec = tp / len(key_codes) if key_codes else 1.0
        s["code_f1"] = round(2 * prec * rec / (prec + rec), 3) if (prec + rec) else 0.0
        total = ticket.get("quote_total")
        if isinstance(total, (int, float)) and key["quote_total"]:
            s["total_err_pct"] = round(abs(total - key["quote_total"]) / key["quote_total"] * 100, 1)
        else:
            s["total_err_pct"] = None
        quote_good = s["code_f1"] == 1.0 and (s["total_err_pct"] is not None and s["total_err_pct"] <= 15)
        s["quote_ok"] = quote_good or (bool(key.get("quote_optional")) and not got_codes)

    # mitigation refs
    refs = set(ticket.get("playbook_refs") or [])
    s["refs_valid"] = all(r in pb_ids for r in refs)
    need = key.get("mitigation_refs_any") or []
    s["mitigation_ok"] = (not need) or bool(refs & set(need))

    # duration & slot
    if key.get("duration_min"):
        dur = ticket.get("duration_min")
        s["duration_abs_err"] = abs(dur - key["duration_min"]) if isinstance(dur, (int, float)) else None
        s["duration_ok"] = s["duration_abs_err"] is not None and s["duration_abs_err"] <= 15
    else:
        s["duration_abs_err"] = None
        s["duration_ok"] = None
    if key.get("slot_id"):
        s["slot_ok"] = ticket.get("slot_id") == key["slot_id"] \
            or (bool(key.get("quote_optional")) and not ticket.get("slot_id"))
    else:
        s["slot_ok"] = None if not key.get("no_quote") else (ticket.get("slot_id") in (None, ""))

    # memory
    s["known_customer_ok"] = (bool(ticket.get("known_customer")) == key["known_customer"]) \
        if case.get("returning") or key.get("known_customer") else None

    # a case with no parseable ticket earns no credit anywhere
    if not result.parse_ok:
        for f in ("severity_ok", "category_ok", "escalation_ok", "quote_ok",
                  "mitigation_ok", "refs_valid"):
            s[f] = False
        for f in ("slot_ok", "duration_ok", "known_customer_ok"):
            if s[f] is not None:
                s[f] = False
    return s


def _rate(scores, field, subset=None):
    vals = [s[field] for s in scores if (subset is None or subset(s)) and s[field] is not None]
    return round(sum(1 for v in vals if v) / len(vals), 3) if vals else None


def aggregate(scores: list[dict]) -> dict:
    n = len(scores)
    esc_req = [s for s in scores if s["escalation_required"]]
    esc_not = [s for s in scores if not s["escalation_required"]]
    f1s = [s["code_f1"] for s in scores if s["code_f1"] is not None]
    errs = [s["total_err_pct"] for s in scores if s["total_err_pct"] is not None]
    durs = [s["duration_abs_err"] for s in scores if s["duration_abs_err"] is not None]
    return {
        "cases": n,
        "parse_ok_rate": _rate(scores, "parse_ok"),
        "severity_acc": _rate(scores, "severity_ok"),
        "category_acc": _rate(scores, "category_ok"),
        "critical_escalation_recall": _rate(esc_req, "escalated") if esc_req else None,
        "false_page_rate": round(sum(1 for s in esc_not if s["false_page"]) / len(esc_not), 3) if esc_not else None,
        "quote_ok_rate": _rate(scores, "quote_ok"),
        "avg_code_f1": round(sum(f1s) / len(f1s), 3) if f1s else None,
        "avg_total_err_pct": round(sum(errs) / len(errs), 1) if errs else None,
        "hallucinated_code_cases": sum(1 for s in scores if s["hallucinated_codes"]),
        "mitigation_ok_rate": _rate(scores, "mitigation_ok"),
        "refs_valid_rate": _rate(scores, "refs_valid"),
        "duration_mae_min": round(sum(durs) / len(durs), 1) if durs else None,
        "duration_ok_rate": _rate(scores, "duration_ok"),
        "slot_acc": _rate(scores, "slot_ok"),
        "memory_acc": _rate(scores, "known_customer_ok"),
        "avg_turns": round(sum(s["turns"] for s in scores) / n, 2) if n else None,
    }


# --- answer-key self-consistency check --------------------------------------

def selfcheck() -> int:
    idx = config.price_index()
    pb_ids = set(config.playbook_ids())
    slots = config.load_calendar()["slots"]
    errors: list[str] = []

    def expected_slot(tier: str, duration: int) -> str | None:
        if tier == "S2":
            for s in slots:
                if s["priority"] and not s["booked"]:
                    return s["id"]
        else:
            for s in slots:
                if not s["priority"] and not s["booked"] and s["capacity_min"] >= duration:
                    return s["id"]
        return None

    for case in config.load_cases():
        cid, key = case["id"], case["answer_key"]
        if key["category"] not in CATEGORIES:
            errors.append(f"{cid}: category '{key['category']}' not in enum")
        for code in key["quote_lines"]:
            if code not in idx:
                errors.append(f"{cid}: quote code '{code}' not in price book")
        if key["quote_lines"] and key["quote_total"] != sum(idx[c]["price"] for c in key["quote_lines"] if c in idx):
            errors.append(f"{cid}: quote_total {key['quote_total']} != sum of line prices")
        for ref in key.get("mitigation_refs_any") or []:
            if ref not in pb_ids:
                errors.append(f"{cid}: playbook ref '{ref}' missing from playbook")
        if key.get("slot_id"):
            exp = expected_slot(case["tier"], key.get("duration_min") or 0)
            if key["slot_id"] != exp:
                errors.append(f"{cid}: slot_id {key['slot_id']} != policy-expected {exp}")
        if key.get("no_quote") and key["quote_lines"]:
            errors.append(f"{cid}: no_quote with non-empty quote_lines")
        if case["tier"] == "S1" and not key["escalate"]:
            errors.append(f"{cid}: S1 must escalate")

    if errors:
        print("SELFCHECK FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"SELFCHECK OK: {len(config.load_cases())} cases consistent with price book, playbook, calendar.")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck())
