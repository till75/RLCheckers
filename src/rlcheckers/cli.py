"""Command-line entry points.

``main`` exposes ``play-random`` with a required integer ``--seed``,
``evaluate`` with a required ``--config`` path, and ``train-q`` with a required
training ``--config`` path. ``play-random`` prints the seed, moves, outcome, and
ply count. ``evaluate`` loads the config, plays the matchup, writes the
artifacts, and prints the ten-line summary. ``train-q`` trains the Q-table, runs
the 1,000-game diagnostic, writes four artifacts, and prints the thirteen-line
summary. Argument errors exit through ``argparse`` with code ``2`` and usage on
stderr; runtime problems print ``error: <message>`` and return ``1``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from rlcheckers.agents import make_agent
from rlcheckers.agents.q_agent import QAgent
from rlcheckers.agents.random_agent import RandomAgent, play_random_game
from rlcheckers.config import load_eval_config, load_train_config
from rlcheckers.evaluation import (
    format_float,
    play_matchup,
    summarize,
    write_artifacts,
)
from rlcheckers.game.moves import format_move
from rlcheckers.training import (
    DIAGNOSTIC_GAMES,
    train_q,
    train_self_play,
    write_training_artifacts,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the rlcheckers command line."""
    arguments = list(sys.argv[1:]) if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog="rlcheckers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    play_random = subparsers.add_parser("play-random")
    play_random.add_argument("--seed", type=int, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--config", required=True)
    train_q = subparsers.add_parser("train-q")
    train_q.add_argument("--config", required=True)
    args = parser.parse_args(arguments)

    if args.command == "play-random":
        return _run_play_random(args.seed)
    if args.command == "train-q":
        return _run_train_q(args.config, arguments)
    return _run_evaluate(args.config, arguments)


def _run_play_random(seed: int) -> int:
    """Play one seeded random game and print its moves."""
    record = play_random_game(seed)
    print(f"seed: {seed}")
    for index, move in enumerate(record.moves, start=1):
        print(f"{index}. {format_move(move)}")
    print(f"result: {record.outcome.value}")
    print(f"plies: {record.plies}")
    return 0


def _run_evaluate(config_path: str, argv: Sequence[str]) -> int:
    """Run the evaluate subcommand."""
    try:
        config = load_eval_config(config_path)
        result = play_matchup(
            lambda seed: make_agent(config.agent, seed),
            lambda seed: make_agent(config.opponent, seed),
            seed=config.seed,
            games=config.games,
            agent_name=config.agent,
            opponent_name=config.opponent,
        )
        summary = summarize([game.outcome for game in result.games])
        write_artifacts(
            result,
            config,
            command_line=["rlcheckers", *argv],
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"agent: {config.agent}")
    print(f"opponent: {config.opponent}")
    print(f"seed: {config.seed}")
    print(f"games: {config.games}")
    print(f"wins: {summary.wins}")
    print(f"draws: {summary.draws}")
    print(f"losses: {summary.losses}")
    print(f"score: {format_float(summary.score)}")
    print(
        f"ci95: {format_float(summary.ci_low)}"
        f"..{format_float(summary.ci_high)}"
    )
    print(f"artifacts: {config.output_dir}")
    return 0


def _run_train_q(config_path: str, argv: Sequence[str]) -> int:
    """Run the train-q subcommand."""
    try:
        config = load_train_config(config_path)
        if config.opponent == "self":
            train_self_play(config)
            raise NotImplementedError(
                "self-play artifacts and summary are not implemented"
            )
        result = train_q(config)
        agent = QAgent(result.table)
        diagnostic = play_matchup(
            lambda seed: agent,
            lambda seed: RandomAgent(seed=seed),
            seed=config.seed,
            games=DIAGNOSTIC_GAMES,
            agent_name="q",
            opponent_name="random",
        )
        summary = summarize([game.outcome for game in diagnostic.games])
        write_training_artifacts(
            result,
            diagnostic,
            config,
            command_line=["rlcheckers", *argv],
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"episodes: {config.episodes}")
    print(f"seed: {config.seed}")
    print(f"table_size: {result.table.size()}")
    print(f"table_bytes: {result.table.estimated_memory_bytes()}")
    print("agent: q")
    print("opponent: random")
    print(f"games: {len(diagnostic.games)}")
    print(f"wins: {summary.wins}")
    print(f"draws: {summary.draws}")
    print(f"losses: {summary.losses}")
    print(f"score: {format_float(summary.score)}")
    print(
        f"ci95: {format_float(summary.ci_low)}"
        f"..{format_float(summary.ci_high)}"
    )
    print(f"artifacts: {config.output_dir}")
    return 0
