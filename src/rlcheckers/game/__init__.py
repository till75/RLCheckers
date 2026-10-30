"""Game rules and board state."""

from rlcheckers.game.board import PLAYABLE_SQUARES, Board, Piece, Side
from rlcheckers.game.moves import Move, apply_move, format_move, generate_moves
from rlcheckers.game.state import (
    NO_PROGRESS_PLY_LIMIT,
    REPETITION_LIMIT,
    DrawReason,
    GameRecord,
    GameState,
    Outcome,
)

__all__ = [
    "NO_PROGRESS_PLY_LIMIT",
    "PLAYABLE_SQUARES",
    "REPETITION_LIMIT",
    "Board",
    "DrawReason",
    "GameRecord",
    "GameState",
    "Move",
    "Outcome",
    "Piece",
    "Side",
    "apply_move",
    "format_move",
    "generate_moves",
]
