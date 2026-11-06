"""Three-seed gate aggregation and diagnostics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rlcheckers.evaluation.metrics import ScoreSummary

if TYPE_CHECKING:
    from rlcheckers.config import GateConfig
    from rlcheckers.training.self_play import SnapshotRecord

GATE_RANDOM_MEAN = 0.60
GATE_GREEDY_MEAN = 0.55
GATE_SEED_FLOOR = 0.50
_THRESHOLD_EPSILON = 1e-12


def _meets(value: float, threshold: float) -> bool:
    """Compare a score to a threshold without float-boundary surprises."""
    return value >= threshold - _THRESHOLD_EPSILON


@dataclass(frozen=True)
class GateMatchup:
    """One opponent's per-seed gate result."""

    opponent: str
    games: int
    unique_games: int
    overall: ScoreSummary
    black: ScoreSummary
    white: ScoreSummary
    ci_applicable: bool


@dataclass(frozen=True)
class SnapshotCurvePoint:
    """One snapshot's diagnostic scores against the gate baselines."""

    episode: int
    table_size: int
    random: ScoreSummary
    stochastic_greedy: ScoreSummary


@dataclass(frozen=True)
class SeedGateResult:
    """One training seed's gate matchups and snapshot curve."""

    seed: int
    table_size: int
    snapshots: tuple[SnapshotRecord, ...]
    matchups: Mapping[str, GateMatchup]
    snapshot_curve: tuple[SnapshotCurvePoint, ...]


@dataclass(frozen=True)
class GateResult:
    """The three-seed gate decision and its per-seed evidence."""

    config: GateConfig
    seeds: tuple[SeedGateResult, ...]
    random_mean: float
    random_min: float
    greedy_mean: float
    greedy_min: float
    passed: bool


def aggregate_gate(
    config: GateConfig,
    seeds: Sequence[SeedGateResult],
) -> GateResult:
    """Aggregate three seed results and apply the ADR 0003 thresholds."""
    random_scores = [
        seed.matchups["random"].overall.score for seed in seeds
    ]
    greedy_scores = [
        seed.matchups["stochastic_greedy"].overall.score
        for seed in seeds
    ]
    random_mean = sum(random_scores) / len(random_scores)
    random_min = min(random_scores)
    greedy_mean = sum(greedy_scores) / len(greedy_scores)
    greedy_min = min(greedy_scores)
    passed = (
        _meets(random_mean, GATE_RANDOM_MEAN)
        and _meets(greedy_mean, GATE_GREEDY_MEAN)
        and _meets(random_min, GATE_SEED_FLOOR)
        and _meets(greedy_min, GATE_SEED_FLOOR)
    )

    return GateResult(
        config=config,
        seeds=tuple(seeds),
        random_mean=random_mean,
        random_min=random_min,
        greedy_mean=greedy_mean,
        greedy_min=greedy_min,
        passed=passed,
    )
