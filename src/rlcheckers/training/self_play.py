"""Self-play training against periodic frozen Q-table snapshots.

``SnapshotPolicy`` owns the schedule and the one active frozen opponent.
``train_self_play`` updates only the learner table and uses a greedy
``QAgent`` over the active snapshot as the opponent. ``write_self_play_artifacts``
writes the self-play Q-table, CSV, run metadata, and learning curve. The
snapshot policy and training loop are implemented; the artifact writer is filled
in by a later S6 TDD slice.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from rlcheckers.agents.q_agent import QAgent, QTable, q_key
from rlcheckers.agents.random_agent import MAX_GAME_PLIES
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import (
    STANDARD_OPENINGS,
    ArenaResult,
    GameOutcome,
    derive_side_seed,
    opening_state,
    outcome_for,
)
from rlcheckers.game.board import Side
from rlcheckers.game.moves import Move
from rlcheckers.training.train_q import (
    choose_epsilon_greedy,
    derive_episode_seed,
    epsilon_at,
    q_update,
    reward_for,
)

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
        if (
            not isinstance(cadence, int)
            or isinstance(cadence, bool)
            or cadence < 10
            or cadence % 10 != 0
        ):
            raise SelfPlayError(
                "cadence must be a positive multiple of 10, "
                f"got {cadence!r}"
            )
        if (
            not isinstance(episodes, int)
            or isinstance(episodes, bool)
            or episodes <= 0
        ):
            raise SelfPlayError(
                f"episodes must be a positive int, got {episodes!r}"
            )
        if cadence >= episodes:
            raise SelfPlayError(
                f"cadence {cadence} must be less than episodes {episodes}"
            )

        self._cadence = cadence
        self._episodes = episodes
        self._snapshots = [
            Snapshot(0, QTable(max_entries=max_entries)),
        ]
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
        if (
            not isinstance(episode, int)
            or isinstance(episode, bool)
            or not 0 <= episode < self._episodes
        ):
            raise SelfPlayError(
                f"episode {episode!r} is out of range "
                f"0..{self._episodes - 1}"
            )

        for snapshot, record in zip(self._snapshots, self._records):
            if record.first_episode <= episode <= record.last_episode:
                return snapshot

        raise SelfPlayError(
            f"episode {episode} is not covered by a snapshot; "
            "refresh is overdue"
        )

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
        if (
            not isinstance(created_at_episode, int)
            or isinstance(created_at_episode, bool)
        ):
            raise SelfPlayError(
                "snapshot created_at_episode must be an int, "
                f"got {created_at_episode!r}"
            )

        last_created = self._records[-1].created_at_episode
        if created_at_episode == last_created:
            raise SelfPlayError(
                f"snapshot at episode {created_at_episode} already exists"
            )
        if created_at_episode >= self._episodes:
            raise SelfPlayError(
                "snapshot refresh at episode "
                f"{created_at_episode} is not scheduled; "
                f"episodes end at {self._episodes - 1}"
            )
        expected = last_created + self._cadence
        if created_at_episode != expected:
            raise SelfPlayError(
                "snapshot refresh at episode "
                f"{created_at_episode} is unscheduled; "
                f"expected episode {expected}"
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
        self._snapshots.append(Snapshot(created_at_episode, clone))
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
    if config.opponent != "self":
        raise ValueError(
            f"config opponent must be 'self', got {config.opponent!r}"
        )
    if (
        not isinstance(config.episodes, int)
        or isinstance(config.episodes, bool)
        or config.episodes <= 0
        or config.episodes % 10 != 0
    ):
        raise ValueError(
            "config episodes must be a positive multiple of 10, "
            f"got {config.episodes!r}"
        )

    interval = config.snapshot_interval
    if (
        not isinstance(interval, int)
        or isinstance(interval, bool)
        or interval < 10
        or interval % 10 != 0
        or interval >= config.episodes
    ):
        raise ValueError(
            "config snapshot_interval must be a multiple of 10, "
            "at least 10, and less than episodes, "
            f"got {interval!r}"
        )
    if not openings:
        raise ValueError("openings must be non-empty")

    suite = tuple(tuple(opening) for opening in openings)
    table = QTable(max_entries=config.max_table_entries)
    policy = SnapshotPolicy(
        cadence=interval,
        episodes=config.episodes,
        max_entries=config.max_table_entries,
    )
    metrics: list[SelfPlayEpisodeMetric] = []

    for episode in range(config.episodes):
        if episode > 0 and episode % interval == 0:
            policy.refresh(table, created_at_episode=episode)

        snapshot = policy.opponent_for(episode)
        opponent = QAgent(snapshot.table)
        opening_index = (episode // 2) % len(suite)
        learner_colour = (
            Side.BLACK if episode % 2 == 0 else Side.WHITE
        )
        state = opening_state(suite[opening_index])
        epsilon = epsilon_at(
            episode,
            config.episodes,
            config.epsilon_start,
            config.epsilon_end,
            config.epsilon_decay_fraction,
        )
        episode_seed = derive_episode_seed(config.seed, episode)
        learner_seed = derive_side_seed(episode_seed, learner_colour)
        learner_rng = random.Random(learner_seed)

        plies = 0
        outcome: GameOutcome | None = None

        if state.board.side_to_move is not learner_colour:
            state = state.apply(opponent.choose_move(state))
            plies += 1
            if plies > MAX_GAME_PLIES:
                raise RuntimeError(
                    f"game did not terminate within {MAX_GAME_PLIES} plies"
                )
            if state.is_terminal:
                outcome = outcome_for(state.outcome, learner_colour)

        while outcome is None:
            learner_move = choose_epsilon_greedy(
                table, state, epsilon, learner_rng
            )
            key = q_key(state, learner_move)
            current = table.get(key)
            after = state.apply(learner_move)
            plies += 1
            if plies > MAX_GAME_PLIES:
                raise RuntimeError(
                    f"game did not terminate within {MAX_GAME_PLIES} plies"
                )

            if after.is_terminal:
                outcome = outcome_for(after.outcome, learner_colour)
                table.set(
                    key,
                    q_update(
                        current,
                        reward_for(outcome),
                        0.0,
                        config.alpha,
                        config.gamma,
                    ),
                )
                break

            opponent_move = opponent.choose_move(after)
            next_state = after.apply(opponent_move)
            plies += 1
            if plies > MAX_GAME_PLIES:
                raise RuntimeError(
                    f"game did not terminate within {MAX_GAME_PLIES} plies"
                )

            if next_state.is_terminal:
                outcome = outcome_for(next_state.outcome, learner_colour)
                table.set(
                    key,
                    q_update(
                        current,
                        reward_for(outcome),
                        0.0,
                        config.alpha,
                        config.gamma,
                    ),
                )
                break

            next_best = table.best_value(next_state)
            table.set(
                key,
                q_update(
                    current,
                    0.0,
                    next_best,
                    config.alpha,
                    config.gamma,
                ),
            )
            state = next_state

        assert outcome is not None
        metrics.append(
            SelfPlayEpisodeMetric(
                episode=episode,
                opening_index=opening_index,
                learner_colour=learner_colour,
                outcome=outcome,
                plies=plies,
                epsilon=epsilon,
                table_size=table.size(),
                opponent_snapshot_episode=snapshot.created_at_episode,
                opponent_table_size=snapshot.table_size,
            )
        )

    return SelfPlayTrainingResult(
        table=table,
        metrics=tuple(metrics),
        openings=suite,
        snapshots=policy.records,
        snapshot_interval=interval,
    )


def write_self_play_artifacts(
    result: SelfPlayTrainingResult,
    diagnostics: Mapping[str, ArenaResult],
    config: TrainConfig,
    *,
    command_line: Sequence[str],
) -> Path:
    """Write the self-play run's four artifacts."""
    raise NotImplementedError
