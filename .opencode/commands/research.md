---
description: Research a question and record sourced findings
---

Research: $ARGUMENTS

Answer the question from evidence, not memory. Do not write production code.

- Restate the question and the decision it will inform.
- Check the project first: pinned versions, existing docs, ADRs, and code.
- Prefer primary sources: papers, official documentation, and source code.
  Record the version and date for anything that can change.
- For each finding note the claim, source, date or version, and confidence.
  Label inference as inference; never present a guess as fact.
- State what would change the conclusion and what could not be verified.
- If sources disagree, say so and explain which one you trust and why.
- Do not copy code or prose without attribution.

Write `docs/research/<slug>.md`, creating the folder if needed. Keep it to one
page unless the question demands more.

Finish with the answer in two or three sentences, the decision it supports, and
the open questions.
