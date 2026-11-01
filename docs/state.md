# State — 2026-10-31

## Where we are
S3 is complete, approved, and pushed at `2a2c47a`. S4 has started: the plan's
ADR/spec split is reconciled and ADR 0003 (evaluation protocol and gate) is
accepted. Spec 0004 is next. Those two prep commits are local and unpushed; 130
tests pass and `ruff check .` is clean.

## Done since last handoff
- `b0e87c4`, `295859d` — `GameState`, `GameRecord`, counters, terminal/draw rules, and constructor validation in `state.py`.
- `450c47b` — display-only `format_move` in `moves.py`.
- `702eb74`, `fa66b1a`, `91c175f` — `RandomAgent`, seeded `play_random_game`, seed checks, and the `MAX_GAME_PLIES` guard.
- `75a7250` — `play-random` CLI and `tests/test_cli.py`.
- `d1fdc22`, `22e0808`, `2a2c47a` — S3 spec, README/architecture/plan updates, and push record.
- `4413bb3` — plan reconciliation: ADR 0003 owns evaluation policy; spec 0004 owns the concrete contract.
- `46a4bea` — ADR 0003 accepted and linked from `docs/architecture.md`.

## Next
1. Run `/spec` for `0004-evaluation-arena.md` (S4).
2. Run `/tdd` for the first S4 behaviour.
3. Keep training code out until the S4 evaluation harness is green.

## Open questions
None blocking.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe` (Python 3.14).
- The package is installed editable, so `python -m rlcheckers` works outside pytest's `src` path.
- `ruff format` also reformats Python fences in Markdown; only `ruff check` is in the gate.
- `Board` validates encoding only; `GameState` adds the at-least-one-piece check.
- `play_random_game` uses one RNG stream for both colours; using two agents requires custom code.
- `play-random` prints moves only; it does not render the board or print a draw reason.
- Generated moves use at most four captures and five path squares, so the six-square action-key limit is not reached.
- ADR 0003 fixes evaluation policy only. Opening positions, baseline functions, seed derivation, the CI method, and CSV/CLI details belong in spec 0004.
- The gate evaluates greedily; the random baseline still draws from its own seeded stream.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves`.
- `format_move` is display-only and has no inverse parser.
- Draw reason prefers repetition over no-progress.
- Interactive/human play and move parsing are out of scope for S3.
