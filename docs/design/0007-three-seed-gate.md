# Design note 0007 — Three-seed gate and report

- **Status:** chosen
- **Date:** 2026-11-06
- **Slice:** S7 — Three-seed gate and report
- **Related:** `docs/00-brief.md`, `docs/plan.md` S7, ADR 0003, ADR 0004,
  ADR 0006, `docs/results/s6-self-play-diagnostics.md`,
  `src/rlcheckers/evaluation/arena.py`, `src/rlcheckers/training/self_play.py`

## Problem

S7 turns the S6 diagnostic into the milestone gate. The caller gets one
reproducible run that trains three independent seeds, evaluates each final agent
against random and a seeded stochastic greedy baseline, reports per-seed and
aggregate W/D/L, scores, intervals, unique-game counts, per-snapshot learning
curves, and a depth-2 diagnostic, then writes the slice report and the
first-milestone report. It exists now because S6 proved the self-play loop works
but also showed that deterministic baselines and repeated games can overstate
strength; S7 must produce a trustworthy pass/fail record.

## Terms

- **Gate** — the pass/fail decision from three seeds and two baselines. Example:
  mean score ≥ 0.60 vs random and ≥ 0.55 vs stochastic greedy, with no seed
  below 0.50.
- **Unique game** — a distinct opening/colour/opponent-seed combination.
  Example: deterministic greedy gives 10 unique games, so 1,000 games are 100
  repeats; random gives 1,000 unique games.
- **Per-snapshot learning curve** — evaluate each frozen self-play snapshot
  against a fixed baseline. Example: the 1,000-episode snapshot scores 0.745 vs
  random; the 10,000-episode snapshot scores 0.8295.

## Approaches

| Approach | Idea | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|---|
| A — Self-contained `gate` command | One command trains 3 seeds, captures snapshots in memory, evaluates final agents and per-snapshot curves, writes JSON/CSV/plots and the Markdown report. | One caller command; no snapshot files; report tied to the run. | Long-running; re-running the report requires retraining; `train_self_play` needs a small snapshot-observer seam. | A small-N integration test produces the report shape; the full run writes all artifacts and a clear pass/fail. |
| B — Two-stage `train-q` + `gate` from saved artifacts | Training writes Q-tables and snapshots per seed; `gate` reads them, evaluates, and writes the report. | Re-runnable report; clear separation; reproducible from saved artifacts. | Snapshot persistence, per-seed artifact layout, more config/CLI, more scope. | The same report is produced from saved artifacts without retraining; bytes are reproducible. |
| C — Generic `verify-slice` command | A manifest-driven command runs a slice’s checks and writes its report. | Reusable across slices. | Speculative; too much abstraction for one slice; the process says not to build it yet. | Deferred; not needed to prove S7. |

## Recommendation

Choose **A**. It is the smallest end-to-end slice, produces the required report,
and avoids new snapshot persistence. B is the deliberate challenge: it is better
if report iteration or audit needs grow, but it adds a storage and artifact
contract that S6 deliberately deferred. C is the right long-term direction but
should wait until the report shape has stabilized.

Keep the ADR 0003 thresholds for this milestone: mean ≥ 0.60 vs random, ≥ 0.55
vs stochastic greedy, and no seed below 0.50. The S6 pilot suggests the gate is
easy, but the brief fixed these thresholds and the pilot is one seed. Report the
margin and the depth-2 diagnostic; do not move the goalposts after seeing the
result.

## Chosen approach

The author chose **A — self-contained `gate` command**. The author’s reason: keep
this milestone easy to finish and move to the next one. The gate command
comprises training, evaluation, and report writing instead of separating those
steps. The author also chose to **keep ADR 0003** because, even though the
thresholds look easy, that is the gate the next milestone should take on. ADR
0007 records the seeded stochastic greedy baseline required by the S7 plan; the
ADR 0003 thresholds remain unchanged.

## What would change the decision

- Report iteration or audit needs make retraining for every report change too
  expensive; move to B and persist snapshots.
- The in-memory snapshot observer makes `train_self_play` harder to test or
  reason about; move the capture to a separate artifact step.
- The full three-seed run no longer fits the “minutes, not hours” target; reduce
  the per-snapshot diagnostic budget or move to B.
- The gate passes so easily that it no longer distinguishes a working agent from
  a broken one; revisit the thresholds in ADR 0003 before the next milestone,
  not after the reported run.

## Sources

- `docs/00-brief.md` — milestone success criteria and gate thresholds.
- `docs/plan.md` S7 — outcome, acceptance criteria, and the revised diagnostic
  plan.
- ADR 0003 — evaluation protocol, mean-plus-floor gate, and uncertainty.
- ADR 0004 — plot ownership.
- ADR 0006 — self-play snapshot policy.
- `docs/results/s6-self-play-diagnostics.md` — deterministic-baseline and
  learning-curve evidence.
- `src/rlcheckers/evaluation/arena.py` — `play_matchup` and `ArenaResult`.
- `src/rlcheckers/training/self_play.py` — `train_self_play` and snapshot
  records.
