---
description: Draft a Conventional Commit message
---

Draft a commit message for the staged changes.

!`git diff --cached --stat`

Format:

```
<type>(<scope>): <imperative subject, max 72 chars>

<body: why this change, what it replaces, anything a reviewer needs>

<footer: BREAKING CHANGE or refs>
```

Rules: types are `feat|fix|refactor|test|docs|chore|perf|build|ci`. Imperative
subject, no trailing period, body wrapped at 72 columns. Explain **why**, not
what the diff already shows.

Show the message and wait for approval. Do not run `git commit` until
approved. Never push.
