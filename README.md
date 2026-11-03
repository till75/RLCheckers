# RLCheckers

An AI learning project: applying reinforcement learning to a checkers AI, while
learning to co-author a program with opencode.

**Status:** S4: the immutable 5x5 board, legal move generation, game state and
draw detection, seeded random play, the depth-1 greedy baseline, the seeded
evaluation arena, metrics with a 95% interval, TOML config, CSV/JSON artifacts,
and the `evaluate` CLI command are implemented. Learning is next.

## Development

Windows and PowerShell, using the virtual environment in `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
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
same games and metrics. S4 writes no plots; plots arrive with training. See
[docs/specs/0004-evaluation-arena.md](docs/specs/0004-evaluation-arena.md) for
the exact contract.

See [AGENTS.md](AGENTS.md) for the working agreement and definition of done.
