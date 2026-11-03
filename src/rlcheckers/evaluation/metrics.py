"""Per-game scores and summary statistics for the evaluation arena.

``summarize`` turns a sequence of ``GameOutcome`` values into counts, the derived
score ``(wins + 0.5 * draws) / games``, and a two-sided 95% interval using the
normal approximation. ``summary_rows`` groups a matchup overall, by colour, and
by opening. No rounding happens here; CSV and display formatting do that.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt
from statistics import NormalDist

from rlcheckers.evaluation.arena import ArenaResult, GameOutcome
from rlcheckers.game.board import Side


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
    if len(outcomes) < 2:
        raise ValueError("summarize needs at least two games")

    scores = [outcome.score for outcome in outcomes]
    games = len(scores)
    wins = sum(1 for outcome in outcomes if outcome is GameOutcome.WIN)
    draws = sum(1 for outcome in outcomes if outcome is GameOutcome.DRAW)
    losses = sum(1 for outcome in outcomes if outcome is GameOutcome.LOSS)

    mean = sum(scores) / games
    variance = sum((score - mean) ** 2 for score in scores) / (games - 1)
    stderr = sqrt(variance / games)
    margin = NormalDist().inv_cdf(0.975) * stderr

    return ScoreSummary(
        games=games,
        wins=wins,
        draws=draws,
        losses=losses,
        score=mean,
        ci_low=max(0.0, mean - margin),
        ci_high=min(1.0, mean + margin),
    )


def summary_rows(result: ArenaResult) -> tuple[SummaryRow, ...]:
    """Return overall, per-colour, and per-opening summary rows."""
    games = result.games
    rows = [
        SummaryRow(
            "overall", "", summarize([game.outcome for game in games])
        ),
        SummaryRow(
            "colour",
            "black",
            summarize(
                [
                    game.outcome
                    for game in games
                    if game.agent_colour is Side.BLACK
                ]
            ),
        ),
        SummaryRow(
            "colour",
            "white",
            summarize(
                [
                    game.outcome
                    for game in games
                    if game.agent_colour is Side.WHITE
                ]
            ),
        ),
    ]

    for index in range(len(result.openings)):
        rows.append(
            SummaryRow(
                "opening",
                str(index),
                summarize(
                    [
                        game.outcome
                        for game in games
                        if game.opening_index == index
                    ]
                ),
            )
        )

    return tuple(rows)


def format_float(value: float) -> str:
    """Format a score or interval bound for CSV and stdout."""
    return f"{value:.6f}"
