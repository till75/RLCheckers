# Spec 0003 — Game application and random play

- **Status:** approved
- **Date:** 2026-10-29
- **Slice:** S3 — Game application and random play
- **Related:** `docs/00-brief.md`, `docs/plan.md`, ADR 0001, ADR 0002,
  `docs/architecture.md`, `docs/specs/0002-legal-move-generation.md`

## Outcome

A caller can wrap a `Board` in a `GameState`, apply legal moves while the game
tracks repetition and no-progress, observe a win or draw as soon as it happens,
and play a seeded random-vs-random game from the initial position to a
reproducible result, including through
`python -m rlcheckers play-random --seed N`.

## Public interface

### Modules and imports

The new production modules are:

- `src/rlcheckers/game/state.py` — `GameState`, `GameRecord`, `Outcome`,
  `DrawReason`, and the draw-limit constants.
- `src/rlcheckers/agents/__init__.py` and
  `src/rlcheckers/agents/random_agent.py` — `RandomAgent`,
  `play_random_game`, and the game-length guard.
- `src/rlcheckers/cli.py` and `src/rlcheckers/__main__.py` — the
  `play-random` command and the `python -m rlcheckers` entry point.

The display helper `format_move` is added to the existing
`src/rlcheckers/game/moves.py`. It is a presentation helper, not a parser.

Canonical imports:

```python
from rlcheckers.game.moves import Move, apply_move, format_move, generate_moves
from rlcheckers.game.state import (
    NO_PROGRESS_PLY_LIMIT,
    REPETITION_LIMIT,
    DrawReason,
    GameRecord,
    GameState,
    Outcome,
)
from rlcheckers.agents.random_agent import (
    MAX_GAME_PLIES,
    RandomAgent,
    play_random_game,
)
```

`rlcheckers.game` re-exports `Outcome`, `DrawReason`, `GameState`, `GameRecord`,
`NO_PROGRESS_PLY_LIMIT`, `REPETITION_LIMIT`, and `format_move` in addition to
its current names. `rlcheckers.agents` re-exports `RandomAgent`,
`play_random_game`, and `MAX_GAME_PLIES`.

`state.py`, `random_agent.py`, and `cli.py` use only the standard library and
the existing `rlcheckers` modules. They do no numeric work and import no numpy.

### Enums and constants

| Symbol | Type | Value / contract |
|---|---|---|
| `Outcome` | `Enum` | `ONGOING = "ongoing"`, `BLACK_WIN = "black_win"`, `WHITE_WIN = "white_win"`, `DRAW = "draw"` |
| `DrawReason` | `Enum` | `THREEFOLD_REPETITION = "threefold_repetition"`, `NO_PROGRESS = "no_progress"` |
| `NO_PROGRESS_PLY_LIMIT` | `int` | `80` |
| `REPETITION_LIMIT` | `int` | `3` |
| `MAX_GAME_PLIES` | `int` | `2000` |

`Outcome` and `DrawReason` are ordinary `Enum` members with string values.
`Outcome` values are the stable machine-readable result names printed by the
CLI; `DrawReason` values are for tests and diagnostics. Comparisons use `is`.

`MAX_GAME_PLIES` is a defensive loop guard, not a game rule. With the 80-ply
no-progress rule and a finite number of captures and promotions, a correct game
terminates well below it. If a random game reaches the guard, the loop raises
`RuntimeError` rather than hanging.

### `GameState`

`GameState` is immutable and compares by value. It owns the current board, the
sequence of canonical position keys seen so far, and the no-progress counter.
Histories and counters are immutable tuples and integers; no public mutator
exists. Two states are equal exactly when `board`, `position_keys`, and
`no_progress_plies` are equal, so states with the same board but different
histories are distinct.

