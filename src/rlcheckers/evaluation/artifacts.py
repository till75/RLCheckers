"""Artifact writing for evaluation runs.

``write_artifacts`` validates the result against the config, creates the output
directory, and writes ``metrics.csv``, ``games.csv``, and ``run.json``. The CSVs
use UTF-8 and ``lineterminator="\\n"`` so the bytes are stable across platforms.
``EvalConfig`` is imported only for type checking to avoid a runtime cycle:
``config.py`` imports the arena, so the arena and artifact modules must not
import ``config`` at runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from rlcheckers.evaluation.arena import ArenaResult

if TYPE_CHECKING:
    from rlcheckers.config import EvalConfig

METRICS_FIELDS = (
    "seed",
    "agent",
    "opponent",
    "group",
    "key",
    "games",
    "wins",
    "draws",
    "losses",
    "score",
    "ci_low",
    "ci_high",
)
GAMES_FIELDS = (
    "seed",
    "agent",
    "opponent",
    "game_index",
    "pair_index",
    "opening_index",
    "agent_colour",
    "outcome",
    "plies",
    "game_seed",
    "final_state_key",
)


def write_artifacts(
    result: ArenaResult,
    config: EvalConfig,
    *,
    command_line: Sequence[str],
) -> Path:
    """Write the run's CSV and JSON artifacts and return the output directory."""
    raise NotImplementedError
