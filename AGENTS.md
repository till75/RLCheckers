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

## Diagram conventions

These are author preferences, not optional styling:

- Use Mermaid. Do not switch to PlantUML or another diagram tool without
  explicit approval.
- Never rely on the viewer's theme for text colour. Grey text is a defect.
- Start every Mermaid block with the canonical light base theme:

  ```text
  %%{init: {"theme": "base", "themeVariables": {"darkMode": false, "primaryTextColor": "#000000", "secondaryTextColor": "#000000", "tertiaryTextColor": "#000000", "textColor": "#000000", "lineColor": "#334155", "edgeLabelBackground": "#ffffff", "clusterBkg": "#f8fafc", "clusterBorder": "#94a3b8"}}}%%
  ```

### Two outputs, two rules

Console chat and Markdown documents use different renderers. Do not copy one
rule to the other.

- **Console chat:** use plain labels, no HTML, no inline CSS, and no colour
  fills. Use a narrow `flowchart TB`, a text tree, or a table. The console
  chooses text colour; check the console render. HTML spans are Markdown-only
  and print literally here.
- **Markdown documents:** force black text with the S4 technique: wrap every
  node and edge label in `<span style='color:#000000'>...</span>`. Give edge
  labels a white backing. This is allowed here because the Markdown renderer
  interprets it; check light and dark previews.
- **Markdown backgrounds:** use only white or light-grey fills: `#ffffff`,
  `#f8fafc`, `#f1f5f9`, or `#e2e8f0`. Never use a darker fill. Carry category
  meaning with the stroke colour, not the fill.

In flowcharts, give each node a short plain label. If a box needs a title and
summary, use two short lines or split the node; do not use inline HTML for bold.
In sequence diagrams, use theme variables for text colour and no inline HTML.
Use one diagram per job. Split a wide diagram rather than letting it overflow.
Use a table for decision lists and classifications. Use colour to carry meaning,
label arrows, and give each box a title and a short summary. Keep the prose or
table as the contract; the diagram explains. Check every diagram in the console
renderer as well as light and dark Markdown previews. Text that renders as raw
HTML, or is clipped, is a defect.

## Working agreement

- **One vertical slice per turn.** A slice includes its tests, implementation,
  docs, diagnostic report, and commits. Finish it, report, and stop; do not
  start the next slice unless asked.
- **Slice for evaluation.** A slice must have an observable diagnostic report
  and pass/fail evidence. If the slice cannot be evaluated that way, split or
  redefine it before `/spec`.
- **Learn before specifying.** Every slice starts with `/learn` when it
  introduces a new approach or the author has not chosen one. `/learn` ends with
  a one-page design note and an explicit choice. Skip it only when the approach
  is already settled and no new concept is involved.
- **Specify, then review, then approve.** `/spec` writes the contract and ends
  with `/spec-review`. `/spec-review` reviews the contract against the design
  note, resolves concrete decisions, and records approval. `/tdd` starts only
  after that approval.
- **Review questions stand alone.** In `/spec-review` and any approval message,
  restate each decision in full: what changes, the recommended choice, and the
  alternative. Do not refer to "decision 1" or "Round 2" without repeating the
  decision; the author should not have to scroll up. Ask for an explicit yes/no
  per decision.
- **TDD, failing test first.** Show the failing test and its output before
  writing implementation code. The failure must be the missing behaviour, not
  an import or syntax error.
- **Commit each successful TDD cycle.** Treat a cycle as one behaviour-sized
  step, not every edit. A cycle is successful when its new test passes (or, for
  a refactor, the existing tests still pass), the full suite passes, and
  `ruff check .` is clean. Commit the test, implementation, and docs for that
  behaviour together. Never commit a red or partially green tree.
- **A slice may span several commits.** Each commit must be self-contained,
  green, and a coherent Conventional Commit. Do not squash or rewrite history
  unless asked.
- **Docs ship with behaviour.** Update the README, architecture notes, ADRs, or
  docstrings in the same commit as the change they describe. Docs that describe
  the whole slice belong in the slice's final commit.
- **Conventional Commits.** Use `<type>(<scope>): <imperative subject>` and
  explain why in the body when the reason is not obvious.
- **Push only at the end of a slice, after approval.** Do not push mid-slice.
  Wait for explicit approval that the slice is implemented, tested, documented,
  and ready. Approval applies to that slice only; it is not blanket permission
  for later pushes.

## Slice diagnostic reports

Every slice must produce a diagnostic report under `docs/results/` named
`<slice-id>-diagnostics.md`. The report is the artefact that records why the
slice was accepted and why we moved on. It is part of the final TDD cycle, not a
separate afterthought.

A slice is only well-formed if it can be evaluated. Before `/spec`, define the
observable goal, the pass/fail criteria, and the evidence that will go in the
report. If that cannot be done, split or redefine the slice.

The report follows `docs/results/_template-slice-diagnostics.md` and records:

- the slice goal and spec;
- the pass/fail criteria and the evidence for each;
- the commands run and their results;
- the diagnostic data, including caveats and effective sample sizes;
- the decision: pass, fail, or partial, and why we move on;
- links to commits, artifacts, and follow-up work.

The final TDD step runs the full suite, `ruff check .`, and any slow or
diagnostic commands, then writes or updates the report and commits it with the
slice's final docs. A slice is not ready for approval without it.

When the report shape has stabilized across slices, add a `verify-slice`
command that reads a slice manifest, runs the verification commands, and writes
the report. Until then, the final TDD step writes the report manually. Do not
build `verify-slice` speculatively.

## Definition of done

A slice is ready for approval when:

1. The slice's spec was approved in `/spec-review` before implementation
   started.
2. A failing test was written and shown first for each new behaviour.
3. The new tests pass, and the full test suite passes.
4. `ruff check .` reports no errors.
5. Behaviour is documented where a reader would look for it.
6. A slice diagnostic report exists under `docs/results/` and records the goal,
   pass/fail criteria, evidence, limitations, and decision.
7. Every commit in the slice is green and self-contained, and the final tree is
   clean.
8. The project is left in a working state.
9. Nothing has been pushed before approval.

After approval, push the completed slice. Do not push again until the next
slice is approved.
