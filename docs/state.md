# State — 2026-10-28

## Where we are
S1 (5x5 board and initial position) is complete and pushed at c37bff0.
S2 (legal move generation) has not started. main tracks origin/main.

## Done since last handoff
First handoff; no previous state file.
- f663fd8 scaffolded the project.
- e075b9e added the brainstorm and first-milestone brief.
- 0a7838c added the first-milestone plan.
- 6229844 added ADRs 0001/0002 and the architecture note.
- c37bff0 added the S1 board, spec, project tooling, and 29 tests.

## Next
1. Run /spec for docs/specs/0002-legal-move-generation.md.
2. TDD quiet moves first, then mandatory captures, multiple captures, promotion, kings, edges, and perft/known positions.
3. Update docs, run pytest and ruff, commit S2; do not push unless asked.

## Open questions
None blocking.

## Gotchas
- Windows/PowerShell; use .\.venv\Scripts\python.exe (Python 3.14).
- gh is not installed; origin is HTTPS; credentials use Git Credential Manager.
- ruff format also reformats Python code fences in Markdown.
- Board validates encoding only; it does not check reachability or piece counts.
- Initial key is 0x36DB001249; white-to-move key is 0xB6DB001249.

## Not in an ADR
- Piece and Side are IntEnums normalized in Board.cells.
- ASCII render uses . # b B w W, exact snapshots, no trailing newline.
- Board.from_state_key is included in S1 to satisfy ADR 0002's decoder requirement.
- ValueError for invalid values; TypeError for non-integer keys/coordinates.
- Tooling: setuptools, dev extra, pytest pythonpath=src, ruff E/F/I, line length 88.
- pyproject requires Python >=3.14.
