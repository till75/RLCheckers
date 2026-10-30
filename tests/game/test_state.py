from __future__ import annotations

import pytest

from rlcheckers.game.board import (
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)
from rlcheckers.game.moves import Move, apply_move, generate_moves
from rlcheckers.game.state import DrawReason, GameState, Outcome


def board_with(pieces: dict[int, Piece], side: Side = Side.BLACK) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def test_fresh_game_wraps_initial_board() -> None:
    game = GameState.from_board(Board.initial())

    assert game.board == Board.initial()
    assert game.position_keys == (Board.initial().state_key,)
    assert game.no_progress_plies == 0


def test_fresh_game_is_ongoing() -> None:
    game = GameState.from_board(Board.initial())

    assert game.outcome is Outcome.ONGOING
    assert game.draw_reason is None
    assert game.is_terminal is False


def test_fresh_game_legal_moves_match_generator() -> None:
    game = GameState.from_board(Board.initial())

    assert game.legal_moves() == generate_moves(Board.initial())


def test_apply_quiet_move_updates_board_and_turn() -> None:
    game = GameState.from_board(Board.initial())
    after = game.apply(Move((6, 10)))

    assert after.board == apply_move(Board.initial(), Move((6, 10)))
    assert after.board.side_to_move is Side.WHITE
    assert after.outcome is Outcome.ONGOING
    assert after.legal_moves() == generate_moves(after.board)


def test_apply_quiet_move_increments_no_progress() -> None:
    game = GameState.from_board(Board.initial())
    after = game.apply(Move((6, 10)))

    assert after.no_progress_plies == 1


def test_apply_appends_position_key() -> None:
    game = GameState.from_board(Board.initial())
    after = game.apply(Move((6, 10)))

    assert after.position_keys == (
        Board.initial().state_key,
        after.board.state_key,
    )


def test_apply_does_not_mutate_source_state() -> None:
    game = GameState.from_board(Board.initial())
    game.apply(Move((6, 10)))

    assert game.board == Board.initial()
    assert game.position_keys == (Board.initial().state_key,)
    assert game.no_progress_plies == 0


def test_capture_resets_no_progress() -> None:
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


def test_promotion_resets_no_progress() -> None:
    board = board_with({16: Piece.BLACK_MAN, 2: Piece.WHITE_KING})
    game = GameState.from_board(board, no_progress_plies=33)
    after = game.apply(Move((16, 20)))

    assert after.board.piece_at(4, 0) is Piece.BLACK_KING
    assert after.no_progress_plies == 0
    assert after.outcome is Outcome.ONGOING


def test_side_without_pieces_loses() -> None:
    game = GameState.from_board(board_with({20: Piece.BLACK_KING}))

    assert game.outcome is Outcome.BLACK_WIN
    assert game.draw_reason is None
    assert game.is_terminal is True
    assert game.legal_moves() == ()


def test_side_without_legal_moves_loses() -> None:
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


def test_capture_ending_the_game_wins() -> None:
    board = board_with({20: Piece.BLACK_KING, 16: Piece.WHITE_MAN})
    game = GameState.from_board(board)
    after = game.apply(Move((20, 12), (16,)))

    assert after.board.side_to_move is Side.WHITE
    assert after.outcome is Outcome.BLACK_WIN
    assert after.legal_moves() == ()


def test_terminal_state_has_no_legal_moves() -> None:
    game = GameState.from_board(
        board_with(
            {
                0: Piece.BLACK_MAN,
                6: Piece.WHITE_MAN,
                12: Piece.WHITE_MAN,
            }
        )
    )

    assert game.is_terminal is True
    assert game.legal_moves() == ()


def test_apply_after_terminal_state_fails() -> None:
    game = GameState.from_board(board_with({20: Piece.BLACK_KING}))

    with pytest.raises(ValueError, match="finished"):
        game.apply(Move((20, 16)))


def test_apply_rejects_illegal_move() -> None:
    game = GameState.from_board(Board.initial())

    with pytest.raises(ValueError, match="not legal"):
        game.apply(Move((0, 6)))


def test_threefold_repetition_draws() -> None:
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


