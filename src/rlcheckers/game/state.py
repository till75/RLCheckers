"""Game state, counters, and terminal detection for the 5x5 board."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rlcheckers.game.board import Board, Piece, Side
from rlcheckers.game.moves import Move, apply_move, generate_moves

NO_PROGRESS_PLY_LIMIT = 80
REPETITION_LIMIT = 3


class Outcome(Enum):
    """The result of a game."""

    ONGOING = "ongoing"
    BLACK_WIN = "black_win"
    WHITE_WIN = "white_win"
    DRAW = "draw"


class DrawReason(Enum):
    """Why a drawn game ended."""

    THREEFOLD_REPETITION = "threefold_repetition"
    NO_PROGRESS = "no_progress"


@dataclass(frozen=True)
class GameState:
    """An immutable board plus repetition and no-progress history."""

    board: Board
    position_keys: tuple[int, ...] = ()
    no_progress_plies: int = 0

    def __post_init__(self) -> None:
        keys = tuple(self.position_keys)
        if not keys:
            keys = (self.board.state_key,)
        object.__setattr__(self, "position_keys", keys)

    @classmethod
    def from_board(cls, board: Board, *, no_progress_plies: int = 0) -> GameState:
        """Create a fresh state with the current position as its first key."""
        return cls(board, (), no_progress_plies)

    @property
    def outcome(self) -> Outcome:
        """Return the outcome, checking wins before draw rules."""
        black_has_pieces = any(
            cell in (Piece.BLACK_MAN, Piece.BLACK_KING) for cell in self.board.cells
        )
        white_has_pieces = any(
            cell in (Piece.WHITE_MAN, Piece.WHITE_KING) for cell in self.board.cells
        )
        if not black_has_pieces:
            return Outcome.WHITE_WIN
        if not white_has_pieces:
            return Outcome.BLACK_WIN
        if not generate_moves(self.board):
            if self.board.side_to_move is Side.BLACK:
                return Outcome.WHITE_WIN
            return Outcome.BLACK_WIN
        return Outcome.ONGOING

    @property
    def draw_reason(self) -> DrawReason | None:
        """Return why the game was drawn, if it was."""
        return None

    @property
    def is_terminal(self) -> bool:
        """Return whether the game has ended."""
        return self.outcome is not Outcome.ONGOING

    def legal_moves(self) -> tuple[Move, ...]:
        """Return every legal move for the side to move."""
        if self.is_terminal:
            return ()
        return generate_moves(self.board)

    def apply(self, move: Move) -> GameState:
        """Return the state after applying a legal move."""
        if self.is_terminal:
            raise ValueError(f"game is finished: {self.outcome.value}")
        next_board = apply_move(self.board, move)
        moving_piece = self.board.cells[move.path[0]]
        landing_piece = next_board.cells[move.path[-1]]
        promoted = (moving_piece, landing_piece) in (
            (Piece.BLACK_MAN, Piece.BLACK_KING),
            (Piece.WHITE_MAN, Piece.WHITE_KING),
        )
        next_no_progress = (
            0 if move.is_capture or promoted else self.no_progress_plies + 1
        )
        return GameState(
            next_board,
            self.position_keys + (next_board.state_key,),
            next_no_progress,
        )


@dataclass(frozen=True)
class GameRecord:
    """The moves and final state of one game."""

    moves: tuple[Move, ...]
    final_state: GameState

    @property
    def outcome(self) -> Outcome:
        """Return the final outcome."""
        raise NotImplementedError

    @property
    def plies(self) -> int:
        """Return the number of plies played."""
        raise NotImplementedError
