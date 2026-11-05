"""Tabular Q-learning training loop.

The trainer owns exploration and updates; the Q-agent only plays. Public
signatures are added in TDD order.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from dataclasses import dataclass

from rlcheckers.agents.protocol import AgentFactory
from rlcheckers.agents.q_agent import QTable, q_key
from rlcheckers.agents.random_agent import MAX_GAME_PLIES, RandomAgent
from rlcheckers.config import TrainConfig
from rlcheckers.evaluation import (
    STANDARD_OPENINGS,
    GameOutcome,
    derive_side_seed,
    opening_state,
    outcome_for,
)
from rlcheckers.game.board import Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


def _random_opponent(seed: int) -> RandomAgent:
    return RandomAgent(seed=seed)


@dataclass(frozen=True)
class EpisodeMetric:
    """One training episode's identity and outcome."""

    episode: int
    opening_index: int
    learner_colour: Side
    outcome: GameOutcome
    plies: int
    epsilon: float
    table_size: int


@dataclass(frozen=True)
class TrainingResult:
    """The trained table, episode metrics, and opening suite."""

    table: QTable
    metrics: tuple[EpisodeMetric, ...]
    openings: tuple[tuple[Move, ...], ...]


def derive_episode_seed(master_seed: int, episode: int) -> int:
    """Derive one training episode's seed from the master seed."""
    if not isinstance(master_seed, int) or isinstance(master_seed, bool):
        raise TypeError(
            f"master_seed must be an int, got {type(master_seed).__name__}"
        )
    if (
        not isinstance(episode, int)
        or isinstance(episode, bool)
        or episode < 0
    ):
        raise ValueError(f"episode must be a non-negative int, got {episode!r}")

    payload = f"{master_seed}|train|{episode}"
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def reward_for(outcome: GameOutcome) -> float:
    """Return the terminal training reward for a learner outcome."""
    if outcome is GameOutcome.WIN:
        return 1.0
    if outcome is GameOutcome.DRAW:
        return 0.0
    if outcome is GameOutcome.LOSS:
        return -1.0
    raise ValueError(f"unknown game outcome: {outcome!r}")


def choose_epsilon_greedy(
    table: QTable,
    state: GameState,
    epsilon: float,
    rng: random.Random,
) -> Move:
    """Choose an exploratory or greedy legal move."""
    if state.is_terminal:
        raise ValueError(f"game is finished: {state.outcome.value}")
    if (
        not isinstance(epsilon, (int, float))
        or isinstance(epsilon, bool)
        or not 0 <= epsilon <= 1
    ):
        raise ValueError(f"epsilon must be in [0, 1], got {epsilon!r}")

    if rng.random() < epsilon:
        return rng.choice(state.legal_moves())
    return table.best_move(state)


