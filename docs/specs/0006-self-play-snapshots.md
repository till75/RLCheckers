# Spec 0006 — Self-play with periodic snapshots

- **Status:** approved (2026-11-06)
- **Date:** 2026-11-05
- **Slice:** S6 — Self-play with periodic snapshots
- **Related:** `docs/00-brief.md`, `docs/plan.md` S6, ADR 0002, ADR 0003,
  ADR 0004, ADR 0005, ADR 0006,
  `docs/design/0006-self-play-snapshots.md`,
  `docs/specs/0004-evaluation-arena.md`, `docs/specs/0005-tabular-q-learning.md`

## Outcome

A caller can run a seeded `train-q` command whose training opponent is the
latest frozen copy of the learner's own Q-table, refreshed every N episodes,
and receive the final Q-table, a self-play training CSV with the opponent
snapshot identity, run metadata with the snapshot schedule, a learning-curve
plot, and 1,000-game diagnostic summaries against both random and depth-1
greedy.

## Context and scope

S5 trained the Q-agent against a fixed random opponent and proved the Q-update
against a fixed baseline. S6 removes the fixed training opponent. The learner
keeps one table and plays against one frozen snapshot of that table, refreshed
every N episodes. The initial opponent is an empty table, so the first block is
self-play against an untrained self. Only the learner's table is updated; the
opponent is a greedy `QAgent` over a frozen copy and never trains.

The S4 arena remains the scoreboard. The final greedy Q-agent is scored against
fixed random and fixed depth-1 greedy over the five S4 openings and both
colours. S6 is a diagnostic: it may still be below the S7 gate. Self-play
training results are not directly comparable to S5 training results because the
opponent distribution changes; final agents are compared on the same fixed
baselines, and the training opponent policy is reported.

## Public interface

### System view

Figure 1 is the runtime path from a self-play TOML file to the four artifacts
and the two diagnostic summaries. It is explanatory rather than a second
contract; the sections below define each row.

| Stage | Input | Output |
|---|---|---|
| Config | self-play TOML | `TrainConfig` with `opponent="self"` and `snapshot_interval` |
| Policy | learner table every N episodes | one frozen opponent snapshot |
| Training | openings, seeds, epsilon | learner table, episode metrics, snapshot records |
| Diagnostics | final `QAgent` | 1,000 games vs random, 1,000 vs greedy |
| Artifacts | table, metrics, snapshot schedule | `q_table.json`, `training.csv`, `run.json`, `learning_curve.png` |

**Figure 1 — S6 self-play pipeline.** The policy freezes the learner table every
N episodes; the trainer updates only the learner. The final table feeds two
fixed-baseline diagnostics, and the snapshot schedule and both summaries go into
`run.json`. The table is explanatory; the sections below define each row. It is a
table rather than a Mermaid diagram so the Markdown contract needs no HTML and
no viewer-dependent text colour; see decision 8.

### Modules and imports

New production module:

- `src/rlcheckers/training/self_play.py` — `SelfPlayError`, `Snapshot`,
  `SnapshotRecord`, `SnapshotPolicy`, `SelfPlayEpisodeMetric`,
  `SelfPlayTrainingResult`, `SELF_PLAY_TRAINING_FIELDS`, `train_self_play`,
  and `write_self_play_artifacts`.

Existing modules gain public names:

- `src/rlcheckers/agents/q_agent.py` gains `QTable.clone()`.
- `src/rlcheckers/config.py` gains the `snapshot_interval` field on
  `TrainConfig` and its conditional validation in `load_train_config`. The S4
  `EvalConfig` and `load_eval_config` remain unchanged.
- `src/rlcheckers/training/__init__.py` re-exports the new self-play names in
  addition to the S5 names.
- `src/rlcheckers/training/train_q.py` gains the `title_prefix` keyword on
  `write_learning_curve` and guards that reject a self-play config. The S5
  fixed-random `train_q` behaviour is otherwise unchanged.
- `src/rlcheckers/cli.py` dispatches the existing `train-q` command on
  `config.opponent`; `play-random` and `evaluate` keep their current behaviour.

Canonical imports:

```python
from rlcheckers.agents import (
    MAX_GAME_PLIES,
    GreedyAgent,
    QAgent,
    QTable,
    RandomAgent,
    q_key,
)
from rlcheckers.config import ConfigError, TrainConfig, load_train_config
from rlcheckers.evaluation import (
    STANDARD_OPENINGS,
    ArenaResult,
    GameOutcome,
    derive_side_seed,
    format_float,
    opening_state,
    outcome_for,
    play_matchup,
    summarize,
)
from rlcheckers.training import (
    DIAGNOSTIC_GAMES,
    SELF_PLAY_TRAINING_FIELDS,
    SelfPlayEpisodeMetric,
    SelfPlayError,
    SelfPlayTrainingResult,
    Snapshot,
    SnapshotPolicy,
    SnapshotRecord,
    choose_epsilon_greedy,
    derive_episode_seed,
    epsilon_at,
    q_update,
    reward_for,
    train_self_play,
    write_self_play_artifacts,
)
```

The self-play module imports the rules, the Q-table and Q-agent, the S4 arena
helpers, and the S5 pure training helpers. The S4 arena never imports the
training package. The Q-agent is still not registered in `make_agent`; the
self-play diagnostic constructs `QAgent` directly.

### Types and units

| Name | Type | Unit / range |
|---|---|---|
| `seed` | `int` | not bool; master seed |
| `episodes` | `int` | count; positive multiple of 10 |
| `snapshot_interval` | `int` | episodes; multiple of 10, `>= 10`, `< episodes` |
| `created_at_episode` | `int` | 0-based episode index; also the first episode using the snapshot |
| `first_episode`, `last_episode` | `int` | inclusive 0-based episode indices |
| `episode` | `int` | 0-based episode index |
| `opening_index` | `int` | index into the five-opening suite |
| `learner_colour` | `Side` | `black` or `white` in CSV |
| `outcome` | `GameOutcome` | `win`, `draw`, or `loss` from the learner's perspective |
| `plies` | `int` | moves after the opening prefix |
| `epsilon` | `float` | dimensionless, `[0, 1]` |
| `table_size` | `int` | number of Q-table entries |
| `table_bytes` | `int` | approximate memory from `estimated_memory_bytes()` |
| `games` | `int` | 1,000 per diagnostic |
| `wins`, `draws`, `losses` | `int` | game counts |
| `score` | `float` | derived score `(wins + 0.5 * draws) / games`, `[0, 1]` |
| `ci_low`, `ci_high` | `float` | 95% interval, `[0, 1]` |

