# Spec 0007 — Three-seed gate and report

- **Status:** draft for review
- **Date:** 2026-11-06
- **Slice:** S7 — Three-seed gate and report
- **Related:** `docs/00-brief.md`, `docs/plan.md` S7, ADR 0003, ADR 0004,
  ADR 0006, ADR 0007, `docs/design/0007-three-seed-gate.md`,
  `docs/results/s6-self-play-diagnostics.md`,
  `docs/specs/0004-evaluation-arena.md`, `docs/specs/0006-self-play-snapshots.md`

## Outcome

A caller can run `python -m rlcheckers gate --config gate.toml` to train three
independent self-play seeds, evaluate each final agent against random and seeded
stochastic greedy, report per-seed and aggregate W/D/L, scores, intervals,
unique-game counts, per-snapshot learning curves, and a depth-2 diagnostic, and
receive a pass/fail gate plus a reproducible Markdown report.

## Context and scope

S6 proved the self-play loop and exposed a measurement problem: deterministic
greedy makes the 1,000-game matchup 10 unique games repeated 100 times. ADR 0007
adds a seeded stochastic greedy baseline for the S7 gate and keeps deterministic
greedy as a secondary diagnostic. The ADR 0003 thresholds remain unchanged:
mean ≥ 0.60 against random, mean ≥ 0.55 against stochastic greedy, and no seed
below 0.50 against either.

S7 is one command, not a two-stage pipeline. The command trains, evaluates, and
writes the report in one flow. Snapshots are captured in memory through a small
observer seam; no snapshot files are written. The deterministic greedy and
depth-2 results are diagnostics, not part of the pass/fail gate. The milestone
report is written in the final TDD step from the same data; the command writes
the slice diagnostic report.

## Public interface

### System view

```text
gate.toml
  -> load_gate_config
  -> for each of three seeds:
       train_self_play with snapshot observer
       final Q-agent + captured snapshots
       evaluate random, stochastic greedy, deterministic greedy, depth-2
       evaluate each snapshot against random and stochastic greedy
  -> aggregate per-seed scores and apply ADR 0003 thresholds
  -> write Q-tables, gate.json, gate.csv, snapshot_curve.csv,
     snapshot_curve.png, and the slice report
  -> print the gate summary and return 0 (pass) or 1 (fail)
```

### Modules and imports

- `src/rlcheckers/config.py` — `GateConfig`, `load_gate_config`.
- `src/rlcheckers/agents/greedy_agent.py` — `StochasticGreedyAgent`.
- `src/rlcheckers/training/self_play.py` — optional `snapshot_observer` on
  `train_self_play`.
- `src/rlcheckers/evaluation/gate.py` — `Depth2Agent`, `GateMatchup`,
  `SnapshotCurvePoint`, `SeedGateResult`, `GateResult`, `run_gate`,
  `write_gate_artifacts`, and the gate threshold constants.
- `src/rlcheckers/evaluation/__init__.py` — re-export the gate public surface.
- `src/rlcheckers/agents/__init__.py` — re-export `StochasticGreedyAgent` for
  tests; do not add it to `AGENT_NAMES` or `make_agent`.
- `src/rlcheckers/cli.py` — the `gate` subcommand.

### Types and units

```python
@dataclass(frozen=True)
class GateConfig:
    seeds: tuple[int, int, int]
    eval_seed: int
    episodes: int
    alpha: float
    gamma: float
    epsilon_start: float
    epsilon_end: float
    epsilon_decay_fraction: float
    output_dir: Path
    max_table_entries: int
    snapshot_interval: int
    games: int
    snapshot_games: int
    unique_games: int

@dataclass(frozen=True)
class GateMatchup:
    opponent: str
    games: int
    unique_games: int
    overall: ScoreSummary
    black: ScoreSummary
    white: ScoreSummary
    ci_applicable: bool

@dataclass(frozen=True)
class SnapshotCurvePoint:
    episode: int
    table_size: int
    random: ScoreSummary
    stochastic_greedy: ScoreSummary

@dataclass(frozen=True)
class SeedGateResult:
    seed: int
    table_size: int
    snapshots: tuple[SnapshotRecord, ...]
    matchups: Mapping[str, GateMatchup]
    snapshot_curve: tuple[SnapshotCurvePoint, ...]

@dataclass(frozen=True)
class GateResult:
    config: GateConfig
    seeds: tuple[SeedGateResult, ...]
    random_mean: float
    random_min: float
    greedy_mean: float
    greedy_min: float
    passed: bool
```

