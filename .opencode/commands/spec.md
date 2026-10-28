---
description: Specify one vertical slice as observable, testable behaviour
---

Specify: $ARGUMENTS

Read `docs/00-brief.md`, `docs/plan.md`, and any relevant ADRs and research
notes. Write `docs/specs/NNNN-<slug>.md` for exactly one vertical slice.

- State the outcome in one sentence: what a user or caller can observe when the
  slice is done.
- Define inputs, outputs, and the public interface, including types and units.
- Write acceptance criteria as concrete examples: happy path, boundaries, and
  failures.
- List the tests that will prove each criterion. Do not write them yet.
- State what is explicitly out of scope for this slice.
- Flag contradictions with the brief, plan, or an ADR instead of silently
  choosing a side.
- Do not write production code or tests in this command.

Finish by asking for approval of the spec. The next step is `/tdd`.