### Snapshot policy and frozen opponent

`src/rlcheckers/training/self_play.py` defines:

```python
class SelfPlayError(RuntimeError): ...

@dataclass(frozen=True)
class Snapshot:
    created_at_episode: int
    table: QTable

    @property
    def table_size(self) -> int: ...

@dataclass(frozen=True)
class SnapshotRecord:
    created_at_episode: int
    first_episode: int
    last_episode: int
    table_size: int

class SnapshotPolicy:
    def __init__(
        self,
        *,
        cadence: int,
        episodes: int,
        max_entries: int,
    ) -> None: ...

    @property
    def cadence(self) -> int: ...

    @property
    def records(self) -> tuple[SnapshotRecord, ...]: ...

    def opponent_for(self, episode: int) -> Snapshot: ...

    def refresh(
        self,
        table: QTable,
        *,
        created_at_episode: int,
    ) -> SnapshotRecord: ...
```

`SnapshotPolicy` owns the one frozen opponent table and the snapshot schedule.
Construction validates `cadence` and `episodes` as described in the units table
and creates the initial snapshot:

- The initial snapshot has `created_at_episode = 0`, an empty `QTable` with
  `max_entries` entries allowed, and `table_size = 0`.
- The initial record is `(created_at_episode=0, first_episode=0,
  last_episode=cadence - 1, table_size=0)`.
- `records` returns only the snapshots created so far, in creation order.
- `opponent_for(episode)` returns the active `Snapshot`. The active record must
  satisfy `first_episode <= episode <= last_episode`; otherwise it raises
  `SelfPlayError` naming the episode and saying that a snapshot refresh is
  overdue. It never falls back to an older snapshot or a random opponent.
- `refresh(table, created_at_episode=e)` is valid only when `e` is exactly the
  next cadence boundary and `e < episodes`. It clones `table` with
  `QTable.clone()`, records `(created_at_episode=e, first_episode=e,
  last_episode=min(e + cadence, episodes) - 1, table_size=clone.size())`,
  makes the clone the active opponent, and returns the record.
- Refreshing at the wrong episode, refreshing the same boundary twice, or
  passing a non-`QTable` raises `SelfPlayError`. A clone failure is wrapped in
  `SelfPlayError`; there is no silent fallback.

The initial empty table is a valid opponent. Because all Q-values are `0.0`,
`QAgent` tie-breaks to the first legal move in `(path, captures)` order. This is
deterministic and uses no RNG.

### `QTable.clone()`

`src/rlcheckers/agents/q_agent.py` adds:

```python
def clone(self) -> QTable: ...
```

The clone has the same entries and the same `max_entries` as the original, and
shares no mutable state. Mutating the learner after a refresh does not change
the snapshot, and mutating the snapshot does not change the learner. Cloning an
empty table is allowed. Cloning does not add keys, so it does not hit the
capacity guard; the clone's own cap still applies to later `set` calls.

### Self-play training loop

`src/rlcheckers/training/self_play.py` defines:

```python
@dataclass(frozen=True)
class SelfPlayEpisodeMetric:
    episode: int
    opening_index: int
    learner_colour: Side
    outcome: GameOutcome
    plies: int
    epsilon: float
    table_size: int
    opponent_snapshot_episode: int
    opponent_table_size: int

@dataclass(frozen=True)
class SelfPlayTrainingResult:
    table: QTable
    metrics: tuple[SelfPlayEpisodeMetric, ...]
    openings: tuple[tuple[Move, ...], ...]
    snapshots: tuple[SnapshotRecord, ...]
    snapshot_interval: int

def train_self_play(
    config: TrainConfig,
    *,
    openings: Sequence[Sequence[Move]] = STANDARD_OPENINGS,
) -> SelfPlayTrainingResult: ...
```

`train_self_play` validates the config before the first game:

- `config.opponent` must be `"self"`; otherwise `ValueError` naming `opponent`.
- `config.snapshot_interval` must be present, an int and not a bool, at least
  `10`, a multiple of `10`, and strictly less than `config.episodes`; otherwise
  `ValueError` naming `snapshot_interval`.
- `config.episodes` must be a positive multiple of `10`; otherwise `ValueError`
  naming `episodes`.
- `openings` must be non-empty; otherwise `ValueError` naming `openings`.

Episode `e` uses the S5 schedule:

- `opening_index = (e // 2) % len(openings)`.
- `learner_colour = Side.BLACK` when `e % 2 == 0`, else `Side.WHITE`.
- `opening = openings[opening_index]` and `state = opening_state(opening)`.
- `epsilon = epsilon_at(e, config.episodes, config.epsilon_start,
  config.epsilon_end, config.epsilon_decay_fraction)`.
- `episode_seed = derive_episode_seed(config.seed, e)`.
- `learner_seed = derive_side_seed(episode_seed, learner_colour)`.
- The learner's exploration RNG is `random.Random(learner_seed)`.
- The opponent uses no RNG. It is `QAgent(snapshot.table)` for the active
  snapshot.

The loop is:

1. Create `SnapshotPolicy(cadence=config.snapshot_interval,
   episodes=config.episodes, max_entries=config.max_table_entries)`.
2. For each `e` in `0..episodes-1`:
   - If `e > 0` and `e % snapshot_interval == 0`, call
     `policy.refresh(table, created_at_episode=e)` before the episode.
   - Get `snapshot = policy.opponent_for(e)` and
     `opponent = QAgent(snapshot.table)`.
   - Build the opening state. If the side to move is not the learner's colour,
     the opponent moves first and counts one ply. If that move ends the game,
     record the outcome and perform no Q-update.
   - While the state is not terminal, use the S5 episode body with the
     snapshot opponent:
     - Choose the learner's move with `choose_epsilon_greedy`.
     - Compute `key = q_key(state, learner_move)` and `current = table.get(key)`.
     - Apply the learner's move and count one ply.
     - If the learner's move ends the game, update with the terminal reward and
       end the episode.
     - Otherwise the opponent replies with `opponent.choose_move(after)` and
       counts one ply.
     - If the opponent's reply ends the game, update with the terminal reward
       and end the episode.
     - Otherwise compute `next_best = table.best_value(next_state)` and pass it
       to `q_update`, which applies gamma; continue from `next_state`.
   - If plies exceed `MAX_GAME_PLIES`, raise `RuntimeError` naming the limit.
   - Append `SelfPlayEpisodeMetric` with the metric fields from S5 plus
     `opponent_snapshot_episode=snapshot.created_at_episode` and
     `opponent_table_size=snapshot.table_size`.
