# Draft 4 — Repo Design, Baseline Specification, Datasets & References

> Status: **design pending approval** (Round 1 decisions below). Nothing here is
> implemented yet; this document is the approval artifact.

## Round 1 decisions (awaiting user approval)

| # | Decision | Recommendation | Status |
|---|----------|----------------|--------|
| 1 | Stack | Python 3.11+ (sklearn, anthropic SDK, discord.py) | PENDING |
| 2 | Agent loop | Anthropic SDK Tool Runner (`client.beta.messages.tool_runner`, `@beta_tool`) | PENDING |
| 3 | Models | `claude-opus-5` for intake agent + verifier; `claude-haiku-4-5` for customer simulator | PENDING |
| 4 | Rung reproducibility | Feature-flag configs (`configs/rung0.yaml` … `rung6.yaml`), one runner command per changelog row | PENDING |

## Repo layout

```
frontier_engineering_challenge_2026/
├── README.md               # four-question framing, setup, reproduction guide
├── CHANGELOG.md            # Improvement Changelog (top-level, one entry per rung,
│                           #   each tied to a committed eval result)
├── docs/                   # drafts 01–04 (this file), decision log
├── agent_core/
│   ├── agent.py            # intake agent (tool runner loop)
│   ├── prompts.py          # system prompts incl. the rung0 baseline prompt
│   ├── tools.py            # price book lookup, slots, duration model
│   ├── safety.py           # deterministic rule layer (severity + hard escalations)
│   ├── verifier.py         # quote + playbook-citation verifier
│   └── memory.py           # contact-ID keyed store
├── eval/
│   ├── run_eval.py         # `python -m eval.run_eval --config configs/rungN.yaml`
│   ├── simulator.py        # customer simulator (LLM, holds hidden case facts)
│   └── scoring.py          # deterministic scoring vs answer keys
├── data/
│   ├── seeds/              # pinned snapshots of upstream dataset rows (committed)
│   ├── cases/              # ~18 cases + answer keys + derivation notes (README)
│   ├── price_book.json     # flat-rate price book (documented assumptions)
│   ├── safety_playbook.md  # approved homeowner mitigation steps, citable IDs
│   └── historical_jobs.csv # synthetic history that trains the duration model
├── configs/
│   ├── rung0.yaml          # ← BASELINE (see spec below)
│   └── rung1..6.yaml       # capabilities added stepwise
├── adapters/discord_bot/   # transport adapter, built LAST (demo only)
├── scripts/                # fetch_seeds.py, train_model.py, mock_missed_call.py
└── results/                # eval outputs per rung, committed as changelog evidence
```

## Baseline specification — rung0, "the naive answering service"

The brief's own canonical baseline: **"one direct prompt with basic
instructions."** Deliberately very simple — it either partially solves the task
or fails outright, and every later rung must justify itself against it with
numbers.

### What it is

- **One model, one system prompt (~8 lines), zero machinery.** Per customer
  turn, a single `messages.create` call. No tools, no price book, no safety
  playbook, no deterministic rules, no clarifying-question policy, no verifier,
  no memory, no structured-output enforcement.
- **Same task, same channel, same cases** as the full agent: it converses with
  the customer simulator under the same max-turn budget and must end by
  emitting a job ticket as JSON (severity, category, mitigation advice, quote
  lines, total, slot, escalate flag). Task parity is what makes the comparison
  fair.
- **Prompt sketch** (final text lives in `agent_core/prompts.py`):

  > You are the after-hours assistant for {company}, a small plumbing company.
  > A customer has reached you because no one answered the phone. Help them:
  > assess how urgent their problem is, give practical advice, and when
  > appropriate provide a price quote and propose an appointment time. When
  > the conversation ends, output a JSON job ticket with fields: severity
  > (S1–S4), category, mitigation_advice, quote_lines, total, slot, escalate.

