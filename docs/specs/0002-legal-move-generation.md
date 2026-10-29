# Spec 0002 — Legal move generation

- **Status:** approved
- **Date:** 2026-10-29
- **Slice:** S2 — Legal move generation
- **Related:** `docs/00-brief.md`, `docs/plan.md`, ADR 0001, ADR 0002,
  `docs/architecture.md`, `docs/specs/0001-board-and-initial-position.md`

## Outcome

A caller can ask any encoding-valid `Board` for every legal move for the side to
move — quiet moves, mandatory captures, multiple-capture sequences, promotions,
and king moves — and can apply one move to obtain the next immutable `Board`,
with a deterministic order and perft counts that match documented fixtures.

## Public interface

### Module and imports

The implementation lives in `src/rlcheckers/game/moves.py`:

```python
from rlcheckers.game.moves import Move, apply_move, generate_moves
```

`src/rlcheckers/game/__init__.py` re-exports `Move`, `apply_move`, and
`generate_moves`, so this also works:

```python
from rlcheckers.game import Move, apply_move, generate_moves
```

`Piece`, `Side`, `Board`, `BOARD_SIZE`, `SQUARE_COUNT`, and `PLAYABLE_SQUARES`
stay in `rlcheckers.game.board`. No new `pieces.py` module is introduced.
`moves.py` uses only the standard library and `rlcheckers.game.board`; it does no
I/O and imports no numpy.

### `Move`

`Move` is an immutable value object that compares and hashes by value.

| Member | Signature | Contract |
|---|---|---|
| Constructor | `Move(path: Sequence[int], captures: Sequence[int] = ())` | Normalises both arguments to tuples. Validates the structural and geometric shape described below. Rejects invalid input with a clear error. |
| `path` | `tuple[int, ...]` | Origin followed by each landing square, in order. Length `2..6`. The same square may appear more than once: a multiple capture may return to an earlier square. |
| `captures` | `tuple[int, ...]` | Captured squares, in the order captured. Empty for a quiet move; otherwise exactly `len(path) - 1` entries. |
| `is_capture` | `bool` property | `True` exactly when `captures` is non-empty. |
| `action_key` | `int` property | ADR 0002 action encoding, described below. |

`Move` does not know or validate the board. It validates only the shape and
geometry that can be checked from the squares alone:

- `path` has at least two squares.
- `path` and `captures` contain integers only.
- Every square in `path` and `captures` is in `0..24` and is a dark square in
  `PLAYABLE_SQUARES`.
- If `captures` is empty, `path` has exactly two squares and the two squares are
  diagonally adjacent (`abs(row_delta) == 1` and `abs(col_delta) == 1`).
- If `captures` is non-empty, each step is a diagonal jump of two squares
  (`abs(row_delta) == 2` and `abs(col_delta) == 2`), and `captures[i]` is the
  midpoint of `path[i]` and `path[i + 1]`.
- `captures` has no duplicates.
- No captured square appears in `path`.
- `path` length is at most `6`, the ADR 0002 action-key limit. An exhaustive
  search of the 13 dark squares shows that a legal capture sequence on 5x5 has
  at most four captures and a path of at most five squares, so this guard is
  never reached by `generate_moves`; it keeps the encoding contract explicit.

`Move` deliberately does **not** enforce whose turn it is, whether a man is
moving forward, whether the landing square is occupied, or whether a capture is
mandatory. Those are board-specific and belong to `apply_move`.

### `generate_moves`

```python
def generate_moves(board: Board) -> tuple[Move, ...]: ...
```

Returns every legal move for `board.side_to_move`, and only for that side. The
result is a tuple sorted by `(move.path, move.captures)` using ordinary tuple
ordering. The same board always produces the same tuple. A side with no pieces
or no legal moves produces `()`. The board is not mutated.

### `apply_move`

```python
def apply_move(board: Board, move: Move) -> Board: ...
```

Returns a new `Board` with the move applied, the captured pieces removed, any
promotion applied, and `side_to_move` switched. The input board is not mutated.

