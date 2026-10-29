from __future__ import annotations

import pytest

from rlcheckers.game.board import PLAYABLE_SQUARES, SQUARE_COUNT, Board, Piece, Side
from rlcheckers.game.moves import apply_move, generate_moves


def board_with(pieces: dict[int, Piece], side: Side = Side.BLACK) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    moves = generate_moves(board)
    if depth == 1:
        return len(moves)
    return sum(perft(apply_move(board, move), depth - 1) for move in moves)


FIXTURES = {
    "P1": (Board.initial(), {1: 4, 2: 8, 3: 18}),
    "P2": (
        board_with({12: Piece.BLACK_KING, 20: Piece.WHITE_MAN}),
        {1: 4, 2: 4, 3: 12},
    ),
    "P3": (
        board_with(
            {
                16: Piece.BLACK_MAN,
                2: Piece.WHITE_KING,
                14: Piece.WHITE_MAN,
            }
        ),
        {1: 2, 2: 6, 3: 9},
    ),
    "P4": (
        board_with(
            {
                20: Piece.BLACK_KING,
                16: Piece.WHITE_MAN,
                8: Piece.WHITE_MAN,
                10: Piece.WHITE_MAN,
            }
        ),
        {1: 1, 2: 1, 3: 1},
    ),
    "P5": (
        board_with(
            {
                20: Piece.BLACK_KING,
                16: Piece.WHITE_MAN,
                8: Piece.WHITE_MAN,
                18: Piece.WHITE_MAN,
                14: Piece.WHITE_MAN,
            }
        ),
        {1: 2, 2: 4, 3: 4},
    ),
    "P6": (
        board_with(
            {
                14: Piece.BLACK_KING,
                0: Piece.WHITE_KING,
                8: Piece.WHITE_MAN,
                6: Piece.WHITE_MAN,
                16: Piece.WHITE_MAN,
                18: Piece.WHITE_MAN,
            }
        ),
        {1: 2, 2: 2, 3: 4},
    ),
}


@pytest.mark.parametrize("name", FIXTURES)
@pytest.mark.parametrize("depth", [1, 2, 3])
def test_perft_known_positions(name: str, depth: int) -> None:
    board, expected = FIXTURES[name]
    assert perft(board, depth) == expected[depth]


def test_perft_depth_zero_is_one() -> None:
    assert perft(Board.initial(), 0) == 1
