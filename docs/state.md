# State — 2026-11-09

## Where we are
S0–S7 are complete, approved, and pushed. The first milestone is complete and the three-seed gate passed. No active slice.

## Done since last handoff
- Full S7 gate passed: random mean 0.830667 (min 0.818000), stochastic greedy mean 0.816833 (min 0.800500). Evidence: `docs/results/s7-three-seed-gate-diagnostics.md`, `docs/results/gate.json`.
- Milestone summary and README updated: `docs/results/first-milestone.md`, `README.md`; commit `48baf05`.
- S7 approved and pushed: commit `5fd3e2c`.
- Local Repomix snapshot at `.repomix/rlcheckers-repomix.md`; `.repomix/` ignored in commit `9995c35` (local only).
- Full suite: 382 passed, 2 deselected; `ruff check .` clean.

## Next
1. Run `/learn` for the next milestone: stronger baselines, broader robustness, and whether to stay on 5x5.
2. Write the next `/spec`; do not start TDD before `/spec-review` approval.

## Open questions
- Next milestone scope is not chosen. Blocking for `/spec`, not for `/learn`.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe`; default pytest excludes slow tests (`-m slow` includes them).
- Full gate takes ~6 minutes and writes to `docs/results/`; run `gate --config gate.toml` from the repo root because `output_dir` resolves relative to the config file.
- The generated S7 report is reproducible, but its `## Verification commands` section was appended manually.
- Deterministic greedy is 10 unique games, not 1,000 independent samples; depth-2 is a diagnostic, not a gate criterion.
- Repomix output is local only; the `.repomix/` ignore commit is not pushed.

## Not in an ADR
- S7 config/CLI: 14-key gate config, `gate` dispatch, 13-line summary, exit codes.
- S7 artifacts live under `docs/results/`; Q-tables and gate JSON/CSV/plot/report are committed.
- Repomix snapshots are local diagnostic artifacts, not repository content.
