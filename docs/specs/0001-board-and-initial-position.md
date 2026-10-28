# Spec 0001 — Board and initial position

- **Status:** approved
- **Date:** 2026-10-28
- **Slice:** S1 — Board and initial position
- **Related:** `docs/00-brief.md`, `docs/plan.md`, ADR 0001, ADR 0002,
  `docs/architecture.md`

## Outcome

A caller can import the board module, construct the correct 5x5 initial
position, inspect pieces and side to move, render a stable text board, and
round-trip a 40-bit canonical state key from a project that runs pytest and
ruff in the `src/` layout.

## Public interface

### Constants and enums

| Symbol | Type | Value / contract |
|---|---|---|
| `BOARD_SIZE` | `int` | `5` |
| `SQUARE_COUNT` | `int` | `25` |
| `PLAYABLE_SQUARES` | `tuple[int, ...]` | `(0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24)` |
| `Side` | `IntEnum` | `Side.BLACK = 0`, `Side.WHITE = 1` |
| `Piece` | `IntEnum` | `Piece.EMPTY = 0`, `Piece.BLACK_MAN = 1`, `Piece.BLACK_KING = 2`, `Piece.WHITE_MAN = 3`, `Piece.WHITE_KING = 4` |

`Piece` and `Side` are integer enums. Their integer values are the encoding in
ADR 0002; using the enum names is for readability, not a different wire format.

### `Board`

`Board` is immutable and compares by value. It has no public mutators.

| Member | Signature | Contract |
|---|---|---|
| Constructor | `Board(cells: Sequence[Piece \| int \| None], side_to_move: Side \| int = Side.BLACK)` | Accepts exactly 25 cells and a side. Normalises accepted integers to `Piece` and `Side`. Rejects invalid input with a clear error. |
| `initial` | `Board.initial() -> Board` | Returns the position in this spec with Black to move. |
| `from_state_key` | `Board.from_state_key(key: int) -> Board` | Decodes a 40-bit canonical key. This is the concrete form of ADR 0002's `decode_state` helper. |
| `cells` | `tuple[Piece \| None, ...]` | Read-only, length 25, row-major. `None` means non-playable; `Piece.EMPTY` means an empty playable square. |
| `side_to_move` | `Side` | `Side.BLACK` or `Side.WHITE`. |
| `state_key` | `int` property | Canonical 40-bit key in `0 .. 2**40 - 1`. |
| `piece_at` | `piece_at(row: int, col: int) -> Piece \| None` | Returns `None` for a non-playable square, `Piece.EMPTY` for an empty playable square, otherwise the piece. |
| `render` | `render() -> str` | Returns the stable plain-text board and side-to-move line described below. |

Canonical import path:

```python
from rlcheckers.game.board import (
    BOARD_SIZE,
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)
```

`rlcheckers.game` re-exports `Board`, `Piece`, `Side`, and
`PLAYABLE_SQUARES`, so `from rlcheckers.game import Board` also works.

## Data model and invariants

- Square index is `row * 5 + col`, with `row` and `col` in `0..4`.
- A square is playable exactly when `(row + col) % 2 == 0`.
- `PLAYABLE_SQUARES` is the row-major list of those 13 indices:
  `0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24`.
- `Board.cells` always has 25 entries.
- Every non-playable entry is `None`.
- Every playable entry is a `Piece` with integer value `0..4`.
- `Board` validates encoding, not reachability or piece counts. A board with no
  pieces, only kings, or more than five pieces per side is encoding-valid; game
  legality is decided later.
- `board.py` is pure Python and uses only the standard library. It does no I/O,
  imports no numpy, and does not depend on agents or training code.

## Initial position

`Board.initial()` has Black to move and this layout:

| Row | Col 0 | Col 1 | Col 2 | Col 3 | Col 4 |
|---|---|---|---|---|---|
| 0 | `BLACK_MAN` | `None` | `BLACK_MAN` | `None` | `BLACK_MAN` |
| 1 | `None` | `BLACK_MAN` | `None` | `BLACK_MAN` | `None` |
| 2 | `EMPTY` | `None` | `EMPTY` | `None` | `EMPTY` |
| 3 | `None` | `WHITE_MAN` | `None` | `WHITE_MAN` | `None` |
| 4 | `WHITE_MAN` | `None` | `WHITE_MAN` | `None` | `WHITE_MAN` |

Counts across the 25 cells:

| Cell kind | Count |
|---|---:|
| Black men | 5 |
| White men | 5 |
| Empty playable squares | 3 |
| Non-playable (`None`) | 12 |

Black squares, in `(row, col)` order, are
`(0,0), (0,2), (0,4), (1,1), (1,3)`. White squares are
`(4,0), (4,2), (4,4), (3,1), (3,3)`.