| Member | Signature | Contract |
|---|---|---|
| Constructor | `GameState(board: Board, position_keys: Sequence[int] = (), no_progress_plies: int = 0)` | Normalises `position_keys` to a tuple. If empty, seeds it with `board.state_key`. Validates the types and ranges below. |
| `from_board` | `from_board(board: Board, *, no_progress_plies: int = 0) -> GameState` | The normal entry point. Equivalent to `GameState(board, (), no_progress_plies)`, so the current position counts as its first occurrence. |
| `board` | `Board` | The current position, including side to move. |
| `position_keys` | `tuple[int, ...]` | Every canonical position key recorded so far, in play order, ending with `board.state_key`. `from_board` starts the tuple with the construction position; a caller-supplied history is trusted for earlier entries. |
| `no_progress_plies` | `int` | Consecutive plies since the last capture or promotion. Range `0..80`. |
| `outcome` | `Outcome` property | `ONGOING`, a win, or a draw, evaluated by the contract below. |
| `draw_reason` | `DrawReason \| None` property | `None` unless `outcome is Outcome.DRAW`, otherwise the rule that triggered the draw. |
| `is_terminal` | `bool` property | `True` exactly when `outcome is not Outcome.ONGOING`. |
| `legal_moves` | `legal_moves() -> tuple[Move, ...]` | `()` when terminal; otherwise `generate_moves(board)`. |
| `apply` | `apply(move: Move) -> GameState` | Returns the next game state. Rejects a move when the game is already finished or the move is not legal. The source state is not mutated. |

Constructor validation:

- `board` must be a `Board`.
- `position_keys` must be a sequence of integers, each in `0..2**40-1`. After
  the empty-sequence default, the last key must equal `board.state_key`.
  Earlier keys are not checked for reachability; this mirrors `Board`'s
  encoding-only validation. Type checks run before the last-key check, so a
  non-integer history raises `TypeError` even when it also fails the last-key
  comparison.
- `no_progress_plies` must be an `int` in `0..80`. A value above 80 is
  contradictory because a state at 80 is already drawn and cannot be advanced.
- The board must contain at least one piece in total. A board with no pieces at
  all is not a game and is rejected. `Board` itself still accepts the empty
  encoding.

Error types and messages:

| Input | Expected |
|---|---|
| `board` is not a `Board` | `TypeError` naming `board` |
| `no_progress_plies=-1` | `ValueError` naming `no_progress_plies` |
| `no_progress_plies=81` | `ValueError` naming `no_progress_plies` |
| `no_progress_plies="0"` | `TypeError` naming `no_progress_plies` |
| `position_keys=(0,)` when the board key is not `0` | `ValueError` naming `position_keys` |
| `position_keys=("0",)` | `TypeError` naming `position_keys` |
| a board with no pieces | `ValueError` naming the board or pieces |

Tests assert substrings, not full wording.

### `GameRecord`

`GameRecord` is an immutable value object for one finished random game.

| Member | Signature | Contract |
|---|---|---|
| Constructor | `GameRecord(moves: Sequence[Move], final_state: GameState)` | Normalises `moves` to a tuple. |
| `moves` | `tuple[Move, ...]` | The move sequence from the initial position, in order. |
| `final_state` | `GameState` | The terminal state after the last move. |
| `outcome` | `Outcome` property | `final_state.outcome`. |
| `plies` | `int` property | `len(moves)`. |

Two records are equal exactly when their `moves` tuples and their
`final_state` values are equal.

### `RandomAgent`

```python
class RandomAgent:
    def __init__(self, seed: int | None = None) -> None: ...
    def choose_move(self, state: GameState) -> Move: ...
```

- `seed` must be an `int` or `None`. Other types raise `TypeError` naming
  `seed`. The agent owns a private `random.Random(seed)`.
- `choose_move` raises `ValueError` containing `finished` when
  `state.is_terminal`.
- Otherwise it chooses uniformly from `state.legal_moves()` and returns one
  move. It does not mutate the state.
- Two agents created with the same seed make the same choice from the same
  state. One agent's successive choices advance its own stream and may differ.
- `choose_move` uses the same rules as every other caller: it never generates
  moves directly and never bypasses terminal detection.

### `play_random_game`

```python
def play_random_game(seed: int) -> GameRecord: ...
```

- Requires an `int` seed; other types raise `TypeError` naming `seed`.
- Creates one `RandomAgent(seed=seed)` and one
  `GameState.from_board(Board.initial())`.
- While the state is not terminal, asks the agent for a move, appends it,
  applies it, and checks the loop guard.
- Returns a `GameRecord` with the full move tuple and the terminal final state.
- Replaying the same seed returns an equal `GameRecord`, including the same
  move sequence, final board, position-key history, counters, and outcome.
