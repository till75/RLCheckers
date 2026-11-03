"""Shared agent protocol for the evaluation arena.

An agent receives the current ``GameState``, which carries the side to move. It
must return a legal move and must not mutate the state. Agents that use
randomness own a seeded RNG. ``AgentFactory`` is the arena's only dependency on
agent construction: it maps a seed to an agent and hides which implementation
was chosen.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


class Agent(Protocol):
    """An object that chooses a legal move for a game state."""

    def choose_move(self, state: GameState) -> Move:
        """Return a legal move for ``state``."""
        ...


AgentFactory = Callable[[int], Agent]