`ScoreSummary` is the existing S4 type. Scores are in `[0, 1]`; W/D/L counts
are integers; `games` and `unique_games` are positive multiples of 10.

### Gate config

The TOML file has exactly these keys:

```toml
seeds = [7, 8, 9]
eval_seed = 7
episodes = 10000
alpha = 0.1
gamma = 0.9
epsilon_start = 1.0
epsilon_end = 0.05
epsilon_decay_fraction = 0.8
output_dir = "docs/results"
max_table_entries = 2000000
snapshot_interval = 1000
games = 1000
snapshot_games = 200
unique_games = 10
```

Validation:

- `seeds` is a list of exactly three distinct integers, not booleans.
- `eval_seed` is an integer, not a boolean.
- `episodes` is a positive multiple of 10.
- `alpha` is in `(0, 1]`; `gamma` is in `[0, 1)`; epsilon endpoints are in
  `[0, 1]` with start at least end; the decay fraction is in `(0, 1]`.
- `output_dir` is a non-empty string, resolved relative to the config file.
- `max_table_entries` is a positive integer.
- `snapshot_interval` is a positive multiple of 10, at least 10, and strictly
  less than `episodes`.
- `games`, `snapshot_games`, and `unique_games` are positive multiples of 10.
- Unknown or missing keys raise `ConfigError` naming the key.

The gate constructs one `TrainConfig` per seed with `opponent = "self"`, the
shared training fields, and `output_dir = config.output_dir / f"seed-{seed}"`.
The gate does not call `write_self_play_artifacts`; the training output directory
is metadata only.

### Stochastic greedy baseline

`StochasticGreedyAgent(seed: int)` lives in `agents/greedy_agent.py`.

- It validates that `seed` is an integer and not a boolean, then owns a private
  `random.Random(seed)`.
- `choose_move(state)` rejects a terminal state, scores every legal move with
  the existing `GreedyAgent._score`, collects all moves with the maximum score,
  and chooses uniformly among them with its RNG.
- It is deterministic for a given seed and state sequence.
- It is not added to `AGENT_NAMES` or `make_agent`; it is a gate baseline only.

### Depth-2 diagnostic

`Depth2Agent` lives in `evaluation/gate.py` and is diagnostic-only.

- For each legal move, apply it. If terminal, score the terminal result from the
  root side: win `+1000`, draw `0`, loss `-1000`.
- Otherwise, for each opponent reply, apply it. If terminal, score the terminal
  result from the root side; otherwise use `material_balance` from the root side
  after the reply. The opponent reply score is the minimum over replies.
- The move score is that minimum. Choose the maximum move score; ties use the
  smallest `(path, captures)`.
- It owns no RNG and is not in the agent registry.

### Snapshot observer

`train_self_play` gains one optional keyword-only parameter:

```python
snapshot_observer: Callable[[Snapshot], None] | None = None
```

- The observer is called once with the initial `Snapshot(0, empty table)` and
  once after each refresh with the new `Snapshot`.
- It is not called for the final table. The gate wraps the final table as
  `Snapshot(episodes, result.table)`.
- Observer exceptions propagate unchanged. The default `None` preserves S6
  behaviour.
- The observer must not mutate the snapshot table; the trainer does not enforce
  this.

### Gate computation

For each seed in `config.seeds`:

1. Train with `train_self_play` and an observer that appends snapshots to a
   list.
2. Build `QAgent(result.table)`.
3. Play four matchups with `play_matchup`, `seed=config.eval_seed`, and
   `openings=result.openings`:
   - `random`: `RandomAgent(seed)`, `games=config.games`.
   - `stochastic_greedy`: `StochasticGreedyAgent(seed)`, `games=config.games`.
   - `deterministic_greedy`: `GreedyAgent()`, `games=config.unique_games`.
   - `depth2`: `Depth2Agent()`, `games=config.unique_games`.
4. Summarize overall, black, and white for each matchup. For deterministic
   matchups, `ci_applicable=False`; JSON uses `null` for the interval and the
   report uses `n/a`.
5. Evaluate the snapshot curve: the initial snapshot, each refresh, and the
   final table, against random and stochastic greedy with
   `games=config.snapshot_games`. The curve stores overall summaries only.