3. Do not create a snapshot after the last episode. A snapshot is created only
   at a boundary strictly before `episodes`, so every record is used for at
   least one episode.
4. Return the learner table, the metrics in episode order, the openings actually
   used, `policy.records`, and `config.snapshot_interval`.

`SelfPlayEpisodeMetric.table_size` is the learner table size after the episode.
`opponent_table_size` is the snapshot's size at creation. The snapshot at
episode `e > 0` is created before episode `e`, so its table size equals the
learner table size after episode `e - 1`.

### Training config

`src/rlcheckers/config.py` keeps the S5 training schema and adds one conditional
field:

```python
@dataclass(frozen=True)
class TrainConfig:
    seed: int
    episodes: int
    alpha: float
    gamma: float
    epsilon_start: float
    epsilon_end: float
    epsilon_decay_fraction: float
    opponent: str
    output_dir: Path
    max_table_entries: int
    snapshot_interval: int | None = None
```

Validation rules:

- `seed`: int, not bool.
- `episodes`: positive int, not bool, and a multiple of 10.
- `alpha`, `gamma`, epsilon endpoints, and `epsilon_decay_fraction`: unchanged
  from spec 0005.
- `opponent`: `"random"` or `"self"`.
- `output_dir`: unchanged from spec 0005.
- `max_table_entries`: positive int, not bool.
- If `opponent == "random"`: `snapshot_interval` must be absent. A present
  `snapshot_interval` raises `ConfigError` naming the key; it is not silently
  ignored.
- If `opponent == "self"`: `snapshot_interval` is required, int not bool, at
  least 10, a multiple of 10, and strictly less than `episodes`. Missing or
  invalid values raise `ConfigError` naming `snapshot_interval`.
- Unknown keys, missing required keys, invalid TOML, and missing files still
  raise `ConfigError`.
- An S5 config with the ten original keys and `opponent = "random"` remains
  valid and loads with `snapshot_interval = None`.

Example self-play `train.toml`:

```toml
seed = 7
episodes = 10000
alpha = 0.1
gamma = 0.9
epsilon_start = 1.0
epsilon_end = 0.05
epsilon_decay_fraction = 0.8
opponent = "self"
output_dir = "out-self-play"
max_table_entries = 2000000
snapshot_interval = 1000
```

The minimum valid self-play run is `episodes = 20` with
`snapshot_interval = 10`: the initial snapshot covers episodes 0–9 and the
first refreshed snapshot covers episodes 10–19.

`train_q` (the S5 fixed-random trainer) rejects a config whose `opponent` is not
`"random"` or whose `snapshot_interval` is not `None`, with a `ValueError`
naming the field. `train_self_play` rejects the converse. The CLI uses the config
to choose the mode; neither trainer silently ignores the other mode's fields.

### Artifacts

`src/rlcheckers/training/self_play.py` defines:

```python
SELF_PLAY_TRAINING_FIELDS = (
    "episode",
    "opening_index",
    "learner_colour",
    "outcome",
    "plies",
    "epsilon",
    "table_size",
    "opponent_snapshot_episode",
    "opponent_table_size",
)

def write_self_play_artifacts(
    result: SelfPlayTrainingResult,
    diagnostics: Mapping[str, ArenaResult],
    config: TrainConfig,
    *,
    command_line: Sequence[str],
) -> Path: ...
```

`diagnostics` must contain exactly the keys `"random"` and `"greedy"`. Before
creating anything, the writer validates:

- `len(result.metrics) == config.episodes`.
- `config.opponent == "self"` and `config.snapshot_interval` is valid.
- `result.snapshot_interval == config.snapshot_interval`.
- `result.snapshots` is non-empty; the first record is
  `(0, 0, snapshot_interval - 1, 0)`; every record's `first_episode` equals its
  `created_at_episode`; every `created_at_episode` is a multiple of the interval
  and strictly increasing; every `last_episode` equals
  `min(created_at_episode + interval, episodes) - 1`; the final record ends at
  `episodes - 1`; and, for `created_at_episode > 0`, the record's `table_size`
  equals `result.metrics[created_at_episode - 1].table_size`.
- Every metric's `opponent_snapshot_episode` is the greatest record
  `created_at_episode <= metric.episode`, and its `opponent_table_size` matches
  that record.
- Each diagnostic has `agent_name == "q"`, `opponent_name` equal to its mapping
  key, `seed == config.seed`, exactly `DIAGNOSTIC_GAMES` (1,000) games, and
  `openings == result.openings`.
- The diagnostic names are exactly `{"random", "greedy"}`.

A mismatch raises `ValueError` naming the problem. The output directory is not
created and no files are written before validation succeeds.

#### `q_table.json`

Same JSON document format and top-level keys as S5: `format`, `version`,
`metadata`, and `table`. `format` is `"rlcheckers.qtable"`, `version` is `1`,
and keys are decimal strings. `metadata` has exactly `config`,
`package_version`, `python_version`, `seed`, and `table_size`. The `config`
object is the self-play config dict with all eleven fields, including
`"opponent": "self"` and `"snapshot_interval": N`. The S5 fixed-random Q-table
metadata keeps its ten-field config. `QTable.load` reads the saved cap from
`metadata.config.max_table_entries` and does not require the S5 key set.

#### `training.csv`

Header, in this exact order:

```text
episode,opening_index,learner_colour,outcome,plies,epsilon,table_size,opponent_snapshot_episode,opponent_table_size
```

One row per `SelfPlayEpisodeMetric`, in episode order. `learner_colour` is
`black` or `white`; `outcome` is `win`, `draw`, or `loss`; `epsilon` uses
`format_float`. The file uses `\n` line endings and is byte-reproducible for the
same result and config.

Example rows for a 20-episode run with interval 10 (illustrative values):

```text
episode,opening_index,learner_colour,outcome,plies,epsilon,table_size,opponent_snapshot_episode,opponent_table_size
0,0,black,win,14,1.000000,3,0,0
1,0,white,loss,16,1.000000,5,0,0
9,4,white,win,13,0.465625,20,0,0
10,0,black,draw,18,0.406250,22,10,20
19,4,white,win,15,0.050000,35,10,20
```

The snapshot at episode 10 has 20 entries because it was cloned after episode 9,
whose `table_size` is 20.

#### `run.json`

A JSON object with exactly these top-level keys:

