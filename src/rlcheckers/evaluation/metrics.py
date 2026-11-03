"""Per-game scores and summary statistics for the evaluation arena.

``summarize`` turns a sequence of ``GameOutcome`` values into counts, the derived
score ``(wins + 0.5 * draws) / games``, and a two-sided 95% interval using the
normal approximation. ``summary_rows`` groups a matchup overall, by colour, and
by opening. No rounding happens here; CSV and display formatting do that.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rlcheckers.evaluation.arena import ArenaResult, GameOutcome


@dataclass(frozen=True)
class ScoreSummary:
    """Win/draw/loss counts, derived score, and 95% interval."""

    games: int
    wins: int
    draws: int
    losses: int
    score: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class SummaryRow:
    """One labelled summary row."""

    group: str
    key: str
    summary: ScoreSummary


def summarize(outcomes: Sequence[GameOutcome]) -> ScoreSummary:
    """Summarize a sequence of per-game outcomes."""
    raise NotImplementedError


def summary_rows(result: ArenaResult) -> tuple[SummaryRow, ...]:
    """Return overall, per-colour, and per-opening summary rows."""
    raise NotImplementedError


def format_float(value: float) -> str:
    """Format a score or interval bound for CSV and stdout."""
    raise NotImplementedError