- If more than `MAX_GAME_PLIES` moves are played without reaching a terminal
  state, raises `RuntimeError` containing `did not terminate`.
- One agent and one RNG stream serve both colours, so the seed reproduces the
  whole game. This is not a per-side seed scheme.

### `format_move`

```python
def format_move(move: Move) -> str: ...
```

Returns the square path as decimal indices with `-` between squares for a quiet
move and `x` between squares for a capture:

| Move | Result |
|---|---|
| `Move((6, 10))` | `"6-10"` |
| `Move((18, 6), (12,))` | `"18x6"` |
| `Move((2, 14, 22), (8, 18))` | `"2x14x22"` |
| `Move((14, 2, 10, 22, 14), (8, 6, 16, 18))` | `"14x2x10x22x14"` |

The captured squares are implied by the path and the board; they are not
printed separately. `format_move` has no inverse and accepts no string input.
It is display-only and does not change `Move.action_key`.

### CLI

`src/rlcheckers/cli.py` exposes:

```python
def main(argv: Sequence[str] | None = None) -> int: ...
```

`main` builds an `argparse` parser with one required subcommand,
`play-random`, and one required option, `--seed INT`. On success it writes the
game to stdout and returns `0`. `argparse` errors, including a missing or
non-integer seed, exit with code `2` and write usage to stderr.

`src/rlcheckers/__main__.py` runs `sys.exit(main())` when executed as a module.

The exact successful output is:

```text
seed: <seed>
1. <move>
2. <move>
...
result: <outcome value>
plies: <move count>
```

- The first line is `seed: ` followed by the seed as parsed by `argparse`.
- Each move line is `"{index}. {format_move(move)}"`, with the index starting
  at `1`.
- The result line is `result: ` followed by `Outcome.value`, so it is one of
  `black_win`, `white_win`, or `draw`.
- The final line is `plies: ` followed by `len(record.moves)`.
- There are no blank lines, no board render, and no draw-reason line.
- `print` adds one trailing newline. The command writes nothing to stderr on
  success.
- `python -m rlcheckers play-random --seed 7` produces the same output as
  `main(["play-random", "--seed", "7"])`.

## State transition contract

`GameState.apply(move)` performs these steps in order:

1. If `is_terminal`, raise `ValueError` containing `finished` and the current
   outcome value. Do not validate or apply the move.
2. Apply the move with S2's `apply_move(board, move)`. That function rejects
   any move not returned by `generate_moves(board)` with `ValueError`
   containing `not legal`.
3. Detect promotion by comparing the moving piece and the landing piece: the
   origin must hold a man and the destination must hold a king of the same
   colour. Promotion ends the move already; this step only records that it
   happened.
4. Compute the next no-progress count:
   - `0` when `move.is_capture` is true;
   - `0` when the move promoted a man;
   - otherwise `self.no_progress_plies + 1`.
5. Append `next_board.state_key` to `position_keys`.
6. Return `GameState(next_board, next_keys, next_no_progress)`.

The source `GameState` and its `Board` are never mutated.

Because a state with `no_progress_plies == 80` is terminal, `apply` is rejected
there and can never produce an 81. A capture or promotion on the 80th ply
resets the counter instead, so that game continues.

The position key is the ADR 0002 key: it includes the side to move and ignores
the no-progress counter and the history length. The no-progress counter is
independent of repetition.

## Outcome and draw contract

`outcome` is evaluated in this order:

1. If Black has no pieces, `WHITE_WIN`.
2. If White has no pieces, `BLACK_WIN`.
3. If the side to move has no legal moves, that side loses:
   `WHITE_WIN` when Black is to move, otherwise `BLACK_WIN`.
4. If `board.state_key` appears at least `REPETITION_LIMIT` times in
   `position_keys`, `DRAW`.
5. If `no_progress_plies >= NO_PROGRESS_PLY_LIMIT`, `DRAW`.
6. Otherwise `ONGOING`.

Consequences:

- A decisive result wins over a draw rule. A move that both reaches 80
  no-progress plies and leaves the opponent with no pieces or no moves is a win,
  not a draw.
- Threefold repetition wins over no-progress when both apply.
- Repetition is counted over the whole game. Captures and promotions do not
  clear the position history; the 80-ply counter is the only reset.