```json
{
  "command_line": ["rlcheckers", "train-q", "--config", "self-play.toml"],
  "config": {
    "alpha": 0.1,
    "epsilon_decay_fraction": 0.8,
    "epsilon_end": 0.05,
    "epsilon_start": 1.0,
    "episodes": 10000,
    "gamma": 0.9,
    "max_table_entries": 2000000,
    "opponent": "self",
    "output_dir": "C:\\...\\out-self-play",
    "seed": 7,
    "snapshot_interval": 1000
  },
  "diagnostics": {
    "greedy": {
      "agent": "q",
      "ci_high": 0.67,
      "ci_low": 0.61,
      "draws": 120,
      "games": 1000,
      "losses": 300,
      "opponent": "greedy",
      "score": 0.64,
      "wins": 580
    },
    "random": {
      "agent": "q",
      "ci_high": 0.75,
      "ci_low": 0.69,
      "draws": 40,
      "games": 1000,
      "losses": 260,
      "opponent": "random",
      "score": 0.72,
      "wins": 700
    }
  },
  "openings": [
    {"index": 0, "state_key": 235602448969},
    {"index": 1, "state_key": 785358295113},
    {"index": 2, "state_key": 785360355913},
    {"index": 3, "state_key": 235206119497},
    {"index": 4, "state_key": 235554996809}
  ],
  "package_version": "0.1.0",
  "python_version": "3.14.0",
  "snapshots": [
    {"created_at_episode": 0, "first_episode": 0, "last_episode": 999, "table_size": 0},
    {"created_at_episode": 1000, "first_episode": 1000, "last_episode": 1999, "table_size": 1234},
    {"created_at_episode": 2000, "first_episode": 2000, "last_episode": 2999, "table_size": 2500},
    {"created_at_episode": 3000, "first_episode": 3000, "last_episode": 3999, "table_size": 4000},
    {"created_at_episode": 4000, "first_episode": 4000, "last_episode": 4999, "table_size": 6000},
    {"created_at_episode": 5000, "first_episode": 5000, "last_episode": 5999, "table_size": 8000},
    {"created_at_episode": 6000, "first_episode": 6000, "last_episode": 6999, "table_size": 11000},
    {"created_at_episode": 7000, "first_episode": 7000, "last_episode": 7999, "table_size": 14000},
    {"created_at_episode": 8000, "first_episode": 8000, "last_episode": 8999, "table_size": 17000},
    {"created_at_episode": 9000, "first_episode": 9000, "last_episode": 9999, "table_size": 21000}
  ],
  "table_bytes": 456789,
  "table_size": 21773
}
```

The diagnostic values and snapshot table sizes are illustrative; a
10,000-episode run with interval 1,000 has ten records, at 0, 1,000, …, 9,000.
The file uses `indent=2`, `sort_keys=True`, and a trailing newline, and is
byte-reproducible for the same run. The S5 `run.json` schema is unchanged for
fixed-random runs.

#### `learning_curve.png`

The plot uses the Agg backend and has episode on the x-axis and rate in `[0, 1]`
on the y-axis. It shows three rolling lines from the learner's perspective: win
rate, draw rate, and loss rate. The rolling window is `min(100, episode + 1)`.
The title is `Self-play training, seed <seed>`. The legend names the three
lines. The plot is generated from the metrics and config; no hidden training
state is used. The PNG is reproducible in content, not byte-identical across
environments. The S5 `write_learning_curve` gains a `title_prefix` keyword with
default `"Q-learning training"`; S5 callers are unchanged. Its metric parameter
accepts either metric type, or a small protocol with `episode` and `outcome`, so
the plotting logic is shared.

### CLI

`src/rlcheckers/cli.py` keeps the command name and dispatches on the config:

```text
python -m rlcheckers train-q --config PATH
```

- `--config` is required. Missing or unparseable arguments are `argparse` errors
  with exit code 2 and usage on stderr.
- If `config.opponent == "random"`, the S5 path runs unchanged: `train_q`, one
  1,000-game diagnostic against random, the S5 artifacts, and the S5 13-line
  summary.
- If `config.opponent == "self"`, the S6 path runs: `train_self_play`, two
  1,000-game diagnostics (random and greedy), the self-play artifacts, and the
  self-play summary below. Both diagnostics use `QAgent(result.table)`, the
  matching baseline factory, `seed=config.seed`, `games=DIAGNOSTIC_GAMES`, and
  `openings=result.openings`.
- Runtime problems (config validation, snapshot failure, capacity overflow,
  illegal move, non-termination, filesystem error) print `error: <message>` to
  stderr and return 1.

On a successful self-play run, the command prints exactly these 21 lines:

```text
episodes: <episodes>
seed: <seed>
snapshot_interval: <snapshot_interval>
snapshots: <len(result.snapshots)>
table_size: <result.table.size()>
table_bytes: <result.table.estimated_memory_bytes()>
agent: q
opponent: self
random_games: 1000
random_wins: <random wins>
random_draws: <random draws>
random_losses: <random losses>
random_score: <format_float(random score)>
random_ci95: <format_float(random ci_low)>..<format_float(random ci_high)>
greedy_games: 1000
greedy_wins: <greedy wins>
greedy_draws: <greedy draws>
greedy_losses: <greedy losses>
greedy_score: <format_float(greedy score)>
greedy_ci95: <format_float(greedy ci_low)>..<format_float(greedy ci_high)>
artifacts: <config.output_dir>
```

`opponent: self` names the training opponent; the two diagnostic blocks name
their own opponents. The command records `["rlcheckers", *argv]` as
`command_line`, where `argv` includes `train-q`, mirroring S4 and S5.

### Performance

A 10,000-episode self-play run has roughly the same per-episode move cost as S5,
plus a table clone every N episodes. With the example `snapshot_interval = 1000`
there are ten clone operations, but only one clone is retained at a time, so
peak extra memory is one table. The two 1,000-game diagnostics add about 2,000
games. The run should finish in minutes on 5x5. Do not add caching, parallel
training, resumable checkpoints, or snapshot files in this slice. Profile first
if the run is materially slower.

## Acceptance criteria

The examples are illustrative. They give one happy path, one boundary, and one
failure per criterion; the named tests below prove them. No test code appears
in this spec.

### A1 — Snapshot policy and cadence

- **Happy:** With `cadence=10` and `episodes=20`, the policy starts with the
  record `(created_at_episode=0, first_episode=0, last_episode=9,
  table_size=0)`. After refreshing a table of 5 entries at
  `created_at_episode=10`, it has the second record `(10, 10, 19, 5)`.
  `opponent_for(0)` and `opponent_for(9)` return the initial snapshot;
  `opponent_for(10)` and `opponent_for(19)` return the second snapshot.
