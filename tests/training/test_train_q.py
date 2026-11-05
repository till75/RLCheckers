from __future__ import annotations

import pytest

from rlcheckers.training import q_update


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
