# State — 2026-10-29

## Where we are
S1 (5x5 board and initial position) is complete and pushed at c37bff0.
S2 (legal move generation) has an approved spec but no code or tests yet.

## Done since last handoff
- Wrote and approved `docs/specs/0002-legal-move-generation.md` (untracked):
  public interface, move rules, action key, six perft fixtures, acceptance
  criteria A1–A14, and the TDD order.
- Cross-checked the perft tables with a scratch enumerator outside the repo.
- Confirmed the suite is still 29 passed and `ruff check .` is clean.

## Next
1. Run `/tdd` in a fresh session and start with `test_initial_black_quiet_moves`
   in `tests/game/test_moves.py`.
2. Follow spec 0002's TDD order: bootstrap `moves.py` and the `game` exports,
   then A1, A2/A8/quiet A10–A11, A3–A4, A5–A7, A9/A12, A13, docs.
3. Commit the spec with the coherent S2 change, or split at the quiet-move and
   capture boundaries as the spec allows. Do not push unless asked.

## Open questions
None blocking. All seven spec decisions were approved on 2026-10-29.

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