- The construction position counts as occurrence `1`. A position that returns
  twice more is the third occurrence.
- Repetition is not required to be consecutive. Any three occurrences of the
  same key trigger the draw.
- `draw_reason` is `THREEFOLD_REPETITION` when step 4 triggers, `NO_PROGRESS`
  when only step 5 triggers, and `None` for every non-draw outcome.

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

### A1 — Fresh game state

A fresh state wraps the initial board, counts the initial position once, and
offers the same moves as the generator:

```python
game = GameState.from_board(Board.initial())
assert game.board == Board.initial()
assert game.position_keys == (Board.initial().state_key,)
assert game.no_progress_plies == 0
assert game.outcome is Outcome.ONGOING
assert game.draw_reason is None
assert game.is_terminal is False
assert game.legal_moves() == generate_moves(Board.initial())
```

### A2 — Applying a quiet move

A quiet move updates the board, alternates the side, increments the counter,
appends the new key, and leaves the source state untouched:

```python
game = GameState.from_board(Board.initial())
after = game.apply(Move((6, 10)))

assert after.board == apply_move(Board.initial(), Move((6, 10)))
assert after.board.side_to_move is Side.WHITE
assert after.no_progress_plies == 1
assert after.position_keys == (
    Board.initial().state_key,
    after.board.state_key,
)
assert after.outcome is Outcome.ONGOING
assert after.legal_moves() == generate_moves(after.board)

assert game.board == Board.initial()
assert game.no_progress_plies == 0
assert game.position_keys == (Board.initial().state_key,)
```

### A3 — Capture and promotion reset no-progress

A capture resets the counter even when it is the 80th ply. On the fixture P4
position, Black has exactly one legal move, the two-capture sequence
`(20, 12, 4)` capturing `16` and `8`:

```python
board = board_with(
    {
        20: Piece.BLACK_KING,
        16: Piece.WHITE_MAN,
        8: Piece.WHITE_MAN,
        10: Piece.WHITE_MAN,
    }
)
game = GameState.from_board(board, no_progress_plies=79)
after = game.apply(Move((20, 12, 4), (16, 8)))

assert after.no_progress_plies == 0
assert after.outcome is Outcome.ONGOING
assert len(after.position_keys) == 2
```

A promotion also resets the counter. On this position, Black's only quiet moves
are two promotions:

```python
board = board_with({16: Piece.BLACK_MAN, 2: Piece.WHITE_KING})
game = GameState.from_board(board, no_progress_plies=33)
after = game.apply(Move((16, 20)))

assert after.board.piece_at(4, 0) is Piece.BLACK_KING
assert after.no_progress_plies == 0
assert after.outcome is Outcome.ONGOING
```

### A4 — Terminal wins

A side with no pieces loses even when it is not to move. A side with pieces but
no legal move loses when it is to move:

```python
game = GameState.from_board(board_with({20: Piece.BLACK_KING}))
assert game.outcome is Outcome.BLACK_WIN
assert game.draw_reason is None
assert game.is_terminal is True
assert game.legal_moves() == ()

game = GameState.from_board(
    board_with(
        {
            0: Piece.BLACK_MAN,
            6: Piece.WHITE_MAN,
            12: Piece.WHITE_MAN,
        }
    )
)
assert game.outcome is Outcome.WHITE_WIN

game = GameState.from_board(board_with({0: Piece.BLACK_KING}, Side.WHITE))
assert game.outcome is Outcome.BLACK_WIN
```

A capture that removes the last opponent piece wins immediately:

```python
board = board_with({20: Piece.BLACK_KING, 16: Piece.WHITE_MAN})
game = GameState.from_board(board)
after = game.apply(Move((20, 12), (16,)))

assert after.board.side_to_move is Side.WHITE
assert after.outcome is Outcome.BLACK_WIN
assert after.legal_moves() == ()
```

Applying a move after the game has finished fails:

```python
with pytest.raises(ValueError, match="finished"):
    GameState.from_board(board_with({20: Piece.BLACK_KING})).apply(Move((20, 16)))
```

An illegal move on a live game fails through S2:

```python
with pytest.raises(ValueError, match="not legal"):
    GameState.from_board(Board.initial()).apply(Move((0, 6)))
```

