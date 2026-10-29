"""Legal move generation for the 5x5 board.

Captures are mandatory, a man captures forward only while a king captures in
any direction, and a capture chain continues until no further jump exists or a
man promotes. A promoting capture ends the move. Moves are returned in sorted
``(path, captures)`` order, and every legal capture path is returned rather
than only a maximum-length one.
"""

from __future__ import annotations

from dataclasses import dataclass

from rlcheckers.game.board import (
    BOARD_SIZE,
    PLAYABLE_SQUARES,
    Board,
    Piece,
    Side,
)

_PLAYABLE_SQUARES = frozenset(PLAYABLE_SQUARES)
_DIAGONAL_DIRECTIONS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
_MAN_DIRECTIONS = {
    Side.BLACK: ((1, -1), (1, 1)),
    Side.WHITE: ((-1, -1), (-1, 1)),
}
_PROMOTION_ROW = {Side.BLACK: BOARD_SIZE - 1, Side.WHITE: 0}


@dataclass(frozen=True)
class Move:
    """An origin, its landing squares, and the captured squares in order."""

    path: tuple[int, ...]
    captures: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        try:
            path = tuple(self.path)
        except TypeError:
            raise TypeError("path must be a sequence of ints") from None
        try:
            captures = tuple(self.captures)
        except TypeError:
            raise TypeError("captures must be a sequence of ints") from None

        if len(path) < 2:
            raise ValueError(f"path must contain at least two squares, got {path}")
        if len(path) > 6:
            raise ValueError(f"path must contain at most six squares, got {path}")

        for name, squares in (("path", path), ("captures", captures)):
            for index, square in enumerate(squares):
                if not isinstance(square, int):
                    raise TypeError(
                        f"{name}[{index}] must be an int, got "
                        f"{type(square).__name__}"
                    )
                if square not in _PLAYABLE_SQUARES:
                    raise ValueError(
                        f"{name}[{index}] must be a playable square 0..24, "
                        f"got {square}"
                    )

        if captures:
            if len(captures) != len(path) - 1:
                raise ValueError(
                    "captures must contain one square per jump, "
                    f"got {len(captures)} captures for {len(path)} path squares"
                )
            for index in range(len(path) - 1):
                start_row, start_col = divmod(path[index], BOARD_SIZE)
                end_row, end_col = divmod(path[index + 1], BOARD_SIZE)
                if abs(end_row - start_row) != 2 or abs(end_col - start_col) != 2:
                    raise ValueError(
                        f"path[{index}:{index + 2}] must be a diagonal jump "
                        "of two squares"
                    )
                midpoint = (
                    ((start_row + end_row) // 2) * BOARD_SIZE
                    + (start_col + end_col) // 2
                )
                if captures[index] != midpoint:
                    raise ValueError(
                        f"captures[{index}] must be the midpoint {midpoint} "
                        f"of path[{index}:{index + 2}], got {captures[index]}"
                    )
            if len(set(captures)) != len(captures):
                raise ValueError(
                    f"captures must not contain duplicates, got {captures}"
                )
            overlap = set(captures).intersection(path)
            if overlap:
                raise ValueError(
                    f"captures must not include path squares, got {overlap}"
                )
        else:
            if len(path) != 2:
                raise ValueError(
                    "captures must be provided when path has more than two squares"
                )
            start_row, start_col = divmod(path[0], BOARD_SIZE)
            end_row, end_col = divmod(path[1], BOARD_SIZE)
            if abs(end_row - start_row) != 1 or abs(end_col - start_col) != 1:
                raise ValueError(
                    f"path {path} must be diagonally adjacent when captures is empty"
                )

        object.__setattr__(self, "path", path)
        object.__setattr__(self, "captures", captures)

    @property
    def is_capture(self) -> bool:
        """Return whether this move captures at least one piece."""
        return bool(self.captures)

    @property
    def action_key(self) -> int:
        """Return the ADR 0002 33-bit action key."""
        key = len(self.path)
        for index, square in enumerate(self.path):
            key |= square << (3 + 5 * index)
        return key


def generate_moves(board: Board) -> tuple[Move, ...]:
    """Return every legal move for the side to move."""
    moves = _capture_moves(board)
    if not moves:
        moves = _quiet_moves(board)
    return tuple(sorted(moves, key=lambda move: (move.path, move.captures)))


def apply_move(board: Board, move: Move) -> Board:
    """Return the board after applying a legal move."""
    if move not in generate_moves(board):
        raise ValueError(f"move {move} is not legal in this position")

    cells = list(board.cells)
    piece = cells[move.path[0]]
    assert piece is not None
    for square in move.captures:
        cells[square] = Piece.EMPTY
    cells[move.path[0]] = Piece.EMPTY

    destination = move.path[-1]
    if piece is Piece.BLACK_MAN and destination // BOARD_SIZE == BOARD_SIZE - 1:
        piece = Piece.BLACK_KING
    elif piece is Piece.WHITE_MAN and destination // BOARD_SIZE == 0:
        piece = Piece.WHITE_KING
    cells[destination] = piece

    next_side = Side.WHITE if board.side_to_move is Side.BLACK else Side.BLACK
    return Board(tuple(cells), next_side)


def _quiet_moves(board: Board) -> list[Move]:
    moves: list[Move] = []
    for square in PLAYABLE_SQUARES:
        piece = board.cells[square]
        if not _belongs_to(piece, board.side_to_move):
            continue
        directions = (
            _DIAGONAL_DIRECTIONS
            if _is_king(piece)
            else _MAN_DIRECTIONS[board.side_to_move]
        )
        for row_delta, col_delta in directions:
            destination = _step(square, row_delta, col_delta)
            if destination is None:
                continue
            if board.cells[destination] is Piece.EMPTY:
                moves.append(Move((square, destination)))
    return moves


def _capture_moves(board: Board) -> list[Move]:
    moves: list[Move] = []
    for square in PLAYABLE_SQUARES:
        piece = board.cells[square]
        if _belongs_to(piece, board.side_to_move):
            moves.extend(_capture_sequences(board, square, piece, frozenset()))
    return moves


def _capture_sequences(
    board: Board,
    start: int,
    piece: Piece,
    captured: frozenset[int],
) -> list[Move]:
    side = _side_of(piece)
    directions = (
        _DIAGONAL_DIRECTIONS if _is_king(piece) else _MAN_DIRECTIONS[side]
    )
    promotion_row = _PROMOTION_ROW[side]

    def search(
        current: int,
        path: tuple[int, ...],
        captures: tuple[int, ...],
        captured_so_far: frozenset[int],
    ) -> list[Move]:
        sequences: list[Move] = []
        for row_delta, col_delta in directions:
            middle = _step(current, row_delta, col_delta)
            landing = _step(current, 2 * row_delta, 2 * col_delta)
            if middle is None or landing is None:
                continue
            if middle in captured_so_far:
                continue
            middle_piece = board.cells[middle]
            if not _is_opponent(middle_piece, side):
                continue
            if landing in captured_so_far:
                continue
            landing_piece = board.cells[landing]
            if landing_piece is not Piece.EMPTY and landing != path[0]:
                continue

            next_path = path + (landing,)
            next_captures = captures + (middle,)
            next_captured = captured_so_far | {middle}
            promoted = (
                not _is_king(piece)
                and landing // BOARD_SIZE == promotion_row
            )
            if promoted:
                sequences.append(Move(next_path, next_captures))
                continue

            continuations = search(landing, next_path, next_captures, next_captured)
            if continuations:
                sequences.extend(continuations)
            else:
                sequences.append(Move(next_path, next_captures))
        return sequences

    return search(start, (start,), (), captured)


def _belongs_to(piece: Piece | None, side: Side) -> bool:
    if piece is None or piece is Piece.EMPTY:
        return False
    return _side_of(piece) is side


def _side_of(piece: Piece) -> Side:
    if piece in (Piece.BLACK_MAN, Piece.BLACK_KING):
        return Side.BLACK
    return Side.WHITE


def _is_king(piece: Piece) -> bool:
    return piece in (Piece.BLACK_KING, Piece.WHITE_KING)


def _is_opponent(piece: Piece | None, side: Side) -> bool:
    if piece is None or piece is Piece.EMPTY:
        return False
    return _side_of(piece) is not side


def _step(square: int, row_delta: int, col_delta: int) -> int | None:
    row, col = divmod(square, BOARD_SIZE)
    new_row = row + row_delta
    new_col = col + col_delta
    if not (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE):
        return None
    return new_row * BOARD_SIZE + new_col
