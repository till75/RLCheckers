# State — 2026-11-03

## Where we are
S4 is complete, approved, and pushed at `b616189`. The workflow change
(`/learn` → `/spec` → `/spec-review` → `/tdd`) is local and unpushed.
191 tests pass and `ruff check .` is clean. S5 (tabular Q-learning) has not started.

## Done since last handoff
- `ff23f98` — S4 bootstrap: protocol, greedy, arena, metrics, artifacts, config, `evaluate` subparser.
- `869e0b4`, `ea3d0d8`, `bbaecd6` — greedy baseline, opening suite, seeded matchup arena.
- `b62fff3`, `d3c8faa`, `a1aa1f9`, `6a24680` — metrics/CI, config, artifacts, `evaluate` CLI.
- `e92f257`, `b616189` — S4 docs and approval record.
- `/learn`, `/spec-review`, design-note template, and `/spec` handoff added locally.

## Next
1. Start S5 with `/learn`: tabular Q-learning; settle the Q-update, epsilon
   schedule, save/load, memory cap, and training config.
2. Write ADR 0005 (Q-learning representation and hyperparameters) before
   implementation; ADR 0004 is plot ownership.
3. Then `/spec` S5 → `/spec-review` → `/tdd`; no push until approval.

## Open questions
- None blocking. S5 hyperparameters and memory cap are undecided until spec 0005.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe` (Python 3.14). `ruff check` is the gate; `ruff format` rewrites Markdown fences.
- `config.py` imports `evaluation.arena`; `artifacts.py` imports `EvalConfig` only under `TYPE_CHECKING`.
- `games` must be a positive multiple of 10; `summarize` rejects fewer than two games per group.
- `games.csv` stores the base `game_seed` only; side seeds are derived.
- `run.json` has no timestamp, but `python_version` varies by environment.
- Mermaid: no HTML spans in labels; console prints them literally. Use plain narrow diagrams; tables for classifications.
- `evaluate` maps `OSError`, `RuntimeError`, and `ValueError` to `error:` plus exit 1.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves`; `format_move` is display-only.
- Greedy: men 1, kings 3, `TERMINAL_SCORE = 1000`; ties by smallest `(path, captures)`.
- S4 writes three artifacts, one seed per run, derived side seeds, CI clamped to `[0, 1]`; the five-opening suite is fixed in code.
- `/spec` no longer asks for approval; `/spec-review` records it.