### A5 — Threefold repetition

Two kings shuffle around a four-ply cycle. The starting position occurs for the
second time after four plies and for the third time after eight:

```python
board = board_with({0: Piece.BLACK_KING, 20: Piece.WHITE_KING})
game = GameState.from_board(board)
cycle = (
    Move((0, 6)),
    Move((20, 16)),
    Move((6, 0)),
    Move((16, 20)),
)

for move in cycle:
    game = game.apply(move)

assert game.board == board
assert game.outcome is Outcome.ONGOING
assert game.position_keys.count(board.state_key) == 2

for move in cycle:
    game = game.apply(move)

assert game.board == board
assert game.outcome is Outcome.DRAW
assert game.draw_reason is DrawReason.THREEFOLD_REPETITION
assert game.position_keys.count(board.state_key) == 3
assert game.legal_moves() == ()
assert game.is_terminal is True
```

### A6 — No-progress draw

A quiet non-promoting move from 79 plies reaches 80 and draws immediately:

```python
board = board_with({0: Piece.BLACK_KING, 20: Piece.WHITE_KING})
game = GameState.from_board(board, no_progress_plies=79)
assert game.outcome is Outcome.ONGOING

after = game.apply(Move((0, 6)))
assert after.no_progress_plies == 80
assert after.outcome is Outcome.DRAW
assert after.draw_reason is DrawReason.NO_PROGRESS
assert after.legal_moves() == ()
```

A constructed state at 80 is already drawn even though the board has moves:

```python
game = GameState.from_board(Board.initial(), no_progress_plies=80)
assert game.outcome is Outcome.DRAW
assert game.draw_reason is DrawReason.NO_PROGRESS
assert game.is_terminal is True
```

### A7 — Draw reasons and precedence

A non-draw has no reason. Repetition takes precedence over no-progress when both
apply:

```python
initial = GameState.from_board(Board.initial())
assert initial.draw_reason is None

board = board_with({0: Piece.BLACK_KING, 20: Piece.WHITE_KING})
key = board.state_key
both = GameState(board, (key, key, key), 80)
assert both.outcome is Outcome.DRAW
assert both.draw_reason is DrawReason.THREEFOLD_REPETITION
```

A decisive result takes precedence over both draw rules:

```python
finished = GameState.from_board(
    board_with({20: Piece.BLACK_KING}), no_progress_plies=80
)
assert finished.outcome is Outcome.BLACK_WIN
assert finished.draw_reason is None
```

### A8 — State validation and immutability

`GameState` is immutable and validates its counters and history:

```python
game = GameState.from_board(Board.initial())
with pytest.raises(AttributeError):
    game.no_progress_plies = 1
assert isinstance(game.position_keys, tuple)

with pytest.raises(ValueError, match="no_progress_plies"):
    GameState.from_board(Board.initial(), no_progress_plies=-1)
with pytest.raises(ValueError, match="no_progress_plies"):
    GameState.from_board(Board.initial(), no_progress_plies=81)
with pytest.raises(TypeError, match="no_progress_plies"):
    GameState.from_board(Board.initial(), no_progress_plies="0")

with pytest.raises(ValueError, match="position_keys"):
    GameState(Board.initial(), (0,))
with pytest.raises(TypeError, match="position_keys"):
    GameState(Board.initial(), ("0",))

with pytest.raises(ValueError, match="piece"):
    GameState.from_board(Board.from_state_key(0))
```

Passing an empty history seeds the current key:

```python
game = GameState(Board.initial(), (), 0)
assert game.position_keys == (Board.initial().state_key,)
assert game.no_progress_plies == 0
```

### A9 — Move display

The display helper is deterministic and uses `-` for quiet moves and `x` for
captures:

```python
assert format_move(Move((6, 10))) == "6-10"
assert format_move(Move((18, 6), (12,))) == "18x6"
assert format_move(Move((2, 14, 22), (8, 18))) == "2x14x22"
assert (
    format_move(Move((14, 2, 10, 22, 14), (8, 6, 16, 18)))
    == "14x2x10x22x14"
)
```

### A10 — Random agent

The agent chooses only legal moves, is reproducible by seed, and refuses a
finished game:

