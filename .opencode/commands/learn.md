---
description: Learn a slice's concepts and choose an approach before specifying it
---

Learn: $ARGUMENTS

Goal: make the author able to choose the slice's approach without reading the
spec first. Teach only what the decision needs; do not write the spec or code.

Read `docs/00-brief.md`, `docs/plan.md`, the relevant ADRs, research notes, and
the current code. If the slice is already settled and introduces no new concept,
say so and hand off to `/spec`.

1. **Frame the slice.** One paragraph: what changes for the caller and why this
   slice exists now.
2. **Define the terms.** At most three terms the author needs, in plain language,
   each with one concrete example. Link deeper sources as optional reading; do
   not require a video.
3. **Present 2–3 approaches.** For each: the idea, what it makes easy, what it
   makes hard, and the evidence that would show it works. Recommend one and say
   why. Include the option that challenges the obvious answer when one exists.
4. **Ask for the choice.** Give concrete options, ask the author to choose, and
   wait. Do not recommend and proceed silently.
5. **Check understanding.** Ask the author to explain the chosen approach in one
   sentence or give a concrete example. If they cannot, explain again before
   recording the choice.
6. **Write a one-page design note** at `docs/design/NNNN-<slug>.md` using
   `docs/design/0000-template.md`. Record the chosen approach and the reason.
   Keep the note to one page; the spec holds the contract.
7. **Escalate policy.** If the choice changes what a result means or whether
   runs are comparable, write or supersede an ADR before `/spec`.
8. **Hand off.** Finish with `Next: /spec <slice>.` Do not ask for approval here.
