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
    """An immutable board plus repetition and no-progress history.

    ``position_keys`` ends with ``board.state_key`` and ``no_progress_plies``
    stays within ``0..NO_PROGRESS_PLY_LIMIT``. Both are validated on
    construction, as is the requirement that the board has at least one piece.
    """

    board: Board
    position_keys: tuple[int, ...] = ()
    no_progress_plies: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.board, Board):
            raise TypeError(
                f"board must be a Board, got {type(self.board).__name__}"
            )

        try:
            keys = tuple(self.position_keys)
        except TypeError:
            raise TypeError("position_keys must be a sequence of ints") from None

        for index, key in enumerate(keys):
            if not isinstance(key, int):
                raise TypeError(
                    f"position_keys[{index}] must be an int, "
                    f"got {type(key).__name__}"
                )
            if not 0 <= key < (1 << 40):
                raise ValueError(
                    f"position_keys[{index}] must be in 0..2**40-1, got {key}"
                )

        if not keys:
            keys = (self.board.state_key,)
        elif keys[-1] != self.board.state_key:
            raise ValueError(
                "position_keys must end with the current board key, "
                f"got {keys[-1]} but board key is {self.board.state_key}"
            )

        if not isinstance(self.no_progress_plies, int):
            raise TypeError(
                "no_progress_plies must be an int, "
                f"got {type(self.no_progress_plies).__name__}"
            )
        if not 0 <= self.no_progress_plies <= NO_PROGRESS_PLY_LIMIT:
            raise ValueError(
                "no_progress_plies must be in "
                f"0..{NO_PROGRESS_PLY_LIMIT}, got {self.no_progress_plies}"
            )

        if not any(
            cell not in (None, Piece.EMPTY) for cell in self.board.cells
        ):
            raise ValueError("board must contain at least one piece")

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
        if self.position_keys.count(self.board.state_key) >= REPETITION_LIMIT:
            return Outcome.DRAW
        if self.no_progress_plies >= NO_PROGRESS_PLY_LIMIT:
            return Outcome.DRAW
        return Outcome.ONGOING

    @property
    def draw_reason(self) -> DrawReason | None:
        """Return the draw reason, preferring repetition over no-progress."""
        if self.outcome is not Outcome.DRAW:
            return None
        if self.position_keys.count(self.board.state_key) >= REPETITION_LIMIT:
            return DrawReason.THREEFOLD_REPETITION
        if self.no_progress_plies >= NO_PROGRESS_PLY_LIMIT:
            return DrawReason.NO_PROGRESS
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
