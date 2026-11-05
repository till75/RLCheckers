# Design note 0006 — Self-play with periodic snapshots

- **Status:** chosen
- **Date:** 2026-11-05
- **Slice:** S6 — Self-play with periodic snapshots
- **Related:** `docs/00-brief.md`, `docs/plan.md` S6, ADR 0005, ADR 0006,
  `src/rlcheckers/agents/q_agent.py`, `src/rlcheckers/training/train_q.py`,
  `src/rlcheckers/evaluation/arena.py`

## Problem

S5 trained a Q-agent against a fixed random opponent. S6 changes what the caller
sees: the training command no longer uses a fixed training opponent. The learner
plays against frozen copies of its own Q-table, refreshed every N episodes. The
run still writes the final Q-table, config, training CSV, and learning curve, and
the S4 arena still scores the final agent against random and depth-1 greedy. S6
exists now because the milestone requires self-play, but self-play is
non-stationary and can collapse. The design choice is how to manage snapshots so
the training result stays reproducible and comparable.

## Terms

- **Self-play** — the learner trains against a frozen earlier copy of itself.
  Example: freeze the table at episode 1,000; episodes 1,001–2,000 train against
  that copy.
- **Snapshot** — a saved or frozen Q-table at a training milestone, used as the
  opponent. Example: `q_table_001000.json`; the opponent loads it and plays
  greedily while the learner keeps updating its own table.
- **Non-stationary opponent** — the opponent's policy changes when snapshots
  refresh. Example: a move that looks good against the 1,000-episode snapshot may
  be bad against the 5,000-episode snapshot, so the Q-value target moves.

## Approaches

| Approach | Idea | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|---|
| A — Latest snapshot only | Train against the latest frozen learner; refresh every N episodes. The first opponent is the initial empty table. | One opponent at a time; reuses `QTable.save`/`load` and `QAgent`; simple artifacts and reproducibility. | No diversity; the learner can overfit to the current snapshot and forget; the empty first opponent gives weak early signal; cadence is a trade-off. | A seeded run's score vs random and greedy rises across blocks; the final agent beats the S5 baseline; no collapse; snapshots replay exactly. |
| B — Fixed-size snapshot pool | Keep K frozen snapshots; sample one deterministically as the opponent. | Diversity; less forgetting; still reuses save/load. | More disk and memory; deterministic selection and artifact bookkeeping; weak old snapshots can dilute learning; bigger spec. | Same scoreboard; final agent beats A under the same seed; selection reproducible; no collapse. |
| C — Shared-table simultaneous self-play | Both sides use and update the same Q-table; no frozen snapshots. | Cheapest memory; one table; truly current self-play. | Non-stationary and unstable; both sides' updates interact; harder to debug and compare; contradicts the plan's periodic-snapshot requirement. | Final agent beats baselines; training stays stable; no forgetting or oscillation. |

## Recommendation

Choose **A**. It is the smallest testable self-play step and matches the plan's
"a snapshot policy" wording. The learner keeps one table and one frozen opponent;
the fixed baselines remain the scoreboard. The first opponent is the empty table,
so the first block is self-play against an untrained self. This isolates the new
concept from pool management. If A collapses or forgets, B is the next refinement.
B is the deliberate challenge to A's "latest only" answer. C challenges the
snapshot premise and would require an ADR and a plan/brief change before `/spec`.

## Chosen approach

The author chose **A — latest snapshot only**. The author's reason: after an
initial block against the empty Q-table, the learner freezes its current Q-table
every N episodes and trains against that fixed copy. The opponent is as strong as
the learner when the copy is taken; as the learner improves, the frozen opponent
becomes relatively weaker. This makes each snapshot a stable benchmark rather
than a live adversary. The learner's table is the only table that updates. The
fixed baselines remain the evaluation scoreboard. Cadence N, the initial opponent,
the exact CSV/run metadata, and the CLI are spec details; N should be a positive
multiple of 10 to align with the five-opening and two-colour cycle. The design
note is superseded if the choice changes.

## What would change the decision

- The latest-snapshot run collapses, oscillates, or forgets; move to B or revisit
  the cadence.
- The empty first opponent gives no useful early signal; use a short random
  warm-up or B, and record the change.
- Snapshot creation or opponent selection cannot be made reproducible from the
  seed and config.
- Self-play does not improve against the fixed baselines; inspect state coverage,
  cadence, and table growth before adding a pool or changing the reward.
- The brief or plan changes to allow a league/pool or shared-table training.

## Sources

- `docs/plan.md` S6 — outcome, acceptance criteria, and the ADR 0006 gate.
- ADR 0005 — tabular Q-learning representation, rewards, and fixed baselines.
- ADR 0006 — proposed self-play snapshot policy.
- `src/rlcheckers/agents/q_agent.py` — `QTable` and greedy `QAgent`.
- `src/rlcheckers/training/train_q.py` — current fixed-opponent training loop.
