"""Three-seed gate aggregation and diagnostics."""

from __future__ import annotations

import csv
import json
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

import rlcheckers
from rlcheckers.evaluation.metrics import ScoreSummary, format_float

if TYPE_CHECKING:
    from rlcheckers.agents.q_agent import QTable
    from rlcheckers.config import GateConfig
    from rlcheckers.training.self_play import SnapshotRecord

GATE_RANDOM_MEAN = 0.60
GATE_GREEDY_MEAN = 0.55
GATE_SEED_FLOOR = 0.50
GATE_CSV_FIELDS = (
    "seed",
    "opponent",
    "group",
    "key",
    "games",
    "unique_games",
    "wins",
    "draws",
    "losses",
    "score",
    "ci_low",
    "ci_high",
)
SNAPSHOT_CURVE_FIELDS = (
    "seed",
    "episode",
    "table_size",
    "opponent",
    "games",
    "unique_games",
    "wins",
    "draws",
    "losses",
    "score",
    "ci_low",
    "ci_high",
)
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
    table: QTable
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


def _config_dict(config: GateConfig) -> dict[str, object]:
    return {
        "seeds": list(config.seeds),
        "eval_seed": config.eval_seed,
        "episodes": config.episodes,
        "alpha": config.alpha,
        "gamma": config.gamma,
        "epsilon_start": config.epsilon_start,
        "epsilon_end": config.epsilon_end,
        "epsilon_decay_fraction": config.epsilon_decay_fraction,
        "output_dir": str(config.output_dir),
        "max_table_entries": config.max_table_entries,
        "snapshot_interval": config.snapshot_interval,
        "games": config.games,
        "snapshot_games": config.snapshot_games,
        "unique_games": config.unique_games,
    }


def _summary_dict(
    summary: ScoreSummary,
    ci_applicable: bool,
) -> dict[str, object]:
    return {
        "wins": summary.wins,
        "draws": summary.draws,
        "losses": summary.losses,
        "score": summary.score,
        "ci_low": summary.ci_low if ci_applicable else None,
        "ci_high": summary.ci_high if ci_applicable else None,
    }


def _matchup_dict(matchup: GateMatchup) -> dict[str, object]:
    return {
        "games": matchup.games,
        "unique_games": matchup.unique_games,
        "overall": _summary_dict(
            matchup.overall, matchup.ci_applicable
        ),
        "black": _summary_dict(matchup.black, matchup.ci_applicable),
        "white": _summary_dict(matchup.white, matchup.ci_applicable),
        "ci_applicable": matchup.ci_applicable,
    }


def _snapshot_dict(record: SnapshotRecord) -> dict[str, int]:
    return {
        "created_at_episode": record.created_at_episode,
        "first_episode": record.first_episode,
        "last_episode": record.last_episode,
        "table_size": record.table_size,
    }


def _curve_point_dict(point: SnapshotCurvePoint) -> dict[str, object]:
    return {
        "episode": point.episode,
        "table_size": point.table_size,
        "random": _summary_dict(point.random, True),
        "stochastic_greedy": _summary_dict(
            point.stochastic_greedy, True
        ),
    }


def _validate_gate_result(
    result: GateResult,
    config: GateConfig,
) -> None:
    if result.config != config:
        raise ValueError("gate result config does not match")
    if len(result.seeds) != 3:
        raise ValueError("gate result must have exactly three seeds")
    if tuple(seed.seed for seed in result.seeds) != config.seeds:
        raise ValueError("gate result seeds do not match config")
    for seed in result.seeds:
        if seed.table_size != seed.table.size():
            raise ValueError(
                f"seed {seed.seed} table_size does not match its table"
            )
        for name in ("random", "stochastic_greedy"):
            if name not in seed.matchups:
                raise ValueError(
                    f"seed {seed.seed} is missing {name} matchup"
                )
        if not seed.snapshot_curve:
            raise ValueError(
                f"seed {seed.seed} has an empty snapshot curve"
            )


def _write_snapshot_curve_plot(
    result: GateResult,
    path: Path,
) -> None:
    figure = Figure(figsize=(10, 4.5))
    FigureCanvasAgg(figure)
    axes = figure.subplots(1, 2)
    for axis, opponent in zip(
        axes, ("random", "stochastic_greedy")
    ):
        for seed in result.seeds:
            points = seed.snapshot_curve
            axis.plot(
                [point.episode for point in points],
                [
                    getattr(point, opponent).score
                    for point in points
                ],
                label=f"seed {seed.seed}",
            )
        axis.set_ylim(0, 1)
        axis.set_xlabel("episode")
        axis.set_ylabel("score")
        axis.set_title(opponent.replace("_", " ").title())
        axis.legend()
        axis.grid(True, alpha=0.3)
    figure.suptitle("Self-play snapshot learning curve")
    figure.tight_layout()
    figure.savefig(path, dpi=150)


