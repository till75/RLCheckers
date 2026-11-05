from __future__ import annotations

import pytest

from rlcheckers.training import epsilon_at, q_update


def test_q_update_non_terminal() -> None:
    assert q_update(0.20, 0.0, 0.60, 0.1, 0.9) == pytest.approx(0.234)


def test_q_update_terminal_win() -> None:
    assert q_update(0.20, 1.0, 0.0, 0.1, 0.9) == pytest.approx(0.28)


def test_q_update_terminal_loss_and_draw() -> None:
    assert q_update(0.20, -1.0, 0.0, 0.1, 0.9) == pytest.approx(0.08)
    assert q_update(0.20, 0.0, 0.0, 0.1, 0.9) == pytest.approx(0.18)


def test_q_update_rejects_bad_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        q_update(0.2, 0.0, 0.6, 0.0, 0.9)


def test_q_update_rejects_bad_gamma() -> None:
    with pytest.raises(ValueError, match="gamma"):
        q_update(0.2, 0.0, 0.6, 0.1, 1.0)


def test_epsilon_schedule_starts_at_start() -> None:
    assert epsilon_at(0, 10, 1.0, 0.05, 0.8) == 1.0


def test_epsilon_schedule_reaches_end() -> None:
    assert epsilon_at(4, 10, 1.0, 0.05, 0.8) == pytest.approx(0.525)
    assert epsilon_at(8, 10, 1.0, 0.05, 0.8) == 0.05


def test_epsilon_schedule_stays_at_end() -> None:
    assert epsilon_at(9, 10, 1.0, 0.05, 0.8) == 0.05


def test_epsilon_schedule_rejects_zero_fraction() -> None:
    with pytest.raises(ValueError, match="decay_fraction"):
        epsilon_at(0, 10, 1.0, 0.05, 0.0)


def test_epsilon_schedule_rejects_bad_episode() -> None:
    with pytest.raises(ValueError, match="episode"):
        epsilon_at(-1, 10, 1.0, 0.05, 0.8)

    with pytest.raises(ValueError, match="episode"):
        epsilon_at(10, 10, 1.0, 0.05, 0.8)


def test_epsilon_schedule_rejects_inverted_endpoints() -> None:
    with pytest.raises(ValueError, match="start"):
        epsilon_at(0, 10, 0.01, 0.05, 0.8)
