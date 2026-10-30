from __future__ import annotations

import subprocess
import sys

import pytest

from rlcheckers.agents.random_agent import play_random_game
from rlcheckers.cli import main
from rlcheckers.game.moves import format_move


def test_cli_play_random_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["play-random", "--seed", "7"]) == 0

    out = capsys.readouterr().out
    lines = out.splitlines()
    record = play_random_game(7)

    assert out.endswith("\n")
    assert lines[0] == "seed: 7"
    assert lines[1:-2] == [
        f"{index}. {format_move(move)}"
        for index, move in enumerate(record.moves, start=1)
    ]
    assert lines[-2] == f"result: {record.outcome.value}"
    assert lines[-1] == f"plies: {record.plies}"


def test_cli_play_random_is_reproducible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["play-random", "--seed", "7"])
    first = capsys.readouterr().out

    main(["play-random", "--seed", "7"])
    second = capsys.readouterr().out

    assert first == second


def test_cli_requires_seed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["play-random"])

    assert excinfo.value.code == 2
    assert "--seed" in capsys.readouterr().err


def test_cli_rejects_non_integer_seed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["play-random", "--seed", "abc"])

    assert excinfo.value.code == 2
    assert "--seed" in capsys.readouterr().err


def test_module_entry_point_runs_play_random() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rlcheckers",
            "play-random",
            "--seed",
            "7",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.startswith("seed: 7\n")
    assert completed.stderr == ""
