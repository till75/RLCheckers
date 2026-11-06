# State — 2026-11-06

## Where we are
S0–S5 are complete, approved, and pushed. S6 (self-play with periodic snapshots)
has its spec approved and ADR 0006 accepted; implementation has not started.

## Done since last handoff
- S6 spec approved 2026-11-06: `docs/specs/0006-self-play-snapshots.md` (untracked).
- ADR 0006 accepted: `docs/adr/0006-self-play-snapshot-policy.md`.
- `docs/plan.md` and this handoff updated; S6 implementation next.
- S5 result: 256 default tests, A9 score 0.819 vs random (794/50/156, CI 0.796–0.842, table 21,773).

## Next
1. Start `/tdd A2`: `QTable.clone()` and the frozen snapshot boundary.
2. Follow the approved TDD order in spec 0006: A2, A1, A5, A3/A4, A6, A7, A8, A9.
3. Do not push S6 without approval.

## Open questions
- None blocking. The three review decisions are recorded in spec 0006’s Approval section.

## Gotchas
- Windows/PowerShell; use `.\.venv\Scripts\python.exe`; `ruff check .` is the gate.
- Default pytest excludes slow tests; A8/A9 slow runs need `-m slow`.
- `/spec-review`: one-page packet, then one round per message; wait for explicit yes/no.
- Spec 0006’s Markdown overview is a table; console diagrams stay plain, no HTML.
- S6 and S5 training curves are not directly comparable; compare final agents on fixed baselines.
- The approved spec and ADR edits are local/uncommitted; nothing pushed.

## Not in an ADR
- S6 config/CLI: conditional `snapshot_interval`, `N < episodes`, `train-q` dispatch.
- S6 artifacts: mode-specific schema, no snapshot files.
- S6 diagnostic: `> 0.50` vs both baselines; S7 owns the gate.
