# Improvement Changelog

The story of the solution, one measured iteration at a time. Every row is
reproducible from HEAD: `python -m eval.run_eval --config configs/<rung>.yaml`.
Evidence: `results/<rung>/results.json` and `results/<rung>/summary.md`.

**The arc in one line:** a baseline that *sounded* right while billing fiction
→ context fixed what the agent knows → code fixed what it decides → tools made
hallucinated billing structurally impossible → verification and memory closed
the last gaps. Net: usable quotes 5.6%→100%, escalation recall 75%→100%,
false pages 0% at both ends.

| Stage | What we tried and why | Evidence | Decision / learning |
|-------|----------------------|----------|---------------------|
| rung0 (baseline) | One direct prompt with basic instructions — the brief's canonical baseline. | 18 cases, $1.39: parse 100%, severity 77.8%, category 94.4%, **critical escalation recall 75%** (missed a burst-pipe S1), false pages 0%, **quotes usable 5.6%** (hallucinated price codes in 16/18 cases, totals off 27.5% avg), playbook-cited mitigation **0/6** required cases, duration MAE 25 min, slot accuracy 23.5% (mostly the S1 "no slot" freebies). `results/rung0/` | The trap confirmed: output *sounds* competent and parses perfectly, but prices are fiction, safety advice is uncited improvisation, and 1 in 4 emergencies didn't page anyone. Next: does context alone fix this, or does it need machinery? |
| rung1 | Pasted price book, safety playbook, and calendar into context — "better context" alone. | 18 cases, $1.58: hallucinated codes 16→**0**, usable quotes 5.6%→**77.8%** (F1 0.94), playbook-cited mitigation 0/6→**6/6**, duration MAE 25→**8.6 min**, slots 23.5%→**76.5%**. But severity accuracy (77.8%) and **escalation recall (75%) did not move at all**. `results/rung1/` | Context fixes what the model *knows*, not what it *decides*. The burst-pipe emergency still paged nobody. Kept; safety needs a different mechanism. |
| rung2 | Deterministic safety rules (code-level severity floor) + severity policy text, after rung1 proved context can't fix triage. | 18 cases, $1.54: **critical escalation recall 75%→100%**, severity 77.8%→88.9%, quote total err 13.9%→2.8%, duration MAE 2.1 min, false pages still 0%. Trajectory evidence: on c01 the model — despite the policy being in its prompt — downgraded to S2 after the customer contained the leak; the code floor forced S1 + page + PB-02 (`results/rung2/case_scores/c01_burst_supply.json`, safety_overrides). One transient API timeout on c01 was retried and documented. | The prompt asked nicely; the rules layer insisted. Safety triage cannot be an LLM judgment call — deterministic floors only ever *raise* severity, so they cost nothing on the 14 non-emergency cases (false pages 0%). Remaining misses are only the S3/S4 boundary (c14, c15). |
| rung3 | Replaced pasted docs with tools (price lookup, slots, ML duration model). | 18 cases, $2.71: hallucinated codes structurally impossible (1→**0**; every code now comes from a tool), code F1 0.94→**0.96**, escalation recall stays **100%**, severity 88.9%. Honest regressions: quote total err 2.8%→9.9% (c12 quoted the right line but wrote total=0 after a successful DIY fix; c16 re-quoted a kitchen snake instead of main-line clearing — it lacks the tech's history note), duration MAE 2.1→5.4 min (the RF model approximates the rule the pasted table stated exactly), cost/case up ~75% from tool round-trips. `results/rung3/` | Tools buy *integrity* (codes can't be invented) and *scale* (a real price book/calendar won't fit in a prompt), not accuracy on a toy corpus — the pasted table was already accurate at this size. Kept for the architecture; its two residual error types are exactly what rung5 (verifier: line/total consistency) and rung6 (memory: job history) exist to fix. |
| rung4 | Clarifying-question policy: info threshold + safety screeners before quoting. | 18 cases, $3.91: the agent actually interviews now (avg turns 2.28→4.22); usable quotes 83.3%→88.9%; escalation recall stays 100%. Honest regressions: slot accuracy 82.4%→64.7% and duration MAE 5.4→10.9 min — the richer conversations surfaced customer *preferences* that pulled bookings off the deterministic slot policy ("afternoon works better"), and on c01 the agent now tried to book a morning repair after containing the emergency. `results/rung4/` | Intake discipline without booking discipline just gives the model more reasons to improvise. The new failure shapes are precisely verifier work — next rung. |
| rung5 | Programmatic verifier + one revision round-trip — then two real bugs found and fixed. | 18 cases, $4.04. **Bug 1 (ordering):** as first shipped, the safety floor ran *after* verification — on c01 the floor raised S2→S1 post-verify, leaving an S1 ticket carrying a repair quote and a slot the verifier never saw. Fixed: floor runs before verification and re-runs after revision; trigger-relevant cases re-run (pre-fix log preserved: `results/run-logs/rung456-pre-orderfix.log`, which also records this project's only false page — see failure modes). **Bug 2 (the model argues with policy):** the revision round-trip returned the *same* quote+slot on the S1 — verifier issues identical before and after revision (`results/rung6/trajectories/c01_burst_supply.json` shows the standoff). Added mechanical fixes: code strips S1 repair lines/slots, resets prices to the book, recomputes totals, drops invalid refs. False pages 0%, recall 100%, quotes 88.9%. | When the model's (reasonable!) real-world judgment conflicts with a business rule, one more prompt doesn't win the argument. Checks that are mechanical must be *enforced* mechanically — ask once, then fix in code. |
| rung6 (final) | Customer memory keyed by phone number (the missed-call contact ID). | 18 cases, $4.23: **usable quotes 100%** (avg total error **0.0%**), category 100%, escalation recall **100%**, false pages **0%**, memory 100%. Memory's measured effect: c13 quoted the cartridge from the March visit note instead of a re-diagnostic (line F1 0.667→1.0), and c16 quoted main-line clearing + camera per the tech's recurrence note instead of a third kitchen snaking (the exact repeat-billing mistake that was burning that customer). `results/rung6/` | Memory didn't make the agent smarter — it changed *which answer is correct*. That's why it has to be a tool reading real records, not a prompt suggestion. Residual misses are label-boundary debates, listed below. |

## What still misses, and why we're not hiding it

- **S3-vs-S4 boundary (c12, c14, c15):** all three remaining severity misses.
  c12: DIY fixed the disposal mid-chat, agent filed S4-inquiry, our key says
  S3 — defensible either way. c14/c15 blur "quote request" vs "ready to book."
  Zero safety impact; a production rubric would collapse the boundary.
- **c16 duration/slot:** the agent predicted duration for a snaking instead of
  main-line clearing (57 vs 132 min) and booked a too-small slot; the quote
  itself was right. Tool-argument correctness is the next verifier extension.
- **c14 duration "error":** the agent applied the old-fixture modifier to a
  14-year-old heater (272 min); our key said 240. The agent arguably
  out-reasoned the answer key. Keys were frozen before runs, so it stays a
  recorded miss.

## Main failure mode

**Model-policy disagreement.** The dangerous failures weren't hallucinations —
context and tools eliminated those early. They were cases where the model's
plausible judgment ("the leak is contained, the emergency is over, let's book
the repair") contradicted the business's dispatch policy, *survived a policy
prompt, a severity floor, and an explicit revision request*, and only stopped
at code-level enforcement. Secondary mode: the deterministic floor itself can
misfire — one false page in ~130 case-runs (pre-fix c17: the customer said
"sprays from the handle" about a hose bib that only leaks when open; the
keyword fired out of context). Direction: keep hard floors for unambiguous
signals (gas, sewage), add one confirming question for borderline water
triggers.

## Hot take

Context and tools fix what an agent **knows**. They never fixed what it
**decides**. Every point of safety improvement in this project came from code
— the severity floor, the programmatic verifier, the mechanical fixes — and
none of it cost a single false page. If a check matters, don't prompt it,
enforce it: the model can argue with a revision request; it cannot argue with
code.
