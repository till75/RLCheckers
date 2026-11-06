# First milestone report

- **Date:** 2026-11-06
- **Status:** pass; S7 approved and pushed
- **Brief:** `docs/00-brief.md`
- **Slice report:** `docs/results/s7-three-seed-gate-diagnostics.md`
- **Gate config:** `gate.toml`
- **Gate artifacts:** `docs/results/gate.json`, `docs/results/gate.csv`,
  `docs/results/snapshot_curve.csv`, `docs/results/snapshot_curve.png`,
  `docs/results/q_table_seed_7.json`, `docs/results/q_table_seed_8.json`,
  `docs/results/q_table_seed_9.json`

## Goal

The first milestone was a headless, reproducible experiment showing that a
tabular agent learns to beat two fixed baselines on 5x5 English draughts. The
approved gate uses three training seeds, 1,000 unique games against random and
seeded stochastic greedy, both colours, and a fixed opening suite. The mean
derived score must be at least 0.60 against random and at least 0.55 against
stochastic greedy, with no seed below 0.50 on either baseline.

## Result

The gate passed.

| Metric | Value | Threshold |
|---|---:|---:|
| Random mean | 0.830667 | 0.600000 |
| Random minimum | 0.818000 | 0.500000 |
| Stochastic greedy mean | 0.816833 | 0.550000 |
| Stochastic greedy minimum | 0.800500 | 0.500000 |

| Seed | Table size | Random W/D/L | Random score | Stochastic greedy W/D/L | Stochastic greedy score | Deterministic greedy, 10 unique | Depth-2, 10 unique |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 7,181 | 818/23/159 | 0.829500 | 808/22/170 | 0.819000 | 10/0/0 | 4/0/6 |
| 8 | 7,409 | 832/25/143 | 0.844500 | 817/28/155 | 0.831000 | 10/0/0 | 4/0/6 |
| 9 | 7,388 | 800/36/164 | 0.818000 | 783/35/182 | 0.800500 | 10/0/0 | 4/0/6 |

The per-snapshot curve shows the expected early gain and later plateau. Against
random, the initial empty table scores about 0.515; the first 1,000 episodes
raise each seed to roughly 0.74–0.75; the final scores are 0.805–0.858. Against
stochastic greedy the same pattern holds, with final scores 0.798–0.828. The
full curve is in the slice report and `snapshot_curve.csv`.

## Success criteria

| Brief criterion | Evidence | Result |
|---|---|---|
| Rules: known positions, perft, terminating games | S1–S3 tests; full suite | pass |
| Training: seeded run produces Q-table, metrics CSV, and rising curve | S5/S6 tests; `snapshot_curve.csv` and plot | pass |
| Evaluation: 3 seeds, 1,000 games against random and greedy, both colours, fixed openings | `gate.json`, `gate.csv`; 1,000 unique games per seed per stochastic baseline | pass |
| Gate: mean at least 0.60 vs random and 0.55 vs greedy; no seed below 0.50 | Aggregate table above; `gate.json` `passed: true` | pass |
| Reproducibility: same config and seed reproduce metrics | A8 tests; byte-identical JSON/CSV/Markdown artifacts | pass |
| Diagnosis: inspect the Q-table to explain a learned preference or failure | Q-tables saved per seed; depth-2 diagnostic shows the narrow 4/10 result | pass |
| Workflow: spec, tests first, review, Conventional Commits, docs and diagrams | S7 spec, ADR 0007, TDD commits, README/architecture/plan/state | pass |

## What was built

The project now has the immutable 5x5 rules engine, seeded random play, the
depth-1 greedy baseline, the seeded evaluation arena, tabular Q-learning against
a fixed random opponent, self-play with periodic frozen snapshots, and the
three-seed gate. The gate adds a seeded stochastic greedy baseline, gate
aggregation, per-snapshot learning curves, Q-table/JSON/CSV/plot artifacts, the
slice report, and the `gate` CLI.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | 382 passed, 2 deselected |
| `.\.venv\Scripts\python.exe -m ruff check .` | clean |
| `.\.venv\Scripts\python.exe -m rlcheckers gate --config gate.toml` | pass; random mean 0.830667, stochastic greedy mean 0.816833 |

## Limitations and caveats

- Random and stochastic greedy are weak baselines. The gate is a diagnostic, not
  a general-strength claim.
- Deterministic greedy is 10 unique games per seed, not 1,000 independent games.
  Its 10/0/0 result is a narrow exploit of the depth-1 policy.
- Depth-2 minimax is a reported diagnostic, not part of the pass/fail gate. The
  agent scores 4/10 against it for every seed, so it is not generally strong.
- The per-snapshot curve uses 200 games per snapshot per opponent; it is a
  diagnostic curve, not a second gate.
- The ADR 0003 thresholds are fixed for this milestone. A later milestone may
  revisit them with stronger baselines.
- The gate is a single 3-seed experiment. It does not prove strength against
  unseen opponents or full 8x8 checkers.

## Decision

The first milestone is **pass**. The approved gate passed with margin on both
means and both seed floors, the artifacts are reproducible, the full suite and
lint are clean, and the slice report records the evidence and caveats. S7 is
approved and pushed.

## Follow-up

- The next milestone should use stronger baselines and a broader robustness
  check before claiming general playing strength.
- Revisit the gate thresholds only with evidence from stronger baselines.
