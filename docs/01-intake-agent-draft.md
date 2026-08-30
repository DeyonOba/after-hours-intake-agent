# Draft 1 — Intake-to-Dispatch Agent for a Small Plumbing Company

> Original concept draft (saved 2026-08-30). Challenge: micro1 Agentic Workflows
> Hackathon (HackerEarth, Aug 28 – Aug 31 2026, solo). Scoring: Agent Solution &
> Engineering 30 / End-to-End Quality 20 / Problem & User Value 15 / Measured
> Improvement 15 / Reproducibility 15 / Hot Take 5.

## The bottleneck map in plumbing services

1. **Intake and quoting.** Home-service businesses miss ~25–40% of inbound calls
   (owner/tech is under a sink); a missed call is usually a lost job worth
   $150–500+. Answered calls still produce vague tickets ("water heater making a
   noise") → wrong-tech dispatch, wrong parts on the truck, evenings spent
   writing quotes.
2. **First-time fix rate.** Tech arrives without the right part because intake
   didn't extract model/symptom details → second truck roll, roughly doubling
   job cost.
3. **Urgency triage.** "Burst pipe, shut the water off now" vs "drip that can
   wait a week", especially after hours. Misclassifying either direction costs
   money or trust.
4. **Job documentation / invoicing lag.** Sparse notes → disputed invoices, no
   usable job history.

**Chosen bottleneck: #1 (intake)** — it subsumes #2 and #3 (parts anticipation
and urgency are fields on a good ticket), it's where the most revenue leaks,
and it's fully evaluable with synthetic cases and zero infrastructure.

## Four-question framing

- **Who has this problem?** A small plumbing company (1–10 techs) with no
  full-time dispatcher. The owner is the intake desk, the estimator, and the
  scheduler — and does all three badly while physically on jobs.
- **What bottleneck makes it worth solving?** Converting a messy customer
  message into a complete, priced, correctly-triaged job ticket requires five
  simultaneous skills: extracting facts, asking the right clarifying questions,
  classifying urgency, pricing against a flat-rate book, and picking a slot
  that matches job duration. Humans do this inconsistently and slowly; missed
  or botched intake is directly lost revenue.
- **Does the agent solve it well?** The agent conducts the intake conversation,
  asks targeted clarifying questions, and produces a signable job ticket:
  urgency tier, job category, likely parts, draft flat-rate quote, proposed
  schedule slot, and a customer confirmation message. **Nothing is sent until a
  human approves the ticket** (satisfies ground rules 04/05 natively).
- **Can another person reproduce it?** Everything is synthetic and in-repo:
  case set, price book, scoring script, one command runs baseline + agent +
  eval.

## Where the ML fits (ML as a tool inside the agentic workflow)

- Small classical model (sklearn regressor trained on a synthetic "historical
  jobs" table) that predicts **job duration** from job type + symptoms +
  property attributes. Changelog entry: "LLM guessed durations (high MAE) →
  replaced with trained regressor as a tool → schedule-slot accuracy jumped."
- Safety escalation stays a **deterministic rule layer** (gas smell, sewage
  backup, active flooding → escalate, never quote). The contrast "we tried
  letting the LLM triage safety and replaced it with rules" is a ready-made
  hot take.

## Evaluation design

- **15–20 synthetic intake cases**: realistic customer messages, each with a
  hidden "full truth" and a validated answer key (urgency tier, category,
  parts, price from the book, duration). Prices based on a public flat-rate
  guide or documented regional averages.
- **Customer-simulator agent** holds each case's hidden facts; intake agent may
  ask up to N clarifying questions. Makes multi-turn intake evaluable and
  counts as purposeful orchestration.
- **Required challenging case**: customer casually mentions a faint gas smell
  while asking about a slow drain → correct output is escalation, not a quote.
  Safety-escalation recall must be 100%.
- **Metrics table**: primary = ticket correctness (% key fields right, quote
  within ±15%); plus human time per intake and cost per task. Baseline = one
  direct prompt with basic instructions (explicitly a valid baseline per the
  brief).

## Iteration ladder (changelog structure)

1. **Baseline:** single prompt → confident but wrong quotes, never asks
   questions.
2. **+ Tools:** price-book lookup, schedule-slot lookup, ML duration model →
   pricing/scheduling errors drop.
3. **+ Clarifying-question policy:** agent must reach an information threshold
   before quoting → field completeness jumps.
4. **+ Verifier agent:** independently re-checks every quote line against the
   price book and runs safety rules → hallucinated line items go to zero.
5. **+ Memory:** returning-customer cases (equipment installed last year, known
   house quirks) where memory measurably changes the answer — 2–3 such cases in
   the eval so the gain shows in numbers.

Each rung is a distinct capability from the brief's own list (tools,
verification, memory, orchestration), each with a measurable delta.

## Deliberately out of scope

- **Photo-based part identification** — strongest ML story in plumbing, but
  sourcing a labeled photo set with ground truth in the time left is too
  risky. Mention as future work.
- **Agent as emergency responder** — emergency handling limited to "escalate to
  a human immediately + standard shut-off-the-main guidance" to stay clean on
  ground rule 05.

## Timing constraint

Challenge closes **Aug 31, 6:00 PM UTC**. Everything must fit ~1 day: build,
eval, changelog, reproduction guide, trajectories, ≤5-min video.
