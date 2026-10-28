from __future__ import annotations

import pytest

from rlcheckers.game.board import (
    BOARD_SIZE,
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)


def test_initial_board_layout_and_counts() -> None:
    board = Board.initial()
    assert board.side_to_move is Side.BLACK
    assert len(board.cells) == SQUARE_COUNT
    assert sum(cell is Piece.BLACK_MAN for cell in board.cells) == 5
    assert sum(cell is Piece.WHITE_MAN for cell in board.cells) == 5
    assert sum(cell is Piece.EMPTY for cell in board.cells) == 3
    assert sum(cell is None for cell in board.cells) == 12

    for row, col in ((0, 0), (0, 2), (0, 4), (1, 1), (1, 3)):
        assert board.piece_at(row, col) is Piece.BLACK_MAN
    for row, col in ((4, 0), (4, 2), (4, 4), (3, 1), (3, 3)):
        assert board.piece_at(row, col) is Piece.WHITE_MAN


def test_initial_board_black_to_move() -> None:
    assert Board.initial().side_to_move is Side.BLACK


def test_playable_square_map() -> None:
    assert BOARD_SIZE == 5
    assert SQUARE_COUNT == 25
    assert PLAYABLE_SQUARES == (
        0,
        2,
        4,
        6,
        8,
        10,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
    )
    board = Board.initial()
    assert all(
        (board.cells[index] is None) == (index not in PLAYABLE_SQUARES)
        for index in range(SQUARE_COUNT)
    )


def test_piece_at_distinguishes_empty_dark_from_light_square() -> None:
    board = Board.initial()
    assert board.piece_at(0, 1) is None
    assert board.piece_at(2, 1) is None
    assert board.piece_at(2, 0) is Piece.EMPTY
    assert board.piece_at(2, 2) is Piece.EMPTY


def test_board_is_immutable_value_object() -> None:
    board = Board.initial()
    assert board == Board.initial()
    assert isinstance(board.cells, tuple)
    with pytest.raises(AttributeError):
        board.side_to_move = Side.WHITE


def test_initial_state_key_is_stable() -> None:
    assert Board.initial().state_key == Board.initial().state_key


def test_initial_state_key_matches_documented_value() -> None:
    assert Board.initial().state_key == 0x36DB001249


def test_state_key_is_within_40_bits() -> None:
    key = Board.initial().state_key
    assert 0 <= key < (1 << 40)


def test_state_key_changes_with_side_to_move() -> None:
    board = Board.initial()
    white_to_move = Board(board.cells, Side.WHITE)
    assert white_to_move.state_key == 0xB6DB001249
    assert white_to_move.state_key != board.state_key


def test_state_key_changes_with_piece() -> None:
    board = Board.initial()
    black_king = list(board.cells)
    black_king[0] = Piece.BLACK_KING
    assert Board(tuple(black_king), Side.BLACK).state_key == board.state_key + 1

    white_king = list(board.cells)
    white_king[16] = Piece.WHITE_KING
    assert Board(tuple(white_king), Side.BLACK).state_key == (
        board.state_key + (1 << 24)
    )


def test_state_key_bit_layout_examples() -> None:
    empty_cells = tuple(
        Piece.EMPTY if index in PLAYABLE_SQUARES else None
        for index in range(SQUARE_COUNT)
    )
    assert Board(empty_cells, Side.BLACK).state_key == 0
    assert Board(empty_cells, Side.WHITE).state_key == 0x8000000000

    black_king_cells = list(empty_cells)
    black_king_cells[0] = Piece.BLACK_KING
    assert Board(tuple(black_king_cells), Side.BLACK).state_key == 0x2

    white_king_cells = list(empty_cells)
    white_king_cells[24] = Piece.WHITE_KING
    assert Board(tuple(white_king_cells), Side.BLACK).state_key == 0x4000000000


def test_from_state_key_round_trips_initial_board() -> None:
    board = Board.initial()
    assert Board.from_state_key(board.state_key) == board


def test_from_state_key_round_trips_custom_board() -> None:
    cells = list(Board.initial().cells)
    cells[0] = Piece.BLACK_KING
    cells[24] = Piece.WHITE_KING
    board = Board(tuple(cells), Side.WHITE)
    assert Board.from_state_key(board.state_key) == board


