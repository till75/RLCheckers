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
