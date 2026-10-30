from __future__ import annotations

import pytest

from rlcheckers.agents.random_agent import RandomAgent
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