`apply_move` accepts exactly the moves that `generate_moves(board)` returns. Any
other structurally valid move is rejected with `ValueError` whose message
contains `not legal`. This includes:

- a quiet move when the side has a capture somewhere;
- a move by a piece that does not belong to the side to move;
- a move whose landing square is occupied;
- a man trying to move or capture backwards;
- a capture of a friendly piece or of an empty square;
- a capture path that stops while a further capture remains;
- a capture path that continues after a promotion.

The membership check is deliberately simple: `apply_move` may call
`generate_moves` and compare. Performance work can replace it later without
changing the observable contract.

## Move generation rules

The generator implements the move rules of ADR 0001. It returns every legal
sequence rather than choosing one; the player or agent chooses.

### Quiet moves

A quiet move exists only when the side to move has no capture anywhere.

- A man moves one square diagonally forward. Black moves toward increasing rows;
  White moves toward decreasing rows.
- A king moves one square diagonally in any direction.
- The destination must be on the board and empty.
- A man that lands on the opponent's back rank is promoted to a king and the
  move ends. A king that lands on a back rank stays a king.
- A move is a single square; there are no multi-square quiet moves and no flying
  kings.

### Captures

- Captures are mandatory. If any piece of the side to move has a capture, no
  quiet move is generated.
- A man captures diagonally forward only. A king captures diagonally in any
  direction.
- A capture jumps over exactly one adjacent opponent piece and lands on the
  empty square immediately beyond it.
- The captured piece is removed for the rest of the move. It cannot be captured
  a second time and does not block later jumps.
- If a capture is available from the landing square, the move must continue.
  A sequence is recorded only when no further capture is available, or when a
  man promotes.
- If more than one continuation exists, every legal sequence is returned. There
  is no maximum-capture requirement: a one-capture sequence is legal even when
  another sequence captures more, as long as no further capture is available
  from its own landing square.
- A man that reaches the opponent's back rank by capturing is promoted and the
  move ends immediately. It does not continue as a king, even if a further
  capture is available.
- A capture path may revisit a square it has already occupied, including its
  origin. It may not capture the same piece twice. The four-capture fixture P6
  below exercises this.
- Squares are ordinary indices from `Board`. No notation layer is introduced.

### Promotion

Black men promote on row `4`; White men promote on row `0`. Promotion happens on
the final landing square of a move. For a capture, that is the landing square of
the last jump. Promotion ends the move, so a promoted man never makes another
jump in the same move.

### Ordering and uniqueness

Moves are sorted by `(path, captures)`. Two paths that capture the same pieces
and finish on the same square in a different order are distinct moves: the path
is part of the action. `generate_moves` never returns duplicate `(path,
captures)` pairs.

## Action key

`Move.action_key` implements ADR 0002's 33-bit action encoding:

```text
action_key = len(path)
             | path[0] << 3
             | path[1] << 8
             | path[2] << 13
             | path[3] << 18
             | path[4] << 23
             | path[5] << 28
```

The length occupies bits `0..2`. Each path square occupies five bits, starting
at bit 3. Unused high bits are zero. With a maximum path length of six, the key
is in `0 .. 2**33 - 1`.

The path determines the captured squares for a given board, so `captures` is not
packed into the key. `q_key = (state_key << 33) | action_key` belongs to S5 and
is out of scope here.

## Perft definition and fixtures

For this slice, perft is a test helper, not production API. It counts leaf nodes:

```python
def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    moves = generate_moves(board)
    if depth == 1:
        return len(moves)
    return sum(perft(apply_move(board, move), depth - 1) for move in moves)
```

- A move is one ply, even when it is a multiple capture.
- Two different capture paths are two moves, even if they remove the same pieces
  and end on the same square.
- A side with no moves contributes zero at a positive depth.
- No win, loss, draw, repetition, or no-progress rule is applied. S3 owns those.

The fixtures use square indices from `Board`. A test helper may build a board
from a `{square: Piece}` mapping with `Piece.EMPTY` on all other playable
squares and `None` on light squares. All fixtures have Black to move.

