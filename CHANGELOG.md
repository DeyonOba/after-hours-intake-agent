# Improvement Changelog

The story of the solution, one measured iteration at a time. Every row is
reproducible from HEAD: `python -m eval.run_eval --config configs/<rung>.yaml`.
Evidence: `results/<rung>/results.json` and `results/<rung>/summary.md`.

| Stage | What we tried and why | Evidence | Decision / learning |
|-------|----------------------|----------|---------------------|
| rung0 (baseline) | One direct prompt with basic instructions — the brief's canonical baseline. | 18 cases, $1.39: parse 100%, severity 77.8%, category 94.4%, **critical escalation recall 75%** (missed a burst-pipe S1), false pages 0%, **quotes usable 5.6%** (hallucinated price codes in 16/18 cases, totals off 27.5% avg), playbook-cited mitigation **0/6** required cases, duration MAE 25 min, slot accuracy 23.5% (mostly the S1 "no slot" freebies). `results/rung0/` | The trap confirmed: output *sounds* competent and parses perfectly, but prices are fiction, safety advice is uncited improvisation, and 1 in 4 emergencies didn't page anyone. Next: does context alone fix this, or does it need machinery? |
| rung1 | Pasted price book, safety playbook, and calendar into context — "better context" alone. | _pending run_ | _pending_ |
| rung2 | Deterministic safety rules + severity policy after observing baseline triage failures. | _pending run_ | _pending_ |
| rung3 | Replaced pasted docs with tools (price lookup, slots, ML duration model). | _pending run_ | _pending_ |
| rung4 | Clarifying-question policy: info threshold before quoting. | _pending run_ | _pending_ |
| rung5 | Programmatic verifier + one revision round-trip. | _pending run_ | _pending_ |
| rung6 (final) | Customer memory keyed by phone number. | _pending run_ | _pending_ |

Removed experiments, failure modes, and the hot take are recorded here as the
runs complete.