def _write_report(result: GateResult, path: Path) -> None:
    lines = [
        "# S7 three-seed gate diagnostics",
        "",
        f"Gate: {'pass' if result.passed else 'fail'}",
        "",
        f"Random mean: {format_float(result.random_mean)}",
        f"Random min: {format_float(result.random_min)}",
        f"Stochastic greedy mean: {format_float(result.greedy_mean)}",
        f"Stochastic greedy min: {format_float(result.greedy_min)}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_gate_artifacts(
    result: GateResult,
    config: GateConfig,
    *,
    command_line: Sequence[str],
) -> Path:
    """Write the gate's Q-tables, summaries, plot, and report."""
    _validate_gate_result(result, config)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for seed in result.seeds:
        metadata = {
            "config": _config_dict(config),
            "package_version": rlcheckers.__version__,
            "python_version": platform.python_version(),
            "seed": seed.seed,
            "table_size": seed.table.size(),
        }
        seed.table.save(
            output_dir / f"q_table_seed_{seed.seed}.json",
            metadata,
        )

    document = {
        "command_line": list(command_line),
        "config": _config_dict(config),
        "gate": {
            "passed": result.passed,
            "random_mean": result.random_mean,
            "random_min": result.random_min,
            "greedy_mean": result.greedy_mean,
            "greedy_min": result.greedy_min,
            "thresholds": {
                "random_mean": GATE_RANDOM_MEAN,
                "greedy_mean": GATE_GREEDY_MEAN,
                "seed_floor": GATE_SEED_FLOOR,
            },
        },
        "seeds": [
            {
                "seed": seed.seed,
                "table_size": seed.table_size,
                "snapshots": [
                    _snapshot_dict(record)
                    for record in seed.snapshots
                ],
                "matchups": {
                    name: _matchup_dict(matchup)
                    for name, matchup in seed.matchups.items()
                },
                "snapshot_curve": [
                    _curve_point_dict(point)
                    for point in seed.snapshot_curve
                ],
            }
            for seed in result.seeds
        ],
        "package_version": rlcheckers.__version__,
        "python_version": platform.python_version(),
    }
    (output_dir / "gate.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    gate_rows = []
    for seed in result.seeds:
        for opponent, matchup in seed.matchups.items():
            for group, key, summary in (
                ("overall", "", matchup.overall),
                ("colour", "black", matchup.black),
                ("colour", "white", matchup.white),
            ):
                gate_rows.append(
                    {
                        "seed": seed.seed,
                        "opponent": opponent,
                        "group": group,
                        "key": key,
                        "games": matchup.games,
                        "unique_games": matchup.unique_games,
                        "wins": summary.wins,
                        "draws": summary.draws,
                        "losses": summary.losses,
                        "score": format_float(summary.score),
                        "ci_low": (
                            format_float(summary.ci_low)
                            if matchup.ci_applicable
                            else ""
                        ),
                        "ci_high": (
                            format_float(summary.ci_high)
                            if matchup.ci_applicable
                            else ""
                        ),
                    }
                )
    with (output_dir / "gate.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=GATE_CSV_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(gate_rows)

    curve_rows = []
    for seed in result.seeds:
        for point in seed.snapshot_curve:
            for opponent, summary in (
                ("random", point.random),
                ("stochastic_greedy", point.stochastic_greedy),
            ):
                curve_rows.append(
                    {
                        "seed": seed.seed,
                        "episode": point.episode,
                        "table_size": point.table_size,
                        "opponent": opponent,
                        "games": config.snapshot_games,
                        "unique_games": config.snapshot_games,
                        "wins": summary.wins,
                        "draws": summary.draws,
                        "losses": summary.losses,
                        "score": format_float(summary.score),
                        "ci_low": format_float(summary.ci_low),
                        "ci_high": format_float(summary.ci_high),
                    }
                )
    with (output_dir / "snapshot_curve.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SNAPSHOT_CURVE_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(curve_rows)

    _write_snapshot_curve_plot(
        result, output_dir / "snapshot_curve.png"
    )
    _write_report(
        result,
        output_dir / "s7-three-seed-gate-diagnostics.md",
    )
    return output_dir