The canonical initial key is:

```text
0x36DB001249  (235602448969 decimal)
```

## Canonical state key

The key is a 40-bit integer. For a board:

```text
key = int(side_to_move) << 39
for i, square in enumerate(PLAYABLE_SQUARES):
    key |= int(cells[square]) << (3 * i)
```

Bit layout:

| Bits | Meaning |
|---|---|
| `3i .. 3i+2` | Piece code at `PLAYABLE_SQUARES[i]` |
| `0..2` | Playable cell 0, square 0 |
| `36..38` | Playable cell 12, square 24 |
| `39` | Side to move: `0` Black, `1` White |

The key contains only playable cells. Non-playable squares contribute no bits.

Concrete examples:

| Board | Key |
|---|---|
| Initial, Black to move | `0x36DB001249` |
| Initial, White to move | `0xB6DB001249` |
| All playable cells empty, Black to move | `0x0` |
| All playable cells empty, White to move | `0x8000000000` |
| Black king on square 0, all else empty, Black | `0x2` |
| White king on square 24, all else empty, Black | `0x4000000000` |

Changing a piece adds `(new_code - old_code) << (3 * i)`. For example, changing
the Black man on square 0 to a Black king adds `1 << 0`; changing the White man
on square 16 to a White king adds `1 << 24`.

`Board.from_state_key(key)`:

- Requires an integer key in `0 .. 2**40 - 1`.
- Rejects piece codes `5..7` with a `ValueError`.
- Reconstructs non-playable cells as `None`.
- Reconstructs the side from bit 39.
- Satisfies `Board.from_state_key(board.state_key) == board` for every
  encoding-valid board.

## Text rendering

`render()` uses plain ASCII and no ANSI colour:

| Symbol | Meaning |
|---|---|
| `.` | Empty playable square |
| `#` | Non-playable square |
| `b` | Black man |
| `B` | Black king |
| `w` | White man |
| `W` | White king |

The exact initial rendering is:

```text
    0 1 2 3 4
0   b # b # b
1   # b # b #
2   . # . # .
3   # w # w #
4   w # w # w
Black to move
```

The exact empty-board rendering is:

```text
    0 1 2 3 4
0   . # . # .
1   # . # . #
2   . # . # .
3   # . # . #
4   . # . # .
Black to move
```

The last line is exactly `Black to move` or `White to move`. The returned string
has no trailing newline. Row labels are `0..4`; the column header is
`0 1 2 3 4`.

## Acceptance criteria

The snippets are illustrative. Later snippets may reuse variables defined in
earlier ones, and tests will import `pytest` explicitly.

### A1 — Initial layout and counts

`Board.initial()` returns a board with Black to move, five Black men, five White
men, three empty playable squares, and twelve `None` cells. Every piece is on a
dark square:

```python
b = Board.initial()
assert b.side_to_move is Side.BLACK
assert b.piece_at(0, 0) is Piece.BLACK_MAN
assert b.piece_at(0, 2) is Piece.BLACK_MAN
assert b.piece_at(0, 4) is Piece.BLACK_MAN
assert b.piece_at(1, 1) is Piece.BLACK_MAN
assert b.piece_at(1, 3) is Piece.BLACK_MAN
assert b.piece_at(4, 0) is Piece.WHITE_MAN
assert b.piece_at(4, 2) is Piece.WHITE_MAN
assert b.piece_at(4, 4) is Piece.WHITE_MAN
assert b.piece_at(3, 1) is Piece.WHITE_MAN
assert b.piece_at(3, 3) is Piece.WHITE_MAN
assert sum(cell is Piece.BLACK_MAN for cell in b.cells) == 5
assert sum(cell is Piece.WHITE_MAN for cell in b.cells) == 5
assert sum(cell is Piece.EMPTY for cell in b.cells) == 3
assert sum(cell is None for cell in b.cells) == 12
```

### A2 — Playable map and piece access

`PLAYABLE_SQUARES` is exactly the 13 dark-square indices. Non-playable cells are
`None`; empty playable cells are `Piece.EMPTY`:

```python
assert PLAYABLE_SQUARES == (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24)
assert all((b.cells[i] is None) == (i not in PLAYABLE_SQUARES) for i in range(25))
assert b.piece_at(0, 1) is None  # light square
assert b.piece_at(2, 0) is Piece.EMPTY  # dark but empty
```

### A3 — Immutable value object

Two boards with the same cells and side compare equal. `Board.cells` is a tuple,
and an attempt to assign to a public field fails:

