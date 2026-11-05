"""Tabular Q-learning agent and Q-table.

This module owns the Q-table representation and the greedy playing adapter. The
training loop lives in ``rlcheckers.training.train_q``; this module does not
train. Public signatures are added in TDD order.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
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


class QTable:
    """A sparse state-action value table."""

    def __init__(
        self,
        entries: Mapping[int, float] | None = None,
        *,
        max_entries: int = 2_000_000,
    ) -> None:
        raise NotImplementedError

    @property
    def entries(self) -> Mapping[int, float]:
        raise NotImplementedError

    @property
    def max_entries(self) -> int:
        raise NotImplementedError

    def get(self, key: int) -> float:
        raise NotImplementedError

    def set(self, key: int, value: float) -> None:
        raise NotImplementedError

    def best_value(self, state: GameState) -> float:
        raise NotImplementedError

    def best_move(self, state: GameState) -> Move:
        raise NotImplementedError

    def size(self) -> int:
        raise NotImplementedError

    def estimated_memory_bytes(self) -> int:
        raise NotImplementedError

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
        raise NotImplementedError

    @property
    def table(self) -> QTable:
        raise NotImplementedError

    def choose_move(self, state: GameState) -> Move:
        raise NotImplementedError
