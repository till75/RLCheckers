from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from rlcheckers.agents.q_agent import QTable
from rlcheckers.config import GateConfig
from rlcheckers.evaluation import (
    GATE_CSV_FIELDS,
    SNAPSHOT_CURVE_FIELDS,
    GameOutcome,
    GateMatchup,
    GateResult,
    SeedGateResult,
    SnapshotCurvePoint,
    aggregate_gate,
    summarize,
    write_gate_artifacts,
)


def _summary(wins: int, draws: int = 0, losses: int = 0):
    outcomes = (
        [GameOutcome.WIN] * wins
        + [GameOutcome.DRAW] * draws
        + [GameOutcome.LOSS] * losses
    )
    return summarize(outcomes)


def _matchup(
    opponent: str,
    wins: int,
    *,
    games: int = 1000,
    unique_games: int = 1000,
    ci_applicable: bool = True,
) -> GateMatchup:
    summary = _summary(wins, losses=games - wins)
    return GateMatchup(
        opponent=opponent,
        games=games,
        unique_games=unique_games,
        overall=summary,
        black=summary,
        white=summary,
        ci_applicable=ci_applicable,
    )


def _seed(
    seed: int,
    random_wins: int,
    greedy_wins: int,
    *,
    games: int = 1000,
    snapshot_curve: tuple[SnapshotCurvePoint, ...] = (),
) -> SeedGateResult:
    table = QTable(max_entries=100)
    return SeedGateResult(
        seed=seed,
        table=table,
        table_size=table.size(),
        snapshots=(),
        matchups={
            "random": _matchup(
                "random",
                random_wins,
                games=games,
                unique_games=games,
            ),
            "stochastic_greedy": _matchup(
                "stochastic_greedy",
                greedy_wins,
                games=games,
                unique_games=games,
            ),
            "deterministic_greedy": _matchup(
                "deterministic_greedy",
                5,
                games=10,
                unique_games=10,
                ci_applicable=False,
            ),
            "depth2": _matchup(
                "depth2",
                4,
                games=10,
                unique_games=10,
                ci_applicable=False,
            ),
        },
        snapshot_curve=snapshot_curve,
    )


def _gate_config(tmp_path: Path) -> GateConfig:
    return GateConfig(
        seeds=(7, 8, 9),
        eval_seed=7,
        episodes=10000,
        alpha=0.1,
        gamma=0.9,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_fraction=0.8,
        output_dir=tmp_path / "out",
        max_table_entries=2000000,
        snapshot_interval=1000,
        games=1000,
        snapshot_games=200,
        unique_games=10,
    )


def _curve_point(
    episode: int,
    table_size: int,
    random_wins: int,
    greedy_wins: int,
    *,
    games: int = 200,
) -> SnapshotCurvePoint:
    return SnapshotCurvePoint(
        episode=episode,
        table_size=table_size,
        random=_summary(random_wins, losses=games - random_wins),
        stochastic_greedy=_summary(
            greedy_wins, losses=games - greedy_wins
        ),
    )


def _gate_result(tmp_path: Path) -> GateResult:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(
            7,
            600,
            550,
            snapshot_curve=(
                _curve_point(0, 0, 100, 100),
                _curve_point(10, 100, 150, 140),
            ),
        ),
        _seed(
            8,
            700,
            650,
            snapshot_curve=(
                _curve_point(0, 0, 100, 100),
                _curve_point(10, 100, 160, 150),
            ),
        ),
        _seed(
            9,
            800,
            750,
            snapshot_curve=(
                _curve_point(0, 0, 100, 100),
                _curve_point(10, 100, 170, 160),
            ),
        ),
    )
    return aggregate_gate(config, seeds)


def _small_gate_result(tmp_path: Path) -> GateResult:
    config = replace(
        _gate_config(tmp_path),
        episodes=20,
        snapshot_interval=10,
        games=10,
        snapshot_games=10,
        unique_games=10,
    )
    seeds = (
        _seed(
            7,
            6,
            5,
            games=10,
            snapshot_curve=(
                _curve_point(0, 0, 5, 5, games=10),
                _curve_point(10, 10, 6, 6, games=10),
            ),
        ),
        _seed(
            8,
            7,
            6,
            games=10,
            snapshot_curve=(
                _curve_point(0, 0, 5, 5, games=10),
                _curve_point(10, 10, 7, 6, games=10),
            ),
        ),
        _seed(
            9,
            8,
            7,
            games=10,
            snapshot_curve=(
                _curve_point(0, 0, 5, 5, games=10),
                _curve_point(10, 10, 8, 7, games=10),
            ),
        ),
    )
    return aggregate_gate(config, seeds)


