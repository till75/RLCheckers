"""Tabular Q-learning training loop.

The trainer owns exploration and updates; the Q-agent only plays. Public
signatures are added in TDD order.
"""

from __future__ import annotations


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
