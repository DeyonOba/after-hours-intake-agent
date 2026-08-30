# Eval summary — rung0 (BASELINE: one direct prompt, no machinery)

Agent: `claude-opus-5` · Simulator: `claude-haiku-4-5` · Cases: 18

| Metric | Value |
|---|---|
| cases | 18 |
| parse_ok_rate | 1.0 |
| severity_acc | 0.778 |
| category_acc | 0.944 |
| critical_escalation_recall | 0.75 |
| false_page_rate | 0.0 |
| quote_ok_rate | 0.056 |
| avg_code_f1 | 0.119 |
| avg_total_err_pct | 27.5 |
| hallucinated_code_cases | 16 |
| mitigation_ok_rate | 0.667 |
| refs_valid_rate | 1.0 |
| duration_mae_min | 25.2 |
| duration_ok_rate | 0.5 |
| slot_acc | 0.235 |
| memory_acc | 0.667 |
| avg_turns | 2.89 |
| total_cost_usd | 1.39 |
| wall_minutes | 15.8 |

| Case | Tier | Sev | Cat | Esc | Quote | Mitig | Slot | Parse |
|---|---|---|---|---|---|---|---|---|
| c01_burst_supply | S1 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| c02_sewage_backup | S1 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| c03_gas_smell_hidden | S1 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| c04_ceiling_leak_shutoff_fail | S1 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| c05_no_hot_water_returning | S2 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c06_leak_contained | S2 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c07_only_toilet_blocked | S2 | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ |
| c08_running_toilet | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c09_slow_kitchen_drain | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c10_dripping_faucet | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c11_damp_spot | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c12_disposal_jam | S3 | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| c13_low_pressure_returning | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c14_wh_replace_quote | S4 | ✗ | ✓ | ✓ | ✗ | ✓ | — | ✓ |
| c15_disposal_install | S4 | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c16_recurring_main_returning | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c17_hose_bib | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| c18_wh_noise | S3 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
