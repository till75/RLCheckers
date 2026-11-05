# ADR 0005 — Tabular Q-learning representation and hyperparameters

- **Status:** accepted
- **Date:** 2026-11-04
- **Deciders:** author, opencode
- **Related:** ADR 0002, ADR 0003, ADR 0004, `docs/00-brief.md`,
  `docs/plan.md`, `docs/design/0005-tabular-q-learning.md`

## Context

S4 built the evaluation arena and the random and greedy baselines. S5 needs an
agent that learns from games against a fixed random opponent and can be scored
by that arena. The S4 `Agent` protocol is an evaluation seam: it returns a move
and validates legality, but it does not pass rewards or terminal signals.
Training therefore needs a separate transition loop. ADR 0002 fixes the sparse
Q-table key and cap; ADR 0003 fixes the evaluation policy; ADR 0004 gives S5
ownership of training plots. S5 must settle the learning state, update,
exploration, rewards, determinism, persistence, and training config.

The draw baseline for this variant is 7 draws in 1,000 seeded random-vs-random
games (0.7%), with an average of 17.5 plies. The game is decisive enough for a
diagnostic. Draws are reported, not treated as failures. S5 does not assume the
previous attempt failed because the game was drawish; it targets a trustworthy
diagnostic instead.

## Decision

### 1. Learning state and key

- Use the 40-bit canonical board key, which includes the side to move. Exclude
  repetition and no-progress counters from the S5 learning state.
- Use ADR 0002's `q_key = (state_key << 33) | action_key`; the table is a sparse
  `dict[int, float]`.
- The initial cap is 2,000,000 entries. The trainer logs entry count and an
  approximate byte estimate. A new key when the cap is full raises a clear
  error; there is no silent eviction.
- Rationale: ADR 0002 already fixes the representation, and the board key keeps
  the table small. Random play draws rarely, so the history is accepted debt for
  S5. Revisit in S6 if repetition or no-progress draws dominate.

### 2. Update and reward

- Standard one-step Q-learning:
  `Q(s,a) <- Q(s,a) + alpha * (r + gamma * max Q(s',a') - Q(s,a))`.
- Unseen Q-values are 0. The learner updates only its own actions. The random
  opponent's moves are part of the environment.
- If the game ends after the learner's action or the opponent's reply, the target
  is the terminal reward. Otherwise, the target is `gamma * max Q(s',a')` at the
  next learner turn.
- `alpha = 0.1`, `gamma = 0.9`.
- Terminal reward from the learner's perspective: `+1` win, `0` draw, `-1` loss.
  No intermediate material shaping. This is a training signal, not the S4
  derived score; the derived score remains an evaluation statistic.
- Rationale: Q-learning is off-policy and works with a random opponent; terminal
  rewards are honest and easy to test. Shaping would bias the diagnostic.

### 3. Exploration

- Epsilon-greedy during training: with probability epsilon choose uniformly from
  legal moves; otherwise choose the highest-Q move.
- Epsilon starts at 1.0 and decays linearly to 0.05 at 80% of episodes, then
  stays at 0.05. Evaluation epsilon is 0.
- Ties in greedy choice use the smallest `(path, captures)` tuple, matching the
  S4 greedy baseline. Exploration uses a seeded RNG derived per episode.
- Rationale: explore early, exploit late; deterministic ties; evaluation measures
  the learned policy, not the exploration schedule.

### 4. Opponent and episode schedule

- The opponent is fixed random for S5. The learner plays both colours.
- Episodes cycle deterministically through the S4 five-opening suite and both
  learner colours. The opponent moves first when the opening leaves the opponent
  to move. The Q-table is side-to-move agnostic because the key includes the side
  to move and rewards are from the learner's perspective.
- One master seed; derive per-episode learner and opponent seeds deterministically.
  Reuse the S4 seed derivation where possible. There is no global RNG.
- Rationale: training and evaluation share the same openings and colours; results
  are reproducible and comparable. Self-play is S6.

### 5. Persistence and metadata

- Save the Q-table as one JSON document: format/version, metadata, and a table
  mapping decimal-string `q_key` values to floats. Load validates the
  format/version, converts keys to int, and preserves metadata.
- Metadata includes the seed, resolved training config, table size, and package
  version. The spec fixes the exact fields.
- Rationale: the brief requires an inspectable Q-table; JSON is readable and
  safe. `q_key` is 73 bits, so decimal string keys avoid an `int64` NPZ trap.
  Pickle and NPZ are rejected for S5 because they are opaque or awkward at this
  key width. If size becomes a problem, revisit in a later ADR.

### 6. Training config

