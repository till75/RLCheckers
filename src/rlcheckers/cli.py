"""Command-line entry points.

``main`` exposes ``play-random`` with a required integer ``--seed`` and
``evaluate`` with a required ``--config`` path. ``play-random`` prints the seed,
the formatted move list, the final outcome, and the ply count to stdout, then
returns ``0``. ``evaluate`` is wired to the evaluation modules and is not
implemented yet. Argument errors exit through ``argparse`` with code ``2`` and
usage on stderr.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from rlcheckers.agents.random_agent import play_random_game
from rlcheckers.game.moves import format_move


def main(argv: Sequence[str] | None = None) -> int:
    """Run the rlcheckers command line."""
    parser = argparse.ArgumentParser(prog="rlcheckers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    play_random = subparsers.add_parser("play-random")
    play_random.add_argument("--seed", type=int, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--config", required=True)
    args = parser.parse_args(argv)

    if args.command == "play-random":
        return _run_play_random(args.seed)
    return _run_evaluate(args.config)


def _run_play_random(seed: int) -> int:
    """Play one seeded random game and print its moves."""
    record = play_random_game(seed)
    print(f"seed: {seed}")
    for index, move in enumerate(record.moves, start=1):
        print(f"{index}. {format_move(move)}")
    print(f"result: {record.outcome.value}")
    print(f"plies: {record.plies}")
    return 0


def _run_evaluate(config_path: str) -> int:
    """Run the evaluate subcommand."""
    raise NotImplementedError