def test_from_state_key_decodes_boundary_keys() -> None:
    empty = Board.from_state_key(0)
    assert empty.cells[0] is Piece.EMPTY
    assert empty.side_to_move is Side.BLACK
    assert Board.from_state_key(0x8000000000).side_to_move is Side.WHITE
    assert Board.from_state_key(0x2).piece_at(0, 0) is Piece.BLACK_KING
    assert Board.from_state_key(0x4000000000).piece_at(4, 4) is Piece.WHITE_KING


def test_from_state_key_rejects_invalid_keys() -> None:
    with pytest.raises(ValueError, match="state key"):
        Board.from_state_key(-1)
    with pytest.raises(ValueError, match="state key"):
        Board.from_state_key(1 << 40)
    with pytest.raises(ValueError, match="piece code"):
        Board.from_state_key(5)
    with pytest.raises(TypeError, match="state key"):
        Board.from_state_key("0x36DB001249")


def test_initial_render_snapshot() -> None:
    assert Board.initial().render() == (
        "    0 1 2 3 4\n"
        "0   b # b # b\n"
        "1   # b # b #\n"
        "2   . # . # .\n"
        "3   # w # w #\n"
        "4   w # w # w\n"
        "Black to move"
    )


def test_empty_board_render() -> None:
    assert Board.from_state_key(0).render() == (
        "    0 1 2 3 4\n"
        "0   . # . # .\n"
        "1   # . # . #\n"
        "2   . # . # .\n"
        "3   # . # . #\n"
        "4   . # . # .\n"
        "Black to move"
    )


def test_render_uses_kings_and_side_line() -> None:
    cells = list(Board.initial().cells)
    cells[0] = Piece.BLACK_KING
    cells[16] = Piece.WHITE_KING
    board = Board(tuple(cells), Side.WHITE)
    rendered = board.render()
    assert "0   B # b # b" in rendered
    assert "3   # W # w #" in rendered
    assert rendered.endswith("White to move")


def test_render_has_no_trailing_newline() -> None:
    assert not Board.initial().render().endswith("\n")


@pytest.mark.parametrize("length", [24, 26])
def test_board_rejects_wrong_cell_count(length: int) -> None:
    cells = tuple(None for _ in range(length))
    with pytest.raises(ValueError, match="25"):
        Board(cells, Side.BLACK)


def test_board_rejects_invalid_cells() -> None:
    non_playable = list(Board.initial().cells)
    non_playable[1] = Piece.EMPTY
    with pytest.raises(ValueError, match=r"cells\[1\]"):
        Board(tuple(non_playable), Side.BLACK)

    playable_none = list(Board.initial().cells)
    playable_none[0] = None
    with pytest.raises(ValueError, match=r"cells\[0\]"):
        Board(tuple(playable_none), Side.BLACK)

    invalid_piece = list(Board.initial().cells)
    invalid_piece[0] = 5
    with pytest.raises(ValueError, match=r"cells\[0\].*0\.\.4"):
        Board(tuple(invalid_piece), Side.BLACK)


def test_board_rejects_invalid_side() -> None:
    with pytest.raises(ValueError, match="side_to_move"):
        Board(Board.initial().cells, 2)


@pytest.mark.parametrize("row,col", [(-1, 0), (5, 0), (0, -1), (0, 5)])
def test_piece_at_rejects_out_of_range_coordinates(row: int, col: int) -> None:
    with pytest.raises(ValueError, match="row|col"):
        Board.initial().piece_at(row, col)


def test_piece_at_rejects_non_integer_coordinates() -> None:
    with pytest.raises(TypeError, match="row"):
        Board.initial().piece_at("0", 0)  # type: ignore[arg-type]


def test_board_normalizes_int_inputs() -> None:
    cells = tuple(
        0 if index in PLAYABLE_SQUARES else None for index in range(SQUARE_COUNT)
    )
    board = Board(cells, 1)
    assert board.side_to_move is Side.WHITE
    assert all(board.cells[index] is Piece.EMPTY for index in PLAYABLE_SQUARES)
    assert all(
        board.cells[index] is None
        for index in range(SQUARE_COUNT)
        if index not in PLAYABLE_SQUARES
    )
