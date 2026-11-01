# ADR 0003 — Evaluation protocol and gate

- **Status:** accepted
- **Date:** 2026-10-31
- **Deciders:** author, opencode
- **Related:** ADR 0001, ADR 0002, `docs/00-brief.md`, `docs/plan.md`,
  `docs/specs/0004-evaluation-arena.md` (next)

## Context

The first attempt failed because there was no trustworthy way to tell whether
the agent had improved. S4 exists to build that scoreboard before any training
code, and S7 turns it into the milestone gate. Two agents must be compared
fairly across colour, opening, and seed, and the result must be reproducible
and honest about sampling noise.

The brief already fixes several inputs: random then depth-1 greedy baselines,
three training seeds, 1,000 games per seed per opponent, both colours, a fixed
opening suite, and a derived score of wins + 0.5 draws. It leaves the gate
statistic, the evaluation policy, and the determinism contract open. This ADR
settles the policy that gives those numbers meaning; spec 0004 fixes the
concrete opening positions, baseline functions, arena mechanics, metric schema,
CSV columns, config schema, and CLI syntax.

## Decision

### 1. Score and perspective

Every game is scored for the **agent under test**, whatever its colour:
win = 1, draw = 0.5, loss = 0. The derived score for a set of games is
`(wins + 0.5 * draws) / games`. Wins, draws, and losses are always reported
separately next to the score. The score is an evaluation and gate statistic,
never a training reward.

### 2. Opponents and colour pairing

Each agent is evaluated against two frozen baselines: uniform random and
depth-1 greedy. Their definitions live in spec 0004 and do not change between
runs or seeds.

Every opening in the suite is played twice per matchup: once with the agent
under test as Black and once as White. Scores pool both colours; per-colour
W/D/L is reported so a colour bias cannot hide inside the aggregate. Results
are never reported from Black's perspective.

### 3. Opening suite

One fixed suite is shared by every seed, opponent, and agent version. It is
small, legal, reachable from the initial position, and reused with both colour
assignments. Openings are selected before the run from the suite; no random or
adaptive opening selection is allowed. The exact positions and count are fixed
in spec 0004. Changing the suite creates a new evaluation contract and is not
comparable with earlier results.

### 4. Game budget and scheduling

Each training seed supplies one agent. For each matchup, that agent plays
1,000 games against the baseline, both colours and all openings included. The
suite repeats deterministically until the budget is met; the exact repetition
schedule is in spec 0004. The full milestone gate is therefore 3 seeds ×
2 opponents × 1,000 games.

### 5. Determinism

Each evaluation run has one master seed. Every per-game random stream is
derived deterministically from the master seed and the game's identity
(opening, colour assignment, and repetition index), not from execution order.
There is no global RNG and no dependence on wall-clock time, filesystem order,
or hash iteration order. Reordering games or running matchups in parallel must
not change any game or metric. The exact derivation function is fixed in spec
0004. Agents used in the gate must be stateless across games or re-seedable:
the arena resets every agent's randomness from the game seed before the first
move. Same code, config, and seed reproduce the same game list and metrics on
the same platform.

### 6. Evaluation policy

The agent under test is evaluated greedily: no exploration, no epsilon
sampling, and a deterministic tie-break when several moves are equally good.
The random baseline still draws from its own seeded stream; that is its
definition, not exploration. Exploration during the gate would measure the
exploration schedule rather than the learned policy.

### 7. Agent interface

The arena depends on one minimal protocol:

```python
class Agent(Protocol):
    def choose_move(self, state: GameState) -> Move: ...
```

`GameState` carries the side to move, so the arena passes no colour. An agent
must return a legal move, must not mutate the state, and may own its own seeded
RNG. The arena validates the returned move against the state's legal moves and
raises on an illegal or terminal-state choice; there is no fallback move. The
arena never asks an agent to move in a terminal state. `RandomAgent` already
satisfies this protocol.

### 8. Gate

For each matchup (agent vs random, agent vs greedy), compute one derived score
per training seed by pooling that seed's 1,000 games. The gate statistic is the
mean of the three per-seed scores. Pass requires both:

- mean ≥ 0.60 against random;
- mean ≥ 0.55 against greedy.

