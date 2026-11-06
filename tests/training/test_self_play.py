from __future__ import annotations

import pytest

from rlcheckers.agents.q_agent import QAgent, QTable, q_key
from rlcheckers.game.board import Board
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState
from rlcheckers.training import SelfPlayError, SnapshotPolicy


def _initial_state() -> GameState:
    return GameState.from_board(Board.initial())


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
