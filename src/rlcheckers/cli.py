"""Command-line entry points.

``main`` exposes one required subcommand, ``play-random``, with a required
integer ``--seed``. On success it prints the seed, the formatted move list, the
final outcome, and the ply count to stdout, then returns ``0``. Argument errors
exit through ``argparse`` with code ``2`` and usage on stderr.
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
    args = parser.parse_args(argv)

    record = play_random_game(args.seed)
    print(f"seed: {args.seed}")
    for index, move in enumerate(record.moves, start=1):
        print(f"{index}. {format_move(move)}")
    print(f"result: {record.outcome.value}")
    print(f"plies: {record.plies}")
    return 0