def test_twofold_repetition_is_not_a_draw() -> None:
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

    assert game.position_keys.count(board.state_key) == 2
    assert game.outcome is Outcome.ONGOING
    assert game.draw_reason is None


def test_no_progress_draws_at_80_plies() -> None:
    board = board_with({0: Piece.BLACK_KING, 20: Piece.WHITE_KING})
    game = GameState.from_board(board, no_progress_plies=79)
    assert game.outcome is Outcome.ONGOING

    after = game.apply(Move((0, 6)))

    assert after.no_progress_plies == 80
    assert after.outcome is Outcome.DRAW
    assert after.draw_reason is DrawReason.NO_PROGRESS
    assert after.legal_moves() == ()


def test_constructed_80_ply_state_is_drawn() -> None:
    game = GameState.from_board(Board.initial(), no_progress_plies=80)

    assert game.outcome is Outcome.DRAW
    assert game.draw_reason is DrawReason.NO_PROGRESS
    assert game.is_terminal is True


def test_draw_reason_for_repetition() -> None:
    board = board_with({0: Piece.BLACK_KING, 20: Piece.WHITE_KING})
    key = board.state_key
    game = GameState(board, (key, key, key))

    assert game.outcome is Outcome.DRAW
    assert game.draw_reason is DrawReason.THREEFOLD_REPETITION


def test_draw_reason_for_no_progress() -> None:
    game = GameState.from_board(Board.initial(), no_progress_plies=80)

    assert game.outcome is Outcome.DRAW
    assert game.draw_reason is DrawReason.NO_PROGRESS


def test_repetition_takes_precedence_over_no_progress() -> None:
    board = board_with({0: Piece.BLACK_KING, 20: Piece.WHITE_KING})
    key = board.state_key
    game = GameState(board, (key, key, key), 80)

    assert game.outcome is Outcome.DRAW
    assert game.draw_reason is DrawReason.THREEFOLD_REPETITION


def test_win_takes_precedence_over_draw_rules() -> None:
    board = board_with({20: Piece.BLACK_KING})
    key = board.state_key

    no_progress = GameState.from_board(board, no_progress_plies=80)
    assert no_progress.outcome is Outcome.BLACK_WIN
    assert no_progress.draw_reason is None

    repeated = GameState(board, (key, key, key), 80)
    assert repeated.outcome is Outcome.BLACK_WIN
    assert repeated.draw_reason is None


def test_non_draw_has_no_draw_reason() -> None:
    game = GameState.from_board(Board.initial())

    assert game.outcome is Outcome.ONGOING
    assert game.draw_reason is None


def test_game_state_rejects_bad_position_history() -> None:
    with pytest.raises(ValueError, match="position_keys"):
        GameState(Board.initial(), (0,))

    with pytest.raises(ValueError, match="position_keys"):
        GameState(Board.initial(), (1 << 40,))

    with pytest.raises(TypeError, match="position_keys"):
        GameState(Board.initial(), ("0",))  # type: ignore[arg-type]


def test_game_state_is_immutable() -> None:
    game = GameState.from_board(Board.initial())

    with pytest.raises(AttributeError):
        game.no_progress_plies = 1

    assert isinstance(game.position_keys, tuple)


def test_game_state_seeds_empty_position_history() -> None:
    game = GameState(Board.initial(), (), 0)

    assert game.position_keys == (Board.initial().state_key,)
    assert game.no_progress_plies == 0


def test_game_state_rejects_bad_no_progress_count() -> None:
    for value in (-1, 81):
        with pytest.raises(ValueError, match="no_progress_plies"):
            GameState.from_board(Board.initial(), no_progress_plies=value)

    with pytest.raises(TypeError, match="no_progress_plies"):
        GameState.from_board(
            Board.initial(), no_progress_plies="0"  # type: ignore[arg-type]
        )


def test_game_state_rejects_empty_board() -> None:
    with pytest.raises(ValueError, match="piece"):
        GameState.from_board(Board.from_state_key(0))


def test_game_state_rejects_bad_board() -> None:
    with pytest.raises(TypeError, match="board"):
        GameState("not a board")  # type: ignore[arg-type]
