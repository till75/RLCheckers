# RLCheckers

An AI learning project: applying reinforcement learning to a checkers AI, while
learning to co-author a program with opencode.

**Status:** S3: the immutable 5x5 board, legal move generation, game state and
draw detection, seeded random play, and the `play-random` CLI command are
implemented. Evaluation and learning are next.

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

See [AGENTS.md](AGENTS.md) for the working agreement and definition of done.