- Add a separate TOML schema from `EvalConfig`. Keys: `seed`, `episodes`,
  `alpha`, `gamma`, `epsilon_start`, `epsilon_end`, `epsilon_decay_fraction`,
  `opponent`, `output_dir`, `max_table_entries`.
- Validate required keys, types, and ranges; reject unknown keys; require
  `episodes` to be a positive multiple of 10 (minimum 10); require
  `0 < alpha <= 1` and `0 <= gamma < 1`; require epsilon values in `[0, 1]` with
  `epsilon_start >= epsilon_end`; require the decay fraction in `(0, 1]` (zero is
  rejected; use `epsilon_start == epsilon_end` for a constant schedule); require
  `max_table_entries > 0`; resolve relative `output_dir` against the config file.
  S5 fixes `opponent = "random"`.
- The resolved config is saved with the run. The S4 `EvalConfig` remains
  unchanged.
- Rationale: evaluation and training are separate concerns; one schema would mix
  them. TOML matches S4 and is human-editable.

### 7. Artifacts and diagnostic

- A short training run writes the resolved config, Q-table JSON, training metrics
  CSV, and learning-curve plot. The CSV records episode identity, epsilon,
  outcome, plies, and table size. The plot shows a rolling win/draw/loss rate or
  derived score over episodes and is reproducible from the CSV and config. The
  spec fixes names and columns; ADR 0004 gives S5 the plot contract.
- The diagnostic matchup uses the S4 arena against random over the five-opening
  suite and both colours. Use 1,000 games and one master seed. Report W/D/L,
  derived score, and table size. This is a diagnostic, not the S7 gate. The
  Q-agent is evaluated greedily.
- The S4 `evaluate` CLI and agent registry remain unchanged in S5; the training
  command runs its own diagnostic through the S4 arena. A later slice may
  register the Q-agent for the CLI.

### 8. Determinism

- Same code, config, and master seed reproduce the same Q-table and metrics on
  the same platform. Episode order is sequential; updates are keyed and
  order-independent within a turn; tie-breaks are deterministic. The resolved
  config and seed are saved. The S4 determinism contract remains in force.

## Consequences

- S5 can train, save, load, and score a tabular Q-agent without changing the S4
  evaluation contract.
- The board-only state keeps the table smaller but ignores draw history; that is
  accepted debt for a diagnostic slice.
- Terminal rewards avoid shaping bias but give no intermediate signal; the short
  episodes and fixed opponent make this practical to test.
- The 2M cap prevents runaway memory but may stop a large run; afterstates or a
  smaller state are the next options.
- The fixed random opponent makes the result diagnostic; self-play in S6 may
  change the learned policy and the comparison.
- JSON is inspectable but larger than a binary format; a later ADR may change
  persistence if size matters.

## Alternatives rejected

- **Agent-owned training:** The S4 protocol has no reward/terminal callback;
  training inside `choose_move` would mix playing and training. Rejected in
  design note 0005.
- **Offline replay:** Adds storage and delayed feedback; online training is
  simpler for S5.
- **Board key plus draw history:** More Markov, but much larger and sparser; the
  draw baseline does not justify it in S5.
- **Afterstates:** The brief defers them; state-action Q-learning first.
- **SARSA:** On-policy and would learn the exploration policy; Q-learning
  matches the greedy evaluation.
- **Monte Carlo returns:** Higher variance and slower; one-step TD is the simpler
  diagnostic.
- **Reward shaping:** Can prefer material over wins and makes Q-values harder to
  interpret.
- **Dense numpy table:** Memory-prohibitive at this state space; ADR 0002
  chooses sparse.
- **Pickle or NPZ persistence:** Opaque or key-width problems; JSON is
  inspectable.
- **Training inside the S4 arena:** Couples the evaluator to the trainer; the
  arena stays evaluation-only.
- **Changing the game rules:** The draw baseline shows the game is decisive; no
  rule change.

## Deferred to spec 0005

- Exact config key names and defaults.
- Exact artifact filenames and CSV columns.
- Exact plot contract.
- Diagnostic game count and smoke-test episode count.
- CLI syntax for training.
- Exact Q-table JSON schema and metadata fields.
- Exact seed derivation for episodes.

## Approval

Accepted on 2026-11-04 in `/spec-review S5`. The design note records the
author's choice of option 1: the agent plays and the trainer trains. The review
approved the final blocking decisions: training episodes are a positive multiple
of 10 (minimum 10), and alpha/gamma ranges are `0 < alpha <= 1` and
`0 <= gamma < 1`. This ADR is the S5 gate and is now accepted.
