# State — 2026-10-29

## Where we are
S2 (legal move generation) is complete in the working tree. The full suite is
84 passed and `ruff check .` is clean. Nothing has been pushed.

## Done since last handoff
- Implemented `Move`, `generate_moves`, and `apply_move` in
  `src/rlcheckers/game/moves.py` and re-exported them from
  `src/rlcheckers/game/__init__.py`.
- Added `tests/game/test_moves.py` and `tests/game/test_perft.py`, covering
  mandatory captures, capture branches, promotion, action keys, move
  application, determinism, a seeded playout, and all six perft fixtures at
  depths 1–3.
- Updated `README.md`, `docs/architecture.md`, and the `moves.py` module
  docstring.

## Next
1. Run `/spec` for S3 (`docs/specs/0003-game-application-and-random-play.md`),
   then `/tdd` for its first behaviour.
2. S3 owns game counters, repetition and no-progress draws, terminal win/loss,
   and seeded random play. It wraps the pure `apply_move` from S2.
3. Do not push unless asked.

## Open questions
None blocking.

## Gotchas
- Windows/PowerShell; use .\.venv\Scripts\python.exe (Python 3.14).
- gh is not installed; origin is HTTPS; credentials use Git Credential Manager.
- ruff format also reformats Python code fences in Markdown.
- Board validates encoding only; it does not check reachability or piece counts.
- Initial key is 0x36DB001249; white-to-move key is 0xB6DB001249.
- P6 is the four-capture loop with two capture orders and a path that returns
  to its origin; perft counts paths, not distinct resulting boards.
- Geometry search found at most four captures and five path squares on 5x5, so
  the six-square action-key limit is never reached by generated moves.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves` (approved).
- Action key puts path length in bits 0..2 and squares from bit 3 upward.
