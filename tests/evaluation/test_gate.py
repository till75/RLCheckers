from __future__ import annotations

from pathlib import Path

import pytest

from rlcheckers.config import GateConfig
from rlcheckers.evaluation import (
    GameOutcome,
    GateMatchup,
    SeedGateResult,
    aggregate_gate,
    summarize,
)


def _summary(wins: int, draws: int = 0, losses: int = 0):
    outcomes = (
        [GameOutcome.WIN] * wins
        + [GameOutcome.DRAW] * draws
        + [GameOutcome.LOSS] * losses
    )
    return summarize(outcomes)


def _matchup(opponent: str, wins: int) -> GateMatchup:
    summary = _summary(wins, losses=1000 - wins)
    return GateMatchup(
        opponent=opponent,
        games=1000,
        unique_games=1000,
        overall=summary,
        black=summary,
        white=summary,
        ci_applicable=True,
    )


def _seed(
    seed: int,
    random_wins: int,
    greedy_wins: int,
) -> SeedGateResult:
    return SeedGateResult(
        seed=seed,
        table_size=100,
        snapshots=(),
        matchups={
            "random": _matchup("random", random_wins),
            "stochastic_greedy": _matchup(
                "stochastic_greedy", greedy_wins
            ),
        },
        snapshot_curve=(),
    )


def _gate_config(tmp_path: Path) -> GateConfig:
    return GateConfig(
        seeds=(7, 8, 9),
        eval_seed=7,
        episodes=10000,
        alpha=0.1,
        gamma=0.9,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_fraction=0.8,
        output_dir=tmp_path / "out",
        max_table_entries=2000000,
        snapshot_interval=1000,
        games=1000,
        snapshot_games=200,
        unique_games=10,
    )


def test_gate_aggregates_three_seeds(tmp_path: Path) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, 600, 550),
        _seed(8, 700, 650),
        _seed(9, 800, 750),
    )

    result = aggregate_gate(config, seeds)

    assert result.config == config
    assert result.seeds == seeds
    assert result.random_mean == pytest.approx(0.70)
    assert result.random_min == pytest.approx(0.60)
    assert result.greedy_mean == pytest.approx(0.65)
    assert result.greedy_min == pytest.approx(0.55)
    assert result.passed is True


def test_gate_passes_at_thresholds(tmp_path: Path) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, 600, 550),
        _seed(8, 500, 500),
        _seed(9, 700, 600),
    )

    result = aggregate_gate(config, seeds)

    assert result.random_mean == pytest.approx(0.60)
    assert result.random_min == pytest.approx(0.50)
    assert result.greedy_mean == pytest.approx(0.55)
    assert result.greedy_min == pytest.approx(0.50)
    assert result.passed is True


@pytest.mark.parametrize(
    ("middle_random", "middle_greedy"),
    [(490, 800), (800, 490)],
)
def test_gate_fails_below_floor(
    tmp_path: Path,
    middle_random: int,
    middle_greedy: int,
) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, 800, 800),
        _seed(8, middle_random, middle_greedy),
        _seed(9, 800, 800),
    )

    result = aggregate_gate(config, seeds)

    assert result.passed is False


@pytest.mark.parametrize(
    ("random_wins", "greedy_wins"),
    [(590, 800), (800, 540)],
)
def test_gate_fails_below_mean(
    tmp_path: Path,
    random_wins: int,
    greedy_wins: int,
) -> None:
    config = _gate_config(tmp_path)
    seeds = (
        _seed(7, random_wins, greedy_wins),
        _seed(8, random_wins, greedy_wins),
        _seed(9, random_wins, greedy_wins),
    )

    result = aggregate_gate(config, seeds)

    assert result.passed is False
