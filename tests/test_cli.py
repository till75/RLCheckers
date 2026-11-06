from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import rlcheckers.cli
from rlcheckers.agents.random_agent import play_random_game
from rlcheckers.cli import main
from rlcheckers.config import load_eval_config
from rlcheckers.evaluation import GateResult
from rlcheckers.game.moves import format_move
from rlcheckers.training import SelfPlayError


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


@pytest.fixture
def eval_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "eval.toml"
    path.write_text(
        'seed = 7\n'
        'games = 10\n'
        'agent = "random"\n'
        'opponent = "greedy"\n'
        'output_dir = "out"\n',
        encoding="utf-8",
    )
    return path


def test_cli_evaluate_writes_artifacts(
    eval_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["evaluate", "--config", str(eval_config_path)]) == 0
    capsys.readouterr()

    out = eval_config_path.parent / "out"
    assert (out / "metrics.csv").exists()
    assert (out / "games.csv").exists()
    assert (out / "run.json").exists()


def test_cli_evaluate_stdout(
    eval_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = load_eval_config(eval_config_path)

    assert main(["evaluate", "--config", str(eval_config_path)]) == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert lines[0] == "agent: random"
    assert lines[1] == "opponent: greedy"
    assert lines[2] == "seed: 7"
    assert lines[3] == "games: 10"
    assert lines[4].startswith("wins: ")
    assert lines[5].startswith("draws: ")
    assert lines[6].startswith("losses: ")
    assert lines[7].startswith("score: ")
    assert lines[8].startswith("ci95: ")
    assert lines[9] == f"artifacts: {config.output_dir}"
    assert captured.err == ""

    wins = int(lines[4].split(": ")[1])
    draws = int(lines[5].split(": ")[1])
    losses = int(lines[6].split(": ")[1])
    assert wins + draws + losses == 10


def test_cli_evaluate_is_reproducible(
    eval_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = eval_config_path.parent / "out"

    assert main(["evaluate", "--config", str(eval_config_path)]) == 0
    capsys.readouterr()
    first = {
        name: (out / name).read_bytes()
        for name in ("metrics.csv", "games.csv")
    }

    assert main(["evaluate", "--config", str(eval_config_path)]) == 0
    capsys.readouterr()
    second = {name: (out / name).read_bytes() for name in first}

    assert first == second


def test_cli_evaluate_requires_config(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["evaluate"])

    assert excinfo.value.code == 2
    assert "--config" in capsys.readouterr().err


def test_cli_evaluate_reports_config_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("seed = 1\n", encoding="utf-8")

    assert main(["evaluate", "--config", str(bad)]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert captured.out == ""


def test_module_entry_point_runs_evaluate(eval_config_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rlcheckers",
            "evaluate",
            "--config",
            str(eval_config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.startswith("agent: random\n")
    assert completed.stderr == ""


@pytest.fixture
def train_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "train.toml"
    path.write_text(
        'seed = 7\n'
        'episodes = 20\n'
        'alpha = 0.1\n'
        'gamma = 0.9\n'
        'epsilon_start = 1.0\n'
        'epsilon_end = 0.05\n'
        'epsilon_decay_fraction = 0.8\n'
        'opponent = "random"\n'
        'output_dir = "out"\n'
        'max_table_entries = 1000\n',
        encoding="utf-8",
    )
    return path


def test_cli_train_q_writes_artifacts(
    train_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["train-q", "--config", str(train_config_path)]) == 0
    capsys.readouterr()

    out = train_config_path.parent / "out"
    assert (out / "q_table.json").exists()
    assert (out / "training.csv").exists()
    assert (out / "run.json").exists()
    assert (out / "learning_curve.png").exists()


def test_cli_train_q_stdout(
    train_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["train-q", "--config", str(train_config_path)]) == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert lines[0] == "episodes: 20"
    assert lines[1] == "seed: 7"
    assert lines[2].startswith("table_size: ")
    assert lines[3].startswith("table_bytes: ")
    assert lines[4] == "agent: q"
    assert lines[5] == "opponent: random"
    assert lines[6] == "games: 1000"
    assert lines[7].startswith("wins: ")
    assert lines[8].startswith("draws: ")
    assert lines[9].startswith("losses: ")
    assert lines[10].startswith("score: ")
    assert lines[11].startswith("ci95: ")
    assert lines[12] == (
        f"artifacts: {(train_config_path.parent / 'out').resolve()}"
    )
    assert captured.err == ""


def test_cli_train_q_is_reproducible(
    train_config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = train_config_path.parent / "out"

    assert main(["train-q", "--config", str(train_config_path)]) == 0
    capsys.readouterr()
    first = {
        name: (out / name).read_bytes()
        for name in ("q_table.json", "training.csv", "run.json")
    }

    assert main(["train-q", "--config", str(train_config_path)]) == 0
    capsys.readouterr()
    second = {name: (out / name).read_bytes() for name in first}

    assert first == second


def test_cli_train_q_requires_config(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["train-q"])

    assert excinfo.value.code == 2
    assert "--config" in capsys.readouterr().err


def test_cli_train_q_reports_config_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("seed = 1\n", encoding="utf-8")

    assert main(["train-q", "--config", str(bad)]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert captured.out == ""


def test_module_entry_point_runs_train_q(
    train_config_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rlcheckers",
            "train-q",
            "--config",
            str(train_config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.startswith("episodes: 20\n")
    assert completed.stderr == ""


@pytest.fixture
def self_play_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "self.toml"
    path.write_text(
        'seed = 7\n'
        'episodes = 20\n'
        'alpha = 0.1\n'
        'gamma = 0.9\n'
        'epsilon_start = 1.0\n'
        'epsilon_end = 0.05\n'
        'epsilon_decay_fraction = 0.8\n'
        'opponent = "self"\n'
        'output_dir = "out"\n'
        'max_table_entries = 1000\n'
        'snapshot_interval = 10\n',
        encoding="utf-8",
    )
    return path


def test_cli_train_q_self_play_writes_artifacts(
    self_play_config_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(
        ["train-q", "--config", str(self_play_config_path)]
    ) == 0
    capsys.readouterr()

    out = self_play_config_path.parent / "out"
    assert (out / "q_table.json").exists()
    assert (out / "training.csv").exists()
    assert (out / "run.json").exists()
    assert (out / "learning_curve.png").exists()


def test_cli_train_q_self_play_stdout(
    self_play_config_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(
        ["train-q", "--config", str(self_play_config_path)]
    ) == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) == 21
    assert lines[0] == "episodes: 20"
    assert lines[1] == "seed: 7"
    assert lines[2] == "snapshot_interval: 10"
    assert lines[3] == "snapshots: 2"
    assert lines[4].startswith("table_size: ")
    assert lines[5].startswith("table_bytes: ")
    assert lines[6] == "agent: q"
    assert lines[7] == "opponent: self"
    assert lines[8] == "random_games: 1000"
    assert lines[9].startswith("random_wins: ")
    assert lines[10].startswith("random_draws: ")
    assert lines[11].startswith("random_losses: ")
    assert lines[12].startswith("random_score: ")
    assert lines[13].startswith("random_ci95: ")
    assert lines[14] == "greedy_games: 1000"
    assert lines[15].startswith("greedy_wins: ")
    assert lines[16].startswith("greedy_draws: ")
    assert lines[17].startswith("greedy_losses: ")
    assert lines[18].startswith("greedy_score: ")
    assert lines[19].startswith("greedy_ci95: ")
    assert lines[20] == (
        f"artifacts: {(self_play_config_path.parent / 'out').resolve()}"
    )
    assert captured.err == ""

    random_counts = [int(lines[index].split(": ")[1]) for index in (9, 10, 11)]
    greedy_counts = [int(lines[index].split(": ")[1]) for index in (15, 16, 17)]
    assert sum(random_counts) == 1000
    assert sum(greedy_counts) == 1000


def test_cli_train_q_self_play_is_reproducible(
    self_play_config_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = self_play_config_path.parent / "out"

    assert main(
        ["train-q", "--config", str(self_play_config_path)]
    ) == 0
    capsys.readouterr()
    first = {
        name: (out / name).read_bytes()
        for name in ("q_table.json", "training.csv", "run.json")
    }

    assert main(
        ["train-q", "--config", str(self_play_config_path)]
    ) == 0
    capsys.readouterr()
    second = {name: (out / name).read_bytes() for name in first}

    assert first == second


def test_cli_train_q_self_play_requires_config(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["train-q"])

    assert excinfo.value.code == 2
    assert "--config" in capsys.readouterr().err


def test_cli_train_q_self_play_reports_config_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = tmp_path / "bad-self.toml"
    bad.write_text(
        'seed = 7\n'
        'episodes = 20\n'
        'alpha = 0.1\n'
        'gamma = 0.9\n'
        'epsilon_start = 1.0\n'
        'epsilon_end = 0.05\n'
        'epsilon_decay_fraction = 0.8\n'
        'opponent = "self"\n'
        'output_dir = "out"\n'
        'max_table_entries = 1000\n',
        encoding="utf-8",
    )

    assert main(["train-q", "--config", str(bad)]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert "snapshot_interval" in captured.err
    assert captured.out == ""


def test_cli_train_q_self_play_reports_snapshot_error(
    self_play_config_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_train(config) -> None:
        raise SelfPlayError("snapshot failed")

    monkeypatch.setattr(rlcheckers.cli, "train_self_play", broken_train)

    assert main(
        ["train-q", "--config", str(self_play_config_path)]
    ) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error: snapshot")
    assert captured.out == ""


def test_cli_train_q_random_mode_unchanged(
    train_config_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["train-q", "--config", str(train_config_path)]) == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) == 13
    assert lines[5] == "opponent: random"
    assert captured.err == ""

    out = train_config_path.parent / "out"
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
    assert "snapshot_interval" not in run["config"]


def test_module_entry_point_runs_self_play(
    self_play_config_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rlcheckers",
            "train-q",
            "--config",
            str(self_play_config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.startswith("episodes: 20\n")
    assert completed.stderr == ""


@pytest.fixture
def gate_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "gate.toml"
    path.write_text(
        'seeds = [7, 8, 9]\n'
        'eval_seed = 7\n'
        'episodes = 20\n'
        'alpha = 0.1\n'
        'gamma = 0.9\n'
        'epsilon_start = 1.0\n'
        'epsilon_end = 0.05\n'
        'epsilon_decay_fraction = 0.8\n'
        'output_dir = "out"\n'
        'max_table_entries = 1000\n'
        'snapshot_interval = 10\n'
        'games = 10\n'
        'snapshot_games = 10\n'
        'unique_games = 10\n',
        encoding="utf-8",
    )
    return path


def _gate_result(config, *, passed: bool) -> GateResult:
    return GateResult(
        config=config,
        seeds=(),
        random_mean=0.70 if passed else 0.50,
        random_min=0.60 if passed else 0.40,
        greedy_mean=0.65 if passed else 0.50,
        greedy_min=0.55 if passed else 0.40,
        passed=passed,
    )


def test_cli_gate_stdout(
    gate_config_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def fake_run_gate(config):
        return _gate_result(config, passed=True)

    def fake_write_gate_artifacts(result, config, *, command_line):
        calls.append((result, config, command_line))
        return config.output_dir

    monkeypatch.setattr(rlcheckers.cli, "run_gate", fake_run_gate)
    monkeypatch.setattr(
        rlcheckers.cli,
        "write_gate_artifacts",
        fake_write_gate_artifacts,
    )

    assert main(
        ["gate", "--config", str(gate_config_path)]
    ) == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) == 13
    assert lines[0] == "seeds: 7,8,9"
    assert lines[1] == "eval_seed: 7"
    assert lines[2] == "episodes: 20"
    assert lines[3] == "snapshot_interval: 10"
    assert lines[4] == "games: 10"
    assert lines[5] == "snapshot_games: 10"
    assert lines[6] == "unique_games: 10"
    assert lines[7] == "random_mean: 0.700000"
    assert lines[8] == "random_min: 0.600000"
    assert lines[9] == "greedy_mean: 0.650000"
    assert lines[10] == "greedy_min: 0.550000"
    assert lines[11] == "gate: pass"
    assert lines[12] == (
        f"artifacts: {(gate_config_path.parent / 'out').resolve()}"
    )
    assert captured.err == ""
    assert len(calls) == 1


def test_cli_gate_returns_one_on_fail(
    gate_config_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def fake_run_gate(config):
        return _gate_result(config, passed=False)

    def fake_write_gate_artifacts(result, config, *, command_line):
        calls.append((result, config, command_line))
        return config.output_dir

    monkeypatch.setattr(rlcheckers.cli, "run_gate", fake_run_gate)
    monkeypatch.setattr(
        rlcheckers.cli,
        "write_gate_artifacts",
        fake_write_gate_artifacts,
    )

    assert main(
        ["gate", "--config", str(gate_config_path)]
    ) == 1
    captured = capsys.readouterr()

    assert "gate: fail" in captured.out
    assert captured.err == ""
    assert len(calls) == 1


def test_cli_gate_requires_config(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["gate"])

    assert excinfo.value.code == 2
    assert "--config" in capsys.readouterr().err


def test_cli_gate_reports_config_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = tmp_path / "bad-gate.toml"
    bad.write_text(
        'seeds = [7, 8, 9]\n'
        'eval_seed = 7\n'
        'episodes = 20\n'
        'alpha = 0.1\n'
        'gamma = 0.9\n'
        'epsilon_start = 1.0\n'
        'epsilon_end = 0.05\n'
        'epsilon_decay_fraction = 0.8\n'
        'output_dir = "out"\n'
        'max_table_entries = 1000\n'
        'snapshot_interval = 10\n'
        'games = 10\n'
        'snapshot_games = 10\n',
        encoding="utf-8",
    )

    assert main(["gate", "--config", str(bad)]) == 1
    captured = capsys.readouterr()

    assert captured.err.startswith("error:")
    assert "unique_games" in captured.err
    assert captured.out == ""


def test_cli_gate_reports_runtime_error(
    gate_config_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def broken_run_gate(config):
        raise RuntimeError("gate failed")

    def fake_write_gate_artifacts(result, config, *, command_line):
        calls.append((result, config, command_line))
        return config.output_dir

    monkeypatch.setattr(rlcheckers.cli, "run_gate", broken_run_gate)
    monkeypatch.setattr(
        rlcheckers.cli,
        "write_gate_artifacts",
        fake_write_gate_artifacts,
    )

    assert main(
        ["gate", "--config", str(gate_config_path)]
    ) == 1
    captured = capsys.readouterr()

    assert captured.err.startswith("error: gate failed")
    assert captured.out == ""
    assert calls == []


def test_module_entry_point_runs_gate(
    gate_config_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "rlcheckers",
            "gate",
            "--config",
            str(gate_config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode in (0, 1)
    assert completed.stdout.startswith("seeds: 7,8,9\n")
    assert completed.stderr == ""
    out = gate_config_path.parent / "out"
    assert (out / "gate.json").exists()
    assert (out / "s7-three-seed-gate-diagnostics.md").exists()
