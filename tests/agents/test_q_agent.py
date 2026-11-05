from __future__ import annotations

from rlcheckers.agents.q_agent import q_key
from rlcheckers.game.board import Board
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


def test_q_key_combines_state_and_action() -> None:
    state = GameState.from_board(Board.initial())
    move = Move((6, 10))

    assert q_key(state, move) == (state.board.state_key << 33) | move.action_key
