"""Evaluation arena, metrics, and artifacts."""

from rlcheckers.evaluation.arena import (
    STANDARD_OPENINGS,
    ArenaError,
    ArenaResult,
    GameOutcome,
    GameResult,
    derive_game_seed,
    derive_side_seed,
    opening_state,
    outcome_for,
    play_matchup,
)
from rlcheckers.evaluation.artifacts import (
    GAMES_FIELDS,
    METRICS_FIELDS,
    write_artifacts,
)
from rlcheckers.evaluation.metrics import (
    ScoreSummary,
    SummaryRow,
    format_float,
    summarize,
    summary_rows,
)

__all__ = [
    "GAMES_FIELDS",
    "METRICS_FIELDS",
    "STANDARD_OPENINGS",
    "ArenaError",
    "ArenaResult",
    "GameOutcome",
    "GameResult",
    "ScoreSummary",
    "SummaryRow",
    "derive_game_seed",
    "derive_side_seed",
    "format_float",
    "opening_state",
    "outcome_for",
    "play_matchup",
    "summarize",
    "summary_rows",
    "write_artifacts",
]
