---
description: Write or update docs, with Mermaid diagrams
---

Document: $ARGUMENTS

- **Where**: `docs/architecture.md` for structure and flows,
  `docs/adr/NNNN-<slug>.md` for decisions, docstrings for API detail.
- **Diagrams**: Mermaid only, in fenced ` ```mermaid ` blocks. Use
  `flowchart` for structure, `sequenceDiagram` for interactions,
  `stateDiagram-v2` for lifecycles, `erDiagram` for data. Keep each one small
  enough to read without zooming.
- **ADRs**: Context / Decision / Consequences / Alternatives rejected. Record
  the alternative you *didn't* pick and why.
- **Docstrings**: state the contract and the failure modes, not the
  implementation.
- Update docs in the same commit as the behaviour they describe.