| ID | Pieces | D1 | D2 | D3 |
|---|---|---:|---:|---:|
| P1 | `Board.initial()` | 4 | 8 | 18 |
| P2 | `12: BLACK_KING`, `20: WHITE_MAN` | 4 | 4 | 12 |
| P3 | `16: BLACK_MAN`, `2: WHITE_KING`, `14: WHITE_MAN` | 2 | 6 | 9 |
| P4 | `20: BLACK_KING`, `16: WHITE_MAN`, `8: WHITE_MAN`, `10: WHITE_MAN` | 1 | 1 | 1 |
| P5 | `20: BLACK_KING`, `16: WHITE_MAN`, `8: WHITE_MAN`, `18: WHITE_MAN`, `14: WHITE_MAN` | 2 | 4 | 4 |
| P6 | `14: BLACK_KING`, `0: WHITE_KING`, `8: WHITE_MAN`, `6: WHITE_MAN`, `16: WHITE_MAN`, `18: WHITE_MAN` | 2 | 2 | 4 |

The fixtures cover:

- P1: initial quiet moves, then both sides' replies.
- P2: king mobility on a mostly empty board and a capture becoming available.
- P3: quiet promotion and a king's replies.
- P4: a forced two-capture sequence.
- P5: branching two-capture sequences.
- P6: the maximum four-capture loop, a path that returns to its origin, and two
  distinct capture orders for the same captured pieces.

The expected values were derived from the rules by hand and cross-checked with an
independent scratch enumerator. They are hard-coded in the tests; the tests must
not compute expected values from the implementation.

## Acceptance criteria

The snippets are illustrative. Later snippets may reuse earlier variables and
helpers. Tests import `pytest` explicitly. A local helper such as this is
allowed in tests but is not production API:

```python
def board_with(
    pieces: dict[int, Piece], side: Side = Side.BLACK
) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)
```

### A1 — Initial quiet moves

`generate_moves` returns exactly the four initial Black moves in sorted order:

```python
assert generate_moves(Board.initial()) == (
    Move((6, 10)),
    Move((6, 12)),
    Move((8, 12)),
    Move((8, 14)),
)
```

With White to move, the initial position has the mirrored four moves:

```python
white = Board(Board.initial().cells, Side.WHITE)
assert generate_moves(white) == (
    Move((16, 10)),
    Move((16, 12)),
    Move((18, 12)),
    Move((18, 14)),
)
```

### A2 — Movement directions and edges

A man moves forward only, a king moves in all four diagonal directions, and a
corner king has one move:

```python
board = board_with({12: Piece.BLACK_MAN, 6: Piece.WHITE_MAN})
assert generate_moves(board) == (Move((12, 16)), Move((12, 18)))

board = board_with({12: Piece.BLACK_KING, 20: Piece.WHITE_MAN})
assert generate_moves(board) == (
    Move((12, 6)),
    Move((12, 8)),
    Move((12, 16)),
    Move((12, 18)),
)

board = board_with({0: Piece.BLACK_KING})
assert generate_moves(board) == (Move((0, 6)),)
```

A board with no pieces for the side to move has no moves:

```python
assert generate_moves(board_with({})) == ()
```

A side with pieces but no legal move also has no moves:

```python
board = board_with(
    {
        0: Piece.BLACK_MAN,
        6: Piece.WHITE_MAN,
        12: Piece.WHITE_MAN,
    }
)
assert generate_moves(board) == ()
```

### A3 — Captures are mandatory

After Black plays `(1, 1) -> (2, 2)`, White has exactly one legal move, the
capture `(3, 3) x (2, 2) -> (1, 1)`. The otherwise legal quiet moves are not
returned:

```python
capture_board = board_with(
    {
        0: Piece.BLACK_MAN,
        2: Piece.BLACK_MAN,
        4: Piece.BLACK_MAN,
        8: Piece.BLACK_MAN,
        12: Piece.BLACK_MAN,
        16: Piece.WHITE_MAN,
        18: Piece.WHITE_MAN,
        20: Piece.WHITE_MAN,
        22: Piece.WHITE_MAN,
        24: Piece.WHITE_MAN,
    },
    Side.WHITE,
)
assert generate_moves(capture_board) == (Move((18, 6), (12,)),)
```

