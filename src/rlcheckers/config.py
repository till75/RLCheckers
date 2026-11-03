"""Evaluation configuration loading and validation.

``load_eval_config`` reads a TOML document with ``tomllib`` and returns an
immutable ``EvalConfig``. It validates exactly five top-level keys and resolves
a relative ``output_dir`` against the config file's directory. Loading does not
create the output directory. ``ConfigError`` subclasses ``ValueError`` so callers
do not need to import ``tomllib`` exceptions.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from rlcheckers.agents import AGENT_NAMES
from rlcheckers.evaluation.arena import STANDARD_OPENINGS

_GAME_CYCLE = 2 * len(STANDARD_OPENINGS)
_CONFIG_KEYS = ("seed", "games", "agent", "opponent", "output_dir")


@dataclass(frozen=True)
class EvalConfig:
    """A validated evaluation configuration."""

    seed: int
    games: int
    agent: str
    opponent: str
    output_dir: Path


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
