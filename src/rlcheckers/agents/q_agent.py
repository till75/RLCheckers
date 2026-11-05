"""Tabular Q-learning agent and Q-table.

This module owns the Q-table representation and the greedy playing adapter. The
training loop lives in ``rlcheckers.training.train_q``; this module does not
train. Public signatures are added in TDD order.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


class QTableError(ValueError):
    """Raised when a Q-table operation or document is invalid."""


class TableCapacityError(QTableError):
    """Raised when a new Q-table key would exceed the configured cap."""


def q_key(state: GameState, move: Move) -> int:
    """Return ADR 0002's combined state-action key."""
    return (state.board.state_key << 33) | move.action_key


def _validate_key(key: object) -> int:
    if not isinstance(key, int) or isinstance(key, bool):
        raise ValueError(f"Q-table key must be an int, got {key!r}")
    return key


def _validate_value(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Q-table value must be a finite float, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Q-table value must be a finite float, got {value!r}")
    return number


class QTable:
    """A sparse state-action value table."""

    def __init__(
        self,
        entries: Mapping[int, float] | None = None,
        *,
        max_entries: int = 2_000_000,
    ) -> None:
        if (
            not isinstance(max_entries, int)
            or isinstance(max_entries, bool)
            or max_entries <= 0
        ):
            raise ValueError(
                f"max_entries must be a positive int, got {max_entries!r}"
            )

        self._max_entries = max_entries
        self._entries: dict[int, float] = {}
        if entries is not None:
            for raw_key, raw_value in entries.items():
                self._entries[_validate_key(raw_key)] = _validate_value(raw_value)
            if len(self._entries) > max_entries:
                raise TableCapacityError(
                    f"Q-table cap of {max_entries} entries exceeded by initial data"
                )

    @property
    def entries(self) -> Mapping[int, float]:
        return MappingProxyType(self._entries)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def get(self, key: int) -> float:
        return self._entries.get(_validate_key(key), 0.0)

    def set(self, key: int, value: float) -> None:
        key = _validate_key(key)
        value = _validate_value(value)
        if key not in self._entries and len(self._entries) >= self._max_entries:
            raise TableCapacityError(
                f"Q-table cap of {self._max_entries} entries reached; "
                "refusing new key"
            )
        self._entries[key] = value

    def best_value(self, state: GameState) -> float:
        if state.is_terminal:
            raise QTableError(f"game is finished: {state.outcome.value}")
        moves = state.legal_moves()
        if not moves:
            raise QTableError("no legal moves")
        return max(self.get(q_key(state, move)) for move in moves)

    def best_move(self, state: GameState) -> Move:
        if state.is_terminal:
            raise QTableError(f"game is finished: {state.outcome.value}")
        moves = state.legal_moves()
        if not moves:
            raise QTableError("no legal moves")

        best = moves[0]
        best_value = self.get(q_key(state, best))
        for move in moves[1:]:
            value = self.get(q_key(state, move))
            if value > best_value:
                best = move
                best_value = value
        return best

    def size(self) -> int:
        return len(self._entries)

    def estimated_memory_bytes(self) -> int:
        return sys.getsizeof(self._entries) + sum(
            sys.getsizeof(key) + sys.getsizeof(value)
            for key, value in self._entries.items()
        )

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def save(self, path: str | Path, metadata: Mapping[str, Any]) -> Path:
        raise NotImplementedError

    @classmethod
    def load(cls, path: str | Path) -> tuple[QTable, dict[str, Any]]:
        raise NotImplementedError


class QAgent:
    """A greedy adapter that reads a Q-table and chooses legal moves."""

    def __init__(self, table: QTable) -> None:
        if not isinstance(table, QTable):
            raise TypeError(
                f"table must be a QTable, got {type(table).__name__}"
            )
        self._table = table

    @property
    def table(self) -> QTable:
        return self._table

    def choose_move(self, state: GameState) -> Move:
        if state.is_terminal:
            raise ValueError(f"game is finished: {state.outcome.value}")
        return self._table.best_move(state)