### A4 — Capture directions and geometry

A man cannot capture backwards; a king can:

```python
board = board_with({12: Piece.BLACK_MAN, 6: Piece.WHITE_MAN})
assert all(not move.is_capture for move in generate_moves(board))

board = board_with({12: Piece.BLACK_KING, 6: Piece.WHITE_MAN})
assert generate_moves(board) == (Move((12, 0), (6,)),)
```

A capture is not generated when the landing square is occupied or off the board:

```python
# Black man at (3, 1) can jump White at (4, 0), but the landing square is off
# the board, so no capture exists.
board = board_with({16: Piece.BLACK_MAN, 20: Piece.WHITE_MAN})
assert generate_moves(board) == (Move((16, 22)),)

# The jump (2, 2) x (3, 1) -> (4, 0) is blocked by the Black king on (4, 0),
# so the only move is the quiet (2, 2) -> (3, 3).
board = board_with(
    {
        12: Piece.BLACK_MAN,
        16: Piece.WHITE_MAN,
        20: Piece.BLACK_KING,
    }
)
assert generate_moves(board) == (Move((12, 18)),)
```

### A5 — Multiple captures continue and branch

A capture chain must continue while a capture remains, and every branch is
returned:

```python
board = board_with(
    {
        20: Piece.BLACK_KING,
        16: Piece.WHITE_MAN,
        8: Piece.WHITE_MAN,
        18: Piece.WHITE_MAN,
        14: Piece.WHITE_MAN,
    }
)
assert generate_moves(board) == (
    Move((20, 12, 4), (16, 8)),
    Move((20, 12, 24), (16, 18)),
)
```

### A6 — No maximum-capture requirement

Both a one-capture sequence and a two-capture sequence are returned when both
are complete:

```python
board = board_with(
    {
        22: Piece.BLACK_KING,
        16: Piece.WHITE_MAN,
        6: Piece.WHITE_MAN,
        18: Piece.WHITE_MAN,
    }
)
assert generate_moves(board) == (
    Move((22, 10, 2), (16, 6)),
    Move((22, 14), (18,)),
)
```

### A7 — Promotion ends the move

A man that promotes after two captures stops, even though the new king could
capture again:

```python
board = board_with(
    {
        2: Piece.BLACK_MAN,
        8: Piece.WHITE_MAN,
        18: Piece.WHITE_MAN,
        16: Piece.WHITE_MAN,
    }
)
assert generate_moves(board) == (Move((2, 14, 22), (8, 18)),)

after = apply_move(board, Move((2, 14, 22), (8, 18)))
assert after.piece_at(4, 2) is Piece.BLACK_KING
assert after.piece_at(3, 1) is Piece.WHITE_MAN
```

A quiet move also promotes:

```python
board = board_with({16: Piece.BLACK_MAN, 2: Piece.WHITE_KING})
assert generate_moves(board) == (Move((16, 20)), Move((16, 22)))
assert apply_move(board, Move((16, 20))).piece_at(4, 0) is Piece.BLACK_KING
assert apply_move(board, Move((16, 22))).piece_at(4, 2) is Piece.BLACK_KING
```

### A8 — Move value object and validation

Two moves with the same fields compare equal and hash equal. Mutating a field
fails:

```python
move = Move((6, 10))
assert move == Move((6, 10))
assert hash(move) == hash(Move((6, 10)))
assert move.captures == ()
assert move.is_capture is False

with pytest.raises(AttributeError):
    move.path = (6, 12)
```

Invalid shapes are rejected at construction:

| Input | Expected |
|---|---|
| `Move((6,))` | `ValueError` naming `path` |
| `Move((6, 10, 14))` | `ValueError` naming `captures` |
| `Move((6, 1))` | `ValueError` naming `path` and the square |
| `Move((6, 25))` | `ValueError` naming `path` and the square |
| `Move((12, 0), (12,))` | `ValueError` naming `captures` |
| `Move((12, 0, 12), (6, 6))` | `ValueError` naming `captures` |
| `Move((12, 0, 12), (6,))` | `ValueError` naming `captures` |
| `Move(("6", 10))` | `TypeError` naming `path` |
| `Move((12, 0), ("6",))` | `TypeError` naming `captures` |

