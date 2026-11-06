"""Configuration loading and validation.

``load_eval_config`` reads the evaluation TOML schema and returns an immutable
``EvalConfig``. ``load_train_config`` reads the training schema and returns an
immutable ``TrainConfig``. A self-play training config requires a valid
``snapshot_interval``; a random-opponent config forbids that key. Both loaders
resolve a relative ``output_dir`` against the config file's directory and do not
create it. ``ConfigError`` subclasses ``ValueError`` so callers do not need to
import ``tomllib`` exceptions.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from rlcheckers.agents import AGENT_NAMES
from rlcheckers.evaluation.arena import STANDARD_OPENINGS

_GAME_CYCLE = 2 * len(STANDARD_OPENINGS)
_CONFIG_KEYS = ("seed", "games", "agent", "opponent", "output_dir")
_TRAIN_CONFIG_KEYS = (
    "seed",
    "episodes",
    "alpha",
    "gamma",
    "epsilon_start",
    "epsilon_end",
    "epsilon_decay_fraction",
    "opponent",
    "output_dir",
    "max_table_entries",
)
_TRAIN_CONFIG_OPTIONAL_KEYS = ("snapshot_interval",)
_GATE_CONFIG_KEYS = (
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
)


@dataclass(frozen=True)
class EvalConfig:
    """A validated evaluation configuration."""

    seed: int
    games: int
    agent: str
    opponent: str
    output_dir: Path


@dataclass(frozen=True)
class TrainConfig:
    """A training configuration; validation lives in ``load_train_config``."""

    seed: int
    episodes: int
    alpha: float
    gamma: float
    epsilon_start: float
    epsilon_end: float
    epsilon_decay_fraction: float
    opponent: str
    output_dir: Path
    max_table_entries: int
    snapshot_interval: int | None = None


@dataclass(frozen=True)
class GateConfig:
    """A three-seed gate configuration."""

    seeds: tuple[int, int, int]
    eval_seed: int
    episodes: int
    alpha: float
    gamma: float
    epsilon_start: float
    epsilon_end: float
    epsilon_decay_fraction: float
    output_dir: Path
    max_table_entries: int
    snapshot_interval: int
    games: int
    snapshot_games: int
    unique_games: int


class ConfigError(ValueError):
    """Raised when an evaluation config is invalid."""


def load_eval_config(path: str | Path) -> EvalConfig:
    """Load and validate an evaluation config from ``path``."""
    config_path = Path(path)
    try:
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {config_path}") from None
    except OSError as error:
        raise ConfigError(
            f"could not read config file {config_path}: {error}"
        ) from None
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(
            f"could not parse config {config_path}: {error}"
        ) from None

    if not isinstance(document, dict):
        raise ConfigError(
            f"config must be a table, got {type(document).__name__}"
        )

    unexpected = sorted(set(document) - set(_CONFIG_KEYS))
    if unexpected:
        raise ConfigError(
            f"unexpected config key(s): {', '.join(unexpected)}"
        )

    for key in _CONFIG_KEYS:
        if key not in document:
            raise ConfigError(f"missing config key: {key}")

    seed = document["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigError(
            f"config seed must be an int, got {type(seed).__name__}"
        )

    games = document["games"]
    if (
        not isinstance(games, int)
        or isinstance(games, bool)
        or games <= 0
        or games % _GAME_CYCLE != 0
    ):
        raise ConfigError(
            f"config games must be a positive multiple of {_GAME_CYCLE}, "
            f"got {games!r}"
        )

    for key in ("agent", "opponent"):
        value = document[key]
        if not isinstance(value, str) or value not in AGENT_NAMES:
            raise ConfigError(
                f"config {key} must be one of {AGENT_NAMES}, got {value!r}"
            )

    output_dir = document["output_dir"]
    if not isinstance(output_dir, str) or not output_dir:
        raise ConfigError(
            "config output_dir must be a non-empty string, "
            f"got {output_dir!r}"
        )

    resolved = Path(output_dir)
    if not resolved.is_absolute():
        resolved = config_path.parent / resolved
    resolved = resolved.resolve()

    return EvalConfig(
        seed=seed,
        games=games,
        agent=document["agent"],
        opponent=document["opponent"],
        output_dir=resolved,
    )


def load_train_config(path: str | Path) -> TrainConfig:
    """Load and validate a training config from ``path``."""
    config_path = Path(path)
    try:
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {config_path}") from None
    except OSError as error:
        raise ConfigError(
            f"could not read config file {config_path}: {error}"
        ) from None
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(
            f"could not parse config {config_path}: {error}"
        ) from None

    if not isinstance(document, dict):
        raise ConfigError(
            f"config must be a table, got {type(document).__name__}"
        )

    allowed = set(_TRAIN_CONFIG_KEYS) | set(_TRAIN_CONFIG_OPTIONAL_KEYS)
    unexpected = sorted(set(document) - allowed)
    if unexpected:
        raise ConfigError(
            f"unexpected config key(s): {', '.join(unexpected)}"
        )

    for key in _TRAIN_CONFIG_KEYS:
        if key not in document:
            raise ConfigError(f"missing config key: {key}")

    seed = document["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigError(
            f"config seed must be an int, got {type(seed).__name__}"
        )

    episodes = document["episodes"]
    if (
        not isinstance(episodes, int)
        or isinstance(episodes, bool)
        or episodes <= 0
        or episodes % 10 != 0
    ):
        raise ConfigError(
            "config episodes must be a positive multiple of 10, "
            f"got {episodes!r}"
        )

    numeric = {}
    for key in (
        "alpha",
        "gamma",
        "epsilon_start",
        "epsilon_end",
        "epsilon_decay_fraction",
    ):
        value = document[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfigError(
                f"config {key} must be a number, got {type(value).__name__}"
            )
        numeric[key] = float(value)

    alpha = numeric["alpha"]
    if not 0 < alpha <= 1:
        raise ConfigError(f"config alpha must be in (0, 1], got {alpha!r}")

    gamma = numeric["gamma"]
    if not 0 <= gamma < 1:
        raise ConfigError(f"config gamma must be in [0, 1), got {gamma!r}")

    for key in ("epsilon_start", "epsilon_end"):
        value = numeric[key]
        if not 0 <= value <= 1:
            raise ConfigError(
                f"config {key} must be in [0, 1], got {value!r}"
            )
    if numeric["epsilon_start"] < numeric["epsilon_end"]:
        raise ConfigError(
            "config epsilon_start must be >= epsilon_end, "
            f"got {numeric['epsilon_start']!r} < "
            f"{numeric['epsilon_end']!r}"
        )

    decay_fraction = numeric["epsilon_decay_fraction"]
    if not 0 < decay_fraction <= 1:
        raise ConfigError(
            "config epsilon_decay_fraction must be in (0, 1], "
            f"got {decay_fraction!r}"
        )

    opponent = document["opponent"]
    if opponent not in ("random", "self"):
        raise ConfigError(
            "config opponent must be 'random' or 'self', "
            f"got {opponent!r}"
        )

    output_dir = document["output_dir"]
    if not isinstance(output_dir, str) or not output_dir:
        raise ConfigError(
            "config output_dir must be a non-empty string, "
            f"got {output_dir!r}"
        )
    resolved = Path(output_dir)
    if not resolved.is_absolute():
        resolved = config_path.parent / resolved
    resolved = resolved.resolve()

    max_table_entries = document["max_table_entries"]
    if (
        not isinstance(max_table_entries, int)
        or isinstance(max_table_entries, bool)
        or max_table_entries <= 0
    ):
        raise ConfigError(
            "config max_table_entries must be a positive int, "
            f"got {max_table_entries!r}"
        )

    snapshot_interval: int | None = None
    if opponent == "random":
        if "snapshot_interval" in document:
            raise ConfigError(
                "config snapshot_interval must be absent when "
                "opponent is 'random'"
            )
    else:
        if "snapshot_interval" not in document:
            raise ConfigError("missing config key: snapshot_interval")
        value = document["snapshot_interval"]
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 10
            or value % 10 != 0
        ):
            raise ConfigError(
                "config snapshot_interval must be a multiple of 10 "
                f"and at least 10, got {value!r}"
            )
        if value >= episodes:
            raise ConfigError(
                "config snapshot_interval must be less than episodes, "
                f"got {value!r} >= {episodes!r}"
            )
        snapshot_interval = value

    return TrainConfig(
        seed=seed,
        episodes=episodes,
        alpha=alpha,
        gamma=gamma,
        epsilon_start=numeric["epsilon_start"],
        epsilon_end=numeric["epsilon_end"],
        epsilon_decay_fraction=decay_fraction,
        opponent=opponent,
        output_dir=resolved,
        max_table_entries=max_table_entries,
        snapshot_interval=snapshot_interval,
    )


def load_gate_config(path: str | Path) -> GateConfig:
    """Load and validate a three-seed gate config from ``path``."""
    config_path = Path(path)
    with config_path.open("rb") as handle:
        document = tomllib.load(handle)

    if not isinstance(document, dict):
        raise ConfigError(
            f"config must be a table, got {type(document).__name__}"
        )

    unexpected = sorted(set(document) - set(_GATE_CONFIG_KEYS))
    if unexpected:
        raise ConfigError(
            f"unexpected config key(s): {', '.join(unexpected)}"
        )

    for key in _GATE_CONFIG_KEYS:
        if key not in document:
            raise ConfigError(f"missing config key: {key}")

    seeds = document["seeds"]
    if (
        not isinstance(seeds, list)
        or len(seeds) != 3
        or any(
            not isinstance(seed, int) or isinstance(seed, bool)
            for seed in seeds
        )
        or len(set(seeds)) != 3
    ):
        raise ConfigError(
            "config seeds must be three distinct ints, "
            f"got {seeds!r}"
        )

    eval_seed = document["eval_seed"]
    if not isinstance(eval_seed, int) or isinstance(eval_seed, bool):
        raise ConfigError(
            f"config eval_seed must be an int, got {type(eval_seed).__name__}"
        )

    episodes = document["episodes"]
    if (
        not isinstance(episodes, int)
        or isinstance(episodes, bool)
        or episodes <= 0
        or episodes % 10 != 0
    ):
        raise ConfigError(
            "config episodes must be a positive multiple of 10, "
            f"got {episodes!r}"
        )

    numeric = {}
    for key in (
        "alpha",
        "gamma",
        "epsilon_start",
        "epsilon_end",
        "epsilon_decay_fraction",
    ):
        value = document[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfigError(
                f"config {key} must be a number, got {type(value).__name__}"
            )
        numeric[key] = float(value)

    alpha = numeric["alpha"]
    if not 0 < alpha <= 1:
        raise ConfigError(f"config alpha must be in (0, 1], got {alpha!r}")

    gamma = numeric["gamma"]
    if not 0 <= gamma < 1:
        raise ConfigError(f"config gamma must be in [0, 1), got {gamma!r}")

    for key in ("epsilon_start", "epsilon_end"):
        value = numeric[key]
        if not 0 <= value <= 1:
            raise ConfigError(
                f"config {key} must be in [0, 1], got {value!r}"
            )
    if numeric["epsilon_start"] < numeric["epsilon_end"]:
        raise ConfigError(
            "config epsilon_start must be >= epsilon_end, "
            f"got {numeric['epsilon_start']!r} < "
            f"{numeric['epsilon_end']!r}"
        )

    decay_fraction = numeric["epsilon_decay_fraction"]
    if not 0 < decay_fraction <= 1:
        raise ConfigError(
            "config epsilon_decay_fraction must be in (0, 1], "
            f"got {decay_fraction!r}"
        )

    output_dir = document["output_dir"]
    if not isinstance(output_dir, str) or not output_dir:
        raise ConfigError(
            "config output_dir must be a non-empty string, "
            f"got {output_dir!r}"
        )
    resolved = Path(output_dir)
    if not resolved.is_absolute():
        resolved = config_path.parent / resolved
    resolved = resolved.resolve()

    max_table_entries = document["max_table_entries"]
    if (
        not isinstance(max_table_entries, int)
        or isinstance(max_table_entries, bool)
        or max_table_entries <= 0
    ):
        raise ConfigError(
            "config max_table_entries must be a positive int, "
            f"got {max_table_entries!r}"
        )

    snapshot_interval = document["snapshot_interval"]
    if (
        not isinstance(snapshot_interval, int)
        or isinstance(snapshot_interval, bool)
        or snapshot_interval < 10
        or snapshot_interval % 10 != 0
    ):
        raise ConfigError(
            "config snapshot_interval must be a multiple of 10 "
            f"and at least 10, got {snapshot_interval!r}"
        )
    if snapshot_interval >= episodes:
        raise ConfigError(
            "config snapshot_interval must be less than episodes, "
            f"got {snapshot_interval!r} >= {episodes!r}"
        )

    for key in ("games", "snapshot_games", "unique_games"):
        value = document[key]
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
            or value % 10 != 0
        ):
            raise ConfigError(
                f"config {key} must be a positive multiple of 10, "
                f"got {value!r}"
            )

    return GateConfig(
        seeds=tuple(seeds),
        eval_seed=eval_seed,
        episodes=episodes,
        alpha=alpha,
        gamma=gamma,
        epsilon_start=numeric["epsilon_start"],
        epsilon_end=numeric["epsilon_end"],
        epsilon_decay_fraction=decay_fraction,
        output_dir=resolved,
        max_table_entries=max_table_entries,
        snapshot_interval=snapshot_interval,
        games=document["games"],
        snapshot_games=document["snapshot_games"],
        unique_games=document["unique_games"],
    )
