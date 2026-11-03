"""Evaluation arena data types and the seeded match loop.

``STANDARD_OPENINGS`` fixes the five move prefixes used by every S4 run. A
matchup schedules every opening with both agent colours, derives one base seed
per game from the master seed and the game's identity, and records one
``GameResult`` per game. The arena validates every agent move and never asks an
agent to move in a terminal state.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from rlcheckers.agents.protocol import AgentFactory
from rlcheckers.agents.random_agent import MAX_GAME_PLIES
from rlcheckers.game.board import Board, Side
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
    state = GameState.from_board(Board.initial())
    for move in moves:
        state = state.apply(move)
    return state


def outcome_for(outcome: Outcome, agent_colour: Side) -> GameOutcome:
    """Map a board outcome to the agent-under-test perspective."""
    if outcome is Outcome.ONGOING:
        raise ValueError("outcome is ongoing")
    if outcome is Outcome.DRAW:
        return GameOutcome.DRAW

    agent_won = (
        outcome is Outcome.BLACK_WIN and agent_colour is Side.BLACK
    ) or (
        outcome is Outcome.WHITE_WIN and agent_colour is Side.WHITE
    )
    return GameOutcome.WIN if agent_won else GameOutcome.LOSS


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
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")

    if not openings:
        raise ValueError("openings must be non-empty")

    cycle = 2 * len(openings)
    if (
        not isinstance(games, int)
        or isinstance(games, bool)
        or games <= 0
        or games % cycle != 0
    ):
        raise ValueError(
            f"games must be a positive multiple of {cycle}, got {games!r}"
        )

    opening_states: list[GameState] = []
    seen_keys: set[int] = set()
    for index, opening in enumerate(openings):
        try:
            state = opening_state(opening)
        except ValueError as error:
            raise ValueError(f"opening {index} is illegal: {error}") from None
        if state.is_terminal:
            raise ValueError(f"opening {index} is terminal")
        key = state.board.state_key
        if key in seen_keys:
            raise ValueError(f"duplicate opening state key at index {index}")
        seen_keys.add(key)
        opening_states.append(state)

    results: list[GameResult] = []
    for pair_index in range(games // 2):
        for offset in (0, 1):
            game_index = 2 * pair_index + offset
            opening_index = pair_index % len(openings)
            agent_colour = Side.BLACK if offset == 0 else Side.WHITE
            opponent_colour = (
                Side.WHITE if agent_colour is Side.BLACK else Side.BLACK
            )
            game_seed = derive_game_seed(
                seed, pair_index, opening_index, agent_colour
            )
            agent = agent_factory(derive_side_seed(game_seed, agent_colour))
            opponent = opponent_factory(
                derive_side_seed(game_seed, opponent_colour)
            )
            if agent_colour is Side.BLACK:
                black_agent, white_agent = agent, opponent
            else:
                black_agent, white_agent = opponent, agent

            state = opening_states[opening_index]
            plies = 0
            while not state.is_terminal:
                active = (
                    black_agent
                    if state.board.side_to_move is Side.BLACK
                    else white_agent
                )
                move = active.choose_move(state)
                if move not in state.legal_moves():
                    raise ArenaError(
                        f"game {game_index}: agent returned an illegal move "
                        f"{move!r}"
                    )
                state = state.apply(move)
                plies += 1
                if plies > MAX_GAME_PLIES:
                    raise RuntimeError(
                        f"game {game_index} did not terminate within "
                        f"{MAX_GAME_PLIES} plies"
                    )

            results.append(
                GameResult(
                    game_index=game_index,
                    pair_index=pair_index,
                    opening_index=opening_index,
                    agent_colour=agent_colour,
                    outcome=outcome_for(state.outcome, agent_colour),
                    plies=plies,
                    game_seed=game_seed,
                    final_state_key=state.board.state_key,
                )
            )

    return ArenaResult(
        agent_name=agent_name,
        opponent_name=opponent_name,
        seed=seed,
        openings=tuple(tuple(opening) for opening in openings),
        games=tuple(results),
    )


def derive_game_seed(
    master_seed: int, pair_index: int, opening_index: int, agent_colour: Side
) -> int:
    """Derive one game's base seed from the run seed and game identity."""
    payload = f"{master_seed}|{pair_index}|{opening_index}|{agent_colour.name}"
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def derive_side_seed(game_seed: int, side: Side) -> int:
    """Derive one side's seed from a game seed."""
    payload = f"{game_seed}|{side.name}"
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")