Type checks run before geometry checks, so a non-integer square raises
`TypeError` even when the shape is otherwise wrong. Error messages must name the
offending field, index, or value. Tests assert substrings, not full wording.

### A9 — Action key

The bit layout is fixed and boundary-safe:

```python
assert Move((6, 10)).action_key == 2610
assert Move((10, 22, 14), (16, 18)).action_key == 120403
assert Move((14, 2, 10, 22, 14), (8, 6, 16, 18)).action_key < (1 << 33)
assert (
    Move((14, 2, 10, 22, 14), (8, 6, 16, 18)).action_key
    != Move((14, 22, 10, 2, 14), (18, 16, 6, 8)).action_key
)
```

A six-square path is accepted by `Move` only if its geometry is valid. The 5x5
dark-square geometry has no five-capture sequence, so no legal move reaches the
six-square action-key limit.

### A10 — Applying a move

A quiet move updates the board, switches the side, and leaves the original
untouched:

```python
board = Board.initial()
after = apply_move(board, Move((6, 10)))
assert after.piece_at(1, 1) is Piece.EMPTY
assert after.piece_at(2, 0) is Piece.BLACK_MAN
assert after.side_to_move is Side.WHITE
assert board.piece_at(1, 1) is Piece.BLACK_MAN
assert board.side_to_move is Side.BLACK
```

A capture removes exactly the captured pieces:

```python
board = board_with(
    {
        0: Piece.BLACK_MAN,
        2: Piece.BLACK_MAN,
        4: Piece.BLACK_MAN,
        8: Piece.BLACK_MAN,
        12: Piece.BLACK_MAN,
        16: Piece.WHITE_MAN,
        18: Piece.WHITE_MAN,
        20: Piece.WHITE_MAN,
        22: Piece.WHITE_MAN,
        24: Piece.WHITE_MAN,
    },
    Side.WHITE,
)
after = apply_move(board, Move((18, 6), (12,)))
assert after.piece_at(3, 3) is Piece.EMPTY
assert after.piece_at(2, 2) is Piece.EMPTY
assert after.piece_at(1, 1) is Piece.WHITE_MAN
assert after.side_to_move is Side.BLACK
```

For every generated move on every fixture position, `apply_move` preserves
single occupancy and piece conservation:

```python
before = sum(cell not in (None, Piece.EMPTY) for cell in board.cells)
for move in generate_moves(board):
    result = apply_move(board, move)
    after = sum(cell not in (None, Piece.EMPTY) for cell in result.cells)
    assert after == before - len(move.captures)
    assert result.side_to_move is not board.side_to_move
```

### A11 — Rejecting illegal applications

`apply_move` rejects structurally valid moves that are not in
`generate_moves(board)`:

```python
with pytest.raises(ValueError, match="not legal"):
    apply_move(Board.initial(), Move((0, 6)))  # (0, 0) -> (1, 1) is occupied

with pytest.raises(ValueError, match="not legal"):
    apply_move(Board(Board.initial().cells, Side.WHITE), Move((6, 10)))  # wrong side

with pytest.raises(ValueError, match="not legal"):
    apply_move(capture_board, Move((16, 10)))  # quiet while a capture exists
```

A structurally invalid move raises in `Move`, before `apply_move`:

```python
with pytest.raises(ValueError, match="captures"):
    Move((18, 6), (14,))  # midpoint is 12, not 14
```

### A12 — Perft fixtures

The six fixture counts are hard-coded and match the table:

```python
assert perft(Board.initial(), 1) == 4
assert perft(Board.initial(), 2) == 8
assert perft(Board.initial(), 3) == 18
# ... P2-P6 as tabled
```

The test suite parametrizes the six fixtures and depths `1, 2, 3`. It also
asserts `perft(position, 0) == 1` for one fixture.

### A13 — Determinism and property checks

`generate_moves` is deterministic and returns no duplicates:

