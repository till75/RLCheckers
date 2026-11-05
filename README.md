# RLCheckers

An AI learning project: applying reinforcement learning to a checkers AI, while
learning to co-author a program with opencode.

**Status:** S5: the immutable 5x5 board, legal move generation, game state and
draw detection, seeded random play, the depth-1 greedy baseline, the seeded
evaluation arena, metrics with a 95% interval, TOML configs, CSV/JSON artifacts,
tabular Q-learning against a fixed random opponent, the Q-table/Q-agent, a
learning curve, and the `train-q` CLI are implemented. Self-play and the final
three-seed gate are next.

## Development

Windows and PowerShell, using the virtual environment in `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

The default test run excludes slow tests. The 10,000-episode improvement check is
explicit:

```powershell
.\.venv\Scripts\python.exe -m pytest -m slow tests/training/test_train_q.py::test_train_q_improves_against_random -q
```

## Play a random game

```powershell
.\.venv\Scripts\python.exe -m rlcheckers play-random --seed 7
```

The command prints the seed, each move as a numbered square path, the final
result, and the ply count. Replaying the same seed reproduces the game. See
[docs/specs/0003-game-application-and-random-play.md](docs/specs/0003-game-application-and-random-play.md)
for the exact output contract.

## Evaluate an agent

```powershell
.\.venv\Scripts\python.exe -m rlcheckers evaluate --config eval.toml
```

The config has exactly five keys:

```toml
seed = 7
games = 10
agent = "random"
opponent = "greedy"
output_dir = "results/smoke"
```

`games` must be a positive multiple of ten; `agent` and `opponent` are
`"random"` or `"greedy"`. The command writes `metrics.csv`, `games.csv`, and
`run.json` to `output_dir` and prints the win/draw/loss counts, the derived
score, and its 95% confidence interval. Replaying the same config reproduces the
same games and metrics. S4 writes no plots; S5's training command writes the
learning curve. See
[docs/specs/0004-evaluation-arena.md](docs/specs/0004-evaluation-arena.md) for
the exact contract.

## Train a Q-table

```powershell
.\.venv\Scripts\python.exe -m rlcheckers train-q --config train.toml
```

The training config has exactly ten keys:

```toml
seed = 7
episodes = 10000
alpha = 0.1
gamma = 0.9
epsilon_start = 1.0
epsilon_end = 0.05
epsilon_decay_fraction = 0.8
opponent = "random"
output_dir = "results/train"
max_table_entries = 2000000
```

Episodes are a positive multiple of ten. `alpha` is in `(0, 1]`, `gamma` in
`[0, 1)`, epsilon endpoints are in `[0, 1]` with start at least end, the decay
fraction is in `(0, 1]` (zero is rejected), and `opponent` is `"random"`. The
command trains against the fixed random opponent, saves `q_table.json`,
`training.csv`, `run.json`, and `learning_curve.png`, and prints a 13-line
summary including the 1,000-game diagnostic against random. The diagnostic is
not the S7 gate. See
[docs/specs/0005-tabular-q-learning.md](docs/specs/0005-tabular-q-learning.md)
for the exact contract.

See [AGENTS.md](AGENTS.md) for the working agreement and definition of done.
