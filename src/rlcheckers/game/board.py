"""The 5x5 board and its canonical encoding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

BOARD_SIZE = 5
SQUARE_COUNT = BOARD_SIZE * BOARD_SIZE
PLAYABLE_SQUARES: tuple[int, ...] = (
    0,
    2,
    4,
    6,
    8,
    10,
    12,
    14,
    16,
    18,
    20,
    22,
    24,
)
_PLAYABLE_SQUARES = frozenset(PLAYABLE_SQUARES)


class Side(IntEnum):
    """The side whose turn it is."""

    BLACK = 0
    WHITE = 1


class Piece(IntEnum):
    """The contents of a playable square."""

    EMPTY = 0
    BLACK_MAN = 1
    BLACK_KING = 2
    WHITE_MAN = 3
    WHITE_KING = 4


_INITIAL_CELLS: tuple[Piece | None, ...] = (
    Piece.BLACK_MAN,
    None,
    Piece.BLACK_MAN,
    None,
    Piece.BLACK_MAN,
    None,
    Piece.BLACK_MAN,
    None,
    Piece.BLACK_MAN,
    None,
    Piece.EMPTY,
    None,
    Piece.EMPTY,
    None,
    Piece.EMPTY,
    None,
    Piece.WHITE_MAN,
    None,
    Piece.WHITE_MAN,
    None,
    Piece.WHITE_MAN,
    None,
    Piece.WHITE_MAN,
    None,
    Piece.WHITE_MAN,
)

_RENDER_SYMBOLS = {
    Piece.EMPTY: ".",
    Piece.BLACK_MAN: "b",
    Piece.BLACK_KING: "B",
    Piece.WHITE_MAN: "w",
    Piece.WHITE_KING: "W",
}


@dataclass(frozen=True)
class Board:
    """A 25-cell board plus the side to move."""

    cells: tuple[Piece | None, ...]
    side_to_move: Side = Side.BLACK

    def __post_init__(self) -> None:
        if len(self.cells) != SQUARE_COUNT:
            raise ValueError(
                f"cells must have {SQUARE_COUNT} entries, got {len(self.cells)}"
            )

        normalized_cells: list[Piece | None] = []
        for index, cell in enumerate(self.cells):
            if index not in _PLAYABLE_SQUARES:
                if cell is not None:
                    raise ValueError(
                        f"cells[{index}] must be None because square {index} "
                        "is not playable"
                    )
                normalized_cells.append(None)
                continue

            if cell is None:
                raise ValueError(f"cells[{index}] must be a piece code 0..4, got None")
            if isinstance(cell, Piece):
                piece = cell
            elif isinstance(cell, int):
                try:
                    piece = Piece(cell)
                except ValueError:
                    raise ValueError(
                        f"cells[{index}] must be a piece code 0..4, got {cell}"
                    ) from None
            else:
                raise ValueError(
                    f"cells[{index}] must be a piece code 0..4, got {cell!r}"
                )
            normalized_cells.append(piece)

        if isinstance(self.side_to_move, Side):
            side = self.side_to_move
        elif isinstance(self.side_to_move, int):
            try:
                side = Side(self.side_to_move)
            except ValueError:
                raise ValueError(
                    "side_to_move must be Side.BLACK (0) or Side.WHITE (1), "
                    f"got {self.side_to_move}"
                ) from None
        else:
            raise ValueError(
                "side_to_move must be Side.BLACK (0) or Side.WHITE (1), "
                f"got {self.side_to_move!r}"
            )

        object.__setattr__(self, "cells", tuple(normalized_cells))
        object.__setattr__(self, "side_to_move", side)

    @classmethod
    def initial(cls) -> Board:
        """Return the standard starting position with Black to move."""
        return cls(_INITIAL_CELLS, Side.BLACK)

    @classmethod
    def from_state_key(cls, key: int) -> Board:
        """Decode a 40-bit canonical state key."""
        if not isinstance(key, int):
            raise TypeError(f"state key must be an int, got {type(key).__name__}")
        if not 0 <= key < (1 << 40):
            raise ValueError(f"state key must be in 0..2**40-1, got {key}")

        cells: list[Piece | None] = [None] * SQUARE_COUNT
        for index, square in enumerate(PLAYABLE_SQUARES):
            code = (key >> (3 * index)) & 0b111
            if code > Piece.WHITE_KING:
                raise ValueError(
                    f"state key has invalid piece code {code} at playable cell {index}"
                )
            cells[square] = Piece(code)

        side = Side((key >> 39) & 1)
        return cls(tuple(cells), side)

    @property
    def state_key(self) -> int:
        """Return the canonical 40-bit state key."""
        key = int(self.side_to_move) << 39
        for index, square in enumerate(PLAYABLE_SQUARES):
            cell = self.cells[square]
            assert cell is not None
            key |= int(cell) << (3 * index)
        return key

    def piece_at(self, row: int, col: int) -> Piece | None:
        """Return the contents of a square, or None for a light square."""
        if not isinstance(row, int):
            raise TypeError(f"row must be an int, got {type(row).__name__}")
        if not isinstance(col, int):
            raise TypeError(f"col must be an int, got {type(col).__name__}")
        if not 0 <= row < BOARD_SIZE:
            raise ValueError(f"row must be in 0..{BOARD_SIZE - 1}, got {row}")
        if not 0 <= col < BOARD_SIZE:
            raise ValueError(f"col must be in 0..{BOARD_SIZE - 1}, got {col}")
        return self.cells[row * BOARD_SIZE + col]

    def render(self) -> str:
        """Render the board and side to move as plain ASCII text."""
        lines = ["    0 1 2 3 4"]
        for row in range(BOARD_SIZE):
            symbols: list[str] = []
            for col in range(BOARD_SIZE):
                cell = self.piece_at(row, col)
                symbols.append("#" if cell is None else _RENDER_SYMBOLS[cell])
            lines.append(f"{row}   " + " ".join(symbols))
        side = "Black" if self.side_to_move is Side.BLACK else "White"
        lines.append(f"{side} to move")
        return "\n".join(lines)
