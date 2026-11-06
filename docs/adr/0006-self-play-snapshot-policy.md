# ADR 0006 — Self-play snapshot policy

- **Status:** accepted
- **Date:** 2026-11-05
- **Deciders:** author, opencode
- **Related:** ADR 0002, ADR 0003, ADR 0005, `docs/00-brief.md`,
  `docs/plan.md` S6, `docs/design/0006-self-play-snapshots.md`

## Context

S5 trained a tabular Q-agent against a fixed random opponent and evaluated the
final greedy agent through the S4 arena. That diagnostic proved the Q-update and
kept the comparison stable. S6 must remove the fixed training opponent and train
through self-play against periodic snapshots. Self-play is non-stationary: the
opponent changes when a snapshot is refreshed, so the Q-value target moves. A
careless policy can collapse, oscillate, or forget. The fixed baselines must
remain the scoreboard even when the training opponent is no longer fixed.

The S6 plan requires a snapshot policy every N episodes, records the opponent
snapshot and evaluation metrics, writes a Q-table, config, CSV, and plot, and
fails clearly on snapshot or opponent-selection errors. The author chose the
latest-snapshot approach in design note 0006: train against the most recent
frozen copy of the learner's Q-table. The opponent is as strong as the learner at
the moment of copying and becomes relatively weaker as the learner improves.

## Decision

### 1. Opponent policy

- Use the latest frozen snapshot as the only training opponent. Do not keep a
  pool or league in S6.
- The initial opponent is the empty Q-table. The first snapshot is the learner's
  table after N episodes. Refresh the opponent every N episodes with a frozen
  copy of the current learner table.
- The learner is the only table that updates. The opponent is a `QAgent` over a
  frozen `QTable` and plays greedily; it does not explore or train.
- The opponent's policy is fixed between refreshes. It is a benchmark, not a live
  adversary.
- Rationale: this is the smallest testable self-play step. It reuses `QTable`,
  `QAgent`, and the existing training loop. A pool is deferred to a later slice
  if the latest-snapshot policy collapses or forgets.

### 2. Cadence and training schedule

- N is a training-config value and must be a positive multiple of 10, minimum 10,
  and strictly less than the episode budget, so snapshots align with the
  five-opening and two-colour cycle and at least one refreshed snapshot is used.
- Keep the S5 episode schedule: both learner colours and the five S4 openings,
  cycling deterministically. The opponent's moves are part of the environment.
- Use one master seed. Derive per-episode learner seeds deterministically. The
  greedy opponent needs no RNG. There is no global RNG and no hidden fallback.
- Rationale: sharing the S4 openings and colours keeps training and evaluation
  comparable. Aligning N with the opening cycle avoids colour/opening bias.

### 3. Snapshot identity and failure behaviour

- Record the opponent snapshot for every episode: its creation episode, the
  episode range in which it was used, and its table size.
- Snapshots are frozen in memory for S6. The final Q-table is persisted; separate
  snapshot files are optional and deferred to the spec. The resolved run metadata
  records the snapshot policy and cadence.
- If a snapshot cannot be created or selected, raise a clear error. Do not fall
  back to a random or earlier opponent silently.
- Rationale: the opponent identity is part of the result. Without it, a training
  run cannot be explained or reproduced.

### 4. Evaluation and comparability

- The S4 arena remains the evaluator. The final greedy Q-agent is scored against
  fixed random and depth-1 greedy over the five-opening suite and both colours.
- Report W/D/L, derived score, confidence interval, table size, and the snapshot
  policy/cadence. S6 is a diagnostic; it may still be below the S7 gate.
- S6 training results are not directly comparable to S5 training results because
  the opponent distribution changes. Compare final agents on the same fixed
  baselines and report the training opponent policy.
- Rationale: self-play changes what a training result means. Fixed baselines keep
  the final comparison trustworthy while the training opponent evolves.

### 5. Configuration and artifacts

- Add a self-play training mode and a snapshot cadence to the training config.
  The exact schema, key names, and default N belong to spec 0006.
- The resolved config must record the opponent policy and cadence. The training
  CSV must include the opponent snapshot identity; the run metadata must include
  the snapshot schedule. Exact fields belong to spec 0006.
- The final Q-table, config, CSV, and learning-curve plot remain required. The
  plot shows training outcomes over episodes and is reproducible from the CSV
  and config. ADR 0004's plot ownership remains in force.

### 6. Determinism

- Same code, config, and master seed reproduce the same snapshots, final Q-table,
  and metrics on the same platform. Snapshot boundaries are deterministic;
  opponent selection is always the latest snapshot; tie-breaks are deterministic.
- The resolved config and seed are saved. The S4 determinism contract remains in
  force.

## Consequences

- S6 trains without a fixed opponent and reuses the S5 Q-table and Q-agent.
- The opponent is a stable benchmark between refreshes; as the learner improves,
  the opponent becomes relatively weaker. This can produce plateaus and requires
  cadence tuning.
- A single latest opponent gives no diversity. Overfitting, forgetting, or cycling
  are the main risks; fixed baselines expose them.
- Snapshots are in memory by default, so the final table is inspectable but
  intermediate opponent tables may not be. The spec may add optional snapshot
  files if audit needs them.
- Self-play changes the comparison to S5; the S7 gate remains the final judge.

## Alternatives rejected

- **Fixed random opponent for S6:** This is S5's diagnostic and does not meet the
  self-play requirement.
- **Fixed-size snapshot pool:** More robust against forgetting, but more memory,
  disk, and selection bookkeeping. Deferred as the fallback if latest-snapshot
  collapses.
- **Shared-table simultaneous self-play:** Cheapest memory and truly current
  self-play, but both sides' updates interact and make the run harder to explain.
  It also contradicts the plan's periodic-snapshot requirement.
- **Offline replay from recorded games:** Adds storage and delayed feedback; S6 is
  an online training slice.
- **Persisting every snapshot by default:** Adds many large JSON files without a
  stated audit need; optional snapshot files are deferred to the spec.

## Deferred to spec 0006

- Exact config schema, key names, and default N.
- Exact CSV columns and run metadata fields for snapshot identity.
- Exact CLI syntax and stdout summary.
- Whether snapshots are persisted as separate files and their naming/retention.
- Diagnostic game count and seed policy for random and greedy.
- Exact failure messages and validation order.

## Approval

Accepted on 2026-11-06 in `/spec-review S6`. The review approved the
latest-snapshot policy, added the refinement that `N` must be strictly less than
the episode budget, and left the exact config schema, artifact fields, CLI, and
diagnostic threshold to spec 0006.
