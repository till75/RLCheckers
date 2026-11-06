"""Self-play training against periodic frozen Q-table snapshots.

``SnapshotPolicy`` owns the schedule and the one active frozen opponent.
``train_self_play`` updates only the learner table and uses a greedy
``QAgent`` over the active snapshot as the opponent. ``write_self_play_artifacts``
writes the self-play Q-table, CSV, run metadata, and learning curve. The
implementation is filled in by the S6 TDD slices; this module currently defines
the public surface only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from rlcheckers.agents.q_agent import QTable
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import STANDARD_OPENINGS, ArenaResult, GameOutcome
from rlcheckers.game.board import Side
from rlcheckers.game.moves import Move

SELF_PLAY_TRAINING_FIELDS = (
    "episode",
    "opening_index",
    "learner_colour",
    "outcome",
    "plies",
    "epsilon",
    "table_size",
    "opponent_snapshot_episode",
    "opponent_table_size",
)


class SelfPlayError(RuntimeError):
    """Raised when a self-play snapshot operation fails."""


@dataclass(frozen=True)
class Snapshot:
    """One frozen opponent table and the episode that created it."""

    created_at_episode: int
    table: QTable

    @property
    def table_size(self) -> int:
        """Return the number of entries in the frozen table."""
        return self.table.size()


@dataclass(frozen=True)
class SnapshotRecord:
    """One snapshot's identity and the episode block that used it."""

    created_at_episode: int
    first_episode: int
    last_episode: int
    table_size: int


class SnapshotPolicy:
    """Own the active frozen opponent and its refresh schedule."""

    def __init__(
        self,
        *,
        cadence: int,
        episodes: int,
        max_entries: int,
    ) -> None:
        self._cadence = cadence
        self._episodes = episodes
        self._active = Snapshot(0, QTable(max_entries=max_entries))
        self._records = [
            SnapshotRecord(
                created_at_episode=0,
                first_episode=0,
                last_episode=cadence - 1,
                table_size=0,
            )
        ]

    @property
    def cadence(self) -> int:
        """Return the refresh cadence in episodes."""
        return self._cadence

    @property
    def records(self) -> tuple[SnapshotRecord, ...]:
        """Return the snapshots created so far in creation order."""
        return tuple(self._records)

    def opponent_for(self, episode: int) -> Snapshot:
        """Return the frozen opponent that covers ``episode``."""
        return self._active

    def refresh(
        self,
        table: QTable,
        *,
        created_at_episode: int,
    ) -> SnapshotRecord:
        """Freeze ``table`` and make it the active opponent."""
        if not isinstance(table, QTable):
            raise SelfPlayError(
                "snapshot must be a QTable, "
                f"got {type(table).__name__}"
            )
        try:
            clone = table.clone()
        except Exception as error:
            raise SelfPlayError(
                f"could not clone snapshot table: {error}"
            ) from error

        record = SnapshotRecord(
            created_at_episode=created_at_episode,
            first_episode=created_at_episode,
            last_episode=min(
                created_at_episode + self._cadence, self._episodes
            )
            - 1,
            table_size=clone.size(),
        )
        self._active = Snapshot(created_at_episode, clone)
        self._records.append(record)
        return record


@dataclass(frozen=True)
class SelfPlayEpisodeMetric:
    """One self-play episode's identity, outcome, and opponent."""

    episode: int
    opening_index: int
    learner_colour: Side
    outcome: GameOutcome
    plies: int
    epsilon: float
    table_size: int
    opponent_snapshot_episode: int
    opponent_table_size: int


@dataclass(frozen=True)
class SelfPlayTrainingResult:
    """The learner table, metrics, openings, and snapshot schedule."""

    table: QTable
    metrics: tuple[SelfPlayEpisodeMetric, ...]
    openings: tuple[tuple[Move, ...], ...]
    snapshots: tuple[SnapshotRecord, ...]
    snapshot_interval: int


def train_self_play(
    config: TrainConfig,
    *,
    openings: Sequence[Sequence[Move]] = STANDARD_OPENINGS,
) -> SelfPlayTrainingResult:
    """Train a Q-table against its own periodically frozen snapshots."""
    raise NotImplementedError


def write_self_play_artifacts(
    result: SelfPlayTrainingResult,
    diagnostics: Mapping[str, ArenaResult],
    config: TrainConfig,
    *,
    command_line: Sequence[str],
) -> Path:
    """Write the self-play run's four artifacts."""
    raise NotImplementedError