- **Boundary:** With `cadence=20` and `episodes=30`, the records are
  `(0, 0, 19, 0)` and `(20, 20, 29, n)`; the second snapshot is used for
  exactly episodes 20–29. With `cadence=10` and `episodes=20`, the minimum
  valid self-play run has exactly two snapshots and no unused snapshot.
- **Failure:** Calling `opponent_for(10)` before refreshing at 10 raises
  `SelfPlayError` naming episode 10 and saying the refresh is overdue.
  Refreshing at 9, refreshing 10 twice, or refreshing at 20 when
  `episodes=20` also raises `SelfPlayError`. A non-table refresh target raises
  `SelfPlayError` naming the snapshot; it never falls back to the empty
  opponent.

### A2 — Frozen opponent

- **Happy:** `QTable.clone()` returns an equal table with the same cap. After
  the learner adds or changes entries, the snapshot's entries and legal move
  choices are unchanged. After the snapshot is refreshed, the opponent's choice
  is based on the cloned table, not on later learner updates.
- **Boundary:** Cloning an empty table yields size 0. Cloning a table at its cap
  preserves the cap; the clone can update existing keys but a new key raises
  `TableCapacityError` at the same limit.
- **Failure:** A refresh whose table cannot be cloned raises `SelfPlayError`
  containing `snapshot`; training stops rather than continuing against the
  previous or empty opponent.

### A3 — Self-play schedule, metrics, and smoke run

- **Happy:** A 20-episode run with `snapshot_interval=10` and seed 7 produces 20
  metrics. Opening indices are `[0, 0, 1, 1, 2, 2, 3, 3, 4, 4]` repeated twice;
  learner colours alternate black, white. There are two snapshot records.
  Metrics 0–9 have `opponent_snapshot_episode=0` and
  `opponent_table_size=0`; metrics 10–19 have
  `opponent_snapshot_episode=10` and the second record's size. The second
  record's `table_size` equals metric 9's `table_size`. The final learner table
  is non-empty and within the cap.
- **Boundary:** A 30-episode run with `snapshot_interval=20` has two records and
  uses the second for episodes 20–29; the second record's `table_size` equals
  metric 19's `table_size`. A 200-episode smoke run with
  `snapshot_interval=100` completes, all metrics have valid outcomes, and the
  table is non-empty.
- **Failure:** `episodes=20` with `snapshot_interval=20` raises `ValueError`
  naming `snapshot_interval` and `episodes`; `snapshot_interval=15` raises
  `ValueError` naming the multiple-of-10 rule; `train_self_play` with
  `opponent="random"` raises `ValueError` naming `opponent`; with
  `snapshot_interval=None` it raises `ValueError` naming `snapshot_interval`.

### A4 — Reproducibility and loud failure

- **Happy:** Two runs with the same config and master seed produce equal
  `table`, `metrics`, `openings`, `snapshots`, and `snapshot_interval`. The
  learner seeds are derived per episode exactly as in S5.
- **Boundary:** The initial opponent is deterministic: the empty table makes
  `QAgent` choose the first legal move, and no opponent RNG is used. A repeated
  run reproduces the same first opponent move and the same snapshot boundaries.
- **Failure:** A snapshot failure inside the policy propagates out of
  `train_self_play` as `SelfPlayError`; the trainer does not catch it, substitute
  an earlier snapshot, or continue silently. A missing refresh raises rather
  than reusing the previous snapshot.

### A5 — Training config

- **Happy:** A self-play TOML with the eleven keys loads with
  `opponent="self"`, `snapshot_interval=1000`, and a resolved absolute
  `output_dir`.
- **Boundary:** An S5 TOML with the ten original keys and
  `opponent="random"` still loads with `snapshot_interval=None`. The minimum
  self-play config, `episodes=20` and `snapshot_interval=10`, loads.
- **Failure:** A self-play TOML missing `snapshot_interval` raises
  `ConfigError` naming `snapshot_interval`. A random TOML that includes
  `snapshot_interval` raises `ConfigError` naming `snapshot_interval`;
  `snapshot_interval=15` fails the multiple-of-10 rule; `snapshot_interval=20`
  with `episodes=20` fails the less-than-episodes rule; a bool, string, zero, or
  negative interval fails. Unknown keys and invalid TOML still raise
  `ConfigError`.

### A6 — Artifacts

- **Happy:** A 20-episode self-play result and two 1,000-game diagnostics
  (random and greedy) write `q_table.json`, `training.csv`, `run.json`, and
  `learning_curve.png` under the resolved output directory. The CSV header is
  exactly `SELF_PLAY_TRAINING_FIELDS` and has 20 rows. `run.json` has exactly
  `command_line`, `config`, `diagnostics`, `openings`, `package_version`,
  `python_version`, `snapshots`, `table_bytes`, and `table_size`. The Q-table
  metadata config includes `opponent="self"` and `snapshot_interval`.
- **Boundary:** Writing twice to the same directory produces identical bytes for
  `q_table.json`, `training.csv`, and `run.json`, and leaves unrelated files
  alone. The `snapshots` records match the CSV's opponent identities and the
  boundary table sizes.
- **Failure:** A missing diagnostic, an unexpected diagnostic key, a wrong
  diagnostic seed, a game count other than 1,000, different openings, a metric
  count different from `episodes`, or a snapshot schedule inconsistent with the
  metrics raises `ValueError` naming the problem. The output directory is not
  created and no partial files are written.

### A7 — CLI

- **Happy:** `python -m rlcheckers train-q --config self-play.toml` returns 0,
  writes the four artifacts, and prints the exact 21-line self-play summary with
  the snapshot count and both diagnostic blocks. `stderr` is empty.
- **Boundary:** The same command with an S5 `opponent="random"` config still
  prints the exact S5 13-line summary, writes the S5 schema, and does not require
  `snapshot_interval`.
- **Failure:** `train-q` without `--config` exits 2 with usage on stderr. A
  self-play config with `snapshot_interval=20` and `episodes=20` returns 1,
  prints `error:` naming `snapshot_interval`, and prints nothing to stdout. A
  runtime snapshot failure also returns 1 with `error:`. The module entry point
  `python -m rlcheckers train-q --config ...` behaves the same in a subprocess.

### A8 — Improvement diagnostic