```python
game = GameState.from_board(Board.initial())
agent = RandomAgent(seed=123)

assert agent.choose_move(game) in game.legal_moves()
assert RandomAgent(seed=123).choose_move(game) == RandomAgent(
    seed=123
).choose_move(game)

finished = GameState.from_board(board_with({20: Piece.BLACK_KING}))
with pytest.raises(ValueError, match="finished"):
    RandomAgent(seed=1).choose_move(finished)

with pytest.raises(TypeError, match="seed"):
    RandomAgent(seed="1")
```

### A11 — Seeded random play

The same seed reproduces the whole game, and every tested seed terminates:

```python
first = play_random_game(7)
second = play_random_game(7)

assert first == second
assert first.plies == len(first.moves)
assert first.plies > 0
assert first.final_state.is_terminal
assert first.outcome is first.final_state.outcome

for seed in range(5):
    record = play_random_game(seed)
    assert record.final_state.is_terminal
    assert 0 < record.plies <= MAX_GAME_PLIES

with pytest.raises(TypeError, match="seed"):
    play_random_game("7")
```

### A12 — CLI

The command prints a stable, readable game:

```python
assert main(["play-random", "--seed", "7"]) == 0
out = capsys.readouterr().out
lines = out.splitlines()
record = play_random_game(7)

assert out.endswith("\n")
assert lines[0] == "seed: 7"
assert lines[1:-2] == [
    f"{index}. {format_move(move)}"
    for index, move in enumerate(record.moves, start=1)
]
assert lines[-2] == f"result: {record.outcome.value}"
assert lines[-1] == f"plies: {record.plies}"
```

Replaying the command with the same seed produces identical output:

```python
main(["play-random", "--seed", "7"])
first = capsys.readouterr().out
main(["play-random", "--seed", "7"])
second = capsys.readouterr().out
assert first == second
```

A missing or non-integer seed is an `argparse` error:

```python
with pytest.raises(SystemExit) as excinfo:
    main(["play-random"])
assert excinfo.value.code == 2
assert "--seed" in capsys.readouterr().err

with pytest.raises(SystemExit) as excinfo:
    main(["play-random", "--seed", "abc"])
assert excinfo.value.code == 2
```

The module entry point works in a subprocess:

```python
completed = subprocess.run(
    [
        sys.executable,
        "-m",
        "rlcheckers",
        "play-random",
        "--seed",
        "7",
    ],
    capture_output=True,
    text=True,
    check=False,
)
assert completed.returncode == 0
assert completed.stdout.startswith("seed: 7\n")
assert completed.stderr == ""
```

### A13 — Documentation

`docs/architecture.md` records that S3 implements `GameState`, `GameRecord`,
`Outcome`, the repetition and no-progress counters, terminal detection,
`RandomAgent`, `play_random_game`, and the `play-random` CLI command. It keeps
the S4 evaluation and S5 learning boundaries accurate. `README.md` updates its
status and shows the command:

```powershell
.\.venv\Scripts\python.exe -m rlcheckers play-random --seed 7
```

Module docstrings in `state.py`, `random_agent.py`, and `cli.py` state the
counter, outcome, reproducibility, and output contracts in a short paragraph.
The `moves.py` docstring mentions `format_move` and its display-only role.

## Tests to add

State tests live in `tests/game/test_state.py`. Random-agent and seeded-play
tests live in `tests/agents/test_random_agent.py`. CLI tests live in
`tests/test_cli.py`. The `format_move` tests are added to
`tests/game/test_moves.py`, next to the S2 `Move` tests. Tests may use local
helpers; no helper becomes production API.

