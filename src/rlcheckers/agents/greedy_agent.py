"""Depth-1 greedy baseline for the evaluation arena.

The baseline scores each legal move by material balance from the moving side's
perspective. An immediate win or draw overrides material with
``TERMINAL_SCORE``. Ties are broken by the smallest ``(path, captures)`` tuple,
so the agent is deterministic and owns no RNG.
"""

from __future__ import annotations

from rlcheckers.game.board import Board, Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState

MAN_VALUE = 1
KING_VALUE = 3
TERMINAL_SCORE = 1000


def material_balance(board: Board, side: Side) -> int:
    """Return the material balance from ``side``'s perspective."""
    raise NotImplementedError


class GreedyAgent:
    """A deterministic depth-1 material baseline."""

    def choose_move(self, state: GameState) -> Move:
        """Return the highest-scoring legal move for ``state``."""
        raise NotImplementedError
