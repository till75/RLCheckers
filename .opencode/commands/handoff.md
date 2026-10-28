---
description: Close a session by writing a handoff note to docs/state.md
---

Write `docs/state.md`. It is a handoff note for whoever picks this repo up
next — human or agent. Overwrite the file; do not append. Keep it under 40
lines.

!`git log --oneline -10`
!`git status --short`

Structure:

```markdown
# State — YYYY-MM-DD

## Where we are
One or two sentences: current slice, and whether it is finished.

## Done since last handoff
Bullets, each pointing at a real commit or file.

## Next
Ordered and concrete. The first item must be startable without asking a
question.

## Open questions
Decisions waiting on the user. Mark which are blocking.

## Gotchas
Things that cost time and are not obvious from the code: environment quirks,
tool behaviours, dead ends already ruled out.

## Not in an ADR
Decisions made this session too small for an ADR, but not to be re-litigated.
```

Rules: facts only. No praise, no recap of the conversation, no restating the
code. If something is uncertain, say so explicitly.