| Criterion | Test(s) |
|---|---|
| A1 | `test_fresh_game_wraps_initial_board`, `test_fresh_game_is_ongoing`, `test_fresh_game_legal_moves_match_generator` |
| A2 | `test_apply_quiet_move_updates_board_and_turn`, `test_apply_quiet_move_increments_no_progress`, `test_apply_appends_position_key`, `test_apply_does_not_mutate_source_state` |
| A3 | `test_capture_resets_no_progress`, `test_promotion_resets_no_progress` |
| A4 | `test_side_without_pieces_loses`, `test_side_without_legal_moves_loses`, `test_capture_ending_the_game_wins`, `test_terminal_state_has_no_legal_moves`, `test_apply_after_terminal_state_fails`, `test_apply_rejects_illegal_move` |
| A5 | `test_threefold_repetition_draws`, `test_twofold_repetition_is_not_a_draw` |
| A6 | `test_no_progress_draws_at_80_plies`, `test_constructed_80_ply_state_is_drawn` |
| A7 | `test_draw_reason_for_repetition`, `test_draw_reason_for_no_progress`, `test_repetition_takes_precedence_over_no_progress`, `test_win_takes_precedence_over_draw_rules`, `test_non_draw_has_no_draw_reason` |
| A8 | `test_game_state_is_immutable`, `test_game_state_seeds_empty_position_history`, `test_game_state_rejects_bad_position_history`, `test_game_state_rejects_bad_no_progress_count`, `test_game_state_rejects_empty_board` |
| A9 | `test_format_move_quiet`, `test_format_move_single_capture`, `test_format_move_multi_capture` |
| A10 | `test_random_agent_chooses_legal_move`, `test_random_agent_same_seed_same_choice`, `test_random_agent_rejects_finished_game`, `test_random_agent_rejects_bad_seed` |
| A11 | `test_play_random_game_is_reproducible`, `test_play_random_game_terminates_for_seeds`, `test_play_random_game_rejects_bad_seed` |
| A12 | `test_cli_play_random_output`, `test_cli_play_random_is_reproducible`, `test_cli_requires_seed`, `test_cli_rejects_non_integer_seed`, `test_module_entry_point_runs_play_random` |
| A13 | Documentation review, not a unit test |

Tests use plain `pytest` assertions, `pytest.raises` with `match` for errors,
exact tuples for move lists, and `capsys` for CLI output.

## TDD order

S3 is an M slice. Follow this order and stop at a testable boundary if the
session runs out; do not carry a half-finished slice across turns.

1. **Bootstrap before the first red test:** create `state.py`, `agents/__init__.py`,
   `agents/random_agent.py`, `cli.py`, and `__main__.py` with the public
   signatures raising `NotImplementedError`; add `format_move` to `moves.py`
   with the same treatment; wire the package re-exports. Verify the imports
   work. The first failure must be missing behaviour, not a missing module.
2. Write the first failing test for A1 (fresh game state) and implement the
   immutable wrapper, history seeding, counter field, `legal_moves`, and the
   ongoing outcome.
3. Add A2 (quiet application), A3 (capture and promotion resets), and A4
   (terminal wins and finished-game rejection).
4. Add A5 (threefold repetition), A6 (no-progress boundary), and A7 (reasons
   and precedence).
5. Add A8 (validation and immutability), then A9 (`format_move`).
6. Add A10 and A11 (agent and seeded random play, including the loop guard).
7. Add A12 (CLI and module entry point).
8. Update `docs/architecture.md`, `README.md`, and the module docstrings; run
   the full suite and `ruff check .`; commit one coherent S3 change. If the work
   was split, use two green commits at the state and random/CLI boundaries,
   update `docs/plan.md`, and keep every commit green.
9. Do not push unless asked.

## Out of scope

- The S4 evaluation arena, opening suite, colour pairing, depth-1 greedy
  baseline, W/D/L metrics, derived score, CSV output, and plots.
- The S5 Q-table, `q_key`, Q-learning, epsilon-greedy selection, save/load,
  memory cap, and training loop.
- Self-play, snapshots, the three-seed gate, and the milestone report.
- TOML config files, CLI overrides, artifact writing, and run metadata.
- A shared `Agent` protocol. S3 defines only `RandomAgent.choose_move`; S4 may
  generalize it.
- Move parsing, round-tripping `format_move`, algebraic or numbered notation,
  and interactive play.
- Board rendering in the CLI, ANSI colour, and terminal-width handling.
- Saving, loading, or serializing `GameState` and `GameRecord`.
- Undo/unmake, replays from saved move lists, and a move-history API beyond
  `GameRecord.moves`.
- Draw claims by agreement, adjudication, and time controls. S3 only detects
  the automatic ADR 0001 draws.
- Maximum-capture rules, huffing, optional captures, and any 8x8 rules. S3
  consumes S2's move set unchanged.
