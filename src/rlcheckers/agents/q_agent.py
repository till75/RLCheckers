"""Tabular Q-learning agent and Q-table.

``q_key`` combines the canonical 40-bit board key with the 33-bit action key.
``QTable`` stores sparse state-action values, enforces the entry cap, estimates
memory, persists JSON, and clones an independent frozen copy for self-play.
``QAgent`` is the greedy playing adapter used by the evaluation arena; it owns
no RNG and does not train. The fixed-opponent and self-play training loops live
in ``rlcheckers.training.train_q`` and ``rlcheckers.training.self_play``.
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState

_QTABLE_FORMAT = "rlcheckers.qtable"
_QTABLE_VERSION = 1
_QKEY_LIMIT = 1 << 73
_METADATA_KEYS = {
    "config",
    "package_version",
    "python_version",
    "seed",
    "table_size",
}


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

    def clone(self) -> QTable:
        """Return an independent copy with the same entries and cap."""
        return QTable(self._entries, max_entries=self._max_entries)

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
        if not isinstance(other, QTable):
            return NotImplemented
        return (
            self._max_entries == other._max_entries
            and self._entries == other._entries
        )

    def save(self, path: str | Path, metadata: Mapping[str, Any]) -> Path:
        target = Path(path)
        document = {
            "format": _QTABLE_FORMAT,
            "version": _QTABLE_VERSION,
            "metadata": dict(metadata),
            "table": {
                str(key): value for key, value in self._entries.items()
            },
        }
        target.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target

    @classmethod
    def load(cls, path: str | Path) -> tuple[QTable, dict[str, Any]]:
        target = Path(path)
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise QTableError(
                f"could not parse Q-table {target}: {error}"
            ) from None

        if not isinstance(document, dict):
            raise QTableError("Q-table JSON must be an object")
        expected = {"format", "version", "metadata", "table"}
        if set(document) != expected:
            raise QTableError(
                "Q-table JSON must have exactly "
                f"{sorted(expected)}, got {sorted(document)}"
            )
        if document["format"] != _QTABLE_FORMAT:
            raise QTableError(
                f"Q-table format must be {_QTABLE_FORMAT!r}, "
                f"got {document['format']!r}"
            )
        if document["version"] != _QTABLE_VERSION:
            raise QTableError(
                f"Q-table version must be {_QTABLE_VERSION}, "
                f"got {document['version']!r}"
            )

        metadata = document["metadata"]
        if not isinstance(metadata, dict):
            raise QTableError("Q-table metadata must be an object")
        if set(metadata) != _METADATA_KEYS:
            raise QTableError(
                "Q-table metadata must have exactly "
                f"{sorted(_METADATA_KEYS)}, got {sorted(metadata)}"
            )

        config = metadata["config"]
        if not isinstance(config, dict):
            raise QTableError("Q-table metadata.config must be an object")
        max_entries = config.get("max_table_entries")
        if (
            not isinstance(max_entries, int)
            or isinstance(max_entries, bool)
            or max_entries <= 0
        ):
            raise QTableError(
                "Q-table metadata.config.max_table_entries must be "
                f"a positive int, got {max_entries!r}"
            )

        raw_table = document["table"]
        if not isinstance(raw_table, dict):
            raise QTableError("Q-table table must be an object")
        table_size = metadata["table_size"]
        if (
            not isinstance(table_size, int)
            or isinstance(table_size, bool)
            or table_size != len(raw_table)
        ):
            raise QTableError(
                "Q-table metadata.table_size must match the table length, "
                f"got {table_size!r} for {len(raw_table)} entries"
            )

        entries: dict[int, float] = {}
        for raw_key, raw_value in raw_table.items():
            if not isinstance(raw_key, str):
                raise QTableError(
                    f"Q-table key must be a decimal string, got {raw_key!r}"
                )
            try:
                key = int(raw_key)
            except ValueError:
                raise QTableError(
                    f"Q-table key must be a decimal string, got {raw_key!r}"
                ) from None
            if not 0 <= key < _QKEY_LIMIT:
                raise QTableError(
                    f"Q-table key must be in 0..{_QKEY_LIMIT - 1}, "
                    f"got {key}"
                )
            try:
                entries[key] = _validate_value(raw_value)
            except ValueError as error:
                raise QTableError(str(error)) from None
        if len(entries) != len(raw_table):
            raise QTableError("Q-table contains duplicate integer keys")

        return cls(entries, max_entries=max_entries), metadata


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
