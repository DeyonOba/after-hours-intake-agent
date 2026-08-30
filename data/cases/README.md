# Evaluation Cases — Provenance & Label Derivation

18 after-hours intake cases in `cases.json`. Tier mix: 4×S1, 3×S2, 9×S3, 2×S4;
3 cases are returning customers (memory). One required challenging case:
`c03_gas_smell_hidden`.

## Seed sources

- `seed:nyc311` — real complaint rows from the Hugging Face mirror
  [`ctgadget/nyc_311_service_requests`](https://huggingface.co/datasets/ctgadget/nyc_311_service_requests)
  (NYC Open Data 311 / HPD provenance). Pinned rows in `data/seeds/`.
- `seed:diyqa` — plumbing rows (category `plumbing_repair`) from
  [`dipenbhuva/home-diy-repair-qa`](https://huggingface.co/datasets/dipenbhuva/home-diy-repair-qa)
  (synthetic home-repair QA). Pinned rows in `data/seeds/`.
- `authored` — written for coverage the seeds lack (gas-smell hidden danger,
  returning-customer memory cases, quote-only inquiries).

Seeds provide the complaint language and category; the customer simulator
renders them as natural after-hours text messages.

## Severity (S1–S4) derivation

No public dataset carries after-hours dispatch severity, so tiers are derived
with this documented mapping (aligned with how NYC's HPD grades complaint
descriptors, e.g. WATER LEAK is graded HEAVY FLOW vs SLOW LEAK vs DAMP SPOT):

| Seed signal | Tier |
|---|---|
| HEAVY FLOW / active uncontained water / sewage backup / any gas smell | S1 |
| Contained leak, fixture outage in a single-bathroom home, no hot water | S2 |
| SLOW LEAK, DAMP SPOT, running/dripping/slow fixtures, jams, noises | S3 |
| Pure quote/installation inquiries | S4 |

## Answer-key ground truth

- `quote_lines` / `quote_total`: from `data/price_book.json` (documented
  flat-rate assumptions).
- `duration_min`: price-book base duration × modifiers (old fixture ×1.15,
  recurring ×1.10, multi-fixture ×1.25), rounded — the same generative rules
  that produce `historical_jobs.csv`, noise-free.
- `slot_id`: deterministic policy against `data/calendar.json` — S2 takes the
  earliest priority slot; S3/S4 take the earliest free non-priority slot whose
  capacity fits the duration; S1 books nothing.
- `mitigation_refs_any`: playbook step IDs (`data/safety_playbook.md`) of which
  at least one must be cited when mitigation is required.

Keys were authored together with the case and cross-checked by
`eval/scoring.py --selfcheck`, which recomputes totals, durations, and slots
from the source data and fails on any inconsistency.
