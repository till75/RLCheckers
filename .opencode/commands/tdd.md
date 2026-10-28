---
description: Red-green-refactor for a single behaviour
---

Implement exactly this behaviour with strict TDD: $ARGUMENTS

1. **RED** — write the smallest failing test in `tests/`. Run
   `.\.venv\Scripts\python.exe -m pytest -q <file>` and show the output. It must
   fail on the assertion, not on a missing import or a typo.
2. **GREEN** — the minimum implementation that passes. No speculative
   generality, no unused parameters. Run the tests and show they pass.
3. **REFACTOR** — `.\.venv\Scripts\python.exe -m ruff check . --fix`, tidy
   names, re-run the tests.

Then report the diff summary and what is still untested. Stop after this one
behaviour; do not continue into the next slice.