In addition, no individual seed may score below 0.50 against either opponent.
All three thresholds are provisional until the S7 pilot and may be revised
once, before the reported gate run, with the revision recorded. Per-seed,
per-colour, and aggregate W/D/L and scores are reported even when the gate
passes.

### 9. Uncertainty

Every matchup reports a two-sided 95% confidence interval for its pooled mean
derived score alongside the point estimate, plus the per-seed point estimates
and the seed-to-seed range. The interval method is fixed in spec 0004 for
per-matchup metrics and reused unchanged by the S7 gate report. The interval
describes game-level sampling noise; it is not a guarantee about unseen
openings or opponents. A pass whose interval crosses the threshold is reported
as marginal, not silently rounded up.

### 10. Frozen evaluation

Evaluation loads a frozen agent (for example a saved Q-table and its policy)
and never trains or updates it. Baselines and evaluated agents use the same
rules engine and legal-move generator as every other caller. If a game exceeds
`MAX_GAME_PLIES` without terminating, the run fails loudly; no partial metrics
are written. Invalid seeds, openings, or configs fail before the first game.

### 11. Artifacts

Every reported number is reproducible from the saved config, the master seed,
and the agent artifact. Each run records the resolved config, seed, code
version, and command line. The CSV schema, file names, and plot contents are
fixed in spec 0004.

## Consequences

- Any agent that satisfies `choose_move(state)` can be compared on the same
  scoreboard, including random, greedy, and later Q-learning agents.
- Both colours and a fixed suite remove the two easiest ways to produce a
  flattering but meaningless score.
- Per-seed floors expose a collapsed or lucky seed that a mean would hide.
- Confidence intervals and per-seed ranges make sampling noise visible instead
  of presenting a single number as certainty.
- The full gate costs 6,000 games per evaluation run. On 5x5 that is expected
  to be minutes, but it is the dominant cost of S7.
- Greedy evaluation ignores how robust a policy is to exploration; that is
  deliberate, because the gate is about the learned policy.
- Results are comparable only within the fixed opening suite and the 5x5
  variant. They do not transfer to 8x8 or to a different suite.
- The 95% interval treats games as independent draws. Games sharing a seed or
  an agent are not fully independent, so the interval is a diagnostic, not a
  formal guarantee.
- Provisional thresholds and the pilot revision are accepted debt; the final
  report must say which thresholds were used.
- S4 builds this scoreboard, S5 and S6 use it for diagnostics, and S7 runs the
  gate; changing this contract affects all three later slices.

## Alternatives rejected

- **Mean score only, no per-seed floor.** Hides a seed that collapsed or got
  lucky. The brief's floor is cheap to enforce and easy to explain.
- **Every seed must meet the threshold.** Too strict at 1,000 games; one noisy
  seed would fail an otherwise improving agent.
- **Evaluate with the training epsilon schedule.** Adds exploration noise and
  makes runs incomparable; the learned policy is what the gate should measure.
- **Point estimates only.** Hides sampling error and invites over-reading small
  differences.
- **Wilson interval on wins only.** Discards draws, which are common and
  meaningful in this variant.
- **Random or adaptive opening selection.** Breaks comparability across seeds
  and agents. A fixed suite is the point.
- **One colour per opening.** Confounds agent strength with the first-player
  advantage. Both colours per opening costs little and removes the bias.
- **One global RNG stream in game order.** Makes results depend on execution
  order and blocks safe parallel evaluation.
- **Explicit per-game seeds in config.** Verbose, error-prone, and easy to
  desynchronize from the opening schedule.
- **Agents as bare callables.** A protocol gives one documented shape, and S3's
  `RandomAgent` already fits it.
- **Passing the side to `choose_move`.** The state already carries it; a second
  source of truth can disagree.
- **Training during evaluation.** Couples the scoreboard to the training loop
  and makes runs non-reproducible.

## Deferred to spec 0004

- Exact opening positions and their count.
- Exact random and greedy baseline definitions, including material values and
  tie-break order.
- Exact per-game seed derivation and suite repetition schedule.
- Exact confidence-interval method.
- Metric schema, CSV columns, config schema, CLI syntax, and artifact layout.

## Approval

Accepted by the author on 2026-10-31, after confirming the gate rule
(mean + 0.50 floor), greedy evaluation, 95% confidence intervals, and the
`choose_move(state)` protocol.
