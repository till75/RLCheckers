# State — 2026-11-06

## Where we are
S0–S5 are complete, approved, and pushed. S6 (self-play with periodic snapshots)
is implemented through A8; A9 documentation is the remaining slice step.

## Done since last handoff
- S6 spec approved 2026-11-06: `docs/specs/0006-self-play-snapshots.md`.
- ADR 0006 accepted: `docs/adr/0006-self-play-snapshot-policy.md`.
- A2: `QTable.clone()` and the frozen snapshot boundary.
- A1: snapshot records, cadence validation, and loud refresh failures.
- A5: conditional `snapshot_interval` config loading and validation.
- A3/A4: the seeded self-play loop, schedule, metrics, and reproducibility.
- A6: self-play artifacts, schema, integrity checks, and titled curve.
- A7: `train-q` self-play dispatch with random and greedy diagnostics.
- A8 slow diagnostic (seed 7, 10,000 episodes, interval 1,000): table 7,181;
  10 snapshots; random 818/23/159, score 0.829500, CI 0.806659–0.852341;
  greedy 1,000/0/0, score 1.000000, CI 1.000000–1.000000. Both point
  estimates are strictly above 0.50; the S7 gate is not applied.
- S5 result: 256 default tests, A9 score 0.819 vs random (794/50/156, CI
  0.796–0.842, table 21,773).

## Next
1. Finish A9: update `docs/architecture.md`, `README.md`, `docs/plan.md`,
   module docstrings, and this handoff.
2. Run the default suite and `ruff check .`; run `-m slow` for A8 when reporting.
3. Do not push S6 without approval.

## Open questions
- None blocking. The three review decisions are recorded in spec 0006’s Approval section.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe`; `ruff check .` is the gate.
- Default pytest excludes slow tests; A8/A9 slow runs need `-m slow`.
- `/spec-review`: one-page packet, then one round per message; wait for explicit yes/no.
- Spec 0006’s Markdown overview is a table; console diagrams stay plain, no HTML.
- S6 and S5 training curves are not directly comparable; compare final agents on fixed baselines.
- Nothing has been pushed.

## Not in an ADR
- S6 config/CLI: conditional `snapshot_interval`, `N < episodes`, `train-q` dispatch.
- S6 artifacts: mode-specific schema, no snapshot files.
- S6 diagnostic: `> 0.50` vs both baselines; S7 owns the gate.
