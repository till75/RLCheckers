# <Slice> diagnostic report

**Slice:** <ID> — <name>  
**Date:** YYYY-MM-DD  
**Status:** pass / fail / partial  
**Spec:** [<spec>](<path>)  
**Commits:** <hashes>  
**Report owner:** <author>

## Intended goal

State the observable outcome the slice was meant to achieve. Link the spec and
the design note or ADR that fixed the approach.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| <criterion from the spec> | <test, command, artifact, or measurement> | pass / fail / partial |

## What was built

Summarise the behaviour, interfaces, and files that changed. Keep this short;
the spec and architecture notes remain the contract.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | <counts and result> |
| `.\.venv\Scripts\python.exe -m ruff check .` | <result> |
| <slow or diagnostic command> | <result> |

## Diagnostic evidence

Record the measurements that justify the decision. Include sample sizes,
effective sample sizes, confidence intervals, caveats, and links to CSV, JSON,
or plot artifacts. For deterministic agents, state how many unique games were
actually played.

## Limitations and caveats

List what the evidence does not prove, known weak baselines, deterministic
repetition, single-seed results, and any deferred work.

## Decision

State pass, fail, or partial. Explain why the slice is ready to move on, or what
blocks it. If partial, name the follow-up slice or condition.

## Follow-up

List the next slice, open questions, and any artifacts that should be revisited.
