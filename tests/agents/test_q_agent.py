from __future__ import annotations

import pytest

from rlcheckers.agents.q_agent import QAgent, QTable, TableCapacityError, q_key
from rlcheckers.game.board import (
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


def _initial_state() -> GameState:
    return GameState.from_board(Board.initial())


def _board_with(
    pieces: dict[int, Piece], side: Side = Side.BLACK
) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def test_q_key_combines_state_and_action() -> None:
    state = _initial_state()
    move = Move((6, 10))

    assert q_key(state, move) == (state.board.state_key << 33) | move.action_key


def test_q_table_defaults_to_zero() -> None:
    state = _initial_state()
    key = q_key(state, Move((6, 10)))

    assert QTable().get(key) == 0.0


def test_q_table_set_and_get() -> None:
    state = _initial_state()
    key = q_key(state, Move((6, 10)))
    table = QTable()

    table.set(key, 0.5)
    table.set(key, 0.6)

    assert table.get(key) == 0.6
    assert table.size() == 1


def test_q_table_capacity_guard() -> None:
    state = _initial_state()
    key_one = q_key(state, Move((6, 10)))
    key_two = q_key(state, Move((8, 14)))
    key_three = q_key(state, Move((6, 12)))
    table = QTable(max_entries=2)

    table.set(key_one, 0.5)
    table.set(key_one, 0.6)
    table.set(key_two, -0.2)

    assert table.size() == 2
    with pytest.raises(TableCapacityError, match="cap"):
        table.set(key_three, 0.0)


def test_q_table_rejects_bad_cap() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        QTable(max_entries=0)

    with pytest.raises(ValueError, match="max_entries"):
        QTable(max_entries=True)


def test_q_table_rejects_non_finite() -> None:
    table = QTable()

    with pytest.raises(ValueError, match="finite"):
        table.set(1, float("nan"))

    with pytest.raises(ValueError, match="finite"):
        table.set(2, float("inf"))


def test_q_table_memory_estimate() -> None:
    assert QTable().estimated_memory_bytes() > 0


def test_q_agent_picks_highest_value() -> None:
    state = _initial_state()
    table = QTable()
    best = Move((6, 10))
    table.set(q_key(state, best), 1.0)
    agent = QAgent(table)

    assert agent.table is table
    assert agent.choose_move(state) == best


def test_q_agent_tie_breaks_by_path() -> None:
    state = _initial_state()

    assert QAgent(QTable()).choose_move(state) == Move((6, 10))


def test_q_agent_returns_legal_move() -> None:
    state = _initial_state()

    assert QAgent(QTable()).choose_move(state) in state.legal_moves()


def test_q_agent_is_deterministic() -> None:
    state = _initial_state()
    agent = QAgent(QTable())

    assert agent.choose_move(state) == agent.choose_move(state)


def test_q_agent_rejects_finished_game() -> None:
    finished = GameState.from_board(
        _board_with({20: Piece.BLACK_KING})
    )

    with pytest.raises(ValueError, match="finished"):
        QAgent(QTable()).choose_move(finished)
