---
description: Turn an approved brief into vertical slices
---

Read `docs/00-brief.md` and write `docs/plan.md`.

- Slice **vertically**: each slice is test + code + docs + one commit, and
  leaves the project in a working state.
- Order by risk. The slice that could invalidate the design goes first.
- For each slice record: ID, outcome, acceptance criterion, files touched,
  tests added, rough size.
- For each slice, say whether it needs `/learn` (new concepts or unsettled
  approach) before `/spec`; every slice goes through `/spec-review` before
  `/tdd`.
- Flag anything that needs an ADR before implementation.
- Call out what you deliberately deferred.

Do not write production code in this command.