```python
assert generate_moves(Board.initial()) == generate_moves(Board.initial())
moves = generate_moves(
    board_with(
        {
            20: Piece.BLACK_KING,
            16: Piece.WHITE_MAN,
            8: Piece.WHITE_MAN,
            18: Piece.WHITE_MAN,
            14: Piece.WHITE_MAN,
        }
    )
)
assert len(moves) == len(set(moves))
```

A seeded random playout of up to 60 plies, stopping early if a side has no
moves, preserves the invariants: total pieces never increase, exactly
`len(captures)` pieces disappear per move, the side alternates, and a man that
finishes on the opponent's back rank is a king. The playout does not add a draw
or win rule.

### A14 — Documentation

`docs/architecture.md` records that S2 implements `Move`, `generate_moves`, and
`apply_move`, and that S3 owns game state, counters, and terminal detection.
`README.md` is updated if it lists implemented features. The module docstring in
`moves.py` states the capture, promotion, and ordering rules in one short
paragraph.

## Tests to add

All move tests live in `tests/game/test_moves.py`; perft tests live in
`tests/game/test_perft.py`. Tests may use local helpers; no helper becomes
production API.

| Criterion | Test(s) |
|---|---|
| A1 | `test_initial_black_quiet_moves`, `test_initial_white_quiet_moves` |
| A2 | `test_man_moves_forward_only`, `test_king_moves_in_all_directions`, `test_corner_king_has_one_move`, `test_side_without_pieces_has_no_moves`, `test_blocked_side_has_no_moves` |
| A3 | `test_capture_is_mandatory` |
| A4 | `test_man_capture_is_forward_only`, `test_king_captures_backward`, `test_capture_needs_empty_landing`, `test_capture_off_board_is_not_generated` |
| A5 | `test_multiple_capture_branches_are_all_returned` |
| A6 | `test_no_maximum_capture_requirement` |
| A7 | `test_promotion_ends_multi_capture`, `test_quiet_move_promotes` |
| A8 | `test_move_is_immutable_value_object`, `test_move_rejects_bad_path`, `test_move_rejects_bad_captures`, `test_move_rejects_non_integer_squares` |
| A9 | `test_action_key_layout`, `test_action_key_fits_33_bits`, `test_action_key_distinguishes_capture_orders` |
| A10 | `test_apply_quiet_move`, `test_apply_capture`, `test_apply_preserves_piece_count`, `test_apply_does_not_mutate_original` |
| A11 | `test_apply_rejects_blocked_move`, `test_apply_rejects_wrong_side`, `test_apply_rejects_quiet_when_capture_exists`, `test_apply_rejects_illegal_capture` |
| A12 | `test_perft_known_positions` (parametrized over P1-P6 and depths 1-3), `test_perft_depth_zero_is_one` |
| A13 | `test_generate_moves_is_deterministic`, `test_generated_moves_are_unique`, `test_seeded_playout_preserves_invariants` |
| A14 | Documentation review, not a unit test |

Tests use plain `pytest` assertions, `pytest.raises` with `match` for errors, and
exact tuples for move lists.

## TDD order

S2 is an L slice. Follow this order and stop at a testable boundary if the
session runs out; do not carry a half-finished slice across turns.

1. **Bootstrap before the first red test:** create `src/rlcheckers/game/moves.py`
   with the `Move` dataclass and `generate_moves`/`apply_move` signatures that
   raise `NotImplementedError`, then export them from
   `src/rlcheckers/game/__init__.py`. Verify the imports work. The first failure
   must be missing behaviour, not a missing module.
2. Write the first failing test for A1 (initial quiet moves) and implement the
   `Move` shape plus quiet-move generation.
3. Add A2, A8, and quiet applications in A10/A11.
4. Add A3 and A4 (mandatory captures, directions, landing rules) and capture
   application.
5. Add A5 and A6 (multi-captures, branches, no maximum), then A7 (promotion).
6. Add A9 (action key) and A12 (perft fixtures).
7. Add A13 (determinism and seeded playout).
8. Update docs, run the full suite and `ruff check .`, and commit one coherent
   S2 change. If the work was split, use two commits at the quiet-move and
   capture boundaries, update `docs/plan.md`, and keep every commit green.
