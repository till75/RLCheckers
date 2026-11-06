# ADR 0007 — Stochastic greedy gate baseline

- **Status:** accepted
- **Date:** 2026-11-06
- **Deciders:** author, opencode
- **Related:** ADR 0003, ADR 0004, ADR 0006, `docs/00-brief.md`,
  `docs/plan.md` S7, `docs/design/0007-three-seed-gate.md`,
  `docs/results/s6-self-play-diagnostics.md`

## Context

ADR 0003 and spec 0004 define the depth-1 greedy baseline with a deterministic
tie-break. The S6 diagnostic showed that this makes the 1,000-game greedy
matchup 10 unique opening/colour games repeated 100 times. The Q-agent won all
10 unique games, producing 1,000/0/0 and a degenerate 1.000–1.000 interval. With
a seeded random tie-break the same agent scored 0.819; against a depth-2
minimax it scored 0.400. The deterministic greedy result is a narrow exploit,
not a meaningful 1,000-game sample.

The approved S7 plan and design note choose a seeded stochastic greedy baseline
for the 1,000-game gate, with the deterministic greedy retained as a secondary
10-unique-game diagnostic. That changes the gate opponent and therefore what the
gate result means and whether it is comparable with S4/S5/S6 greedy results.
This ADR resolves that conflict before spec 0007.

## Decision

1. The S7 gate uses a **seeded stochastic greedy baseline**: the same depth-1
   material score as `GreedyAgent`, but ties are broken uniformly at random
   using a per-game seeded RNG. It is a new baseline; `GreedyAgent` itself is
   unchanged.
2. The deterministic depth-1 greedy remains a **secondary diagnostic**, reported
   as 10 unique games per seed. It is not the 1,000-game gate opponent.
3. The random baseline remains unchanged.
4. ADR 0003’s score, colour pairing, fixed opening suite, 1,000-game budget,
   mean-plus-floor gate, thresholds, and uncertainty requirements remain in
   force. Only the greedy baseline used for the 1,000-game gate changes.
5. Results against stochastic greedy are **not directly comparable** with
   deterministic-greedy results from S4/S5/S6. The S7 report labels both and
   does not pool them.

## Consequences

- The 1,000-game greedy matchup contains 1,000 unique games, not 10 repeated
  games.
- The gate is less exploitable by a deterministic policy, but stochastic greedy
  is still a weak baseline; the depth-2 diagnostic remains a separate
  robustness check.
- The S7 gate result is a new evaluation contract. It cannot be compared
  directly with earlier deterministic-greedy diagnostics.
- The deterministic greedy baseline remains available and unchanged for
  historical comparison.
- The gate thresholds stay as ADR 0003; this ADR does not move them.

## Alternatives rejected

- **Keep deterministic greedy for the gate.** It produces 10 unique games
  repeated 100 times and a narrow exploit; the 1,000-game interval is
  misleading.
- **Use depth-2 minimax as the gate baseline.** It is stronger, but it changes
  the brief’s baseline and would require new thresholds and a larger scope.
- **Use random only.** It does not test the greedy style the brief requires.
- **Change `GreedyAgent` itself.** It would break S4/S5/S6 comparability and the
  deterministic baseline contract.

## Approval

Accepted by the author on 2026-11-06 as part of the S7 plan and design note. The
author explicitly kept the ADR 0003 thresholds; this ADR changes only the greedy
baseline used for the 1,000-game gate.
