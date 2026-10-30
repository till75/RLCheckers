from __future__ import annotations

import pytest

from rlcheckers.agents.random_agent import (
    MAX_GAME_PLIES,
    RandomAgent,
    play_random_game,
)
from rlcheckers.game.board import (
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)
from rlcheckers.game.state import GameState


def board_with(pieces: dict[int, Piece], side: Side = Side.BLACK) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def test_random_agent_chooses_legal_move() -> None:
    game = GameState.from_board(Board.initial())
    agent = RandomAgent(seed=123)

    assert agent.choose_move(game) in game.legal_moves()


def test_random_agent_same_seed_same_choice() -> None:
    game = GameState.from_board(Board.initial())

    assert RandomAgent(seed=123).choose_move(game) == RandomAgent(
        seed=123
    ).choose_move(game)


def test_random_agent_rejects_finished_game() -> None:
    finished = GameState.from_board(board_with({20: Piece.BLACK_KING}))

    with pytest.raises(ValueError, match="finished"):
        RandomAgent(seed=1).choose_move(finished)


def test_random_agent_rejects_bad_seed() -> None:
    with pytest.raises(TypeError, match="seed"):
        RandomAgent(seed="1")  # type: ignore[arg-type]


def test_play_random_game_is_reproducible() -> None:
    first = play_random_game(7)
    second = play_random_game(7)

    assert first == second
    assert first.plies == len(first.moves)
    assert first.plies > 0
    assert first.final_state.is_terminal
    assert first.outcome is first.final_state.outcome


def test_play_random_game_terminates_for_seeds() -> None:
    for seed in range(5):
        record = play_random_game(seed)

        assert record.final_state.is_terminal
        assert 0 < record.plies <= MAX_GAME_PLIES