```python
assert Board.initial() == Board.initial()
assert isinstance(Board.initial().cells, tuple)

b = Board.initial()
with pytest.raises(AttributeError):
    b.side_to_move = Side.WHITE
```

### A4 — Initial key and stability

The initial key is documented and stable:

```python
b = Board.initial()
assert b.state_key == 0x36DB001249
assert Board.initial().state_key == b.state_key
assert 0 <= b.state_key < (1 << 40)
```

### A5 — Key changes with side and pieces

Changing side or a piece changes the key:

```python
b = Board.initial()
white_to_move = Board(b.cells, Side.WHITE)
assert white_to_move.state_key == 0xB6DB001249

black_king = list(b.cells)
black_king[0] = Piece.BLACK_KING
assert Board(tuple(black_king), Side.BLACK).state_key == b.state_key + 1

white_king = list(b.cells)
white_king[16] = Piece.WHITE_KING
assert Board(tuple(white_king), Side.BLACK).state_key == b.state_key + (1 << 24)
```

### A6 — Decode and round-trip

Decoding a key reconstructs the same board, including boundary keys:

```python
assert Board.from_state_key(0x36DB001249) == Board.initial()
assert Board.from_state_key(0).cells[0] is Piece.EMPTY
assert Board.from_state_key(0).side_to_move is Side.BLACK
assert Board.from_state_key(0x8000000000).side_to_move is Side.WHITE
assert Board.from_state_key(0x2).piece_at(0, 0) is Piece.BLACK_KING
assert Board.from_state_key(0x4000000000).piece_at(4, 4) is Piece.WHITE_KING

custom = Board(tuple(black_king), Side.WHITE)
assert Board.from_state_key(custom.state_key) == custom
```

### A7 — Render snapshots

The initial and empty renders match exactly, kings are uppercase, and the side
line follows `side_to_move`:

```python
assert Board.initial().render() == (
    "    0 1 2 3 4\n"
    "0   b # b # b\n"
    "1   # b # b #\n"
    "2   . # . # .\n"
    "3   # w # w #\n"
    "4   w # w # w\n"
    "Black to move"
)
assert not Board.initial().render().endswith("\n")

assert Board.from_state_key(0).render() == (
    "    0 1 2 3 4\n"
    "0   . # . # .\n"
    "1   # . # . #\n"
    "2   . # . # .\n"
    "3   # . # . #\n"
    "4   . # . # .\n"
    "Black to move"
)
assert Board(Board.initial().cells, Side.WHITE).render().endswith("White to move")
```

A board with kings renders `B` and `W`:

```python
assert "0   B # b # b" in Board(tuple(black_king), Side.BLACK).render()
assert "3   # W # w #" in Board(tuple(white_king), Side.BLACK).render()
```

### A8 — Invalid input fails clearly

The constructor and `piece_at` reject malformed input:

| Input | Expected |
|---|---|
| 24 cells | `ValueError` mentioning `25` |
| 26 cells | `ValueError` mentioning `25` |
| `Piece.EMPTY` on a light square | `ValueError` naming the cell index |
| `None` on a dark square | `ValueError` naming the cell index |
| Piece code `5` on a dark square | `ValueError` naming the cell index and `0..4` |
| `side_to_move=2` | `ValueError` naming `side_to_move` |
| `piece_at(-1, 0)` | `ValueError` naming `row` |
| `piece_at(0, 5)` | `ValueError` naming `col` |
| `piece_at("0", 0)` | `TypeError` naming the coordinate |

`from_state_key` rejects invalid keys:

| Input | Expected |
|---|---|
| `-1` | `ValueError` mentioning `state key` |
| `1 << 40` | `ValueError` mentioning `state key` |
| `5` (piece code `5` at cell 0) | `ValueError` mentioning `piece code` |
| non-integer | `TypeError` |

Error messages must name the offending argument, index, or value. Tests assert
substrings, not full wording.

### A9 — Project tooling