- **Ticket parsing is tolerant** (regex-extract the JSON block); an
  unparseable ticket scores its fields as missing rather than crashing the
  harness. Format drift is itself a baseline failure mode worth measuring.

### Resource difference vs the final solution (per the brief's fairness rule)

The baseline has **no access to the price book or playbook documents**. This is
intentional and documented rather than hidden: rung1 adds exactly those
documents as pasted context ("better context") with no other change, so the
resource gap is converted into the first measured iteration instead of an
unexplained advantage. From rung1 onward, baseline-vs-solution differences are
pure engineering (rules, tools, policy, verification, memory).

### Predicted failure modes → the metric that will expose each

| # | Failure mode | Why it happens | Metric that catches it |
|---|--------------|----------------|------------------------|
| 1 | Invented prices / hallucinated line items | No price book, but the prompt asks for a quote | Quote error (MAPE), hallucinated-line count |
| 2 | Quotes immediately without asking anything | No question policy; single-pass habit | Field completeness, category accuracy |
| 3 | Severity misclassification both directions | Vibes-based triage | Severity accuracy, false-page rate |
| 4 | Misses the buried gas-smell danger signal | No deterministic rule layer | Critical escalation recall (< 100%) |
| 5 | Generic or unsafe DIY advice | No approved playbook to cite | Playbook adherence = 0 by construction |
| 6 | Re-interrogates returning customers | No memory | Returning-customer case scores |
| 7 | Malformed or missing ticket JSON | No structured enforcement | Parse-failure rate |

### What it will still get right (the "partially solves" part)

It will sound helpful, comfort the customer, produce a plausible ticket shape,
and probably land the right category on easy S3 cases. That is exactly the trap
the changelog dismantles: output that *looks fine in isolation* while the
numbers show wrong prices, wrong severities, and a missed safety signal.

## Rung ladder (revised — context split out as its own rung)

| Rung | Adds | Capability class | Primary expected delta |
|------|------|------------------|------------------------|
| 0 | Baseline: single prompt | — | Starting point |
| 1 | Price book + playbook pasted into context | Better context | Quote error ↓, adherence > 0 |
| 2 | Deterministic safety rules + severity tiers | Verification (rules) | Critical escalation recall → 100% |
| 3 | Tools: price lookup, slots, ML duration model | Better tools | Hallucinated lines ↓, slot accuracy ↑ |
| 4 | Clarifying-question policy (info threshold) | Context acquisition | Field completeness ↑ |
| 5 | Verifier agent (quote lines + playbook citations) | Verification (agent) | Residual quote errors → ~0 |
| 6 | Memory keyed by contact ID | Memory | Returning-customer cases ↑ |

## Dataset selection (evaluation case seeds)

**Requirement:** open dataset of user complaints, plumbing-focused, with
usable labels. Searched Hugging Face (hub API + datasets-server, 2026-08-30).

### Findings

| Candidate | What it is | Verified contents | Verdict |
|-----------|-----------|-------------------|---------|
| `dipenbhuva/home-diy-repair-qa` (HF) | 4,000 synthetic home-repair Q&A rows | **804 rows** with `category=plumbing_repair`; fields: user-voiced `question`, `equipment_problem`, reference `answer`, `steps`, `safety_info` | **Selected — primary seed** |
| `ctgadget/nyc_311_service_requests` (HF) | 5,000-row mirror of real NYC 311 complaints | Literal `PLUMBING` complaint_type rows (descriptors BASIN/SINK, TOILET, BATHTUB/SHOWER) + `WATER LEAK` rows with severity-graded descriptors (SLOW LEAK, DAMP SPOT, HEAVY FLOW); resolution_description present | **Selected — secondary seed (real-world grounding)** |
| NYC Open Data Socrata API (canonical 311 / HPD) | Millions of real complaints incl. official emergency classifications | **HTTP 403 from our network** (verified from two paths) | Rejected as a runtime dependency; cited as provenance for the mirror |
| `taptwicemedia/us-plumbing-ai-visibility-2026` | AI-visibility SEO study of plumbing businesses | Not complaints | Rejected |
| `Bikram323/plumbingDiagnosis` | Image dataset | No text complaints | Rejected |
| Generic complaint sets (`hpe-ai`, `hblim`, CFPB-style) | Finance/billing domains | Wrong domain | Rejected |

