from __future__ import annotations

import csv
import json
import platform
from pathlib import Path

import pytest

import rlcheckers
from rlcheckers.agents import Agent
from rlcheckers.config import EvalConfig
from rlcheckers.evaluation.arena import (
    STANDARD_OPENINGS,
    ArenaResult,
    opening_state,
    play_matchup,
)
from rlcheckers.evaluation.artifacts import (
    GAMES_FIELDS,
    METRICS_FIELDS,
    write_artifacts,
)
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


class FirstLegalAgent:
    def choose_move(self, state: GameState) -> Move:
        return state.legal_moves()[0]


def first_legal(seed: int) -> Agent:
    return FirstLegalAgent()


@pytest.fixture
def result() -> ArenaResult:
    return play_matchup(first_legal, first_legal, seed=7, games=10)


@pytest.fixture
def artifact_config(tmp_path: Path) -> EvalConfig:
    return EvalConfig(
        seed=7,
        games=10,
        agent="agent",
        opponent="opponent",
        output_dir=tmp_path / "out",
    )


@pytest.fixture
def artifact_command_line() -> list[str]:
    return ["rlcheckers", "evaluate", "--config", "eval.toml"]


def test_write_artifacts_creates_files(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    out = write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )

    assert out == artifact_config.output_dir
    assert (out / "metrics.csv").exists()
    assert (out / "games.csv").exists()
    assert (out / "run.json").exists()


def test_metrics_csv_schema(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    out = write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )

    with (out / "metrics.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0]) == list(METRICS_FIELDS)
    assert len(rows) == 8
    assert rows[0]["seed"] == "7"
    assert rows[0]["agent"] == "agent"
    assert rows[0]["opponent"] == "opponent"
    assert rows[0]["group"] == "overall"
    assert rows[0]["key"] == ""
    assert rows[0]["games"] == "10"
    assert len(rows[0]["score"].split(".")[1]) == 6


def test_games_csv_schema(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    out = write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )

    with (out / "games.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0]) == list(GAMES_FIELDS)
    assert len(rows) == 10
    assert [int(row["game_index"]) for row in rows] == list(range(10))
    assert {row["agent_colour"] for row in rows} == {"black", "white"}
    assert {row["outcome"] for row in rows} <= {"win", "draw", "loss"}
    assert all(row["seed"] == "7" for row in rows)
    assert all(row["agent"] == "agent" for row in rows)
    assert all(row["opponent"] == "opponent" for row in rows)


def test_run_json_schema(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    out = write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )

    run = json.loads((out / "run.json").read_text(encoding="utf-8"))

    assert set(run) == {
        "command_line",
        "config",
        "openings",
        "package_version",
        "python_version",
    }
    assert run["command_line"] == artifact_command_line
    assert run["config"] == {
        "agent": "agent",
        "games": 10,
        "opponent": "opponent",
        "output_dir": str(artifact_config.output_dir),
        "seed": 7,
    }
    assert len(run["openings"]) == 5
    assert [entry["index"] for entry in run["openings"]] == list(range(5))
    assert [entry["state_key"] for entry in run["openings"]] == [
        opening_state(opening).board.state_key
        for opening in STANDARD_OPENINGS
    ]
    assert run["package_version"] == rlcheckers.__version__
    assert run["python_version"] == platform.python_version()


def test_artifacts_are_byte_reproducible(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    out = write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )
    first = {
        name: (out / name).read_bytes()
        for name in ("metrics.csv", "games.csv", "run.json")
    }

    write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )
    second = {name: (out / name).read_bytes() for name in first}

    assert first == second


def test_write_artifacts_preserves_unrelated_files(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    out = write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )
    (out / "keep.txt").write_text("keep", encoding="utf-8")

    write_artifacts(
        result,
        artifact_config,
        command_line=artifact_command_line,
    )

    assert (out / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_write_artifacts_rejects_mismatched_config(
    result: ArenaResult,
    artifact_config: EvalConfig,
    artifact_command_line: list[str],
) -> None:
    wrong_seed = EvalConfig(
        seed=8,
        games=10,
        agent="agent",
        opponent="opponent",
        output_dir=artifact_config.output_dir,
    )
    with pytest.raises(ValueError, match="config"):
        write_artifacts(
            result,
            wrong_seed,
            command_line=artifact_command_line,
        )

    wrong_games = EvalConfig(
        seed=7,
        games=20,
        agent="agent",
        opponent="opponent",
        output_dir=artifact_config.output_dir,
    )
    with pytest.raises(ValueError, match="config"):
        write_artifacts(
            result,
            wrong_games,
            command_line=artifact_command_line,
        )