- **Happy:** A slow test trains 10,000 episodes with seed 7 and
  `snapshot_interval=1000`, then plays 1,000 games against random and 1,000
  against greedy over the five-opening suite and both colours. Each diagnostic
  has W + D + L = 1,000, a score in `[0, 1]`, and a 95% interval in `[0, 1]`.
  Both derived scores are strictly greater than 0.50.
- **Boundary:** The point estimate is the S6 diagnostic threshold. The 95%
  interval may cross 0.50 and is reported; the S7 mean-plus-floor gate is not
  applied here. S6 may still be below the final gate thresholds.
- **Failure:** If either score is at or below 0.50, the slow test fails with the
  W/D/L and score in its message. The next action is to inspect snapshot
  cadence, state coverage, and table growth; do not change the game rules or
  hide the result. The observed W/D/L, scores, intervals, table size, and
  snapshot count are recorded in `docs/state.md`.

### A9 — Documentation

`docs/architecture.md` records the snapshot policy, self-play trainer, config
extension, artifacts, plot, and the two diagnostic paths, and keeps the S6/S7
boundaries accurate. `README.md` updates its status and shows a self-play config
and:

```powershell
.\.venv\Scripts\python.exe -m rlcheckers train-q --config train.toml
```

Module docstrings in `self_play.py`, `q_agent.py`, `config.py`, and `cli.py`
state the contracts above in a short paragraph. `docs/plan.md` marks S6
complete when the slice is finished. `docs/state.md` records the handoff and the
slow diagnostic result. ADR 0006 is already accepted; keep its status and
approval record accurate. The spec's Markdown overview is a table per decision
8; any console diagram uses plain labels, no HTML, and no fills. The S4 and S5
figures are corrected if touched.

## Tests to add

| Criterion | Tests |
|---|---|
| A1 | `test_snapshot_policy_initial_record`, `test_snapshot_policy_refreshes_every_cadence`, `test_snapshot_policy_uses_latest_snapshot`, `test_snapshot_policy_rejects_missed_refresh`, `test_snapshot_policy_rejects_unscheduled_refresh`, `test_snapshot_policy_rejects_duplicate_refresh`, `test_snapshot_policy_rejects_bad_cadence`, `test_snapshot_policy_rejects_cadence_not_less_than_episodes`, `test_snapshot_policy_rejects_out_of_range_episode` |
| A2 | `test_q_table_clone_is_independent`, `test_q_table_clone_preserves_cap`, `test_snapshot_policy_refresh_freezes_learner_table`, `test_snapshot_policy_refresh_rejects_non_table` |
| A3 | `test_train_self_play_episode_schedule`, `test_train_self_play_snapshot_boundaries`, `test_train_self_play_uses_both_colours`, `test_train_self_play_metrics_match_snapshots`, `test_train_self_play_minimum_run`, `test_train_self_play_30_episodes_with_20_interval`, `test_train_self_play_smoke`, `test_train_self_play_rejects_bad_opponent`, `test_train_self_play_rejects_missing_snapshot_interval`, `test_train_self_play_rejects_interval_not_less_than_episodes` |
| A4 | `test_train_self_play_is_reproducible`, `test_train_self_play_initial_opponent_is_deterministic`, `test_train_self_play_propagates_snapshot_error`, `test_train_self_play_rejects_random_opponent` |
| A5 | `test_load_self_play_config_reads_snapshot_interval`, `test_load_train_config_keeps_random_config_without_interval`, `test_load_train_config_accepts_minimum_self_play`, `test_load_train_config_rejects_missing_snapshot_interval`, `test_load_train_config_rejects_interval_with_random_opponent`, `test_load_train_config_rejects_bad_snapshot_interval`, `test_load_train_config_rejects_interval_not_less_than_episodes`, `test_load_train_config_rejects_bad_opponent` |
| A6 | `test_write_self_play_artifacts_creates_files`, `test_self_play_training_csv_schema`, `test_self_play_run_json_schema`, `test_self_play_q_table_metadata`, `test_self_play_artifacts_are_byte_reproducible`, `test_write_self_play_artifacts_preserves_unrelated_files`, `test_write_self_play_artifacts_rejects_missing_diagnostic`, `test_write_self_play_artifacts_rejects_mismatched_seed`, `test_write_self_play_artifacts_rejects_wrong_games`, `test_write_self_play_artifacts_rejects_mismatched_config`, `test_write_self_play_artifacts_rejects_bad_snapshot_schedule`, `test_self_play_learning_curve_is_written` |
| A7 | `test_cli_train_q_self_play_writes_artifacts`, `test_cli_train_q_self_play_stdout`, `test_cli_train_q_self_play_is_reproducible`, `test_cli_train_q_self_play_requires_config`, `test_cli_train_q_self_play_reports_config_error`, `test_cli_train_q_self_play_reports_snapshot_error`, `test_cli_train_q_random_mode_unchanged`, `test_module_entry_point_runs_self_play` |
| A8 | `test_train_self_play_improves_against_random_and_greedy` (slow) |
| A9 | Documentation review, not a unit test |

Test files:

- `tests/agents/test_q_agent.py` — A2 clone tests, next to the S5 QTable tests.
- `tests/training/test_self_play.py` — A1–A4, A6, and A8.
- `tests/test_config.py` — A5, next to the `TrainConfig` tests.
- `tests/test_cli.py` — A7, next to the `train-q` tests.

Tests use plain `pytest` assertions, `pytest.raises` with `match` for errors,
`tmp_path` for files, `capsys` for output, and local fake tables or monkeypatch
for forced snapshot failures. The slow improvement test uses the `slow` marker.
No fake table or monkeypatch target becomes production API.

## TDD order

S6 is an M slice. Follow this order and stop at a testable boundary if the
session runs out; do not carry a half-finished slice across turns.

1. **Bootstrap before the first red test:** add the `TrainConfig.snapshot_interval`
   field with default `None`, add a `QTable.clone()` stub that raises
   `NotImplementedError`, create `training/self_play.py` with the public
   signatures and `NotImplementedError` bodies, update the training re-exports,
   and add a CLI dispatch skeleton that routes to the stubs. Keep the S5 config
   loader behaviour intact. Verify the imports. Do not implement clone or
   conditional config validation yet; A2 and A5 drive those behaviours with
   failing tests. The first failure must be missing behaviour, not a missing
   module.
2. Add A2: `QTable.clone()` independence and cap, and the policy's frozen
   refresh. Commit the frozen-table boundary when green.
3. Add A1: the snapshot policy records, cadence, latest-snapshot selection, and
   loud refresh failures. Commit the policy boundary when green.
