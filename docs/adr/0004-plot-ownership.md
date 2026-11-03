# ADR 0004 — Plot ownership

- **Status:** accepted
- **Date:** 2026-11-03
- **Deciders:** author, opencode
- **Related:** ADR 0003, `docs/00-brief.md`, `docs/plan.md`,
  `docs/specs/0004-evaluation-arena.md`

## Context

The brief requires plots in the final artifacts. ADR 0003 §11 said the CSV
schema, file names, and plot contents are fixed in spec 0004. Spec 0004 defines
the S4 evaluation arena; the plan's S4 acceptance criteria require only a CSV,
while S5 and S7 are the slices that produce training curves and the milestone
report. The mismatch blocked approval of spec 0004: it writes no plots, so it
cannot fix their contents as ADR 0003 §11 required.

The evaluation contract itself is not in doubt. Only the slice that owns the
plot contract is.

## Decision

S4 writes `metrics.csv`, `games.csv`, and `run.json` only. It does not render or
save plots and does not add matplotlib.

Plot contents and rendering belong to S5 (training diagnostics) and S7 (the
three-seed gate report). Each slice fixes the plot contract for the plots it
produces, in its own spec, using the CSV/JSON artifacts as the reproducible
input. A plot must be reproducible from the saved config, seed, and agent
artifact, exactly as every reported number is under ADR 0003.

This ADR supersedes only the plot sentence of ADR 0003 §11. The rest of ADR
0003 — score and perspective, colour pairing, opening suite, game budget,
determinism, evaluation policy, gate, uncertainty, frozen evaluation, and the
CSV/JSON artifact requirements — remains in force.

## Consequences

- Spec 0004 can be approved without a plot contract and stays headless.
- S4 has no matplotlib dependency and no partial plot output on failure.
- S5 and S7 must define their own plot contents; they cannot rely on spec 0004
  for that contract.
- Plot reproducibility is still required; it is derived from the saved artifacts
  rather than added as a new evaluation contract.
- ADR 0003 remains the evaluation policy; only its plot sentence is superseded.
- ADR 0004 is created before the planned Q-learning and self-play ADRs, so those
  shift to 0005 and 0006 in `docs/plan.md`.

## Alternatives rejected

- **Add a deferred plot contract to spec 0004.** It would satisfy the old
  sentence literally, but puts S5/S7 content in the S4 spec and invites a
  contract that S4 cannot exercise.
- **Leave the conflict and approve spec 0004 anyway.** It would leave ADR 0003
  inaccurate and the approval ambiguous.
- **Drop plots entirely.** The brief requires them; they move to S5/S7, not out
  of scope.
- **Put plots in S4.** S4's job is the scoreboard; plots need training data and
  the gate report, which do not exist yet.

## Approval

Accepted by the author on 2026-11-03 as option 2 for spec 0004 decision 6.
