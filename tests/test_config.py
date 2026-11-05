from __future__ import annotations

from pathlib import Path

import pytest

from rlcheckers.config import (
    ConfigError,
    EvalConfig,
    TrainConfig,
    load_eval_config,
    load_train_config,
)


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


TRAIN_CONFIG_TEXT = (
    'seed = 7\n'
    'episodes = 20\n'
    'alpha = 0.1\n'
    'gamma = 0.9\n'
    'epsilon_start = 1.0\n'
    'epsilon_end = 0.05\n'
    'epsilon_decay_fraction = 0.8\n'
    'opponent = "random"\n'
    'output_dir = "out"\n'
    'max_table_entries = 1000\n'
)


def write_train_config(
    tmp_path: Path, text: str = TRAIN_CONFIG_TEXT
) -> Path:
    return write_config(tmp_path, text, name="train.toml")


def test_load_train_config_reads_fields(tmp_path: Path) -> None:
    path = write_train_config(tmp_path)

    config = load_train_config(path)

    assert config == TrainConfig(
        seed=7,
        episodes=20,
        alpha=0.1,
        gamma=0.9,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_fraction=0.8,
        opponent="random",
        output_dir=(tmp_path / "out").resolve(),
        max_table_entries=1000,
    )


def test_load_train_config_resolves_relative_output_dir(
    tmp_path: Path,
) -> None:
    path = write_train_config(tmp_path)

    assert load_train_config(path).output_dir == (tmp_path / "out").resolve()


def test_load_train_config_keeps_absolute_output_dir(
    tmp_path: Path,
) -> None:
    absolute = tmp_path / "elsewhere"
    text = TRAIN_CONFIG_TEXT.replace(
        'output_dir = "out"',
        f'output_dir = "{absolute.as_posix()}"',
    )
    path = write_train_config(tmp_path, text)

    assert load_train_config(path).output_dir == absolute.resolve()


def test_load_train_config_accepts_10_episodes(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace("episodes = 20", "episodes = 10"),
    )

    assert load_train_config(path).episodes == 10


def test_load_train_config_rejects_missing_key(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace("max_table_entries = 1000\n", ""),
    )

    with pytest.raises(ConfigError, match="max_table_entries"):
        load_train_config(path)


def test_load_train_config_rejects_unknown_key(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path, TRAIN_CONFIG_TEXT + "extra = 1\n"
    )

    with pytest.raises(ConfigError, match="extra"):
        load_train_config(path)


def test_load_train_config_rejects_bad_seed(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path, TRAIN_CONFIG_TEXT.replace("seed = 7", 'seed = "7"')
    )

    with pytest.raises(ConfigError, match="seed"):
        load_train_config(path)


def test_load_train_config_rejects_bad_episodes(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace("episodes = 20", "episodes = 15"),
    )

    with pytest.raises(ConfigError, match="episodes"):
        load_train_config(path)


def test_load_train_config_rejects_bad_alpha(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path, TRAIN_CONFIG_TEXT.replace("alpha = 0.1", "alpha = 0.0")
    )

    with pytest.raises(ConfigError, match="alpha"):
        load_train_config(path)


def test_load_train_config_rejects_bad_gamma(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path, TRAIN_CONFIG_TEXT.replace("gamma = 0.9", "gamma = 1.0")
    )

    with pytest.raises(ConfigError, match="gamma"):
        load_train_config(path)


def test_load_train_config_rejects_bad_epsilon(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace(
            "epsilon_start = 1.0", "epsilon_start = 0.05"
        ).replace("epsilon_end = 0.05", "epsilon_end = 1.0"),
    )

    with pytest.raises(ConfigError, match="epsilon"):
        load_train_config(path)


def test_load_train_config_rejects_bad_fraction(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace(
            "epsilon_decay_fraction = 0.8",
            "epsilon_decay_fraction = 1.1",
        ),
    )

    with pytest.raises(ConfigError, match="epsilon_decay_fraction"):
        load_train_config(path)


def test_load_train_config_rejects_zero_decay_fraction(
    tmp_path: Path,
) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace(
            "epsilon_decay_fraction = 0.8",
            "epsilon_decay_fraction = 0.0",
        ),
    )

    with pytest.raises(ConfigError, match="epsilon_decay_fraction"):
        load_train_config(path)


def test_load_train_config_rejects_bad_opponent(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace(
            'opponent = "random"', 'opponent = "greedy"'
        ),
    )

    with pytest.raises(ConfigError, match="opponent"):
        load_train_config(path)


def test_load_train_config_rejects_bad_output_dir(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace('output_dir = "out"', 'output_dir = ""'),
    )

    with pytest.raises(ConfigError, match="output_dir"):
        load_train_config(path)


def test_load_train_config_rejects_bad_cap(tmp_path: Path) -> None:
    path = write_train_config(
        tmp_path,
        TRAIN_CONFIG_TEXT.replace(
            "max_table_entries = 1000", "max_table_entries = 0"
        ),
    )

    with pytest.raises(ConfigError, match="max_table_entries"):
        load_train_config(path)


def test_load_train_config_rejects_invalid_toml(tmp_path: Path) -> None:
    path = write_train_config(tmp_path, "seed = [\n")

    with pytest.raises(ConfigError, match="config"):
        load_train_config(path)


def test_load_train_config_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config"):
        load_train_config(tmp_path / "missing.toml")
