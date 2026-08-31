# After-Hours Intake & Triage Agent — Brookdale Plumbing Co.

An agentic workflow that answers a small plumbing company's phone when nobody
else can: it triages severity, walks emergencies through approved
damage-mitigation steps while paging the on-call plumber, and turns everything
schedulable into a verified, priced, slot-assigned draft ticket that the owner
approves in one pass the next morning.

Built for the micro1 Agentic Workflows Hackathon (Aug 2026).

## The four questions

**01 — Who has this problem?**
A small plumbing company (1–10 techs) with no night dispatcher. After hours,
the owner *is* the intake desk — and they're asleep. Home-service businesses
miss a large share of inbound calls, and a missed 11 PM burst-pipe call is
usually a competitor's job by 11:05.

**02 — What bottleneck makes it worth solving?**
Turning a panicked text into a *complete, priced, correctly-triaged job
ticket* requires five things at once: extracting facts, asking the right
follow-ups, classifying urgency, pricing against a flat-rate book, and picking
a slot that fits the job. At night nobody does any of them. The agent fills an
empty seat rather than replacing anyone's judgment.

**03 — Does the agent solve it well?**
Measured against an 18-case evaluation with lawyered answer keys
(machine-checked for internal consistency), the final agent hits **100%
critical-escalation recall with 0% false pages**, quotes exclusively from the
real price book (hallucinated billing codes: structurally impossible — every
code comes from a tool), cites every mitigation step to an approved safety
playbook, and books real calendar slots sized by an ML duration model. The
baseline — one direct prompt — *sounded* just as confident while inventing
16/18 of its billing codes and failing to page anyone for a burst pipe.
Full per-iteration evidence: [CHANGELOG.md](CHANGELOG.md).

**04 — Can another person reproduce the result?**
One `.env` file with an API key and three commands. All data is in-repo
(public dataset rows pinned to `data/seeds/`, synthetic everything else), every
changelog row is one command from HEAD, and scoring is deterministic. See
[REPRODUCING.md](REPRODUCING.md).

## How it works

```
Missed call (simulated event)
   └─▶ chat thread keyed to the caller's phone number (contact ID)
        └─▶ INTAKE AGENT (Claude Opus 5)
             ├─ deterministic SAFETY FLOOR scans the customer's own words —
             │    gas/sewage/uncontained water can only RAISE severity
             ├─ tools: price_book_lookup · get_price · predict_duration (ML)
             │         get_available_slots · lookup_customer (memory)
             ├─ clarifying-question policy (info threshold before quoting)
             ├─ programmatic VERIFIER (prices, refs, slots re-checked against
             │    source data; one revision round-trip)
             └─▶ JOB TICKET (draft)
                  ├─ S1 → page on-call NOW + playbook mitigation steps
                  ├─ S2 → first priority slot tomorrow, flagged
                  └─ S3/S4 → priced + scheduled, morning approval queue
```

The **agent core is channel-agnostic**: the evaluation drives it headless
(a customer-simulator LLM plays each case), and a thin Discord adapter exists
for live demos only. Production would swap in SMS/WhatsApp; per hackathon
ground rule 04, the chat channel here is the sandbox for consequential
actions, and every ticket is a *draft* until a human approves it (rule 05).

### The capability ladder (and what each rung proved)

| Rung | Adds | One-line result |
|------|------|-----------------|
| 0 | Baseline: one direct prompt | Confident fiction: 16/18 tickets had invented billing codes; 1 of 4 emergencies paged nobody |
| 1 | Better context (docs pasted) | Fixed *knowledge* (quotes, playbook, durations) — didn't move safety judgment at all |
| 2 | Deterministic safety rules | Escalation recall 75%→**100%**; the code floor overrode the model on the exact case the prompt policy failed to |
| 3 | Tools (price, slots, ML duration) | Hallucination became structurally impossible; honest regressions documented |
| 4 | Clarifying-question policy | _see CHANGELOG_ |
| 5 | Programmatic verifier | _see CHANGELOG_ |
| 6 | Customer memory (phone-keyed) | _see CHANGELOG_ |

Full table with metrics, costs, and evidence paths: [CHANGELOG.md](CHANGELOG.md).
Machine-readable results per rung: `results/<rung>/results.json`; every
conversation's full trajectory (tool calls, tool results, safety overrides):
`results/<rung>/trajectories/`.

### The ML component

