# AGENTS.md

## Purpose

RLCheckers is a learning project with two goals:

1. Learn how to apply reinforcement learning to a checkers AI.
2. Learn how to co-author a real program with opencode.

Correctness and understanding matter more than speed. Prefer small, explainable
steps over large speculative changes.

## Environment

- Windows, PowerShell.
- Python lives in the project virtual environment:
  `.venv\Scripts\python.exe` (Python 3.14).
- Run every Python command through that interpreter; do not rely on a globally
  activated `python`.
- The repository root is `C:\dev\RLCheckers`.

## Commands

```powershell
# Tests
.\.venv\Scripts\python.exe -m pytest

# Lint
.\.venv\Scripts\python.exe -m ruff check .

# Lint and apply safe fixes
.\.venv\Scripts\python.exe -m ruff check . --fix
```

Add dependencies to the virtual environment only when the current slice needs
them, and record them in the project metadata.

## Working agreement

- **One vertical slice per turn.** A slice includes its test, implementation,
  docs, and commit. Finish it, report, and stop; do not start the next slice
  unless asked.
- **TDD, failing test first.** Show the failing test and its output before
  writing implementation code. The failure must be the missing behaviour, not
  an import or syntax error.
- **Docs ship with behaviour.** Update the README, architecture notes, ADRs, or
  docstrings in the same commit as the change they describe.
- **Conventional Commits.** Use `<type>(<scope>): <imperative subject>` and
  explain why in the body when the reason is not obvious.
- **Never push without being asked.** Commits stay local until explicitly
  requested.

## Definition of done

A slice is done when:

1. A failing test was written and shown first.
2. The new test passes, and the full test suite passes.
3. `ruff check .` reports no errors.
4. Behaviour is documented where a reader would look for it.
5. The change is one coherent Conventional Commit.
6. The project is left in a working state.
7. Nothing has been pushed.
