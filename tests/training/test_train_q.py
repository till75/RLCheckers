from __future__ import annotations

import csv
import json
from dataclasses import replace

import pytest

from rlcheckers.agents.q_agent import QAgent, TableCapacityError
from rlcheckers.agents.random_agent import RandomAgent
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import (
    STANDARD_OPENINGS,
    GameOutcome,
    play_matchup,
    summarize,
)
from rlcheckers.game.board import Side
from rlcheckers.training import (
    DIAGNOSTIC_GAMES,
    TRAINING_FIELDS,
    epsilon_at,
    q_update,
    reward_for,
    train_q,
    write_learning_curve,
    write_training_artifacts,
)


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


def _artifact_inputs(tmp_path):
    config = _train_config(tmp_path)
    result = train_q(config)
    agent = QAgent(result.table)
    diagnostic = play_matchup(
        lambda seed: agent,
        RandomAgent,
        seed=config.seed,
        games=DIAGNOSTIC_GAMES,
        agent_name="q",
        opponent_name="random",
    )
    return config, result, diagnostic


def test_write_training_artifacts_creates_files(tmp_path) -> None:
    config, result, diagnostic = _artifact_inputs(tmp_path)

    out = write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q", "--config", "train.toml"],
    )

    assert out == config.output_dir
    assert (out / "q_table.json").exists()
    assert (out / "training.csv").exists()
    assert (out / "run.json").exists()
    assert (out / "learning_curve.png").exists()


def test_training_csv_schema(tmp_path) -> None:
    config, result, diagnostic = _artifact_inputs(tmp_path)
    out = write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q"],
    )

    with (out / "training.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0]) == list(TRAINING_FIELDS)
    assert len(rows) == config.episodes


def test_run_json_schema(tmp_path) -> None:
    config, result, diagnostic = _artifact_inputs(tmp_path)
    out = write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q"],
    )

    run = json.loads((out / "run.json").read_text(encoding="utf-8"))

    assert set(run) == {
        "command_line",
        "config",
        "diagnostic",
        "openings",
        "package_version",
        "python_version",
        "table_bytes",
        "table_size",
    }
    assert run["diagnostic"]["games"] == DIAGNOSTIC_GAMES
    assert len(run["openings"]) == 5


def test_training_artifacts_are_byte_reproducible(tmp_path) -> None:
    config, result, diagnostic = _artifact_inputs(tmp_path)
    out = write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q"],
    )
    first = {
        name: (out / name).read_bytes()
        for name in ("q_table.json", "training.csv", "run.json")
    }

    write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q"],
    )

    second = {name: (out / name).read_bytes() for name in first}
    assert first == second


def test_write_training_artifacts_preserves_unrelated_files(
    tmp_path,
) -> None:
    config, result, diagnostic = _artifact_inputs(tmp_path)
    out = write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q"],
    )
    keep = out / "keep.txt"
    keep.write_text("keep", encoding="utf-8")

    write_training_artifacts(
        result,
        diagnostic,
        config,
        command_line=["rlcheckers", "train-q"],
    )

    assert keep.read_text(encoding="utf-8") == "keep"


def test_write_training_artifacts_rejects_mismatched_config(
    tmp_path,
) -> None:
    config, result, diagnostic = _artifact_inputs(tmp_path)

    with pytest.raises(ValueError, match="episodes"):
        write_training_artifacts(
            result,
            diagnostic,
            replace(config, episodes=10),
            command_line=["rlcheckers", "train-q"],
        )


def test_learning_curve_is_written(tmp_path) -> None:
    config, result, _ = _artifact_inputs(tmp_path)
    path = tmp_path / "learning_curve.png"

    assert write_learning_curve(result.metrics, path, seed=config.seed) == path
    assert path.stat().st_size > 0


@pytest.mark.slow
def test_train_q_improves_against_random(tmp_path) -> None:
    config = _train_config(
        tmp_path,
        episodes=10000,
        max_table_entries=2_000_000,
    )
    result = train_q(config)
    agent = QAgent(result.table)
    diagnostic = play_matchup(
        lambda seed: agent,
        RandomAgent,
        seed=config.seed,
        games=DIAGNOSTIC_GAMES,
        agent_name="q",
        opponent_name="random",
    )
    summary = summarize([game.outcome for game in diagnostic.games])

    assert summary.games == DIAGNOSTIC_GAMES
    assert summary.wins + summary.draws + summary.losses == DIAGNOSTIC_GAMES
    assert 0.0 <= summary.ci_low <= summary.score <= summary.ci_high <= 1.0
    assert summary.score > 0.5, (
        f"W/D/L {summary.wins}/{summary.draws}/{summary.losses}, "
        f"score {summary.score:.6f}"
    )
