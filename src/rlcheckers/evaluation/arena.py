"""Evaluation arena data types and the seeded match loop.

``STANDARD_OPENINGS`` fixes the five move prefixes used by every S4 run. A
matchup schedules every opening with both agent colours, derives one base seed
per game from the master seed and the game's identity, and records one
``GameResult`` per game. The arena validates every agent move and never asks an
agent to move in a terminal state.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from rlcheckers.agents.protocol import AgentFactory
from rlcheckers.game.board import Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState, Outcome


class GameOutcome(Enum):
    """The result of one game from the agent-under-test perspective."""

    WIN = "win"
    DRAW = "draw"
    LOSS = "loss"

    @property
    def score(self) -> float:
        """Return the per-game score for this outcome."""
        raise NotImplementedError


@dataclass(frozen=True)
class GameResult:
    """One game's outcome and identity."""

    game_index: int
    pair_index: int
    opening_index: int
    agent_colour: Side
    outcome: GameOutcome
    plies: int
    game_seed: int
    final_state_key: int


@dataclass(frozen=True)
class ArenaResult:
    """A complete matchup and the opening suite it used."""

    agent_name: str
    opponent_name: str
    seed: int
    openings: tuple[tuple[Move, ...], ...]
    games: tuple[GameResult, ...]


STANDARD_OPENINGS: tuple[tuple[Move, ...], ...] = (
    (),
    (Move((6, 10)),),
    (Move((8, 14)),),
    (Move((6, 10)), Move((18, 14))),
    (Move((8, 14)), Move((16, 12))),
)


def opening_state(moves: Sequence[Move]) -> GameState:
    """Return the game state after applying an opening prefix."""
    raise NotImplementedError


def outcome_for(outcome: Outcome, agent_colour: Side) -> GameOutcome:
    """Map a board outcome to the agent-under-test perspective."""
    raise NotImplementedError


class ArenaError(RuntimeError):
    """Raised when an agent returns an illegal move."""


def play_matchup(
    agent_factory: AgentFactory,
    opponent_factory: AgentFactory,
    *,
    seed: int,
    games: int,
    agent_name: str = "agent",
    opponent_name: str = "opponent",
    openings: Sequence[Sequence[Move]] = STANDARD_OPENINGS,
) -> ArenaResult:
    """Play a seeded matchup and return its results."""
    raise NotImplementedError


def derive_game_seed(
    master_seed: int, pair_index: int, opening_index: int, agent_colour: Side
) -> int:
    """Derive one game's base seed from the run seed and game identity."""
    raise NotImplementedError


def derive_side_seed(game_seed: int, side: Side) -> int:
    """Derive one side's seed from a game seed."""
    raise NotImplementedError
