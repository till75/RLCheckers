from __future__ import annotations

import pytest

from rlcheckers.agents.greedy_agent import (
    GreedyAgent,
    StochasticGreedyAgent,
    material_balance,
)
from rlcheckers.game.board import (
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState, Outcome


def board_with(
    pieces: dict[int, Piece], side: Side = Side.BLACK
) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def test_material_balance_counts_men_and_kings() -> None:
    board = board_with(
        {0: Piece.BLACK_KING, 6: Piece.BLACK_MAN, 20: Piece.WHITE_MAN}
    )
    assert material_balance(board, Side.BLACK) == 3
    assert material_balance(board, Side.WHITE) == -3


def test_material_balance_from_both_sides() -> None:
    board = board_with({0: Piece.BLACK_MAN, 20: Piece.WHITE_KING})
    assert material_balance(board, Side.BLACK) == -2
    assert material_balance(board, Side.WHITE) == 2


def test_greedy_prefers_higher_value_capture() -> None:
    game = GameState.from_board(
        board_with(
            {
                12: Piece.BLACK_KING,
                6: Piece.WHITE_KING,
                18: Piece.WHITE_MAN,
            }
        )
    )
    assert GreedyAgent().choose_move(game) == Move((12, 0), (6,))


def test_greedy_tie_breaks_by_path() -> None:
    game = GameState.from_board(
        board_with(
            {
                12: Piece.BLACK_KING,
                6: Piece.WHITE_MAN,
                18: Piece.WHITE_MAN,
            }
        )
    )
    assert GreedyAgent().choose_move(game) == Move((12, 0), (6,))


def test_greedy_prefers_promotion() -> None:
    game = GameState.from_board(
        board_with({16: Piece.BLACK_MAN, 2: Piece.WHITE_KING})
    )
    assert GreedyAgent().choose_move(game) == Move((16, 20))


def test_greedy_uses_quiet_tie_break() -> None:
    game = GameState.from_board(
        board_with({12: Piece.BLACK_KING, 0: Piece.WHITE_KING})
    )
    assert GreedyAgent().choose_move(game) == Move((12, 6))


def test_greedy_takes_terminal_win() -> None:
    game = GameState.from_board(
        board_with({20: Piece.BLACK_KING, 16: Piece.WHITE_MAN})
    )
    move = GreedyAgent().choose_move(game)
    assert move == Move((20, 12), (16,))
    assert game.apply(move).outcome is Outcome.BLACK_WIN


def test_greedy_rejects_finished_game() -> None:
    finished = GameState.from_board(board_with({20: Piece.BLACK_KING}))
    with pytest.raises(ValueError, match="finished"):
        GreedyAgent().choose_move(finished)


def test_greedy_returns_legal_move() -> None:
    game = GameState.from_board(Board.initial())
    agent = GreedyAgent()
    first = agent.choose_move(game)
    assert first in game.legal_moves()


def test_greedy_is_deterministic() -> None:
    game = GameState.from_board(Board.initial())
    agent = GreedyAgent()
    first = agent.choose_move(game)
    assert agent.choose_move(game) == first


def test_stochastic_greedy_is_seeded() -> None:
    game = GameState.from_board(
        board_with({12: Piece.BLACK_KING, 0: Piece.WHITE_KING})
    )
    first = StochasticGreedyAgent(seed=7)
    second = StochasticGreedyAgent(seed=7)
    third = StochasticGreedyAgent(seed=8)

    first_moves = [first.choose_move(game) for _ in range(20)]
    second_moves = [second.choose_move(game) for _ in range(20)]
    third_moves = [third.choose_move(game) for _ in range(20)]

    assert first_moves == second_moves
    assert len(set(first_moves)) > 1
    assert third_moves != first_moves


def test_stochastic_greedy_uses_best_moves() -> None:
    game = GameState.from_board(
        board_with(
            {
                12: Piece.BLACK_KING,
                6: Piece.WHITE_KING,
                18: Piece.WHITE_MAN,
            }
        )
    )
    expected = Move((12, 0), (6,))

    assert all(
        StochasticGreedyAgent(seed=seed).choose_move(game) == expected
        for seed in range(10)
    )


@pytest.mark.parametrize("seed", [True, "7", 7.0, None])
def test_stochastic_greedy_rejects_bad_seed(seed: object) -> None:
    with pytest.raises(ValueError, match="seed"):
        StochasticGreedyAgent(seed=seed)


def test_stochastic_greedy_rejects_terminal_state() -> None:
    finished = GameState.from_board(board_with({20: Piece.BLACK_KING}))

    with pytest.raises(ValueError, match="finished"):
        StochasticGreedyAgent(seed=7).choose_move(finished)


def test_stochastic_greedy_is_exported() -> None:
    from rlcheckers.agents import StochasticGreedyAgent as Exported

    assert Exported is StochasticGreedyAgent
