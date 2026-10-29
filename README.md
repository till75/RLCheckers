# RLCheckers

An AI learning project: applying reinforcement learning to a checkers AI, while
learning to co-author a program with opencode.

**Status:** S2: the immutable 5x5 board, initial position, ASCII renderer,
canonical 40-bit state key, and legal move generation (quiet moves, mandatory
captures, multiple captures, promotion, action keys, and move application) are
implemented. Game state and learning are next.

## Development

Windows and PowerShell, using the virtual environment in `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

See [AGENTS.md](AGENTS.md) for the working agreement and definition of done.