def test_gate_writes_artifacts(tmp_path: Path) -> None:
    result = _gate_result(tmp_path)

    out = write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )

    assert out == result.config.output_dir
    assert (out / "q_table_seed_7.json").exists()
    assert (out / "q_table_seed_8.json").exists()
    assert (out / "q_table_seed_9.json").exists()
    assert (out / "gate.json").exists()
    assert (out / "gate.csv").exists()
    assert (out / "snapshot_curve.csv").exists()
    assert (out / "snapshot_curve.png").exists()
    assert (out / "s7-three-seed-gate-diagnostics.md").exists()


def test_gate_json_schema(tmp_path: Path) -> None:
    result = _gate_result(tmp_path)
    out = write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )

    document = json.loads((out / "gate.json").read_text(encoding="utf-8"))

    assert set(document) == {
        "command_line",
        "config",
        "gate",
        "seeds",
        "package_version",
        "python_version",
    }
    assert document["command_line"] == [
        "rlcheckers",
        "gate",
        "--config",
        "gate.toml",
    ]
    assert set(document["config"]) == {
        "seeds",
        "eval_seed",
        "episodes",
        "alpha",
        "gamma",
        "epsilon_start",
        "epsilon_end",
        "epsilon_decay_fraction",
        "output_dir",
        "max_table_entries",
        "snapshot_interval",
        "games",
        "snapshot_games",
        "unique_games",
    }
    assert document["config"]["seeds"] == [7, 8, 9]
    assert document["config"]["output_dir"] == str(result.config.output_dir)
    assert set(document["gate"]) == {
        "passed",
        "random_mean",
        "random_min",
        "greedy_mean",
        "greedy_min",
        "thresholds",
    }
    assert document["gate"]["thresholds"] == {
        "random_mean": 0.60,
        "greedy_mean": 0.55,
        "seed_floor": 0.50,
    }
    assert len(document["seeds"]) == 3
    seed = document["seeds"][0]
    assert set(seed) == {
        "seed",
        "table_size",
        "snapshots",
        "matchups",
        "snapshot_curve",
    }
    assert set(seed["matchups"]) == {
        "random",
        "stochastic_greedy",
        "deterministic_greedy",
        "depth2",
    }
    assert set(seed["matchups"]["random"]) == {
        "games",
        "unique_games",
        "overall",
        "black",
        "white",
        "ci_applicable",
    }
    assert set(seed["matchups"]["random"]["overall"]) == {
        "wins",
        "draws",
        "losses",
        "score",
        "ci_low",
        "ci_high",
    }
    assert seed["matchups"]["deterministic_greedy"]["ci_applicable"] is False
    assert (
        seed["matchups"]["deterministic_greedy"]["overall"]["ci_low"]
        is None
    )
    assert (
        seed["matchups"]["deterministic_greedy"]["overall"]["ci_high"]
        is None
    )
    assert seed["matchups"]["random"]["overall"]["ci_low"] is not None
    assert len(seed["snapshot_curve"]) == 2
    assert set(seed["snapshot_curve"][0]) == {
        "episode",
        "table_size",
        "random",
        "stochastic_greedy",
    }
    assert set(seed["snapshot_curve"][0]["random"]) == {
        "wins",
        "draws",
        "losses",
        "score",
        "ci_low",
        "ci_high",
    }


