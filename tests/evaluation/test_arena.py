from __future__ import annotations

from rlcheckers.evaluation.arena import STANDARD_OPENINGS, opening_state
from rlcheckers.game.board import Board, Side
from rlcheckers.game.moves import Move


def test_standard_openings_are_legal() -> None:
    for moves in STANDARD_OPENINGS:
        opening_state(moves)


def test_standard_openings_are_distinct() -> None:
    keys = {
        opening_state(moves).board.state_key for moves in STANDARD_OPENINGS
    }
    assert len(keys) == 5


def test_standard_opening_state_keys() -> None:
    expected = (
        (Side.BLACK, 235602448969, 0),
        (Side.WHITE, 785358295113, 1),
        (Side.WHITE, 785360355913, 1),
        (Side.BLACK, 235206119497, 2),
        (Side.BLACK, 235554996809, 2),
    )

    for index, moves in enumerate(STANDARD_OPENINGS):
        state = opening_state(moves)
        side, key, no_progress = expected[index]
        assert state.board.side_to_move is side
        assert state.board.state_key == key
        assert state.no_progress_plies == no_progress
        assert state.position_keys[-1] == key


def test_standard_openings_are_not_terminal() -> None:
    for moves in STANDARD_OPENINGS:
        assert opening_state(moves).is_terminal is False


def test_opening_state_preserves_prefix_history() -> None:
    assert opening_state(STANDARD_OPENINGS[3]).position_keys == (
        Board.initial().state_key,
        opening_state((Move((6, 10)),)).board.state_key,
        235206119497,
    )