`pyproject.toml` exists and configures the `src/` layout. The editable install
and tooling checks succeed:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Minimum configuration:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "rlcheckers"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["numpy>=2", "matplotlib>=3.9"]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.9"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py314"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I"]
```

### A10 — Documentation

`docs/architecture.md` records that S1 implements the board module and keeps the
component boundaries accurate. `README.md` no longer says "No application code
yet." No diagram change is required unless the implementation adds a component.

## Tests to add

All board tests live in `tests/game/test_board.py`. Tests may use local helper
functions to build custom boards; no helper becomes production API.

| Criterion | Test(s) |
|---|---|
| A1 | `test_initial_board_layout_and_counts`, `test_initial_board_black_to_move` |
| A2 | `test_playable_square_map`, `test_piece_at_distinguishes_empty_dark_from_light_square` |
| A3 | `test_board_is_immutable_value_object` |
| A4 | `test_initial_state_key_is_stable`, `test_initial_state_key_matches_documented_value`, `test_state_key_is_within_40_bits` |
| A5 | `test_state_key_changes_with_side_to_move`, `test_state_key_changes_with_piece`, `test_state_key_bit_layout_examples` |
| A6 | `test_from_state_key_round_trips_initial_board`, `test_from_state_key_round_trips_custom_board`, `test_from_state_key_decodes_boundary_keys`, `test_from_state_key_rejects_invalid_keys` |
| A7 | `test_initial_render_snapshot`, `test_empty_board_render`, `test_render_uses_kings_and_side_line`, `test_render_has_no_trailing_newline` |
| A8 | `test_board_rejects_wrong_cell_count`, `test_board_rejects_invalid_cells`, `test_board_rejects_invalid_side`, `test_piece_at_rejects_invalid_coordinates`, `test_board_normalizes_int_inputs` |
| A9 | Tooling smoke check: editable install, `pytest`, and `ruff check .`; the board tests themselves prove the import path |
| A10 | Documentation review, not a unit test |

Tests should use plain `pytest` assertions, `pytest.raises` with `match` for
errors, and triple-quoted exact strings for render snapshots.

## TDD order

1. **Bootstrap before the first red test:** create `pyproject.toml`, the
   `src/rlcheckers/` and `src/rlcheckers/game/` packages, and an empty `tests/`
   layout; install the dependencies. Verify `import rlcheckers` works so the
   first failure is missing behaviour, not a missing package.
2. Write the first failing test for A1 (initial layout and counts).
3. Implement the minimum board data model, `Piece`, `Side`, and
   `Board.initial()` to pass it.
4. Add A2, then A4/A5 key tests, then A6 decode, then A7 render, then A8
   validation.
5. Refactor only after the relevant tests are green.
6. Update the docs, run the full suite and ruff, and commit one slice.

## Out of scope

- Legal move generation, captures, multiple captures, promotion, and king
  movement. These belong to S2.
- Move application, side switching after a move, terminal win/loss detection,
  repetition counters, and no-progress counters. These belong to S3.
- `Move`, `action_key`, and `q_key`. ADR 0002 defines them, but S1 has no move
  object; they belong to S2/S5.
- Q-table storage, Q-learning, agents, training, evaluation, CLI commands,
  config files, and artifact writing.
- Full 8x8 checkers, neural networks, MCTS, and interactive UI.
- Serialization of boards to JSON/TOML and parsing boards from files.
- Reachability validation, legal piece-count validation, or opening-book
  validation.
- ANSI colour or terminal-width-aware rendering.
- Performance optimisation beyond straightforward tuple and bit operations.
- Packaging, publishing, and distribution.

## Contradictions, gaps, and decisions

No contradiction was found in the rules, starting position, or state-key bit
layout. These gaps need explicit approval because the brief, plan, or ADR does
not fully settle them:

1. **ADR 0002 requires a decoder and a pretty-printer, but the S1 acceptance
   criteria in the plan do not mention them.** This spec includes
   `Board.from_state_key` as the decoder and `render()` as the pretty-printer.
   If you want a smaller S1, defer both to S5; that leaves ADR 0002's
   requirement unmet until then.
2. **ADR 0002 defines `action_key` and `q_key`, but S1 has no `Move`.** This
   spec deliberately limits S1 to the state key. Action and Q keys are
   implemented when moves and the Q-table exist.
3. **The plan says S1 installs dependencies and configures the project, but
   does not define the packaging or lint configuration.** This spec proposes
   setuptools, a `dev` extra, pytest with `pythonpath = ["src"]`, and a minimal
   ruff selection.
4. **The plan requires clear errors but does not define error types or
   messages.** This spec uses `ValueError` for invalid values, `TypeError` for
   non-integer keys or coordinates, and messages that name the offending field
   or index.
5. **The plan requires a text render but does not define its format.** This
   spec fixes an ASCII format, symbols, side line, and no trailing newline so
   snapshot tests are stable.
6. **ADR 0002 says the board holds integer piece codes; this spec exposes
   `Piece` and `Side` as `IntEnum` values.** The integer values remain `0..4`
   and `0..1`, so the encoding is unchanged; the enums only make the public
   interface self-documenting.

## Approval

Approved by the author on 2026-10-28.

Approved decisions:

1. Including `Board.from_state_key` and the render pretty-printer in S1.
2. The exact ASCII render format and no trailing newline.
3. `Piece` and `Side` as `IntEnum`, normalized in `Board.cells`.
4. The error taxonomy and message requirements.
5. The proposed `pyproject.toml` and tooling configuration.
