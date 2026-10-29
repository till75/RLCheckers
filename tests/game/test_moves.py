from __future__ import annotations

import random

import pytest

from rlcheckers.game.board import PLAYABLE_SQUARES, SQUARE_COUNT, Board, Piece, Side
from rlcheckers.game.moves import Move, apply_move, generate_moves


def board_with(pieces: dict[int, Piece], side: Side = Side.BLACK) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def capture_board() -> Board:
    return board_with(
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


def fixture_positions() -> tuple[Board, ...]:
    return (
        Board.initial(),
        board_with({12: Piece.BLACK_KING, 20: Piece.WHITE_MAN}),
        board_with(
            {
                16: Piece.BLACK_MAN,
                2: Piece.WHITE_KING,
                14: Piece.WHITE_MAN,
            }
        ),
        board_with(
            {
                20: Piece.BLACK_KING,
                16: Piece.WHITE_MAN,
                8: Piece.WHITE_MAN,
                10: Piece.WHITE_MAN,
            }
        ),
        board_with(
            {
                20: Piece.BLACK_KING,
                16: Piece.WHITE_MAN,
                8: Piece.WHITE_MAN,
                18: Piece.WHITE_MAN,
                14: Piece.WHITE_MAN,
            }
        ),
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
    )


def test_initial_black_quiet_moves() -> None:
    assert generate_moves(Board.initial()) == (
        Move((6, 10)),
        Move((6, 12)),
        Move((8, 12)),
        Move((8, 14)),
    )


def test_initial_white_quiet_moves() -> None:
    white = Board(Board.initial().cells, Side.WHITE)
    assert generate_moves(white) == (
        Move((16, 10)),
        Move((16, 12)),
        Move((18, 12)),
        Move((18, 14)),
    )


def test_man_moves_forward_only() -> None:
    board = board_with({12: Piece.BLACK_MAN, 6: Piece.WHITE_MAN})
    assert generate_moves(board) == (Move((12, 16)), Move((12, 18)))


def test_king_moves_in_all_directions() -> None:
    board = board_with({12: Piece.BLACK_KING, 20: Piece.WHITE_MAN})
    assert generate_moves(board) == (
        Move((12, 6)),
        Move((12, 8)),
        Move((12, 16)),
        Move((12, 18)),
    )


def test_corner_king_has_one_move() -> None:
    board = board_with({0: Piece.BLACK_KING})
    assert generate_moves(board) == (Move((0, 6)),)


def test_side_without_pieces_has_no_moves() -> None:
    assert generate_moves(board_with({})) == ()


def test_blocked_side_has_no_moves() -> None:
    board = board_with(
        {
            0: Piece.BLACK_MAN,
            6: Piece.WHITE_MAN,
            12: Piece.WHITE_MAN,
        }
    )
    assert generate_moves(board) == ()


def test_capture_is_mandatory() -> None:
    assert generate_moves(capture_board()) == (Move((18, 6), (12,)),)


def test_man_capture_is_forward_only() -> None:
    board = board_with({12: Piece.BLACK_MAN, 6: Piece.WHITE_MAN})
    assert all(not move.is_capture for move in generate_moves(board))


def test_king_captures_backward() -> None:
    board = board_with({12: Piece.BLACK_KING, 6: Piece.WHITE_MAN})
    assert generate_moves(board) == (Move((12, 0), (6,)),)


def test_capture_needs_empty_landing() -> None:
    board = board_with(
        {
            12: Piece.BLACK_MAN,
            16: Piece.WHITE_MAN,
            20: Piece.BLACK_KING,
        }
    )
    assert generate_moves(board) == (Move((12, 18)),)


def test_capture_off_board_is_not_generated() -> None:
    board = board_with({16: Piece.BLACK_MAN, 20: Piece.WHITE_MAN})
    assert generate_moves(board) == (Move((16, 22)),)


def test_multiple_capture_branches_are_all_returned() -> None:
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


def test_no_maximum_capture_requirement() -> None:
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


def test_promotion_ends_multi_capture() -> None:
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


def test_quiet_move_promotes() -> None:
    board = board_with({16: Piece.BLACK_MAN, 2: Piece.WHITE_KING})
    assert generate_moves(board) == (Move((16, 20)), Move((16, 22)))
    assert apply_move(board, Move((16, 20))).piece_at(4, 0) is Piece.BLACK_KING
    assert apply_move(board, Move((16, 22))).piece_at(4, 2) is Piece.BLACK_KING


def test_move_is_immutable_value_object() -> None:
    move = Move((6, 10))
    assert move == Move((6, 10))
    assert hash(move) == hash(Move((6, 10)))
    assert move.captures == ()
    assert move.is_capture is False

    with pytest.raises(AttributeError):
        move.path = (6, 12)


def test_move_rejects_bad_path() -> None:
    with pytest.raises(ValueError, match="path"):
        Move((6,))
    with pytest.raises(ValueError, match=r"path.*1"):
        Move((6, 1))
    with pytest.raises(ValueError, match=r"path.*25"):
        Move((6, 25))


def test_move_rejects_bad_captures() -> None:
    with pytest.raises(ValueError, match="captures"):
        Move((6, 10, 14))
    with pytest.raises(ValueError, match="captures"):
        Move((12, 0), (12,))
    with pytest.raises(ValueError, match="captures"):
        Move((12, 0, 12), (6, 6))
    with pytest.raises(ValueError, match="captures"):
        Move((12, 0, 12), (6,))
    with pytest.raises(ValueError, match="captures"):
        Move((18, 6), (14,))


def test_move_rejects_non_integer_squares() -> None:
    with pytest.raises(TypeError, match="path"):
        Move(("6", 10))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="captures"):
        Move((12, 0), ("6",))  # type: ignore[arg-type]


