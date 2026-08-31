# Solution Video Script (≤5:00)

**Visuals: the slide deck** — `docs/slides.html` (open locally in a browser, or
the published copy; ← → to navigate, F11 for fullscreen). Record the deck
full-screen with voiceover; optionally switch to a terminal for the live case.

## 0:00–0:35 · Slides 1–2 — the problem

> "A small plumbing company has no dispatcher at 11 PM. A missed burst-pipe
> call is a competitor's job by 11:05 — and even an answered one needs five
> things at once: facts, follow-ups, urgency triage, a price from the
> flat-rate book, and a slot the job fits. I built an after-hours intake agent
> that fills that empty seat, and measured it on an 18-case evaluation with
> machine-checked answer keys."

## 0:35–1:10 · Slide 3 — the baseline

> "The baseline is the brief's canonical one: a single direct prompt. It
> *sounds* great — and it invented billing codes in 16 of 18 tickets. This is
> a real ticket: 'SUP-LINE-REPL', 'CREDIT-CAM' — codes that don't exist — and
> on a burst pipe it decided the emergency was over once the customer shut the
> valve, and paged nobody."

## 1:10–1:40 · Slide 4 — architecture

> "The design puts rails around the model's judgment: a deterministic safety
> floor in code, tools for prices, slots and an ML duration model, a
> programmatic verifier with mechanical enforcement, memory keyed to the
> phone number — and a human gate: every ticket is a draft until the owner
> approves it. Emergencies page a human immediately."

## 1:40–2:30 · Slide 5 — one realistic execution (the gas trap)

Optional: run it live in a terminal instead of the slide —
`.venv/bin/python -m eval.run_eval --config configs/rung6.yaml --cases c03_gas_smell_hidden`

> "The required challenging case: a customer wants a drain quote and mentions
> a faint rotten-egg smell *in passing*. The safety floor — plain code
> scanning the customer's own words — fires on the gas signal. The agent tells
> them to evacuate, citing playbook step PB-06, pages the on-call plumber, and
> refuses to quote. The baseline happily quoted the drain."

## 2:30–3:10 · Slides 6–7 — the ladder and the change that mattered

> "Same 18 cases, same task spec, seven configurations — every changelog row
> is one command. Better context fixed what the model *knows*: quotes jumped
> from six to seventy-eight percent usable. It didn't move safety judgment at
> all. Escalation recall sat at 75 percent until rung 2 added a code-level
> severity floor — then it went to 100 and stayed there. False pages: zero,
> at every rung."

## 3:10–3:50 · Slide 8 — the best bug

> "The best bug of the project: the model *argues with policy*. On the
> contained burst pipe it kept insisting — reasonably! — on booking the
> morning repair. The verifier flagged it; the revision came back with the
> same quote. It only stopped at mechanical enforcement: code strips what
> policy forbids. The standoff is preserved verbatim in the committed
> trajectory."

## 3:50–4:20 · Slide 9 — honest experiments

> "Not everything helped. Tools made quote totals slightly worse on a corpus
> this small — the model had been reading the pasted table perfectly. I kept
> them and said so in the changelog: they make invented billing codes
> structurally impossible. The ML duration model beat guessing five-fold, not
> table-reading. And the safety floor itself misfired once in about 130 runs —
> that's in there too."

## 4:20–4:45 · Slides 10–11 — results and reproduction

> "End to end: escalation recall 75 to 100 percent, usable quotes 5.6 to 100
> percent with zero total error, hallucinated codes eliminated structurally,
> about 24 cents per intake against a $150-to-500 job saved. Reproduction is a
> .env file and three commands; scoring is deterministic; every claim traces
> to a committed trajectory."

## 4:45–5:00 · Slide 12 — close

> "My takeaway: context and tools fix what an agent knows. They never fixed
> what it decides. If a check matters, don't prompt it — enforce it. Thanks."
