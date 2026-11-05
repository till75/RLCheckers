# State — 2026-11-04

## Where we are
S4 is complete, approved, and pushed at `b616189`. The workflow change
(`/learn` → `/spec` → `/spec-review` → `/tdd`) is pushed at `7a2643f`.
S5's `/learn` and spec review are done: design note 0005 is chosen, spec 0005 is
approved, and ADR 0005 is accepted. S5 code has started: A1-A8 are implemented
(Q-table, QAgent, training loop, config, artifacts, plot, and `train-q` CLI).
256 tests pass and `ruff check .` is clean, but the full suite now takes about
82s because the artifact and CLI tests retrain and replay 1,000 diagnostic games
each. Local commits after `7a2643f` are not pushed.

## Done since last handoff
- `ff23f98` — S4 bootstrap: protocol, greedy, arena, metrics, artifacts, config, `evaluate` subparser.
- `869e0b4`, `ea3d0d8`, `bbaecd6` — greedy baseline, opening suite, seeded matchup arena.
- `b62fff3`, `d3c8faa`, `a1aa1f9`, `6a24680` — metrics/CI, config, artifacts, `evaluate` CLI.
- `e92f257`, `b616189` — S4 docs and approval record.
- `7a2643f` — workflow change: `/learn`, `/spec-review`, design-note template, and `/spec` handoff; pushed.
- `0da3f19` — design note 0005 and proposed ADR 0005; local.
- `04eb6da` — Mermaid rules split by output; local.
- Approved spec 0005 and accepted ADR 0005; local.
- A1 `q_key` and QTable storage/defaults/cap/memory implemented; 198 tests.
- A2 `q_update` arithmetic and alpha/gamma validation implemented; 203 tests.
- A3 `epsilon_at` schedule and validation implemented; 209 tests.
- A4 best-value/best-move and the greedy QAgent adapter implemented; 214 tests.
- A5 JSON save/load, schema, byte reproducibility, saved cap, and equality; 219 tests.
- A6 fixed-opponent training loop, schedule, rewards, reproducibility, and cap; 225 tests.
- A7 training TOML loader and validation implemented; 243 tests.
- A8 artifacts/plot (`q_table.json`, `training.csv`, `run.json`, PNG) implemented; 250 tests.
- A8 `train-q` CLI, diagnostic, and 13-line stdout implemented; 256 tests.

## Next
1. Add A9: the slow improvement diagnostic.
2. Then A10: documentation and the final slice checks.
3. Do not push local commits without approval.

## Open questions
- None blocking. Continue the spec's TDD order at the improvement diagnostic.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe` (Python 3.14). `ruff check` is the gate; `ruff format` rewrites Markdown fences.
- `config.py` imports `evaluation.arena`; `artifacts.py` imports `EvalConfig` only under `TYPE_CHECKING`.
- `games` must be a positive multiple of 10; `summarize` rejects fewer than two games per group.
- `games.csv` stores the base `game_seed` only; side seeds are derived.
- `run.json` has no timestamp, but `python_version` varies by environment.
- Mermaid: console = plain labels, no HTML, narrow; Markdown = S4 black-text spans, white/light-grey fills only. See `AGENTS.md` "Two outputs, two rules".
- `evaluate` maps `OSError`, `RuntimeError`, and `ValueError` to `error:` plus exit 1.
- Draw baseline: 7/1,000 random-vs-random draws; 17.5 plies average. The game is not inherently drawish.
- Full suite is about 82s after A8: artifact and CLI tests retrain 20 episodes and play 1,000 diagnostic games repeatedly.
- S5 design note chooses the trainer-owned loop, a JSON Q-table, and board-only state. ADR 0005 is accepted; implementation starts with `/tdd A1`.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves`; `format_move` is display-only.
- Greedy: men 1, kings 3, `TERMINAL_SCORE = 1000`; ties by smallest `(path, captures)`.
- S4 writes three artifacts, one seed per run, derived side seeds, CI clamped to `[0, 1]`; the five-opening suite is fixed in code.
- `/spec` no longer asks for approval; `/spec-review` records it.
- S5 design note 0005 is chosen and records the trainer-owned loop; ADR 0005 is accepted. It fixes board-only state, alpha 0.1, gamma 0.9, epsilon 1.0→0.05, JSON persistence, episodes as a multiple of 10, and alpha/gamma ranges.
