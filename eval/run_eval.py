"""Run the evaluation for one rung config.

Usage:
  python -m eval.run_eval --config configs/rung0.yaml            # full run
  python -m eval.run_eval --config configs/rung3.yaml --cases c01_burst_supply
  python -m eval.run_eval --selfcheck                            # keys only
  python -m eval.run_eval --config configs/rung0.yaml --dry-run  # no API calls
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

from agent_core import config
from agent_core.agent import IntakeSession
from eval import scoring
from eval.simulator import CustomerSimulator


def run(cfg_path: str, case_filter: list[str] | None, dry_run: bool, resume: bool = False) -> int:
    config.load_dotenv()
    cfg = config.load_rung_config(cfg_path)
    cases = config.load_cases()
    if case_filter:
        cases = [c for c in cases if c["id"] in case_filter]
        if not cases:
            print(f"No cases match {case_filter}")
            return 1

    out_dir = config.RESULTS_DIR / cfg.name
    (out_dir / "trajectories").mkdir(parents=True, exist_ok=True)
    scores_dir = out_dir / "case_scores"
    scores_dir.mkdir(exist_ok=True)

    done: dict[str, dict] = {}
    if resume:
        for f in scores_dir.glob("*.json"):
            rec = json.loads(f.read_text())
            done[rec["case"]] = rec
        if done:
            print(f"[resume] {len(done)} case(s) already scored, skipping them")
        cases = [c for c in cases if c["id"] not in done]

    if dry_run:
        from agent_core import prompts
        sys_prompt = prompts.build_system(cfg, cases[0])
        print(f"[dry-run] config={cfg.name} cases={len(cases)} agent={cfg.agent_model} sim={cfg.sim_model}")
        print(f"[dry-run] system prompt: {len(sys_prompt)} chars; flags: "
              f"context_docs={cfg.context_docs} safety={cfg.safety_rules} tools={cfg.tools} "
              f"qpolicy={cfg.question_policy} verifier={cfg.verifier} memory={cfg.memory}")
        return scoring.selfcheck()

    import anthropic  # noqa: F401 (error types)
    client = config.make_client()

    all_scores, records = [], []
    total_cost = 0.0
    started = time.time()
    for i, case in enumerate(cases, 1):
        print(f"[{i:2d}/{len(cases)}] {case['id']} ...", end=" ", flush=True)
        sim = CustomerSimulator(case, cfg.sim_model, client=client)
        session = IntakeSession(cfg, case, client=client)
        t0 = time.time()
        try:
            result = session.run(sim.respond)
        except anthropic.APIError as exc:
            print(f"API ERROR: {exc}")
            result = session.result
        agent_cost = config.estimate_cost(cfg.agent_model,
                                          result.agent_input_tokens, result.agent_output_tokens)
        case_cost = agent_cost + sim.cost
        total_cost += case_cost
        score = scoring.score_case(case, result)
        score["cost_usd"] = round(case_cost, 4)
        score["wall_s"] = round(time.time() - t0, 1)
        all_scores.append(score)
        record = {"case": case["id"], "ticket": result.ticket,
                  "safety_overrides": result.safety_overrides,
                  "verifier_issues_initial": result.verifier_issues_initial,
                  "verifier_issues_final": result.verifier_issues_final,
                  "score": score}
        records.append(record)
        # incremental save: a killed run loses nothing that already finished
        (scores_dir / f"{case['id']}.json").write_text(json.dumps(record, indent=1))
        (out_dir / "trajectories" / f"{case['id']}.json").write_text(
            json.dumps({"config": cfg.name, "case": case["id"],
                        "system_prompt_chars": len(session.system),
                        "trajectory": result.trajectory}, indent=1))
        flag = "OK " if score["severity_ok"] and score["parse_ok"] else "MISS"
        print(f"{flag} sev={result.ticket.get('severity') if result.ticket else '-'} "
              f"(key {case['answer_key']['severity']}) turns={result.turns} ${case_cost:.2f}")

    # merge resumed cases back in, keeping canonical case order
    if done:
        records = list(done.values()) + records
        order = {c["id"]: i for i, c in enumerate(config.load_cases())}
        records.sort(key=lambda r: order.get(r["case"], 99))
        all_scores = [r["score"] for r in records]
        total_cost += sum(r["score"].get("cost_usd") or 0 for r in done.values())

    agg = scoring.aggregate(all_scores)
    agg["total_cost_usd"] = round(total_cost, 2)
    agg["wall_minutes"] = round((time.time() - started) / 60, 1)

    payload = {"config": dataclasses.asdict(cfg), "aggregate": agg, "cases": records}
    (out_dir / "results.json").write_text(json.dumps(payload, indent=1))
    _write_summary(out_dir / "summary.md", cfg, agg, all_scores)

    print("\n=== AGGREGATE:", cfg.name, "===")
    for k, v in agg.items():
        print(f"  {k}: {v}")
    print(f"\nSaved: {out_dir}/results.json, summary.md, trajectories/")
    return 0


def _write_summary(path: Path, cfg, agg: dict, scores: list[dict]) -> None:
    lines = [f"# Eval summary — {cfg.name} ({cfg.label})", "",
             f"Agent: `{cfg.agent_model}` · Simulator: `{cfg.sim_model}` · Cases: {agg['cases']}", "",
             "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in agg.items()]
    lines += ["", "| Case | Tier | Sev | Cat | Esc | Quote | Mitig | Slot | Parse |", "|---|---|---|---|---|---|---|---|---|"]
    for s in scores:
        def m(v):
            return "—" if v is None else ("✓" if v else "✗")
        lines.append(f"| {s['case_id']} | {s['tier']} | {m(s['severity_ok'])} | {m(s['category_ok'])} "
                     f"| {m(s['escalation_ok'])} | {m(s['quote_ok'])} | {m(s['mitigation_ok'])} "
                     f"| {m(s['slot_ok'])} | {m(s['parse_ok'])} |")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="configs/rungN.yaml")
    ap.add_argument("--cases", help="comma-separated case ids")
    ap.add_argument("--dry-run", action="store_true", help="validate data + prompts, no API calls")
    ap.add_argument("--selfcheck", action="store_true", help="answer-key consistency check only")
    ap.add_argument("--resume", action="store_true", help="skip cases already in results/<rung>/case_scores/")
    args = ap.parse_args()
    if args.selfcheck:
        return scoring.selfcheck()
    if not args.config:
        ap.error("--config required (or use --selfcheck)")
    return run(args.config, args.cases.split(",") if args.cases else None, args.dry_run, args.resume)


if __name__ == "__main__":
    sys.exit(main())