- Performance work beyond straightforward Python. `outcome` may regenerate
  moves; optimize only if profiling shows a problem.
- Packaging, publishing, a console-script entry point, and distribution.

## Contradictions, gaps, and decisions

These need explicit approval because the brief, plan, or an ADR does not fully
settle them:

1. **Win versus draw precedence.** ADR 0001 lists no-piece/no-move losses and
   the two draw rules without an order. This spec checks decisive results first,
   then threefold repetition, then no-progress. A move that both reaches 80
   plies and leaves the opponent with no moves is therefore a win, not a draw.
   If you prefer the draw rule to win, the outcome order changes.
2. **Repetition scope and the starting occurrence.** ADR 0001 says "threefold
   repetition of the same position with the same side to move" but does not say
   whether the history resets on captures or promotions, or whether the
   construction position counts. This spec counts the whole game, does not
   reset on irreversible moves, and counts the construction position as
   occurrence `1`. The 80-ply counter is the only reset.
3. **No-progress boundary and reset timing.** "After 80 plies" could mean the
   game is drawn before or after the 80th move. This spec plays the 80th ply,
   then draws, and lets a capture or promotion on that ply reset the counter and
   continue. A state constructed at 80 is immediately drawn.
4. **A board with no pieces at all.** ADR 0001 says each side loses when it has
   no pieces, which is contradictory when both sides have none. This spec
   rejects such a board in `GameState` as not a game. `Board` remains
   encoding-only and still accepts the empty encoding.
5. **Where the game loop and record live.** The plan lists `state.py`,
   `random_agent.py`, `cli.py`, and `__main__.py` but does not name a record
   type or say where the loop belongs. This spec adds `GameRecord` to
   `state.py` and `play_random_game` to `random_agent.py` rather than creating
   a separate play module. S4 can reuse or replace the loop when it adds the
   arena.
6. **CLI format and seed requirement.** The plan requires moves and a result
   but does not define the text or whether the seed is optional. This spec
   fixes the four-part output, makes `--seed` required, and does not print the
   board or the draw reason. A missing seed is an `argparse` error, not a
   defaulted run.
7. **Display notation.** S2 declared move notation out of scope. S3 needs
   readable CLI output, so it adds `format_move` to `moves.py`. This is a
   display-only path string with no parser and no effect on `action_key`. If
   notation should stay entirely out of S3, the CLI can print path tuples
   instead, at the cost of readability.
8. **One RNG stream for both colours.** `play_random_game` uses one
   `RandomAgent` for the whole game, so both sides draw from the same seeded
   stream. This makes replay exact but is not a per-side seed scheme. S4 may
   choose separate agents and seeds when it pairs different baselines.
9. **No shared agent protocol yet.** S3 exposes only
   `RandomAgent.choose_move(state)`. A common `Agent` protocol, colour handling,
   and deterministic tie-breaks belong to S4. This avoids inventing an interface
   before the second agent exists.
10. **Loop guard.** `MAX_GAME_PLIES = 2000` is a defensive cap, not a rule. A
    correct draw rule makes it unreachable, but a rules bug should fail loudly
    with `RuntimeError` instead of hanging a test or a training run.
11. **Full position-key history.** `GameState` stores every key rather than only
    occurrence counts. The history is public, participates in equality, and
    makes repetition tests and future replay straightforward. The cost is
    `O(plies)` memory, which is negligible on 5x5. Counts-only storage is the
    alternative if the history should be hidden.

## Approval

Approved by the author on 2026-10-30.

Approved decisions:

1. The `GameState`, `GameRecord`, `Outcome`, and `DrawReason` public interface
   and the `apply` transition contract.
2. Decisive results before draws, and threefold repetition before no-progress.
3. Whole-game repetition history, the construction position as the first
   occurrence, and the 80th-ply draw boundary.
4. Rejecting a board with no pieces at all in `GameState`.
5. `RandomAgent.choose_move(state)`, one shared RNG stream in
   `play_random_game`, and the 2000-ply guard.
6. The CLI output format, required `--seed`, and `format_move` as a
   display-only helper.
7. The file placement in `state.py`, `agents/random_agent.py`, `cli.py`, and
   `__main__.py`, with state tests, agent tests, and CLI tests as listed.

The next step is `/tdd` for the first behaviour in S3.