4. Add A5: the self-play config and the preserved random config. Commit.
5. Add A3 and A4: the self-play loop, schedule, metrics, boundaries,
   reproducibility, and error propagation. Split the loop from the smoke test
   if the session is short; commit each green boundary.
6. Add A6: the four artifacts, plot title, schemas, byte reproducibility, and
   integrity checks. Commit the composition boundary when green.
7. Add A7: CLI dispatch for both modes, the 21-line self-play summary, the
   unchanged 13-line random summary, and the subprocess entry point. Commit.
8. Add A8: the slow 10,000-episode diagnostic. Run it explicitly and record the
   observed W/D/L, scores, intervals, table size, and snapshot count. If it does
   not improve, inspect cadence, state coverage, and table growth; do not change
   the game rules or hide the result.
9. Add A9: update `docs/architecture.md`, `README.md`, `docs/plan.md`,
   `docs/state.md`, ADR 0006, and module docstrings. Run the full suite and
   `ruff check .`; commit. Do not push unless asked.

## Out of scope

- The S7 three-seed gate, the mean-plus-floor rule, the milestone report, and
  the final gate decision.
- Snapshot pools, leagues, opponent sampling, shared-table simultaneous
  self-play, and any opponent diversity beyond the single latest snapshot.
- Persisting intermediate snapshot files, resumable runs, mid-run checkpoints,
  and training resumption.
- Changing the learning state to include repetition or no-progress counters.
  S6 keeps the S5 board-only key. If self-play draws dominate, that is a
  follow-up ADR, not a silent S6 change.
- Afterstates, function approximation, neural networks, DQN, AlphaZero, MCTS,
  and GPU training.
- Reward shaping, material shaping, draw-avoidance rewards, and changing the
  terminal `+1/0/-1` reward.
- Changes to the S4 evaluation contract, opening suite, or the S4 `evaluate`
  artifacts (`metrics.csv`, `games.csv`, `run.json`) and CLI.
- Registering the Q-agent in `make_agent`, loading a saved Q-table through
  `evaluate`, or adding a playable Q-agent CLI.
- Configurable opening suites; S6 uses the S4 five-opening suite.
- Multiple training seeds in one S6 run; S7 owns the three seeds.
- Hyperparameter search, sweeps, tuning scripts, or schedules beyond the fixed
  epsilon schedule.
- Q-table eviction, LRU, pruning, or truncation. The S5 cap still raises.
- A new `train-self-play` command. S6 reuses `train-q` and selects the mode from
  the config; if review prefers a separate command, that is a review change.
- Pickle, NPZ, SQLite, compressed persistence, or separate snapshot files.
- Plot customization beyond the one learning curve; no dashboards or reports.
- Full 8x8 checkers, an interactive UI, packaging, publishing, cloud, or
  distributed training.
- Performance work beyond straightforward Python. Profile a 10,000-episode run
  before optimizing.

## Contradictions, gaps, and decisions

These were the concrete choices approved in `/spec-review S6`. Each restates
the change, the recommendation, and the alternative.

1. **Cadence must be smaller than the episode budget.** What changes:
   self-play configs with `snapshot_interval >= episodes` are rejected. Choose
   the recommended reject. Alternative: allow them and train the whole run
   against the initial empty table. Reason: with no refresh before the end, the
   run never uses a refreshed snapshot, so it is not self-play and fails the
   slice's observable outcome. This refines ADR 0006 §2, which fixes the
   multiple-of-10 and minimum-10 rules but not this upper bound.

2. **`snapshot_interval` is conditional, not a new universal key.** What
   changes: `TrainConfig` gains `snapshot_interval: int | None = None`;
   `opponent` accepts `"random"` or `"self"`; self-play requires the interval,
   random mode forbids it. Choose the recommended conditional schema.
   Alternative: require the key for every config, which breaks existing S5
   configs, or add a separate `SelfPlayConfig` and loader. Reason: S5 configs
   and artifacts remain loadable and byte-compatible, and ADR 0006 §5 describes
   a training-config mode rather than a separate schema.

3. **Self-play artifacts reuse the S5 filenames but have a mode-specific
   schema.** What changes: self-play `training.csv` has two extra columns
   (`opponent_snapshot_episode`, `opponent_table_size`); self-play `run.json` has
   `diagnostics` and `snapshots` instead of `diagnostic`. S5 fixed-random runs
   keep their exact S5 schema and bytes. Choose the recommended mode-specific
   schema, identified by `config.opponent`. Alternative: one extended schema
   for both modes, which changes the S5 contract, or distinct filenames such as
   `self_play_training.csv`. Reason: ADR 0006 §5 requires the opponent snapshot
   identity and schedule; preserving the S5 contract avoids invalidating S5
   artifacts. This does not change what a result means because the mode is
   recorded in the config.

4. **Only the latest snapshot table is retained in memory.** What changes: the
   policy keeps one frozen opponent table; `run.json` and
   `SelfPlayTrainingResult` keep metadata records for every snapshot. Choose the
   recommended latest-only table. Alternative: keep every snapshot table or
   persist snapshot files. Reason: design note 0006 says the learner keeps one
   table and one frozen opponent; ADR 0006 §3 allows intermediate opponent
   tables not to be inspectable. This keeps memory bounded for small cadences.

5. **S6 uses a diagnostic threshold of greater than 0.50 against each fixed
   baseline.** What changes: the slow test checks the point-estimate derived
   score against random and greedy; the 95% interval may cross 0.50. Choose the
   recommended >0.50. Alternative: apply the S7 gate thresholds (0.60 vs random,
   0.55 vs greedy) in S6. Reason: ADR 0006 §4 says S6 is a diagnostic and may be
   below the final gate; the gate needs three seeds and is S7. A failure means
   inspect cadence, coverage, and table growth, not change the game rules.

6. **`train-q` dispatches on the config; there is no new command.** What
   changes: `train-q` runs fixed-random training for `opponent="random"` and
   self-play training for `opponent="self"`. Choose the recommended single
   command. Alternative: add `train-self-play` and keep `train-q` fixed-random.
   Reason: ADR 0006 §5 describes a training mode in the config, and the command
   still trains a Q-table. The plan's S6 "Files touched" list omits
   `src/rlcheckers/cli.py` and `tests/test_cli.py`, but the design note and ADR
   0006 defer the CLI to this spec, so the spec includes them. If the author
   intended S6 to be library-only, remove A7 and the CLI sections at review.

