# State — 2026-11-03

## Where we are
S3 is complete, approved, and pushed at `2a2c47a`. S4 has started: the plan's
ADR/spec split is reconciled, ADR 0003 (evaluation protocol and gate) is
accepted, and ADR 0004 (plot ownership) resolves the last spec-level conflict.
Spec 0004 is written and proposed, with explanatory diagrams in the spec and
`docs/architecture.md`; Step 2 of the walkthrough is approved, decision 6 is
resolved, and Step 3 is next. The prep commits are local and unpushed; 130 tests
pass and `ruff check .` is clean.

## Done since last handoff
- `b0e87c4`, `295859d` — `GameState`, `GameRecord`, counters, terminal/draw rules, and constructor validation in `state.py`.
- `450c47b` — display-only `format_move` in `moves.py`.
- `702eb74`, `fa66b1a`, `91c175f` — `RandomAgent`, seeded `play_random_game`, seed checks, and the `MAX_GAME_PLIES` guard.
- `75a7250` — `play-random` CLI and `tests/test_cli.py`.
- `d1fdc22`, `22e0808`, `2a2c47a` — S3 spec, README/architecture/plan updates, and push record.
- `4413bb3` — plan reconciliation: ADR 0003 owns evaluation policy; spec 0004 owns the concrete contract.
- `46a4bea` — ADR 0003 written and linked from `docs/architecture.md`.
- `a283938` — handoff note.
- ADR 0003 status corrected to `proposed`, then accepted by the author on 2026-11-01.
- `5240c7c`, `e8f7080` — spec 0004 written, clarified, and proposed.
- Added explanatory, colour-coded diagrams to spec 0004 and `docs/architecture.md`.
- `fcfaf33`, `a4dbe96` — all Mermaid diagrams forced to black text on light
  surfaces, including edge, cluster, participant, and note labels.
- `7d1e5a6` — spec 0004's `eval.toml` example states the input rules in comments.
- Walkthrough Step 2: decisions 1, 3, 9, and 12 accepted; decision 6 resolved by
  ADR 0004.
- ADR 0004 accepted: S4 writes CSV/JSON only; S5/S7 own plot contents; ADR 0003
  §11 superseded in part. The planned Q-learning and self-play ADRs shifted to
  0005 and 0006.

## Next
1. Resume the spec walkthrough at Step 3: agent protocol, registry, and greedy
   baseline (decisions 7 and 13).
2. Finish the remaining walkthrough steps and approve spec 0004.
3. Run `/tdd` for the first S4 behaviour.
4. Keep training code out until the S4 evaluation harness is green.

## Open questions
- No spec-level blocker remains. Decisions 7 and 13 are next in the walkthrough;
  the rest are listed in spec 0004's “Contradictions, gaps, and decisions”
  section.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe` (Python 3.14).
- The package is installed editable, so `python -m rlcheckers` works outside pytest's `src` path.
- `ruff format` also reformats Python fences in Markdown; only `ruff check` is in the gate.
- `Board` validates encoding only; `GameState` adds the at-least-one-piece check.
- `play_random_game` uses one RNG stream for both colours; using two agents requires custom code.
- `play-random` prints moves only; it does not render the board or print a draw reason.
- Generated moves use at most four captures and five path squares, so the six-square action-key limit is not reached.
- ADR 0003 fixes evaluation policy only. Opening positions, baseline functions, seed derivation, the CI method, and CSV/CLI details belong in spec 0004.
- ADR 0004 fixes plot ownership only: S4 writes CSV/JSON, S5/S7 own plot contents. The planned Q-learning and self-play ADRs are now 0005 and 0006.
- Spec 0004 remains `proposed` until the walkthrough finishes; decisions 1, 3, 9, and 12 are accepted, and decision 6 is resolved.
- Diagrams in spec 0004 are explanatory; the tables and prose are the contract.
- Mermaid diagrams force a light base theme and explicit black labels. Sequence diagrams must use theme variables, not inline HTML spans. See the diagram conventions in `AGENTS.md`.
- The gate evaluates greedily; the random baseline still draws from its own seeded stream.

## Not in an ADR
- `apply_move` validates by membership in `generate_moves`.
- `format_move` is display-only and has no inverse parser.
- Draw reason prefers repetition over no-progress.
- Interactive/human play and move parsing are out of scope for S3.
