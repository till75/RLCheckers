"""Artifact writing for evaluation runs.

``write_artifacts`` validates the result against the config, creates the output
directory, and writes ``metrics.csv``, ``games.csv``, and ``run.json``. The CSVs
use UTF-8 and ``lineterminator="\\n"`` so the bytes are stable across platforms.
``EvalConfig`` is imported only for type checking to avoid a runtime cycle:
``config.py`` imports the arena, so the arena and artifact modules must not
import ``config`` at runtime.
"""

from __future__ import annotations

import csv
import json
import platform
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import rlcheckers
from rlcheckers.evaluation.arena import ArenaResult, opening_state
from rlcheckers.evaluation.metrics import format_float, summary_rows

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
    if result.seed != config.seed or len(result.games) != config.games:
        raise ValueError(
            "result does not match config: "
            f"seed {result.seed} vs {config.seed}, "
            f"games {len(result.games)} vs {config.games}"
        )

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows = [
        {
            "seed": result.seed,
            "agent": config.agent,
            "opponent": config.opponent,
            "group": row.group,
            "key": row.key,
            "games": row.summary.games,
            "wins": row.summary.wins,
            "draws": row.summary.draws,
            "losses": row.summary.losses,
            "score": format_float(row.summary.score),
            "ci_low": format_float(row.summary.ci_low),
            "ci_high": format_float(row.summary.ci_high),
        }
        for row in summary_rows(result)
    ]
    with (output_dir / "metrics.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=METRICS_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(metrics_rows)

    games_rows = [
        {
            "seed": result.seed,
            "agent": config.agent,
            "opponent": config.opponent,
            "game_index": game.game_index,
            "pair_index": game.pair_index,
            "opening_index": game.opening_index,
            "agent_colour": game.agent_colour.name.lower(),
            "outcome": game.outcome.value,
            "plies": game.plies,
            "game_seed": game.game_seed,
            "final_state_key": game.final_state_key,
        }
        for game in result.games
    ]
    with (output_dir / "games.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=GAMES_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(games_rows)

    document = {
        "command_line": list(command_line),
        "config": {
            "agent": config.agent,
            "games": config.games,
            "opponent": config.opponent,
            "output_dir": str(config.output_dir),
            "seed": config.seed,
        },
        "openings": [
            {
                "index": index,
                "state_key": opening_state(opening).board.state_key,
            }
            for index, opening in enumerate(result.openings)
        ],
        "package_version": rlcheckers.__version__,
        "python_version": platform.python_version(),
    }
    (output_dir / "run.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return output_dir
