---
description: Review a spec against the chosen approach and record approval
---

Review the spec for $ARGUMENTS. This is the approval gate; `/spec` no longer asks
for approval. Do not write production code or tests.

Read the spec, its linked design note, the brief, plan, and relevant ADRs.

1. **Recap the choice.** State the chosen approach from the design note in three
   bullets. Ask the author to confirm it in one sentence. If they cannot, stop
   and return to `/learn`; do not use the review as first exposure.
2. **Present a one-page review packet.** The full spec stays as reference. The
   packet contains: the outcome; the public contract; up to five representative
   examples covering happy path, boundary, and failure; at most three open
   decisions; the assumptions; the out-of-scope list; and one narrow overview
   diagram or table.
   The packet is an approval view, not a tutorial. If it does not fit one page,
   split the review, not the slice.
3. **Check the spec against the design note.** Flag every deviation. A deviation
   that changes the chosen approach goes back to `/learn`; a concrete detail is
   decided here.
4. **Review in rounds.** One theme per round; do not mix outputs, semantics, and
   internals. At most three blocking decisions per round. After each round give a
   one-line recap and ask for an explicit yes/no on each decision. Restate each
   decision in full in the same message: what changes, the recommendation, and the
   alternative. Never refer to "decision 1" or "Round 2" without repeating it; the
   author should not have to scroll up.
5. **Triage decisions.** Ask only contract-level choices. For semantics,
   recommend and ask for a veto. Record internal or reversible choices as
   assumptions. If a choice changes what a result means or whether runs are
   comparable, write or supersede an ADR before approval.
6. **Approve explicitly.** End with a checklist:
   - chosen approach matches the design note;
   - the contract is complete;
   - examples cover happy path, boundary, and failure;
   - assumptions and out-of-scope are explicit;
   - no blocking questions remain;
   - tests are listed, not written.
   Ask: `Approve this spec? yes / change / stop.`
7. **Record the approval.** Add the date, approved decisions, assumptions, and
   deferred items to the spec. Then finish with
   `Next: /tdd <first behaviour>.`
