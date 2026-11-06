from __future__ import annotations

from dataclasses import replace

import pytest

from rlcheckers.agents.q_agent import QAgent, QTable, q_key
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import GameOutcome, opening_state
from rlcheckers.game.board import Board, Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState
from rlcheckers.training import (
    SelfPlayError,
    SnapshotPolicy,
    SnapshotRecord,
    train_self_play,
)


def _initial_state() -> GameState:
    return GameState.from_board(Board.initial())


def _table_with(size: int) -> QTable:
    table = QTable(max_entries=100)
    for key in range(size):
        table.set(key, float(key))
    return table


def _self_play_config(tmp_path, **overrides) -> TrainConfig:
    base = TrainConfig(
        seed=7,
        episodes=20,
        alpha=0.1,
        gamma=0.9,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_fraction=0.8,
        opponent="self",
        output_dir=tmp_path / "out",
        max_table_entries=1000,
        snapshot_interval=10,
    )
    return replace(base, **overrides)


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


def test_train_self_play_episode_schedule(tmp_path) -> None:
    result = train_self_play(_self_play_config(tmp_path))

    assert len(result.metrics) == 20
    assert [metric.episode for metric in result.metrics] == list(range(20))
    assert [metric.opening_index for metric in result.metrics] == [
        0, 0, 1, 1, 2, 2, 3, 3, 4, 4,
    ] * 2
    assert [metric.learner_colour for metric in result.metrics] == [
        Side.BLACK,
        Side.WHITE,
    ] * 10


def test_train_self_play_snapshot_boundaries(tmp_path) -> None:
    result = train_self_play(_self_play_config(tmp_path))

    assert result.snapshot_interval == 10
    assert result.snapshots == (
        SnapshotRecord(0, 0, 9, 0),
        SnapshotRecord(
            10,
            10,
            19,
            result.metrics[9].table_size,
        ),
    )


def test_train_self_play_uses_both_colours(tmp_path) -> None:
    result = train_self_play(_self_play_config(tmp_path))

    assert {metric.learner_colour for metric in result.metrics} == {
        Side.BLACK,
        Side.WHITE,
    }


def test_train_self_play_metrics_match_snapshots(tmp_path) -> None:
    result = train_self_play(_self_play_config(tmp_path))
    second_size = result.snapshots[1].table_size

    assert [metric.opponent_snapshot_episode for metric in result.metrics] == (
        [0] * 10 + [10] * 10
    )
    assert [
        metric.opponent_table_size for metric in result.metrics
    ] == [0] * 10 + [second_size] * 10
    assert second_size == result.metrics[9].table_size


def test_train_self_play_minimum_run(tmp_path) -> None:
    config = _self_play_config(tmp_path)
    result = train_self_play(config)

    assert len(result.snapshots) == 2
    assert {metric.opponent_snapshot_episode for metric in result.metrics} == {
        0,
        10,
    }
    assert 0 < result.table.size() <= config.max_table_entries


def test_train_self_play_30_episodes_with_20_interval(tmp_path) -> None:
    config = _self_play_config(
        tmp_path,
        episodes=30,
        snapshot_interval=20,
    )
    result = train_self_play(config)

    assert result.snapshots == (
        SnapshotRecord(0, 0, 19, 0),
        SnapshotRecord(
            20,
            20,
            29,
            result.metrics[19].table_size,
        ),
    )
    assert [metric.opponent_snapshot_episode for metric in result.metrics] == (
        [0] * 20 + [20] * 10
    )
    assert result.snapshots[1].table_size == result.metrics[19].table_size


def test_train_self_play_smoke(tmp_path) -> None:
    config = _self_play_config(
        tmp_path,
        episodes=200,
        snapshot_interval=100,
    )
    result = train_self_play(config)

    assert len(result.metrics) == config.episodes
    assert all(
        metric.outcome in tuple(GameOutcome)
        for metric in result.metrics
    )
    assert 0 < result.table.size() <= config.max_table_entries
    assert len(result.snapshots) == 2


def test_train_self_play_rejects_bad_opponent(tmp_path) -> None:
    config = _self_play_config(tmp_path, opponent="greedy")

    with pytest.raises(ValueError, match="opponent"):
        train_self_play(config)


def test_train_self_play_rejects_missing_snapshot_interval(
    tmp_path,
) -> None:
    config = _self_play_config(tmp_path, snapshot_interval=None)

    with pytest.raises(ValueError, match="snapshot_interval"):
        train_self_play(config)


def test_train_self_play_rejects_interval_not_less_than_episodes(
    tmp_path,
) -> None:
    config = _self_play_config(tmp_path, snapshot_interval=20)

    with pytest.raises(ValueError, match="snapshot_interval"):
        train_self_play(config)


def test_train_self_play_is_reproducible(tmp_path) -> None:
    config = _self_play_config(tmp_path)

    assert train_self_play(config) == train_self_play(config)


def test_train_self_play_initial_opponent_is_deterministic(
    tmp_path,
    monkeypatch,
) -> None:
    opening = (Move((6, 10)),)
    state = opening_state(opening)
    expected = QAgent(QTable()).choose_move(state)
    calls: list[tuple[int, Move]] = []
    original = QAgent.choose_move

    def recording(agent: QAgent, current: GameState) -> Move:
        move = original(agent, current)
        calls.append((current.board.state_key, move))
        return move

    monkeypatch.setattr(QAgent, "choose_move", recording)
    config = _self_play_config(tmp_path)

    first = train_self_play(config, openings=(opening,))
    first_calls = list(calls)
    calls.clear()
    second = train_self_play(config, openings=(opening,))

    assert first_calls
    assert first_calls[0][1] == expected
    assert calls == first_calls
    assert first.snapshots == second.snapshots


def test_train_self_play_propagates_snapshot_error(
    tmp_path,
    monkeypatch,
) -> None:
    def broken_refresh(
        policy: SnapshotPolicy,
        table: QTable,
        *,
        created_at_episode: int,
    ) -> SnapshotRecord:
        raise SelfPlayError(
            f"snapshot refresh failed at episode {created_at_episode}"
        )

    monkeypatch.setattr(SnapshotPolicy, "refresh", broken_refresh)

    with pytest.raises(SelfPlayError, match="snapshot"):
        train_self_play(_self_play_config(tmp_path))


def test_train_self_play_rejects_random_opponent(tmp_path) -> None:
    config = _self_play_config(
        tmp_path,
        opponent="random",
        snapshot_interval=None,
    )

    with pytest.raises(ValueError, match="opponent"):
        train_self_play(config)
