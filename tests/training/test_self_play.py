from __future__ import annotations

import csv
import json
import platform
from dataclasses import replace

import pytest

import rlcheckers
from rlcheckers.agents import GreedyAgent
from rlcheckers.agents.q_agent import QAgent, QTable, q_key
from rlcheckers.agents.random_agent import RandomAgent
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import (
    ArenaResult,
    GameOutcome,
    GameResult,
    opening_state,
    play_matchup,
    summarize,
)
from rlcheckers.game.board import Board, Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState
from rlcheckers.training import (
    DIAGNOSTIC_GAMES,
    SELF_PLAY_TRAINING_FIELDS,
    SelfPlayError,
    SnapshotPolicy,
    SnapshotRecord,
    train_self_play,
    write_learning_curve,
    write_self_play_artifacts,
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


def _diagnostic(
    opponent: str,
    seed: int,
    openings,
    *,
    games: int = DIAGNOSTIC_GAMES,
) -> ArenaResult:
    results = tuple(
        GameResult(
            game_index=index,
            pair_index=index // 2,
            opening_index=(index // 2) % len(openings),
            agent_colour=(
                Side.BLACK if index % 2 == 0 else Side.WHITE
            ),
            outcome=GameOutcome.WIN,
            plies=10,
            game_seed=0,
            final_state_key=0,
        )
        for index in range(games)
    )
    return ArenaResult(
        agent_name="q",
        opponent_name=opponent,
        seed=seed,
        openings=tuple(tuple(opening) for opening in openings),
        games=results,
    )


def _artifact_inputs(tmp_path):
    config = _self_play_config(tmp_path)
    result = train_self_play(config)
    diagnostics = {
        "random": _diagnostic("random", config.seed, result.openings),
        "greedy": _diagnostic("greedy", config.seed, result.openings),
    }
    return config, result, diagnostics


def _write_artifacts(config, result, diagnostics):
    return write_self_play_artifacts(
        result,
        diagnostics,
        config,
        command_line=["rlcheckers", "train-q", "--config", "self.toml"],
    )


def test_write_self_play_artifacts_creates_files(tmp_path) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)

    out = _write_artifacts(config, result, diagnostics)

    assert out == config.output_dir
    assert (out / "q_table.json").exists()
    assert (out / "training.csv").exists()
    assert (out / "run.json").exists()
    assert (out / "learning_curve.png").exists()


def test_self_play_training_csv_schema(tmp_path) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    out = _write_artifacts(config, result, diagnostics)

    with (out / "training.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0]) == list(SELF_PLAY_TRAINING_FIELDS)
    assert len(rows) == config.episodes
    assert [int(row["episode"]) for row in rows] == list(range(20))
    assert {row["learner_colour"] for row in rows} == {"black", "white"}
    assert {row["outcome"] for row in rows} <= {"win", "draw", "loss"}


def test_self_play_run_json_schema(tmp_path) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    out = _write_artifacts(config, result, diagnostics)

    run = json.loads((out / "run.json").read_text(encoding="utf-8"))

    assert set(run) == {
        "command_line",
        "config",
        "diagnostics",
        "openings",
        "package_version",
        "python_version",
        "snapshots",
        "table_bytes",
        "table_size",
    }
    assert run["command_line"] == [
        "rlcheckers",
        "train-q",
        "--config",
        "self.toml",
    ]
    assert set(run["config"]) == {
        "alpha",
        "epsilon_decay_fraction",
        "epsilon_end",
        "epsilon_start",
        "episodes",
        "gamma",
        "max_table_entries",
        "opponent",
        "output_dir",
        "seed",
        "snapshot_interval",
    }
    assert run["config"]["opponent"] == "self"
    assert run["config"]["snapshot_interval"] == 10
    assert set(run["diagnostics"]) == {"random", "greedy"}
    assert run["diagnostics"]["random"]["games"] == DIAGNOSTIC_GAMES
    assert run["diagnostics"]["greedy"]["opponent"] == "greedy"
    assert len(run["openings"]) == len(result.openings)
    assert [record["created_at_episode"] for record in run["snapshots"]] == [
        0,
        10,
    ]
    assert run["snapshots"] == [
        {
            "created_at_episode": record.created_at_episode,
            "first_episode": record.first_episode,
            "last_episode": record.last_episode,
            "table_size": record.table_size,
        }
        for record in result.snapshots
    ]
    assert run["table_size"] == result.table.size()
    assert run["table_bytes"] == result.table.estimated_memory_bytes()
    assert run["package_version"] == rlcheckers.__version__
    assert run["python_version"] == platform.python_version()


def test_self_play_q_table_metadata(tmp_path) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    out = _write_artifacts(config, result, diagnostics)

    loaded, metadata = QTable.load(out / "q_table.json")

    assert loaded == result.table
    assert metadata["config"]["opponent"] == "self"
    assert metadata["config"]["snapshot_interval"] == 10
    assert metadata["table_size"] == result.table.size()


def test_self_play_artifacts_are_byte_reproducible(tmp_path) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    out = _write_artifacts(config, result, diagnostics)
    first = {
        name: (out / name).read_bytes()
        for name in ("q_table.json", "training.csv", "run.json")
    }

    _write_artifacts(config, result, diagnostics)

    second = {name: (out / name).read_bytes() for name in first}
    assert first == second


def test_write_self_play_artifacts_preserves_unrelated_files(
    tmp_path,
) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    out = _write_artifacts(config, result, diagnostics)
    keep = out / "keep.txt"
    keep.write_text("keep", encoding="utf-8")

    _write_artifacts(config, result, diagnostics)

    assert keep.read_text(encoding="utf-8") == "keep"


def test_write_self_play_artifacts_rejects_missing_diagnostic(
    tmp_path,
) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    incomplete = {"random": diagnostics["random"]}

    with pytest.raises(ValueError, match="diagnostic"):
        _write_artifacts(config, result, incomplete)

    assert not config.output_dir.exists()


def test_write_self_play_artifacts_rejects_mismatched_seed(
    tmp_path,
) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    diagnostics["greedy"] = replace(
        diagnostics["greedy"],
        seed=config.seed + 1,
    )

    with pytest.raises(ValueError, match="seed"):
        _write_artifacts(config, result, diagnostics)


def test_write_self_play_artifacts_rejects_wrong_games(
    tmp_path,
) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    diagnostics["random"] = replace(
        diagnostics["random"],
        games=diagnostics["random"].games[:-1],
    )

    with pytest.raises(ValueError, match="games"):
        _write_artifacts(config, result, diagnostics)


def test_write_self_play_artifacts_rejects_mismatched_config(
    tmp_path,
) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)

    with pytest.raises(ValueError, match="episodes"):
        _write_artifacts(
            replace(config, episodes=30),
            result,
            diagnostics,
        )


def test_write_self_play_artifacts_rejects_bad_snapshot_schedule(
    tmp_path,
) -> None:
    config, result, diagnostics = _artifact_inputs(tmp_path)
    bad = replace(result, snapshots=result.snapshots[:1])

    with pytest.raises(ValueError, match="snapshot"):
        _write_artifacts(config, bad, diagnostics)

    assert not config.output_dir.exists()


def test_self_play_learning_curve_is_written(tmp_path) -> None:
    config, result, _ = _artifact_inputs(tmp_path)
    path = tmp_path / "learning_curve.png"

    assert (
        write_learning_curve(
            result.metrics,
            path,
            seed=config.seed,
            title_prefix="Self-play training",
        )
        == path
    )
    assert path.stat().st_size > 0


@pytest.mark.slow
def test_train_self_play_improves_against_random_and_greedy(
    tmp_path,
) -> None:
    config = _self_play_config(
        tmp_path,
        episodes=10_000,
        snapshot_interval=1_000,
        max_table_entries=2_000_000,
    )
    result = train_self_play(config)
    agent = QAgent(result.table)
    diagnostics = {
        "random": play_matchup(
            lambda seed: agent,
            lambda seed: RandomAgent(seed=seed),
            seed=config.seed,
            games=DIAGNOSTIC_GAMES,
            agent_name="q",
            opponent_name="random",
            openings=result.openings,
        ),
        "greedy": play_matchup(
            lambda seed: agent,
            lambda seed: GreedyAgent(),
            seed=config.seed,
            games=DIAGNOSTIC_GAMES,
            agent_name="q",
            opponent_name="greedy",
            openings=result.openings,
        ),
    }

    summaries = {}
    for name, diagnostic in diagnostics.items():
        summary = summarize(
            [game.outcome for game in diagnostic.games]
        )
        summaries[name] = summary

        assert summary.games == DIAGNOSTIC_GAMES
        assert (
            summary.wins + summary.draws + summary.losses
            == DIAGNOSTIC_GAMES
        )
        assert (
            0.0
            <= summary.ci_low
            <= summary.score
            <= summary.ci_high
            <= 1.0
        )
        assert summary.score > 0.50, (
            f"{name} W/D/L "
            f"{summary.wins}/{summary.draws}/{summary.losses}, "
            f"score {summary.score:.6f}"
        )

    assert result.table.size() > 0
    assert len(result.snapshots) == 10
    print(
        "self-play improvement: "
        f"table_size={result.table.size()} "
        f"snapshots={len(result.snapshots)} "
        f"random={summaries['random'].wins}/"
        f"{summaries['random'].draws}/"
        f"{summaries['random'].losses} "
        f"score={summaries['random'].score:.6f} "
        f"ci95={summaries['random'].ci_low:.6f}.."
        f"{summaries['random'].ci_high:.6f} "
        f"greedy={summaries['greedy'].wins}/"
        f"{summaries['greedy'].draws}/"
        f"{summaries['greedy'].losses} "
        f"score={summaries['greedy'].score:.6f} "
        f"ci95={summaries['greedy'].ci_low:.6f}.."
        f"{summaries['greedy'].ci_high:.6f}"
    )