Gate statistics:

- `random_mean` and `random_min` are the mean and minimum of the three
  per-seed random overall scores.
- `greedy_mean` and `greedy_min` are the mean and minimum of the three
  per-seed stochastic-greedy overall scores.
- `passed` is true only when `random_mean >= 0.60`, `greedy_mean >= 0.55`,
  `random_min >= 0.50`, and `greedy_min >= 0.50`.
- Deterministic greedy and depth-2 never affect `passed`.

### Artifacts

`write_gate_artifacts` creates `output_dir` only after all seeds and evaluations
succeed. It writes:

- `q_table_seed_<seed>.json` for each seed, using the existing `QTable.save`
  metadata shape: `config`, `package_version`, `python_version`, `seed`, and
  `table_size`.
- `gate.json` with exactly these top-level keys: `command_line`, `config`,
  `gate`, `seeds`, `package_version`, `python_version`.
  - `gate` has `passed`, `random_mean`, `random_min`, `greedy_mean`,
    `greedy_min`, and `thresholds` (`random_mean`, `greedy_mean`, `seed_floor`).
  - Each seed has `seed`, `table_size`, `snapshots`, `matchups`, and
    `snapshot_curve`.
  - Each matchup has `games`, `unique_games`, `overall`, `black`, `white`, and
    `ci_applicable`. Each summary has `wins`, `draws`, `losses`, `score`,
    `ci_low`, and `ci_high`.
  - Each snapshot curve point has `episode`, `table_size`, `random`, and
    `stochastic_greedy`.
- `gate.csv` with columns
  `seed,opponent,group,key,games,unique_games,wins,draws,losses,score,ci_low,ci_high`.
  Rows cover overall, black, and white for each seed and opponent. Deterministic
  rows leave `ci_low` and `ci_high` empty.
- `snapshot_curve.csv` with columns
  `seed,episode,table_size,opponent,games,unique_games,wins,draws,losses,score,ci_low,ci_high`.
  Rows cover random and stochastic greedy for each seed and curve episode.
- `snapshot_curve.png`: two panels, one for random and one for stochastic
  greedy; x-axis episode, y-axis score, one line per seed, title
  `Self-play snapshot learning curve`, legend by seed. It is reproducible from
  `snapshot_curve.csv`.
- `s7-three-seed-gate-diagnostics.md`: the slice report. It follows
  `docs/results/_template-slice-diagnostics.md` and includes the goal, config,
  command line, gate decision and thresholds, per-seed table, aggregate table,
  per-colour table, per-snapshot curve table and plot link, unique-game
  accounting, depth-2 diagnostic, caveats, and artifact links.

The milestone report `docs/results/first-milestone.md` is written in the final
TDD step, not by the gate command. It summarizes the gate result and links to
the slice report.

JSON, CSV, and Markdown are byte-reproducible. The PNG is reproducible in
content from the CSV. A runtime error writes no output directory and no partial
files.

### CLI

`python -m rlcheckers gate --config PATH` loads the gate config, runs the gate,
writes the artifacts, and prints exactly these 13 lines:

```text
seeds: 7,8,9
eval_seed: 7
episodes: 10000
snapshot_interval: 1000
games: 1000
snapshot_games: 200
unique_games: 10
random_mean: 0.xxxxxx
random_min: 0.xxxxxx
greedy_mean: 0.xxxxxx
greedy_min: 0.xxxxxx
gate: pass
artifacts: C:\...\docs\results
```

`gate: fail` replaces `gate: pass` when the gate fails. The command returns 0 on
pass, 1 on fail, 1 on runtime error, and 2 on argument error. On a gate fail the
artifacts and report are still written. On a runtime error stdout is empty,
stderr is `error: <message>`, and no artifacts are written.

### Performance

The full S7 config trains three seeds for 10,000 episodes, plays 1,000 games
against random and stochastic greedy per seed, plays 200 games per snapshot per
opponent, and plays 10 unique games against deterministic greedy and depth-2 per
seed. The target is minutes, not hours. If the run is too slow, reduce
`snapshot_games` in the config; the report records the sample size. Do not
reduce the 1,000-game gate budget for the milestone.

## Acceptance criteria

### A1 — Gate config

- **Happy:** the full config above loads with `seeds == (7, 8, 9)`,
  `eval_seed == 7`, `episodes == 10000`, `snapshot_interval == 1000`,
  `games == 1000`, `snapshot_games == 200`, and `unique_games == 10`.