No open dataset provides exactly our target label set (S1–S4 after-hours
dispatch severity + quote + slot), so per the fallback plan we use
**relatively-similar datasets as seeds** and derive the remaining labels.

### Derivation pipeline (documented, reproducible)

1. `scripts/fetch_seeds.py` pulls the selected rows from both datasets via the
   HF datasets-server API and pins them to `data/seeds/` (committed — judges
   never need network access to the sources).
2. Case construction (mapping committed in `data/cases/README.md`):
   - **S1/S2 cases** ← NYC `WATER LEAK`/`PLUMBING` rows; severity derived from
     the descriptor grade (HEAVY FLOW → S1, SLOW LEAK/DAMP SPOT → S3, fixture
     outage → S2) — a documented mapping, aligned with HPD's published
     emergency/non-emergency complaint conventions.
   - **S3/S4 cases** ← DIY-QA plumbing rows; the `question` field seeds the
     customer's opening message; `safety_info`/`steps` ground the reference
     mitigation guidance in the answer key.
   - The gas-smell hidden-danger case and 2–3 returning-customer (memory)
     cases are authored, marked `origin: authored`.
3. Every case file records its seed row ID (`origin: hf://dataset/row`),
   the hidden facts for the simulator, and the answer key (severity, category,
   price-book lines, duration, required escalation, reference mitigation).
4. Quote/duration ground truth comes from our `price_book.json` — no open
   dataset carries quotes; the price book documents its assumptions.

**Honesty note for the README:** `home-diy-repair-qa` is itself synthetic
(LLM-generated); NYC 311 rows are real complaints but written as terse
categories rather than conversational messages. The simulator renders seeds as
natural after-hours messages; the transformation script and prompts are
committed, so the whole path from public seed → eval case is auditable.

## References

### Challenge
- micro1 Frontier Engineering Challenge 2026 (HackerEarth): https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/
- Challenge brief PDF: `micro1 - First Hackathon97ce7c5.pdf` (repo root) — rubric, ground rules, deliverables, baseline/changelog requirements

### Datasets
- Home DIY Repair QA (primary seed): https://huggingface.co/datasets/dipenbhuva/home-diy-repair-qa
- NYC 311 service requests mirror (secondary seed): https://huggingface.co/datasets/ctgadget/nyc_311_service_requests
- Canonical provenance (not a runtime dependency; API returned 403 from our network 2026-08-30):
  - NYC 311 Service Requests 2010–present: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9
  - NYC HPD Housing Maintenance Code Complaints and Problems: https://data.cityofnewyork.us/Housing-Development/Housing-Maintenance-Code-Complaints-and-Problems/ygpa-z7cr
- HF datasets-server API (seed fetching): https://huggingface.co/docs/datasets-server

### APIs, SDKs, libraries
- Anthropic Claude API docs: https://docs.claude.com/ — models used: `claude-opus-5` (agent/verifier, adaptive thinking), `claude-haiku-4-5` (customer simulator); pricing Opus 5 $5/$25 per MTok, Haiku 4.5 $1/$5 (verified 2026-08-30)
- Anthropic Python SDK (tool runner, `@beta_tool`): https://github.com/anthropics/anthropic-sdk-python
- scikit-learn (duration regressor): https://scikit-learn.org/
- discord.py (demo adapter only): https://discordpy.readthedocs.io/

### Claims to source-check before the final README
- "25–40% of calls to home-service businesses go unanswered" — industry-blog
  figure; find a citable primary source or soften the claim.
- Average plumbing job value ($150–500+) — same treatment.
