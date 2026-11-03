from __future__ import annotations

from pathlib import Path

import pytest

from rlcheckers.config import ConfigError, EvalConfig, load_eval_config


def write_config(tmp_path: Path, text: str, name: str = "eval.toml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_reads_fields(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\n'
        'games = 10\n'
        'agent = "random"\n'
        'opponent = "greedy"\n'
        'output_dir = "out"\n',
    )

    config = load_eval_config(path)

    assert config.seed == 7
    assert config.games == 10
    assert config.agent == "random"
    assert config.opponent == "greedy"


def test_load_config_resolves_relative_output_dir(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\n'
        'games = 10\n'
        'agent = "random"\n'
        'opponent = "greedy"\n'
        'output_dir = "out"\n',
    )

    config = load_eval_config(path)

    assert config == EvalConfig(
        seed=7,
        games=10,
        agent="random",
        opponent="greedy",
        output_dir=(tmp_path / "out").resolve(),
    )


def test_load_config_keeps_absolute_output_dir(tmp_path: Path) -> None:
    absolute = tmp_path / "elsewhere"
    path = write_config(
        tmp_path,
        f'seed = 7\ngames = 1000\nagent = "greedy"\n'
        f'opponent = "random"\noutput_dir = "{absolute.as_posix()}"\n',
        name="absolute.toml",
    )

    config = load_eval_config(path)

    assert config.output_dir == absolute.resolve()
    assert config.games == 1000


def test_load_config_rejects_missing_key(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\ngames = 10\nagent = "random"\nopponent = "greedy"\n',
    )

    with pytest.raises(ConfigError, match="output_dir"):
        load_eval_config(path)


def test_load_config_rejects_unknown_key(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\ngames = 10\nagent = "random"\n'
        'opponent = "greedy"\noutput_dir = "out"\nextra = 1\n',
    )

    with pytest.raises(ConfigError, match="extra"):
        load_eval_config(path)


def test_load_config_rejects_bad_seed(tmp_path: Path) -> None:
    for text in (
        'seed = "7"\ngames = 10\nagent = "random"\n'
        'opponent = "greedy"\noutput_dir = "out"\n',
        'seed = true\ngames = 10\nagent = "random"\n'
        'opponent = "greedy"\noutput_dir = "out"\n',
    ):
        with pytest.raises(ConfigError, match="seed"):
            load_eval_config(write_config(tmp_path, text))


def test_load_config_rejects_bad_games(tmp_path: Path) -> None:
    for games in ("9", "true", "0", "-10"):
        text = (
            f"seed = 7\ngames = {games}\nagent = \"random\"\n"
            'opponent = "greedy"\noutput_dir = "out"\n'
        )
        with pytest.raises(ConfigError, match="games"):
            load_eval_config(write_config(tmp_path, text))


def test_load_config_rejects_unknown_agent(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\ngames = 10\nagent = "q"\n'
        'opponent = "greedy"\noutput_dir = "out"\n',
    )

    with pytest.raises(ConfigError, match="agent"):
        load_eval_config(path)


def test_load_config_rejects_bad_output_dir(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\ngames = 10\nagent = "random"\n'
        'opponent = "greedy"\noutput_dir = ""\n',
    )

    with pytest.raises(ConfigError, match="output_dir"):
        load_eval_config(path)


def test_load_config_rejects_invalid_toml(tmp_path: Path) -> None:
    path = write_config(tmp_path, "seed = [\n")

    with pytest.raises(ConfigError, match="config"):
        load_eval_config(path)


def test_load_config_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config"):
        load_eval_config(tmp_path / "missing.toml")


def test_load_config_accepts_1000_games(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        'seed = 7\ngames = 1000\nagent = "random"\n'
        'opponent = "greedy"\noutput_dir = "out"\n',
        name="large.toml",
    )

    assert load_eval_config(path).games == 1000
