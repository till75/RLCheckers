# Design note 0005 — Tabular Q-learning

- **Status:** chosen
- **Date:** 2026-11-04
- **Slice:** S5 — Tabular Q-learning against a fixed random opponent
- **Related:** `docs/00-brief.md`, `docs/plan.md`, ADR 0002, ADR 0003, ADR 0004

## Problem

S5 must add an agent that learns from games against a fixed random opponent and
can be scored by the S4 arena. The S4 `Agent` protocol only returns a move; it
never tells the agent the reward or that the game ended. Training therefore needs
a seam that exposes transitions without turning the evaluator into a trainer.
This slice is diagnostic: prove the Q-update works and improves against random
before S6 adds self-play.

## Terms

- **Q-value `Q(s, a)`** — the current estimate of discounted future reward for
  taking action `a` in state `s`. Example: `Q(s, a) = 0.20` means the move looks
  worth about 0.20 from here.
- **TD update** — move `Q(s, a)` toward `r + gamma * max Q(s', a')`. Example:
  with `Q = 0.20`, `alpha = 0.1`, `gamma = 0.9`, and best next value `0.60`, the
  target is `0.54`, so the new value is `0.234`.
- **Epsilon-greedy** — with probability `epsilon`, pick a random legal move;
  otherwise pick the highest-Q move. Example: `epsilon = 1.0` explores;
  `epsilon = 0` exploits greedily.

## Approaches

| Approach | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|
| A — Agent-owned training | One object; reuses the S4 arena | The protocol has no reward or terminal callback; the agent must cache state and infer the end; training and evaluation mix | A unit test can inspect the table, but terminal credit assignment is awkward |
| B — Trainer-owned loop + thin Q-agent adapter | Clean reward/terminal handling; evaluation stays honest; reuses the S4 arena | Two components; shared table/artifact format; the trainer must mirror the game loop | Deterministic Q-update test; short run improves vs random; adapter passes arena legality |
| C — Offline replay from recorded games | Reproducible; collection and learning are separate | Storage; delayed feedback; no online exploration; more scope | Same Q-update test and improvement, but slower iteration |

## Recommendation

Choose **B**. The S4 arena is an evaluator: its `Agent` protocol returns a move
and validates legality, but it does not pass rewards or terminal signals. A
separate `train_q` loop can step the same engine, record
`(state, action, reward, next_state, done)`, and update the table with correct
terminal handling. A thin `QAgent` adapter then exposes the learned table to the
S4 arena for the improvement check. This keeps learning and evaluation
independent and avoids changing the S4 contract. Initial defaults to validate in
the spec: `alpha = 0.1`, `gamma = 0.9`, `epsilon` linearly from `1.0` to `0.05`
over 80% of episodes then constant, and the ADR 0002 cap of 2,000,000 entries.
Terminal reward is `+1` win, `0` draw, `-1` loss from the learner's perspective;
no draw-avoidance shaping.

## Chosen approach

The author chose **option 1**, interpreted here as **B — trainer-owned loop with
a thin Q-agent adapter**. The S4 arena remains the evaluator. The trainer owns
exploration and updates; the Q-agent owns greedy action selection at evaluation
time. The author's reason: an agent playing and a trainer training are easier to
understand and separate the concerns of playing and training. The draw baseline
(7/1,000 random-vs-random games) supports keeping the standard game and
reporting draws rather than changing the rules.

## What would change the decision

- The separate loop cannot reuse the engine without duplicating rules or seeds.
- The adapter cannot satisfy the S4 `Agent` protocol or the arena's legality
  checks.
- The Q-table hits the 2,000,000-entry cap; then revisit afterstates or a smaller
  state.
- The diagnostic run does not improve against random after the Q-update is
  verified; inspect state coverage and rewards before adding shaping.
- Draws dominate the learned policy; report them and revisit the reward/state,
  not the game rules.

## Sources

- ADR 0002 — board/state/action encoding and Q-table cap.
- ADR 0003 — evaluation protocol and greedy evaluation.
- ADR 0004 — plot ownership.
- `src/rlcheckers/evaluation/arena.py` — S4 arena and `Agent` protocol.