9. Do not push unless asked.

## Out of scope

- Game state wrapper, repetition and no-progress counters, terminal win/loss,
  and draw detection. These belong to S3.
- `q_key`, Q-table storage, Q-learning, agents, training, evaluation, and the
  CLI. These belong to later slices.
- Random move selection and depth-1 greedy selection. These belong to S3/S4.
- Move notation, parsing, serialization, and an interactive or text gameplay
  UI.
- A production `perft` function. The tests own the recursion helper.
- Undo/unmake, incremental make/unmake, bitboards, transposition tables, and
  performance work beyond straightforward Python.
- Full 8x8 checkers, flying kings, maximum-capture rules, backward captures by
  men, huffing, and optional captures.
- Reachability validation, legal piece-count validation, and opening-book
  validation. Board remains encoding-only.
- Serialization of boards or moves to JSON/TOML.
- ANSI colour, terminal rendering, and packaging.

## Contradictions, gaps, and decisions

These need explicit approval because the brief, plan, or an ADR does not fully
settle them:

1. **S2 and S3 both mention move application.** Plan S2 requires applying
   returned moves for piece-conservation and turn-alternation checks, while plan
   S3 says applying a move updates the board, captures, promotion, counters, and
   side to move. This spec puts a pure `apply_move(board, move) -> Board` in S2,
   with no counters or terminal logic. S3 wraps it in game state and adds
   repetition, no-progress, and win/loss. If you prefer S3 to own all
   application, S2 cannot satisfy its own property tests without a test-only
   helper; say so and the spec will change.
2. **ADR 0001 says "any legal sequence may be chosen"; plan S2 says "each legal
   sequence is returned."** These are compatible: the generator returns all
   sequences so the player or agent can choose one. The generator does not
   impose a maximum-capture rule. This spec follows the plan.
3. **ADR 0002 does not fix the action-key bit order.** This spec puts the path
   length in bits `0..2` and the first path square in bits `3..7`, then each
   subsequent square five bits higher. The alternative is length in the high
   bits, which changes every stored action key. The low-bits layout is proposed.
4. **ADR 0001 does not define capture-removal timing or whether a path may
   revisit a square.** This spec removes captured pieces for the rest of the
   move, forbids capturing the same piece twice, and allows path squares to
   repeat, including returning to the origin (P6). On 5x5, an exhaustive
   search finds at most four captures and no legal path that lands on a
   previously captured square, so removal timing does not change the generated
   move set. If you want the stricter "no square may be visited twice" rule,
   P6 and the expected counts change.
5. **The plan requires perft counts but does not define positions or values.**
   This spec fixes six encoding-valid positions and counts in the table above.
   They are deliberately small enough to verify by hand. P1 is the reachable
   initial position; P2-P6 are legal-looking constructed positions, not
   necessarily reachable from the opening, because S1 validates encoding only.
6. **The plan does not define whether perft counts paths or resulting boards.**
   This spec counts paths: two capture orders that remove the same pieces and
   end on the same square are two moves. P6 demonstrates the difference. If the
   project wants perft to count distinct resulting boards, P6 depth 1 becomes
   `1` and later counts change.
7. **The plan does not define the apply-move legality check.** This spec makes
   `apply_move` validate by membership in `generate_moves`. That is simple and
   correct for 5x5, but it makes every application regenerate moves. Later
   slices may replace it with incremental checks; tests assert behaviour, not
   implementation.

## Approval

Approved by the author on 2026-10-29.

Approved decisions:

1. The `Move`, `generate_moves`, and `apply_move` public interface.
2. The S2/S3 boundary: pure board application in S2, counters and terminal
   logic in S3.
3. Mandatory captures, no maximum-capture rule, promotion ending the move, and
   the capture/path rules above.
4. The action-key bit layout and the 33-bit limit.
5. The six perft fixtures, their counts, and path-based counting.
6. The `apply_move` membership check.
7. The TDD order and the option to split S2 into green quiet-move and capture
   commits if needed.

The next step is `/tdd` for the first behaviour in S2.
