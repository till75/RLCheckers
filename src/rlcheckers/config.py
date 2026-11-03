"""Evaluation configuration loading and validation.

``load_eval_config`` reads a TOML document with ``tomllib`` and returns an
immutable ``EvalConfig``. It validates exactly five top-level keys and resolves
a relative ``output_dir`` against the config file's directory. Loading does not
create the output directory. ``ConfigError`` subclasses ``ValueError`` so callers
do not need to import ``tomllib`` exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rlcheckers.evaluation.arena import STANDARD_OPENINGS

_GAME_CYCLE = 2 * len(STANDARD_OPENINGS)


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
    raise NotImplementedError