7. **The learning state stays board-only.** What changes: no repetition or
   no-progress counters enter the Q-table key. Choose the recommended S5 state.
   Alternative: include the draw history, which changes the key, table size,
   and comparability with S5. Reason: ADR 0005 §1 deferred a revisit if draws
   dominate; S6 reports draws in both diagnostics. If they dominate, a
   follow-up ADR should change the representation rather than doing it silently
   in S6. The S6 and S5 training results are not directly comparable in any
   case because the opponent distribution changes.

8. **The Markdown overview is a table, not a Mermaid diagram.** What changes:
   Figure 1 is a table, so the spec avoids the conflict between `/spec`'s
   no-HTML-in-Mermaid rule and `AGENTS.md`'s S4 black-text spans. Alternative:
   keep a Mermaid diagram and wrap every node and edge label in the S4 spans.
   Reason: the table conveys the same pipeline, fits the approval view, and
   needs no HTML or viewer-dependent text colour. Console output remains plain.
   This is a docs rule, not an evaluation-contract change, so no ADR is needed.

9. **`QTable.clone()` is a public method.** What changes: `QTable` gains a
   clone that copies entries and the cap. Choose the recommended public clone.
   Alternative: construct a new `QTable` inside `SnapshotPolicy` from
   `table.entries`. Reason: the frozen-copy contract becomes explicit and
   testable, and the plan lists `src/rlcheckers/agents/q_agent.py` as touched.

10. **The initial opponent is the empty table, with no random warm-up.** What
    changes: the first snapshot is the learner's empty table, so the first
    block trains against an untrained greedy self. Choose the recommended empty
    table. Alternative: a random warm-up block or a copy of an S5 table. Reason:
    design note 0006 chooses the empty initial opponent; it explicitly lists a
    warm-up as a change to consider only if the early signal is weak. S6 does
    not add one.

11. **`snapshot_interval` has no hidden default.** What changes: a self-play
    config must state the interval; a random config must omit it. Choose the
    recommended no-default. Alternative: default to 1,000 episodes. Reason: S5
    requires all ten keys with no hidden defaults, and ADR 0006 leaves the
    default to this spec. An explicit interval makes the snapshot schedule part
    of the run's identity.

12. **Both diagnostics use the run seed and the standard opening suite.** What
    changes: random and greedy diagnostics each use `seed=config.seed`, 1,000
    games, the five S4 openings, both colours, and the same final `QAgent`.
    Choose the recommended shared schedule. Alternative: separate diagnostic
    seeds or game counts per opponent. Reason: the fixed baselines are the
    scoreboard; sharing the schedule keeps the two summaries comparable and
    matches S4/S5. The arena still derives per-game and per-side seeds.

13. **No separate snapshot files.** What changes: `run.json` records the
    snapshot schedule; no `snapshots/` directory is written. Choose the
    recommended metadata-only audit. Alternative: persist every snapshot as
    `q_table_<episode>.json`. Reason: ADR 0006 §3 defers snapshot files to the
    spec and no audit need is stated; persisting every snapshot at small cadences
    would create many large files. The final Q-table is saved.

14. **The config key is `snapshot_interval`, measured in episodes.** What
    changes: the new key is named `snapshot_interval`, not `cadence` or
    `snapshot_every`. Choose the recommended name. Alternative: `snapshot_every`
    or `cadence`. Reason: the value is an interval in episodes and the name
    reads directly in TOML; `cadence` remains the prose word in the design note
    and ADR. The exact key name was deferred to this spec by ADR 0006 §5.

## Approval

Approved on 2026-11-06 in `/spec-review S6`.

### Approved decisions

- **Config and CLI:** `TrainConfig.snapshot_interval` is optional with no hidden
  default; `opponent` accepts `"random"` or `"self"`; self-play requires N, a
  multiple of 10, at least 10, and strictly less than `episodes`; random mode
  forbids N; `train-q --config` dispatches on `config.opponent`; no new command.
- **Artifacts:** self-play reuses the S5 filenames with a mode-specific schema;
  `training.csv` adds `opponent_snapshot_episode` and `opponent_table_size`;
  `run.json` uses `diagnostics` and `snapshots`; S5 random schema and bytes are
  unchanged; no separate snapshot files.
- **Diagnostic:** 10,000 episodes, seed 7, `snapshot_interval = 1000`; 1,000
  games each against random and greedy with the run seed and S4 openings; both
  point-estimate scores must be strictly greater than 0.50; the 95% interval is
  reported and may cross 0.50; the S7 gate is not applied; S6 does not require
  beating S5's 0.819 against random.

The other decisions in `## Contradictions, gaps, and decisions` are accepted as
specified.

### Assumptions

- Only the latest snapshot table is retained; all snapshot metadata is in
  `run.json`; no snapshot files are written.
- `QTable.clone()` is public and copies entries and cap without shared mutable
  state.
- The initial opponent is the empty table; there is no random warm-up.
- Learning state stays board-only; no repetition or no-progress counters.
- The config key is `snapshot_interval`, measured in episodes, with no hidden
  default.
- Both diagnostics share the run seed, 1,000 games, the S4 openings, and both
  colours.
- Per-episode CSV records the snapshot creation episode and table size; the full
  first/last range is in `run.json`.
- The S6 plot is the S5-style rolling win/draw/loss training curve, not a
  periodic arena score.
- S6 does not add CLI overrides; the brief's "TOML plus CLI overrides" remains a
  pre-existing gap.
- ADR 0006 is accepted with `N < episodes` recorded as a refinement of §2.

### Deferred

- S7 three-seed gate, mean-plus-floor rule, milestone report, final pass/fail.
- Snapshot pools/leagues, snapshot files, resumable runs, repetition counters,
  afterstates/function approximation, reward shaping, configurable opening
  suites, multiple seeds, hyperparameter search, Q-table eviction, a new
  command, other persistence formats, plot extras, 8x8/UI/packaging/cloud/
  distributed training.

### Corrections applied at approval

- Clarified the S5 update: `next_best = table.best_value(next_state)` is passed
  to `q_update`, which applies gamma.
- Made the `run.json` snapshot example complete for 10,000 episodes and
  `snapshot_interval = 1000`.
- Corrected the performance note to say only one snapshot table is retained.
- Changed TDD step 1 to stubs/signatures only; A2 and A5 drive clone and config
  validation with failing tests.
- Replaced the Markdown Mermaid overview with a table, resolving the `/spec`
  no-HTML rule and `AGENTS.md`'s S4-span rule.

Next: /tdd A2.