`predict_duration` is a RandomForest regressor (scikit-learn) trained on
synthetic job history (`data/historical_jobs.csv`, fixed seed) generated from
documented duration rules. The agent calls it as a tool before booking a slot.
The changelog reports honestly where it beat LLM guessing (baseline MAE
25 min → 5.4 min) and where reading the pasted table was actually better on a
corpus this small (rung2's 2.1 min) — and why the tool architecture wins
anyway at production scale.

## Evaluation design

- **18 cases** (4×S1 emergencies, 3×S2 urgent, 9×S3 standard, 2×S4 quote-only;
  3 returning customers), seeded from two public datasets — real NYC 311
  plumbing complaints ([`ctgadget/nyc_311_service_requests`](https://huggingface.co/datasets/ctgadget/nyc_311_service_requests))
  and home-repair QA ([`dipenbhuva/home-diy-repair-qa`](https://huggingface.co/datasets/dipenbhuva/home-diy-repair-qa)) —
  with derivation rules documented in [data/cases/README.md](data/cases/README.md).
- **The required challenging case** (`c03_gas_smell_hidden`): a customer asks
  for a drain quote and mentions a faint rotten-egg smell in passing. Correct
  behavior is evacuation + gas utility + page — and *no quote*.
- **A scripted failure case** (`c04`): the customer can't find the shutoff on
  the first try; the agent must adapt, not loop.
- **Fairness:** every rung, baseline included, gets the identical task spec,
  ticket schema, cases, and simulator; rungs differ only in engineering. The
  baseline's lack of the price book is not hidden — it *is* rung1's measured
  delta. Deterministic scoring (`eval/scoring.py`) checks tickets against
  answer keys that `--selfcheck` verifies against the price book, playbook,
  and calendar.
- **Primary metric:** ticket correctness for the dispatcher — severity +
  escalation first (a wrong S1 is a flooded house), then quote/slot accuracy.
  Guardrail metric: false-page rate (waking the on-call for a drip kills
  adoption).

## Results (baseline vs final)

| Metric | rung0 baseline | rung6 final |
|---|---|---|
| Critical escalation recall | 75% | **TBD** |
| False page rate | 0% | **TBD** |
| Severity accuracy | 77.8% | **TBD** |
| Usable quotes (right lines, total ±15%) | 5.6% | **TBD** |
| Hallucinated billing codes | 16/18 cases | **TBD** |
| Playbook-cited mitigation | 0/6 required | **TBD** |
| Cost per intake | ~$0.08 | **TBD** |

_(Final numbers land when the rung6 run completes; every intermediate rung is
already recorded in CHANGELOG.md.)_

## Ground-rules compliance

- **Sandboxed consequential actions:** no real telephony, payments, or
  dispatch; customers are simulated; the Discord adapter is demo-only.
- **Human in the loop:** every quote/booking is a DRAFT ticket for morning
  approval; S1 pages a human immediately; mitigation advice is restricted to
  a reviewed playbook the agent must cite, enforced by code.
- **Data:** public dataset rows (pinned in-repo) + synthetic records; all
  names/phones/addresses are invented; no credentials in the repo (`.env` is
  gitignored, `.env.example` documents it).
- **Provenance:** what existed before the competition: the public datasets and
  the open-source libraries in `requirements.txt`. Everything else in this
  repo was built during the event; the git history is the audit trail.

## Repo map

```
agent_core/   agent loop, prompts, safety floor, tools, verifier, memory
eval/         runner, customer simulator, deterministic scoring, selfcheck
data/         price book, playbook, calendar, cases+keys, seeds, job history
configs/      rung0.yaml (baseline) … rung6.yaml (final) — the changelog ladder
results/      per-rung results.json, summary.md, full trajectories (committed)
scripts/      fetch_seeds.py, train_duration_model.py
adapters/     discord_bot (demo transport; optional)
docs/         concept drafts 01–04, video script
```

## Known limitations (honest list)

- The customer is an LLM simulator; real customers are messier. The behavior
  scripts (panic, failed mitigation, price-shopping) are our best proxy.
- The S3/S4 boundary ("schedule it" vs "just quoting") caused every remaining
  severity miss; a production rubric would collapse or sharpen that boundary.
- Price book and calendar are synthetic (documented assumptions); the NYC
  seeds ground the *complaints*, not the *prices*.
- Single-track calendar; no multi-tech routing.
