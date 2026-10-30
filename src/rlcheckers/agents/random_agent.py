"""Random move selection and seeded random play.

Each ``RandomAgent`` owns a private ``random.Random``. It rejects terminal
states and otherwise chooses uniformly from the state's legal moves; agents
with the same seed make the same choice from the same state. ``play_random_game``
uses one agent and one RNG stream for both colours, so a seed reproduces the
whole game.
"""

from __future__ import annotations

import random

from rlcheckers.game.board import Board
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameRecord, GameState

MAX_GAME_PLIES = 2000


class RandomAgent:
    """An agent that chooses uniformly from legal moves."""

    def __init__(self, seed: int | None = None) -> None:
        if seed is not None and not isinstance(seed, int):
            raise TypeError(
                f"seed must be an int or None, got {type(seed).__name__}"
            )
        self._random = random.Random(seed)

    def choose_move(self, state: GameState) -> Move:
        """Return a uniformly chosen legal move."""
        if state.is_terminal:
            raise ValueError(f"game is finished: {state.outcome.value}")
        return self._random.choice(state.legal_moves())


def play_random_game(seed: int) -> GameRecord:
    """Play one seeded random game from the initial position."""
    if not isinstance(seed, int):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")

    agent = RandomAgent(seed=seed)
    state = GameState.from_board(Board.initial())
    moves: list[Move] = []

    while not state.is_terminal:
        move = agent.choose_move(state)
        moves.append(move)
        state = state.apply(move)
        if len(moves) > MAX_GAME_PLIES:
            raise RuntimeError(
                f"game did not terminate within {MAX_GAME_PLIES} plies"
            )

    return GameRecord(tuple(moves), state)
