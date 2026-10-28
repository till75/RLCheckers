---
description: Review a diff by severity
---

Review $ARGUMENTS. If no target is given, use the uncommitted changes:

!`git status --short && git diff`

Report in this order, and omit empty sections:

1. **Blocking** — real bugs, with `file:line`, why it fails, and a concrete patch.
2. **Tests** — missing coverage for the new behaviour, or tests that would pass
   even if the code were wrong.
3. **Risks** — error handling, edge cases, resource leaks, concurrency.
4. **Design** — only where it will cost something later.
5. **Nits** — one line each, at the end.

Do not restate the diff. Do not rewrite the code unless asked. If nothing is
wrong, say so plainly and stop.
