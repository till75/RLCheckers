---
description: Specify one vertical slice as observable, testable behaviour
---

Specify: $ARGUMENTS

Read `docs/00-brief.md`, `docs/plan.md`, the slice's design note (if any), and
any relevant ADRs and research notes. Write `docs/specs/NNNN-<slug>.md` for
exactly one vertical slice. If the slice introduces a new approach and has no
design note, stop and run `/learn` first.

- State the outcome in one sentence: what a user or caller can observe when the
  slice is done.
- Define inputs, outputs, and the public interface, including types and units.
- Write acceptance criteria as concrete examples: happy path, boundaries, and
  failures. Keep examples short; one happy, one boundary, and one failure per
  criterion is enough.
- List the tests that will prove each criterion. Do not write runnable test code;
  that belongs in `/tdd`.
- State what is explicitly out of scope for this slice.
- Flag contradictions with the brief, plan, or an ADR instead of silently
  choosing a side. If a contradiction changes what a result means or whether runs
  are comparable, resolve it in an ADR before writing the spec.
- Do not use HTML inside Mermaid labels; keep diagrams narrow and plain.
- Do not write production code or tests in this command.
- Keep the spec as the reference contract. `/spec-review` produces the one-page
  review packet and asks for approval; `/spec` does not.

Finish with `Next: /spec-review <slice>.` Approval happens there, not here.
