from __future__ import annotations

from dataclasses import replace

import pytest

from rlcheckers.agents.q_agent import TableCapacityError
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import STANDARD_OPENINGS, GameOutcome
from rlcheckers.game.board import Side
from rlcheckers.training import epsilon_at, q_update, reward_for, train_q


def test_q_update_non_terminal() -> None:
    assert q_update(0.20, 0.0, 0.60, 0.1, 0.9) == pytest.approx(0.234)


def test_q_update_terminal_win() -> None:
    assert q_update(0.20, 1.0, 0.0, 0.1, 0.9) == pytest.approx(0.28)


def test_q_update_terminal_loss_and_draw() -> None:
    assert q_update(0.20, -1.0, 0.0, 0.1, 0.9) == pytest.approx(0.08)
    assert q_update(0.20, 0.0, 0.0, 0.1, 0.9) == pytest.approx(0.18)


def test_q_update_rejects_bad_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        q_update(0.2, 0.0, 0.6, 0.0, 0.9)


def test_q_update_rejects_bad_gamma() -> None:
    with pytest.raises(ValueError, match="gamma"):
        q_update(0.2, 0.0, 0.6, 0.1, 1.0)


def test_epsilon_schedule_starts_at_start() -> None:
    assert epsilon_at(0, 10, 1.0, 0.05, 0.8) == 1.0


def test_epsilon_schedule_reaches_end() -> None:
    assert epsilon_at(4, 10, 1.0, 0.05, 0.8) == pytest.approx(0.525)
    assert epsilon_at(8, 10, 1.0, 0.05, 0.8) == 0.05


def test_epsilon_schedule_stays_at_end() -> None:
    assert epsilon_at(9, 10, 1.0, 0.05, 0.8) == 0.05


def test_epsilon_schedule_rejects_zero_fraction() -> None:
    with pytest.raises(ValueError, match="decay_fraction"):
        epsilon_at(0, 10, 1.0, 0.05, 0.0)


def test_epsilon_schedule_rejects_bad_episode() -> None:
    with pytest.raises(ValueError, match="episode"):
        epsilon_at(-1, 10, 1.0, 0.05, 0.8)

    with pytest.raises(ValueError, match="episode"):
        epsilon_at(10, 10, 1.0, 0.05, 0.8)


def test_epsilon_schedule_rejects_inverted_endpoints() -> None:
    with pytest.raises(ValueError, match="start"):
        epsilon_at(0, 10, 0.01, 0.05, 0.8)


def _train_config(tmp_path, **overrides) -> TrainConfig:
    base = TrainConfig(
        seed=7,
        episodes=20,
        alpha=0.1,
        gamma=0.9,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_fraction=0.8,
        opponent="random",
        output_dir=tmp_path / "out",
        max_table_entries=1000,
    )
    return replace(base, **overrides)


def test_train_q_episode_schedule(tmp_path) -> None:
    result = train_q(_train_config(tmp_path))

    assert len(result.metrics) == 20
    assert [metric.episode for metric in result.metrics] == list(range(20))
    assert [metric.opening_index for metric in result.metrics] == [
        0, 0, 1, 1, 2, 2, 3, 3, 4, 4,
    ] * 2
    assert [metric.learner_colour for metric in result.metrics] == [
        Side.BLACK,
        Side.WHITE,
    ] * 10


def test_train_q_uses_both_colours(tmp_path) -> None:
    result = train_q(_train_config(tmp_path))

    assert {metric.learner_colour for metric in result.metrics} == {
        Side.BLACK,
        Side.WHITE,
    }


def test_train_q_rewards_and_updates(tmp_path) -> None:
    assert reward_for(GameOutcome.WIN) == 1.0
    assert reward_for(GameOutcome.DRAW) == 0.0
    assert reward_for(GameOutcome.LOSS) == -1.0

    result = train_q(_train_config(tmp_path))

    assert result.table.size() > 0
    assert all(metric.outcome in tuple(GameOutcome) for metric in result.metrics)


def test_train_q_is_reproducible(tmp_path) -> None:
    config = _train_config(tmp_path)

    assert train_q(config) == train_q(config)


def test_train_q_capacity_guard(tmp_path) -> None:
    config = _train_config(tmp_path, max_table_entries=1)

    with pytest.raises(TableCapacityError, match="cap"):
        train_q(config)


def test_train_q_smoke(tmp_path) -> None:
    config = _train_config(tmp_path)
    result = train_q(config)

    assert len(result.metrics) == config.episodes
    assert 0 < result.table.size() <= config.max_table_entries
    assert all(metric.plies > 0 for metric in result.metrics)
    assert all(metric.outcome in tuple(GameOutcome) for metric in result.metrics)
    assert result.openings == STANDARD_OPENINGS
