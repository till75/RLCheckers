# State — 2026-10-30

## Where we are
S3 (game application and random play) is implemented and awaiting approval. The
full suite is 130 passed and `ruff check .` is clean. The working tree is clean.
Nothing has been pushed; `origin/main` is still at `3483f1c`.

## Done since last handoff
- Added `GameState`, `GameRecord`, `Outcome`, and `DrawReason` in
  `src/rlcheckers/game/state.py`, including terminal wins, threefold repetition,
  the 80-ply no-progress draw, draw-reason precedence, and constructor
  validation.
- Added `format_move` for display-only move paths.
- Added `RandomAgent`, `play_random_game`, and the `MAX_GAME_PLIES` guard in
  `src/rlcheckers/agents/random_agent.py`.
- Added the `play-random` CLI command and the `python -m rlcheckers` entry point.
- Added `tests/game/test_state.py`, `tests/agents/test_random_agent.py`, and
  `tests/test_cli.py`.
- Updated `README.md`, `docs/architecture.md`, `docs/plan.md`, and the module
  docstrings for S3.
- Committed S3 as green, behaviour-sized commits.

## Next
1. Review and approve S3, then push the S3 commits.
2. Run `/adr` 0003 for the evaluation protocol (S4).
3. Run `/spec` for `0004-evaluation-arena.md` (S4).
4. Run `/tdd` for the first behaviour in S4.

## Open questions
None blocking.

## Gotchas
- Windows/PowerShell; use .\.venv\Scripts\python.exe (Python 3.14).
- gh is not installed; origin is HTTPS; credentials use Git Credential Manager.
- ruff format also reformats Python code fences in Markdown.
- Board validates encoding only; it does not check reachability or piece counts.
- GameState additionally requires at least one piece and a history whose last
  key matches the board.
- Initial key is 0x36DB001249; white-to-move key is 0xB6DB001249.
- P6 is the four-capture loop with two capture orders and a path that returns
  to its origin; perft counts paths, not distinct resulting boards.
- Geometry search found at most four captures and five path squares on 5x5, so
  the six-square action-key limit is never reached by generated moves.
- `play_random_game` uses one RNG stream for both colours; the same seed
  reproduces the whole game.
- CLI output has no board render, no draw-reason line, and no blank lines.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves` (approved).
- Action key puts path length in bits 0..2 and squares from bit 3 upward.
- Draw reasons prefer threefold repetition over no-progress.