def train_q(
    config: TrainConfig,
    *,
    openings: Sequence[Sequence[Move]] = STANDARD_OPENINGS,
    opponent_factory: AgentFactory | None = None,
) -> TrainingResult:
    """Train a Q-table against a fixed random opponent."""
    if (
        not isinstance(config.episodes, int)
        or isinstance(config.episodes, bool)
        or config.episodes <= 0
    ):
        raise ValueError(
            f"episodes must be a positive int, got {config.episodes!r}"
        )
    if not openings:
        raise ValueError("openings must be non-empty")
    if opponent_factory is None:
        opponent_factory = _random_opponent

    suite = tuple(tuple(opening) for opening in openings)
    table = QTable(max_entries=config.max_table_entries)
    metrics: list[EpisodeMetric] = []

    for episode in range(config.episodes):
        opening_index = (episode // 2) % len(suite)
        learner_colour = (
            Side.BLACK if episode % 2 == 0 else Side.WHITE
        )
        opponent_colour = (
            Side.WHITE if learner_colour is Side.BLACK else Side.BLACK
        )
        state = opening_state(suite[opening_index])
        epsilon = epsilon_at(
            episode,
            config.episodes,
            config.epsilon_start,
            config.epsilon_end,
            config.epsilon_decay_fraction,
        )
        episode_seed = derive_episode_seed(config.seed, episode)
        learner_seed = derive_side_seed(episode_seed, learner_colour)
        opponent_seed = derive_side_seed(episode_seed, opponent_colour)
        learner_rng = random.Random(learner_seed)
        opponent = opponent_factory(opponent_seed)

        plies = 0
        outcome: GameOutcome | None = None

        if state.board.side_to_move is not learner_colour:
            state = state.apply(opponent.choose_move(state))
            plies += 1
            if plies > MAX_GAME_PLIES:
                raise RuntimeError(
                    f"game did not terminate within {MAX_GAME_PLIES} plies"
                )
            if state.is_terminal:
                outcome = outcome_for(state.outcome, learner_colour)

        while outcome is None:
            learner_move = choose_epsilon_greedy(
                table, state, epsilon, learner_rng
            )
            key = q_key(state, learner_move)
            current = table.get(key)
            after = state.apply(learner_move)
            plies += 1
            if plies > MAX_GAME_PLIES:
                raise RuntimeError(
                    f"game did not terminate within {MAX_GAME_PLIES} plies"
                )

            if after.is_terminal:
                outcome = outcome_for(after.outcome, learner_colour)
                table.set(
                    key,
                    q_update(
                        current,
                        reward_for(outcome),
                        0.0,
                        config.alpha,
                        config.gamma,
                    ),
                )
                break

            opponent_move = opponent.choose_move(after)
            next_state = after.apply(opponent_move)
            plies += 1
            if plies > MAX_GAME_PLIES:
                raise RuntimeError(
                    f"game did not terminate within {MAX_GAME_PLIES} plies"
                )

            if next_state.is_terminal:
                outcome = outcome_for(next_state.outcome, learner_colour)
                table.set(
                    key,
                    q_update(
                        current,
                        reward_for(outcome),
                        0.0,
                        config.alpha,
                        config.gamma,
                    ),
                )
                break

            next_best = table.best_value(next_state)
            table.set(
                key,
                q_update(
                    current,
                    0.0,
                    next_best,
                    config.alpha,
                    config.gamma,
                ),
            )
            state = next_state

        assert outcome is not None
        metrics.append(
            EpisodeMetric(
                episode=episode,
                opening_index=opening_index,
                learner_colour=learner_colour,
                outcome=outcome,
                plies=plies,
                epsilon=epsilon,
                table_size=table.size(),
            )
        )

    return TrainingResult(
        table=table,
        metrics=tuple(metrics),
        openings=suite,
    )


def q_update(
    current: float,
    reward: float,
    next_best: float,
    alpha: float,
    gamma: float,
) -> float:
    """Return the one-step Q-learning update."""
    if (
        not isinstance(alpha, (int, float))
        or isinstance(alpha, bool)
        or not 0 < alpha <= 1
    ):
        raise ValueError(f"alpha must be in (0, 1], got {alpha!r}")
    if (
        not isinstance(gamma, (int, float))
        or isinstance(gamma, bool)
        or not 0 <= gamma < 1
    ):
        raise ValueError(f"gamma must be in [0, 1), got {gamma!r}")

    return current + alpha * (reward + gamma * next_best - current)


def epsilon_at(
    episode: int,
    episodes: int,
    start: float,
    end: float,
    decay_fraction: float,
) -> float:
    """Return the epsilon for a 0-based training episode."""
    if (
        not isinstance(episodes, int)
        or isinstance(episodes, bool)
        or episodes <= 0
    ):
        raise ValueError(f"episodes must be a positive int, got {episodes!r}")
    if (
        not isinstance(episode, int)
        or isinstance(episode, bool)
        or not 0 <= episode < episodes
    ):
        raise ValueError(
            f"episode must be in 0..{episodes - 1}, got {episode!r}"
        )

    for name, value in (("start", start), ("end", end)):
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0 <= value <= 1
        ):
            raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    if start < end:
        raise ValueError(f"start must be >= end, got {start!r} < {end!r}")
    if (
        not isinstance(decay_fraction, (int, float))
        or isinstance(decay_fraction, bool)
        or not 0 < decay_fraction <= 1
    ):
        raise ValueError(
            f"decay_fraction must be in (0, 1], got {decay_fraction!r}"
        )

    decay_episodes = max(1, int(episodes * decay_fraction))
    if episode >= decay_episodes:
        return float(end)
    return start + (end - start) * episode / decay_episodes