def test_action_key_layout() -> None:
    assert Move((6, 10)).action_key == 2610
    assert Move((10, 22, 14), (16, 18)).action_key == 120403


def test_action_key_fits_33_bits() -> None:
    move = Move((14, 2, 10, 22, 14), (8, 6, 16, 18))
    assert move.action_key < (1 << 33)


def test_action_key_distinguishes_capture_orders() -> None:
    assert (
        Move((14, 2, 10, 22, 14), (8, 6, 16, 18)).action_key
        != Move((14, 22, 10, 2, 14), (18, 16, 6, 8)).action_key
    )


def test_apply_quiet_move() -> None:
    board = Board.initial()
    after = apply_move(board, Move((6, 10)))
    assert after.piece_at(1, 1) is Piece.EMPTY
    assert after.piece_at(2, 0) is Piece.BLACK_MAN
    assert after.side_to_move is Side.WHITE
    assert board.piece_at(1, 1) is Piece.BLACK_MAN
    assert board.side_to_move is Side.BLACK


def test_apply_capture() -> None:
    board = capture_board()
    after = apply_move(board, Move((18, 6), (12,)))
    assert after.piece_at(3, 3) is Piece.EMPTY
    assert after.piece_at(2, 2) is Piece.EMPTY
    assert after.piece_at(1, 1) is Piece.WHITE_MAN
    assert after.side_to_move is Side.BLACK


def test_apply_preserves_piece_count() -> None:
    for board in fixture_positions():
        before = sum(cell not in (None, Piece.EMPTY) for cell in board.cells)
        for move in generate_moves(board):
            result = apply_move(board, move)
            after = sum(cell not in (None, Piece.EMPTY) for cell in result.cells)
            assert after == before - len(move.captures)
            assert result.side_to_move is not board.side_to_move


def test_apply_does_not_mutate_original() -> None:
    board = capture_board()
    original = board
    apply_move(board, Move((18, 6), (12,)))
    assert board == original
    assert board.cells is original.cells


def test_apply_rejects_blocked_move() -> None:
    with pytest.raises(ValueError, match="not legal"):
        apply_move(Board.initial(), Move((0, 6)))


def test_apply_rejects_wrong_side() -> None:
    white = Board(Board.initial().cells, Side.WHITE)
    with pytest.raises(ValueError, match="not legal"):
        apply_move(white, Move((6, 10)))


def test_apply_rejects_quiet_when_capture_exists() -> None:
    with pytest.raises(ValueError, match="not legal"):
        apply_move(capture_board(), Move((16, 10)))


def test_apply_rejects_illegal_capture() -> None:
    board = board_with({12: Piece.BLACK_MAN, 6: Piece.WHITE_MAN})
    with pytest.raises(ValueError, match="not legal"):
        apply_move(board, Move((12, 0), (6,)))


def test_apply_rejects_capture_that_stops_early() -> None:
    board = board_with(
        {
            20: Piece.BLACK_KING,
            16: Piece.WHITE_MAN,
            8: Piece.WHITE_MAN,
            18: Piece.WHITE_MAN,
            14: Piece.WHITE_MAN,
        }
    )
    with pytest.raises(ValueError, match="not legal"):
        apply_move(board, Move((20, 12), (16,)))


def test_apply_rejects_capture_that_continues_after_promotion() -> None:
    board = board_with(
        {
            2: Piece.BLACK_MAN,
            8: Piece.WHITE_MAN,
            18: Piece.WHITE_MAN,
            16: Piece.WHITE_MAN,
        }
    )
    with pytest.raises(ValueError, match="not legal"):
        apply_move(board, Move((2, 14, 22, 10), (8, 18, 16)))


def test_generate_moves_is_deterministic() -> None:
    assert generate_moves(Board.initial()) == generate_moves(Board.initial())


def test_generated_moves_are_unique() -> None:
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


def test_seeded_playout_preserves_invariants() -> None:
    randomizer = random.Random(20261029)
    board = Board.initial()
    for _ in range(60):
        moves = generate_moves(board)
        if not moves:
            break
        move = randomizer.choice(moves)
        before = sum(cell not in (None, Piece.EMPTY) for cell in board.cells)
        after = apply_move(board, move)
        after_count = sum(cell not in (None, Piece.EMPTY) for cell in after.cells)
        assert after_count == before - len(move.captures)
        assert after_count <= before
        assert after.side_to_move is not board.side_to_move
        for square in PLAYABLE_SQUARES:
            piece = after.cells[square]
            row, _ = divmod(square, 5)
            if piece is Piece.BLACK_MAN:
                assert row != 4
            if piece is Piece.WHITE_MAN:
                assert row != 0
        board = after
