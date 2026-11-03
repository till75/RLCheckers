from __future__ import annotations

import pytest

from rlcheckers.agents import Agent
from rlcheckers.evaluation.arena import ArenaResult, GameOutcome, play_matchup
from rlcheckers.evaluation.metrics import (
    format_float,
    summarize,
    summary_rows,
)
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


class FirstLegalAgent:
    def choose_move(self, state: GameState) -> Move:
        return state.legal_moves()[0]


def first_legal(seed: int) -> Agent:
    return FirstLegalAgent()


@pytest.fixture
def result() -> ArenaResult:
    return play_matchup(first_legal, first_legal, seed=7, games=10)


def test_summarize_counts_and_score() -> None:
    summary = summarize(
        [GameOutcome.WIN, GameOutcome.WIN, GameOutcome.DRAW, GameOutcome.LOSS]
    )

    assert summary.games == 4
    assert summary.wins == 2
    assert summary.draws == 1
    assert summary.losses == 1
    assert summary.score == pytest.approx(0.625)
    assert GameOutcome.WIN.score == 1.0
    assert GameOutcome.DRAW.score == 0.5
    assert GameOutcome.LOSS.score == 0.0


def test_summarize_confidence_interval() -> None:
    summary = summarize(
        [GameOutcome.WIN, GameOutcome.WIN, GameOutcome.DRAW, GameOutcome.LOSS]
    )

    assert summary.ci_low == pytest.approx(0.155855, abs=1e-3)
    assert summary.ci_high == 1.0


def test_summarize_clamps_interval() -> None:
    two = summarize([GameOutcome.WIN, GameOutcome.LOSS])

    assert two.score == pytest.approx(0.5)
    assert (two.ci_low, two.ci_high) == pytest.approx((0.0, 1.0))


def test_summarize_rejects_short_input() -> None:
    with pytest.raises(ValueError, match="at least two"):
        summarize([])

    with pytest.raises(ValueError, match="at least two"):
        summarize([GameOutcome.WIN])


def test_summary_rows_order(result: ArenaResult) -> None:
    rows = summary_rows(result)

    assert [(row.group, row.key) for row in rows] == [
        ("overall", ""),
        ("colour", "black"),
        ("colour", "white"),
        ("opening", "0"),
        ("opening", "1"),
        ("opening", "2"),
        ("opening", "3"),
        ("opening", "4"),
    ]
    assert all(row.summary.games >= 2 for row in rows)


def test_summary_rows_groups(result: ArenaResult) -> None:
    by_key = {
        (row.group, row.key): row.summary for row in summary_rows(result)
    }
    overall = by_key[("overall", "")]
    black = by_key[("colour", "black")]
    white = by_key[("colour", "white")]

    assert overall.games == 10
    assert black.games == 5
    assert white.games == 5
    assert black.wins + white.wins == overall.wins
    assert black.draws + white.draws == overall.draws
    assert black.losses + white.losses == overall.losses

    opening_wins = 0
    for index in range(5):
        opening = by_key[("opening", str(index))]
        assert opening.games == 2
        opening_wins += opening.wins
    assert opening_wins == overall.wins


def test_format_float() -> None:
    assert format_float(0.8) == "0.800000"
    assert format_float(1.0) == "1.000000"
