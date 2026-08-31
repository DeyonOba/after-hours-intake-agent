# Solution Video Script (≤5:00)

Record screen + voice. Have open: README.md, CHANGELOG.md, a terminal,
`results/rung0/trajectories/c01_burst_supply.json`, and
`results/rung6/trajectories/c03_gas_smell_hidden.json`.

## 0:00–0:40 — The problem (README on screen)

> "A small plumbing company has no dispatcher at 11 PM. A missed burst-pipe
> call is a competitor's job by 11:05 — and even an answered one needs five
> things at once: facts, follow-up questions, urgency triage, a price from the
> flat-rate book, and a slot that fits. I built an after-hours intake agent
> that fills that empty seat, and measured it against an 18-case evaluation
> with machine-checked answer keys."

## 0:40–1:20 — The baseline (rung0 trajectory on screen)

> "The baseline is the brief's canonical one: a single direct prompt. It
> *sounds* great — and it invented billing codes in 16 of 18 tickets. Here it
> is billing 'SUP-LINE-REPL' — a code that doesn't exist — and here, on a
> burst pipe, it decided the emergency was over once the customer shut the
> valve and paged nobody."

Show: rung0 c01 ticket (`escalate_now: false`, fake codes).

## 1:20–2:50 — One realistic execution, start to finish (terminal)

Run live (or replay the committed trajectory if time is tight):

```
.venv/bin/python -m eval.run_eval --config configs/rung6.yaml --cases c03_gas_smell_hidden
```

> "The challenging case: a customer wants a drain quote and mentions a faint
> rotten-egg smell *in passing*. Watch the final agent: the deterministic
> safety floor — plain code, not a prompt — flags the gas signal. The agent
> tells them to evacuate, cites playbook step PB-06, pages the on-call
> plumber, and refuses to quote. The dispatcher, not the model, has the final
> word: every ticket is a draft until a human approves it."

Walk the trajectory: tool calls → safety override → final ticket.

## 2:50–3:50 — The comparison and the changelog (CHANGELOG.md on screen)

> "Same 18 cases, same task spec, seven configurations — each changelog row is
> one command. Better context fixed what the model *knows*: quotes went from 6
> to 78 percent usable. But it didn't move safety judgment at all — escalation
> recall stayed at 75 percent until rung2 added a code-level severity floor.
> That's the change that contributed most: recall went to 100 percent with
> zero false pages, and it stayed there through every later rung."

Point at the rung1 → rung2 rows.

## 3:50–4:30 — The honest experiment + what I removed/kept anyway

> "Not everything helped. Replacing the pasted price table with tools made
> quote totals slightly *worse* on this small corpus — the model had been
> reading the table perfectly. I kept the tools anyway and said so in the
> changelog: they make hallucinated billing codes structurally impossible and
> they're the only architecture that survives a real price book. The ML
> duration model tells the same story: it beat LLM guessing five-fold, but not
> table-reading — until the table can't fit in the prompt."

## 4:30–5:00 — Close

> "Reproduction is a .env file and three commands; scoring is deterministic;
> every claim traces to a committed trajectory. My takeaway: an agent's
> *knowledge* problems die with context and tools — its *judgment* problems
> need rails made of code. Thanks."
