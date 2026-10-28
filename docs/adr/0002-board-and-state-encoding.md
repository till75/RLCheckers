# ADR 0002 — Board, move, and state encoding

- **Status:** accepted
- **Date:** 2026-10-27
- **Deciders:** author, opencode
- **Related:** ADR 0001, `docs/00-brief.md`, `docs/plan.md`

## Context

Tabular Q-learning needs hashable states and actions, and the Q-table may hold
millions of entries. A readable tuple-of-cells key is convenient but expensive
at that scale. The 5x5 board has only 13 playable squares, so a compact integer
encoding is feasible without making the rules code obscure.

Move generation still needs a readable board, and debugging needs a way to turn
a key back into a position.

## Decision

### Board

- `Board` is immutable and holds a 25-cell tuple in row-major order.
- Non-playable squares are `None`.
- Piece codes are `0 = empty`, `1 = black man`, `2 = black king`,
  `3 = white man`, `4 = white king`.
- `PLAYABLE_SQUARES` is the 13 dark-square indices in row-major order:
  `[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]`.
- Side to move is `BLACK = 0`, `WHITE = 1`.

### Canonical state key

- Extract the 13 playable cells in `PLAYABLE_SQUARES` order.
- Pack cell `i` into bits `3i .. 3i+2`, using three bits per cell.
- Put the side-to-move bit at bit 39.
- The result is a 40-bit integer.
- Repetition and no-progress counters are environment state, not part of this
  key. Whether they enter the agent's learning state is decided in ADR 0004.

### Move and action key

- `Move` carries `path: tuple[int, ...]`, the origin followed by each landing
  square, and `captures: tuple[int, ...]`, the captured square indices.
- The path determines the captured squares for a given board.
- `action_key` packs the path length into 3 bits, then each square index into
  5 bits. A path has at most 6 squares, so the key fits in 33 bits.
- `q_key = (state_key << 33) | action_key`.

### Q-table

- The table is a sparse `dict[int, float]` keyed by `q_key`.
- The initial cap is 2,000,000 entries. The count is logged, and training stops
  with a clear error if the cap is exceeded.
- Provide `decode_state` and a pretty-printer so keys can be inspected during
  debugging and tests.

## Consequences

- A Q-table entry is a pair of Python integers/floats rather than a tuple of
  cells, which keeps memory and hashing costs down.
- Encoding and decoding need round-trip tests; a bad bit layout would silently
  merge states.
- The table is opaque without helpers, so the decoder and pretty-printer are
  part of the debugging surface, not optional extras.
- If the cap is reached, the next options are afterstate values, a smaller
  board, or function approximation, in that order.

## Alternatives rejected

- **Tuple-of-cells keys:** easier to read, but much larger per entry at millions
  of entries.
- **Full 25-cell keys:** include non-playable squares and add no information.
- **Bitboards:** fastest, but more complex than needed for 5x5; revisit if
  profiling shows a bottleneck.
- **Square-to-piece dictionaries:** convenient for sparse boards, but harder to
  canonicalize and slower to hash.
- **Dense numpy Q-table:** memory-prohibitive because most state-action pairs
  are never visited.
