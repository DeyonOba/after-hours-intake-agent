# Draft 3 — Feasibility Check & Merged Concept

> Merges [Draft 1](01-intake-agent-draft.md) (intake-to-dispatch engine) with
> [Draft 2](02-after-hours-user-stories.md) (after-hours Discord flow).

## Merged pitch (one paragraph)

**The After-Hours Intake & Triage Agent.** When a small plumbing company's
phone goes unanswered at night, the missed call routes the customer to a chat
agent (Discord in this build, standing in for SMS/WhatsApp). The agent
identifies the customer by phone-number ID, triages severity, walks emergencies
through approved damage-mitigation steps while paging the on-call plumber, and
turns everything schedulable into a verified, priced, slot-assigned draft
ticket. The owner opens the shop to a triaged queue and approves with one pass
— the human gate through which every consequential action flows.

The merge strengthens Draft 1's story: after hours there is *no dispatcher to
replace* — the agent covers an empty seat, and the morning review queue makes
human oversight structural rather than bolted on.

## Feasibility, piece by piece

| Piece | Verdict | Notes |
|-------|---------|-------|
| Discord bot (threads per customer, on-call role ping) | **Feasible, hours** | discord.py / discord.js; private thread per contact ID; @on-call mention = the page. |
| Missed call → SMS redirect | **Simulate** | No real telephony (Twilio = accounts, cost, irreproducible). A mock "missed-call event" script starts the flow. State this plainly in the README. |
| Phone-number ID as primary key | **Feasible, trivial** | Hash the number → contact ID; keys the memory store and ticket records. Never store raw numbers in the repo (ground rule 08); eval uses synthetic numbers. |
| Severity triage + rule layer | **Feasible** | Deterministic safety rules + LLM classification beneath them. |
| De-escalation playbook | **Feasible with care** | Steps must come only from an approved, in-repo homeowner-safety playbook (cited per step). Gas → evacuate + call utility, full stop. |
| Human handoff by severity | **Feasible** | S1 page / S2 flag / S3-S4 queue. False-page rate becomes a metric. |
| ML duration model, price book, verifier, memory | **Unchanged from Draft 1** | All still apply; the after-hours frame adds cases, not complexity. |

## The one architectural decision that makes this work

**The eval must not run through Discord.** Judges reproducing 15–20 multi-turn
cases through a live Discord server would be slow, flaky, and dependent on bot
tokens — a direct hit to the 15-pt Reproducibility criterion.

Therefore:

```
                    ┌────────────────────────────┐
   Eval harness ───▶│   AGENT CORE (headless)    │◀─── Discord adapter (demo)
   (customer        │ triage · rules · tools ·   │     threads, pings,
    simulator,      │ verifier · memory · ML     │     human handoff UI
    15–20 cases)    └────────────────────────────┘
```

- The **agent core** is channel-agnostic. The eval harness drives it directly
  with the customer-simulator agent — fully scripted, one command, no tokens.
- The **Discord adapter** is a thin transport used for the live demo and the
  video. Optional setup guide for judges who want to try it interactively.
- README framing (honest and rubric-aligned): production channel would be
  SMS/WhatsApp; Discord is the **sandbox/simulation** for consequential actions
  and human handoff — exactly what ground rule 04 asks for. The adapter pattern
  proves the core is transport-independent.

## Realism objection, pre-answered

"Would a real customer join a Discord server?" — Mostly no, and the README
should say so. Discord is the demo transport; the produced artifact (chat →
mitigation → page → ticket → morning approval) is channel-independent. This
turns a weakness into an architecture point.

## What the merge adds to the evaluation

New metrics on top of Draft 1's ticket-correctness/quote-accuracy/time/cost:

| Metric | Why it matters |
|--------|----------------|
| Severity classification accuracy | The core triage claim |
| Critical escalation recall | Must be **100%** — a single miss fails the safety story |
| False-page rate | Waking Rita for a drip = the product fails socially |
| Mitigation playbook adherence | Every de-escalation step traceable to the approved playbook |
| Time-to-first-response | The "missed call = lost customer" headline metric |

Case set update: keep ~15–20 total. Mix: 4–5 S1 (incl. gas-smell hidden-danger
case and a failed-de-escalation case), 3–4 S2, 5–6 S3, 2–3 S4, and 2–3
returning-customer cases that exercise memory.

## Updated iteration ladder (changelog spine)

1. **Baseline:** single prompt handling the whole conversation — misquotes,
   never asks questions, and (predictably) mishandles a safety case.
2. **+ Deterministic safety rules + severity tiers** → critical escalation
   recall hits 100%; hot-take material ("safety triage cannot be a prompt").
3. **+ Tools:** price book, slots, ML duration model → quote/slot errors drop.
4. **+ Clarifying-question policy** (info threshold before quoting) → field
   completeness jumps.
5. **+ Verifier agent** (re-checks quote lines + playbook citations) →
   hallucinated line items and uncited advice go to zero.
6. **+ Memory** (phone-number-ID keyed) → returning-customer case scores jump.
7. **Discord adapter** — no metric change expected; logged as the
   productization step proving transport independence.

## Risks & cuts (deadline: Aug 31, 6 PM UTC)

- **Scope risk is the only real risk.** Build order: eval harness + cases →
  agent core rungs 1–6 → README/changelog → video → Discord adapter **last**.
  If time runs out, a merged concept with a mocked chat UI still scores on
  90 of 100 points; a beautiful Discord bot with a thin eval does not.
- Cut US-9 (DIY deflection) first if squeezed; it's optional flavor.
- Keep the safety playbook short (5–8 steps) and quotable; breadth adds risk,
  not points.