- **Boundary:** a minimum config with `episodes = 20`, `snapshot_interval = 10`,
  `games = 10`, `snapshot_games = 10`, and `unique_games = 10` loads.
- **Failure:** missing or unknown keys, fewer or more than three seeds,
  duplicate seeds, boolean seeds, non-multiple game counts, and
  `snapshot_interval >= episodes` raise `ConfigError` naming the key.

### A2 — Stochastic greedy baseline

- **Happy:** the same seed reproduces the same move sequence; two seeds can
  choose different moves when several moves tie for the best score.
- **Boundary:** when one move is uniquely best, every seed chooses it.
- **Failure:** a boolean or non-integer seed raises `ValueError`; a terminal
  state raises `ValueError`.

### A3 — Snapshot observer

- **Happy:** the observer receives the initial snapshot and each refresh, in
  creation order, with the correct `created_at_episode` and table size.
- **Boundary:** `snapshot_observer=None` produces the same result as S6.
- **Failure:** an observer exception propagates unchanged and the trainer does
  not swallow it.

### A4 — Gate aggregation

- **Happy:** three known per-seed summaries produce the expected means, minima,
  and `passed=True`.
- **Boundary:** a seed exactly at the 0.50 floor passes; a seed just below it
  fails.
- **Failure:** a mean below 0.60 against random or 0.55 against stochastic
  greedy sets `passed=False`; deterministic greedy and depth-2 do not change
  `passed`.

### A5 — Gate artifacts

- **Happy:** a small-N run writes the three Q-tables, `gate.json`, `gate.csv`,
  `snapshot_curve.csv`, `snapshot_curve.png`, and the slice report.
- **Boundary:** deterministic rows have empty intervals and
  `unique_games == 10`; random and stochastic-greedy rows have
  `unique_games == games`.
- **Failure:** a runtime error leaves no output directory and no partial files.

### A6 — Slice report

- **Happy:** the report contains the goal, config, command line, gate decision,
  thresholds, per-seed table, aggregate table, per-colour table, snapshot curve,
  unique-game accounting, depth-2 diagnostic, caveats, and artifact links.
- **Boundary:** a failing gate still writes the report and says `fail`.
- **Failure:** missing or inconsistent result data raises before writing.

### A7 — CLI

- **Happy:** `gate --config` returns 0 on pass, writes the artifacts, and prints
  the 13-line summary with `gate: pass`.
- **Boundary:** a failing gate returns 1, writes the artifacts, and prints
  `gate: fail`.
- **Failure:** missing `--config` exits 2; a bad config returns 1 with `error:`
  and no stdout; a runtime error returns 1 with no artifacts.

### A8 — Reproducibility

- **Happy:** the same config and seeds produce byte-identical `gate.json`,
  `gate.csv`, `snapshot_curve.csv`, Q-tables, and report; the PNG is
  reproducible in content.
- **Boundary:** changing `eval_seed` changes the random and stochastic-greedy
  evaluations but not the trained Q-tables.
- **Failure:** nondeterministic output is a defect.

### A9 — Documentation

- README, architecture, plan, state, module docstrings, the slice report, and the
  milestone report describe the gate, the stochastic greedy baseline, the
  unique-game accounting, the per-snapshot curve, and the depth-2 diagnostic.

## Tests to add

| Criterion | Tests |
|---|---|
| A1 | `test_load_gate_config_reads_fields`, `test_load_gate_config_accepts_minimum`, `test_load_gate_config_rejects_missing_key`, `test_load_gate_config_rejects_bad_seeds`, `test_load_gate_config_rejects_bad_games`, `test_load_gate_config_rejects_bad_snapshot_interval`, `test_load_gate_config_rejects_bad_hyperparameters` |
| A2 | `test_stochastic_greedy_is_seeded`, `test_stochastic_greedy_uses_best_moves`, `test_stochastic_greedy_rejects_bad_seed`, `test_stochastic_greedy_rejects_terminal_state` |
| A3 | `test_train_self_play_calls_snapshot_observer`, `test_train_self_play_without_observer_unchanged`, `test_train_self_play_propagates_observer_error` |
| A4 | `test_gate_aggregates_three_seeds`, `test_gate_passes_at_thresholds`, `test_gate_fails_below_floor`, `test_gate_fails_below_mean` |
| A5 | `test_gate_writes_artifacts`, `test_gate_json_schema`, `test_gate_csv_schema`, `test_snapshot_curve_csv_schema`, `test_gate_artifacts_are_byte_reproducible`, `test_gate_writes_no_partial_artifacts_on_error`, `test_gate_small_n_integration` |
| A6 | `test_gate_report_contains_required_sections`, `test_gate_fail_report_is_written` |
| A7 | `test_cli_gate_stdout`, `test_cli_gate_returns_one_on_fail`, `test_cli_gate_requires_config`, `test_cli_gate_reports_config_error`, `test_cli_gate_reports_runtime_error`, `test_module_entry_point_runs_gate` |
| A8 | `test_gate_is_reproducible`, `test_gate_eval_seed_changes_evaluation_only` |
| A9 | Documentation review, not a unit test |