def test_gate_csv_schema(tmp_path: Path) -> None:
    result = _gate_result(tmp_path)
    out = write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )

    with (out / "gate.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0]) == list(GATE_CSV_FIELDS)
    assert len(rows) == 3 * 4 * 3
    assert {row["opponent"] for row in rows} == {
        "random",
        "stochastic_greedy",
        "deterministic_greedy",
        "depth2",
    }
    assert {row["group"] for row in rows} == {"overall", "colour"}
    assert {
        row["key"] for row in rows if row["group"] == "colour"
    } == {"black", "white"}

    deterministic = [
        row
        for row in rows
        if row["opponent"] in ("deterministic_greedy", "depth2")
    ]
    assert all(row["ci_low"] == "" for row in deterministic)
    assert all(row["ci_high"] == "" for row in deterministic)
    assert all(row["unique_games"] == "10" for row in deterministic)

    random_rows = [
        row for row in rows if row["opponent"] == "random"
    ]
    assert all(row["unique_games"] == "1000" for row in random_rows)
    assert all(row["ci_low"] != "" for row in random_rows)


def test_snapshot_curve_csv_schema(tmp_path: Path) -> None:
    result = _gate_result(tmp_path)
    out = write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )

    with (out / "snapshot_curve.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0]) == list(SNAPSHOT_CURVE_FIELDS)
    assert len(rows) == 3 * 2 * 2
    assert {row["opponent"] for row in rows} == {
        "random",
        "stochastic_greedy",
    }
    assert all(row["games"] == "200" for row in rows)
    assert all(row["unique_games"] == "200" for row in rows)
    assert all(row["ci_low"] != "" for row in rows)


def test_gate_artifacts_are_byte_reproducible(tmp_path: Path) -> None:
    result = _gate_result(tmp_path)
    out = write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )
    names = (
        "q_table_seed_7.json",
        "q_table_seed_8.json",
        "q_table_seed_9.json",
        "gate.json",
        "gate.csv",
        "snapshot_curve.csv",
        "s7-three-seed-gate-diagnostics.md",
    )
    first = {name: (out / name).read_bytes() for name in names}

    write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )

    second = {name: (out / name).read_bytes() for name in names}
    assert first == second


def test_gate_writes_no_partial_artifacts_on_error(
    tmp_path: Path,
) -> None:
    result = _gate_result(tmp_path)
    bad_seed = replace(
        result.seeds[0],
        matchups={
            "random": result.seeds[0].matchups["random"],
        },
    )
    bad = replace(result, seeds=(bad_seed, *result.seeds[1:]))

    with pytest.raises(ValueError, match="stochastic_greedy"):
        write_gate_artifacts(
            bad,
            bad.config,
            command_line=["rlcheckers", "gate", "--config", "gate.toml"],
        )

    assert not bad.config.output_dir.exists()


def test_gate_small_n_integration(tmp_path: Path) -> None:
    result = _small_gate_result(tmp_path)

    out = write_gate_artifacts(
        result,
        result.config,
        command_line=["rlcheckers", "gate", "--config", "gate.toml"],
    )

    assert out == result.config.output_dir
    assert (out / "gate.json").exists()
    assert (out / "gate.csv").exists()
    assert (out / "snapshot_curve.csv").exists()
    assert (out / "snapshot_curve.png").exists()
    assert (out / "s7-three-seed-gate-diagnostics.md").exists()


def test_gate_aggregates_three_seeds(tmp_path: Path) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, 600, 550),
        _seed(8, 700, 650),
        _seed(9, 800, 750),
    )

    result = aggregate_gate(config, seeds)

    assert result.config == config
    assert result.seeds == seeds
    assert result.random_mean == pytest.approx(0.70)
    assert result.random_min == pytest.approx(0.60)
    assert result.greedy_mean == pytest.approx(0.65)
    assert result.greedy_min == pytest.approx(0.55)
    assert result.passed is True


def test_gate_passes_at_thresholds(tmp_path: Path) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, 600, 550),
        _seed(8, 500, 500),
        _seed(9, 700, 600),
    )

    result = aggregate_gate(config, seeds)

    assert result.random_mean == pytest.approx(0.60)
    assert result.random_min == pytest.approx(0.50)
    assert result.greedy_mean == pytest.approx(0.55)
    assert result.greedy_min == pytest.approx(0.50)
    assert result.passed is True


@pytest.mark.parametrize(
    ("middle_random", "middle_greedy"),
    [(490, 800), (800, 490)],
)
def test_gate_fails_below_floor(
    tmp_path: Path,
    middle_random: int,
    middle_greedy: int,
) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, 800, 800),
        _seed(8, middle_random, middle_greedy),
        _seed(9, 800, 800),
    )

    result = aggregate_gate(config, seeds)

    assert result.passed is False


@pytest.mark.parametrize(
    ("random_wins", "greedy_wins"),
    [(590, 800), (800, 540)],
)
def test_gate_fails_below_mean(
    tmp_path: Path,
    random_wins: int,
    greedy_wins: int,
) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, random_wins, greedy_wins),
        _seed(8, random_wins, greedy_wins),
        _seed(9, random_wins, greedy_wins),
    )

    result = aggregate_gate(config, seeds)

    assert result.passed is False
