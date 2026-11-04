# State — 2026-11-04

## Where we are
S4 is complete, approved, and pushed at `b616189`. The workflow change
(`/learn` → `/spec` → `/spec-review` → `/tdd`) is pushed at `7a2643f`.
S5's `/learn` is done: design note 0005 is chosen and ADR 0005 is proposed.
No S5 code has started. 191 tests pass and `ruff check .` is clean.

## Done since last handoff
- `ff23f98` — S4 bootstrap: protocol, greedy, arena, metrics, artifacts, config, `evaluate` subparser.
- `869e0b4`, `ea3d0d8`, `bbaecd6` — greedy baseline, opening suite, seeded matchup arena.
- `b62fff3`, `d3c8faa`, `a1aa1f9`, `6a24680` — metrics/CI, config, artifacts, `evaluate` CLI.
- `e92f257`, `b616189` — S4 docs and approval record.
- `7a2643f` — workflow change: `/learn`, `/spec-review`, design-note template, and `/spec` handoff; pushed.
- `docs/design/0005-tabular-q-learning.md` — chosen design note for S5.
- `docs/adr/0005-tabular-q-learning.md` — proposed ADR for S5.

## Next
1. Run `/spec` S5, then `/spec-review`; approval happens in the review.
2. Implement S5 with `/tdd`; no push until the slice is approved.
3. Review and approve ADR 0005 in `/spec-review`; it is proposed, not accepted.

## Open questions
- Spec 0005 details: exact config keys, artifact names, CSV columns, plot
  contract, diagnostic game count, and smoke-test episode count.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe` (Python 3.14). `ruff check` is the gate; `ruff format` rewrites Markdown fences.
- `config.py` imports `evaluation.arena`; `artifacts.py` imports `EvalConfig` only under `TYPE_CHECKING`.
- `games` must be a positive multiple of 10; `summarize` rejects fewer than two games per group.
- `games.csv` stores the base `game_seed` only; side seeds are derived.
- `run.json` has no timestamp, but `python_version` varies by environment.
- Mermaid: console = plain labels, no HTML, narrow; Markdown = S4 black-text spans, white/light-grey fills only. See `AGENTS.md` "Two outputs, two rules".
- `evaluate` maps `OSError`, `RuntimeError`, and `ValueError` to `error:` plus exit 1.
- Draw baseline: 7/1,000 random-vs-random draws; 17.5 plies average. The game is not inherently drawish.
- S5 design note chooses the trainer-owned loop, a JSON Q-table, and board-only state. ADR 0005 is proposed; do not implement until `/spec-review` approves.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves`; `format_move` is display-only.
- Greedy: men 1, kings 3, `TERMINAL_SCORE = 1000`; ties by smallest `(path, captures)`.
- S4 writes three artifacts, one seed per run, derived side seeds, CI clamped to `[0, 1]`; the five-opening suite is fixed in code.
- `/spec` no longer asks for approval; `/spec-review` records it.
- S5 design note 0005 is chosen and records the trainer-owned loop; ADR 0005 is proposed. ADR 0005 proposes board-only state, alpha 0.1, gamma 0.9, epsilon 1.0→0.05, JSON persistence.