Test files:

- `tests/test_config.py` — A1.
- `tests/agents/test_greedy_agent.py` — A2.
- `tests/training/test_self_play.py` — A3.
- `tests/evaluation/test_gate.py` — A4–A6, A8.
- `tests/test_cli.py` — A7.

Tests use plain `pytest` assertions, `pytest.raises` with `match`, `tmp_path`
for files, and `capsys` for output. The small-N integration test uses three
seeds, 20 episodes, `snapshot_interval=10`, `games=10`, `snapshot_games=10`, and
`unique_games=10`; it asserts the artifacts and report exist and the return code
is 0 or 1. The full S7 run is the slice diagnostic, not a default test.

## TDD order

1. **Bootstrap:** add `GateConfig` and `load_gate_config` stubs,
   `StochasticGreedyAgent`, `Depth2Agent`, the `snapshot_observer` parameter,
   `gate.py` public stubs, the CLI `gate` skeleton, and exports. Keep the
   existing suite green.
2. A1 — gate config.
3. A2 — stochastic greedy.
4. A3 — snapshot observer.
5. A4 — gate aggregation with small-N inputs.
6. A5 — gate artifacts and schemas.
7. A6 — slice report.
8. A7 — CLI.
9. A8 — reproducibility.
10. A9 — docs, full S7 run, slice report, and milestone report.

Split the slice at a testable boundary if the session runs out; do not carry a
half-finished slice across turns.

## Out of scope

- A generic `verify-slice` command. S7 implements `gate`; `verify-slice` remains
  a future slice.
- Snapshot persistence. Snapshots are captured in memory only.
- New training algorithms, hyperparameter search, or changes to the S6
  self-play policy.
- Changing the ADR 0003 thresholds.
- Per-opening gate report rows. The gate reports overall and per-colour; the S4
  artifacts remain the per-opening source.
- Adding stochastic greedy or depth-2 to `AGENT_NAMES` or `make_agent`.
- Changing the deterministic `GreedyAgent`.
- 8x8, neural networks, UI, cloud, or distributed training.
- Running the full gate as a default test.

## Contradictions, gaps, and decisions

- **ADR 0003/spec 0004 deterministic greedy vs S7 stochastic greedy.** Resolved
  by ADR 0007. The gate uses stochastic greedy; deterministic greedy is a
  10-unique-game diagnostic.
- **ADR 0003 1,000 games per seed per opponent.** The gate uses 1,000 games for
  random and stochastic greedy. Deterministic greedy and depth-2 are 10 unique
  games each and are not the gate.
- **ADR 0003 95% confidence intervals.** The gate reports intervals for random
  and stochastic greedy. Deterministic diagnostics have no interval.
- **Brief says 1,000 games against depth-1 greedy.** Stochastic greedy is a
  depth-1 greedy variant; ADR 0007 records the change and the comparability
  caveat.
- **Plan says per-snapshot learning curve.** The spec uses
  `snapshot_games=200` per snapshot per opponent. This is a diagnostic sample
  size, not the gate; the report records it.
- **Plan says depth-2 diagnostic.** The spec uses 10 unique games per seed.
- **Plan says slice report and milestone report.** The gate command writes the
  slice report; the final TDD step writes the milestone report.
- **Process says `verify-slice` is future.** S7 implements `gate`, not
  `verify-slice`.
- **New gate config.** The plan’s file list did not include `config.py`; the
  spec adds `GateConfig` and `load_gate_config` there. This is a refinement, not
  a contradiction.

## Approval

Pending `/spec-review S7`.
