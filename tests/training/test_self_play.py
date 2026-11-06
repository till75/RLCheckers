from __future__ import annotations

import pytest

from rlcheckers.agents.q_agent import QAgent, QTable, q_key
from rlcheckers.game.board import Board
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState
from rlcheckers.training import SelfPlayError, SnapshotPolicy, SnapshotRecord


def _initial_state() -> GameState:
    return GameState.from_board(Board.initial())


def _table_with(size: int) -> QTable:
    table = QTable(max_entries=100)
    for key in range(size):
        table.set(key, float(key))
    return table


def test_snapshot_policy_refresh_freezes_learner_table() -> None:
    state = _initial_state()
    first = Move((6, 10))
    second = Move((8, 14))
    learner = QTable(max_entries=10)
    learner.set(q_key(state, first), 1.0)
    learner.set(q_key(state, second), 2.0)
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=10)

    policy.refresh(learner, created_at_episode=10)
    snapshot = policy.opponent_for(10)

    expected = dict(learner.entries)
    assert snapshot.created_at_episode == 10
    assert snapshot.table == learner
    assert dict(snapshot.table.entries) == expected
    assert QAgent(snapshot.table).choose_move(state) == second

    learner.set(q_key(state, first), 5.0)
    learner.set(q_key(state, second), -1.0)

    assert dict(snapshot.table.entries) == expected
    assert QAgent(snapshot.table).choose_move(state) == second
    assert QAgent(learner).choose_move(state) == first


def test_snapshot_policy_refresh_rejects_non_table() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=10)

    with pytest.raises(SelfPlayError, match="snapshot"):
        policy.refresh("not a table", created_at_episode=10)


class _BrokenTable(QTable):
    def clone(self) -> QTable:
        raise RuntimeError("clone failed")


def test_snapshot_policy_refresh_wraps_clone_failure() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=10)

    with pytest.raises(SelfPlayError, match="snapshot"):
        policy.refresh(_BrokenTable(), created_at_episode=10)


def test_snapshot_policy_initial_record() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=100)

    assert policy.cadence == 10
    assert policy.records == (SnapshotRecord(0, 0, 9, 0),)
    snapshot = policy.opponent_for(0)
    assert snapshot.created_at_episode == 0
    assert snapshot.table_size == 0
    assert snapshot.table.max_entries == 100


def test_snapshot_policy_refreshes_every_cadence() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=30, max_entries=100)

    record = policy.refresh(_table_with(5), created_at_episode=10)
    policy.refresh(_table_with(7), created_at_episode=20)

    assert record == SnapshotRecord(10, 10, 19, 5)
    assert policy.records == (
        SnapshotRecord(0, 0, 9, 0),
        SnapshotRecord(10, 10, 19, 5),
        SnapshotRecord(20, 20, 29, 7),
    )


def test_snapshot_policy_uses_latest_snapshot() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=30, max_entries=100)
    policy.refresh(_table_with(3), created_at_episode=10)
    policy.refresh(_table_with(8), created_at_episode=20)

    assert policy.opponent_for(0).created_at_episode == 0
    assert policy.opponent_for(9).created_at_episode == 0
    assert policy.opponent_for(10).created_at_episode == 10
    assert policy.opponent_for(19).created_at_episode == 10
    assert policy.opponent_for(20).created_at_episode == 20
    assert policy.opponent_for(29).created_at_episode == 20


def test_snapshot_policy_rejects_missed_refresh() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=100)

    with pytest.raises(SelfPlayError, match=r"episode 10.*overdue"):
        policy.opponent_for(10)


def test_snapshot_policy_rejects_unscheduled_refresh() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=100)
    table = _table_with(1)

    with pytest.raises(SelfPlayError, match="snapshot"):
        policy.refresh(table, created_at_episode=9)

    with pytest.raises(SelfPlayError, match="snapshot"):
        policy.refresh(table, created_at_episode=20)


def test_snapshot_policy_rejects_duplicate_refresh() -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=100)
    table = _table_with(1)
    policy.refresh(table, created_at_episode=10)

    with pytest.raises(SelfPlayError, match="snapshot"):
        policy.refresh(table, created_at_episode=10)


@pytest.mark.parametrize("cadence", [0, 9, 15, True, "10"])
def test_snapshot_policy_rejects_bad_cadence(cadence: object) -> None:
    with pytest.raises(SelfPlayError, match="cadence"):
        SnapshotPolicy(cadence=cadence, episodes=20, max_entries=100)


@pytest.mark.parametrize(
    ("cadence", "episodes"),
    [(10, 10), (20, 10), (20, 20), (30, 20)],
)
def test_snapshot_policy_rejects_cadence_not_less_than_episodes(
    cadence: int,
    episodes: int,
) -> None:
    with pytest.raises(SelfPlayError, match="cadence"):
        SnapshotPolicy(
            cadence=cadence,
            episodes=episodes,
            max_entries=100,
        )


@pytest.mark.parametrize("episode", [-1, 20])
def test_snapshot_policy_rejects_out_of_range_episode(episode: int) -> None:
    policy = SnapshotPolicy(cadence=10, episodes=20, max_entries=100)

    with pytest.raises(SelfPlayError, match="episode"):
        policy.opponent_for(episode)
