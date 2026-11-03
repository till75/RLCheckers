"""Depth-1 greedy baseline for the evaluation arena.

The baseline scores each legal move by material balance from the moving side's
perspective. An immediate win or draw overrides material with
``TERMINAL_SCORE``. Ties are broken by the smallest ``(path, captures)`` tuple,
so the agent is deterministic and owns no RNG.
"""

from __future__ import annotations

from rlcheckers.game.board import Board, Piece, Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState, Outcome

MAN_VALUE = 1
KING_VALUE = 3
TERMINAL_SCORE = 1000


def material_balance(board: Board, side: Side) -> int:
    """Return the material balance from ``side``'s perspective."""
    black = 0
    white = 0
    for cell in board.cells:
        if cell is Piece.BLACK_MAN:
            black += MAN_VALUE
        elif cell is Piece.BLACK_KING:
            black += KING_VALUE
        elif cell is Piece.WHITE_MAN:
            white += MAN_VALUE
        elif cell is Piece.WHITE_KING:
            white += KING_VALUE

    if side is Side.BLACK:
        return black - white
    return white - black


class GreedyAgent:
    """A deterministic depth-1 material baseline."""

    def choose_move(self, state: GameState) -> Move:
        """Return the highest-scoring legal move for ``state``."""
        if state.is_terminal:
            raise ValueError(f"game is finished: {state.outcome.value}")

        moves = state.legal_moves()
        best_move = moves[0]
        best_score = self._score(state, best_move)
        for move in moves[1:]:
            score = self._score(state, move)
            if score > best_score or (
                score == best_score
                and (move.path, move.captures)
                < (best_move.path, best_move.captures)
            ):
                best_move = move
                best_score = score
        return best_move

    @staticmethod
    def _score(state: GameState, move: Move) -> int:
        """Score one candidate move for the side to move."""
        moving_side = state.board.side_to_move
        next_state = state.apply(move)
        if not next_state.is_terminal:
            return material_balance(next_state.board, moving_side)

        outcome = next_state.outcome
        if outcome is Outcome.DRAW:
            return 0
        winner = Side.BLACK if outcome is Outcome.BLACK_WIN else Side.WHITE
        return TERMINAL_SCORE if winner is moving_side else -TERMINAL_SCORE
