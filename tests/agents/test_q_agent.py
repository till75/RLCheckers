from __future__ import annotations

import json

import pytest

from rlcheckers.agents import (
    QAgent,
    QTable,
    QTableError,
    TableCapacityError,
    q_key,
)
from rlcheckers.game.board import (
    PLAYABLE_SQUARES,
    SQUARE_COUNT,
    Board,
    Piece,
    Side,
)
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState


def _initial_state() -> GameState:
    return GameState.from_board(Board.initial())


def _board_with(
    pieces: dict[int, Piece], side: Side = Side.BLACK
) -> Board:
    cells: list[Piece | None] = [None] * SQUARE_COUNT
    for square in PLAYABLE_SQUARES:
        cells[square] = pieces.get(square, Piece.EMPTY)
    return Board(tuple(cells), side)


def test_q_key_combines_state_and_action() -> None:
    state = _initial_state()
    move = Move((6, 10))

    assert q_key(state, move) == (state.board.state_key << 33) | move.action_key


def test_q_table_defaults_to_zero() -> None:
    state = _initial_state()
    key = q_key(state, Move((6, 10)))

    assert QTable().get(key) == 0.0


def test_q_table_set_and_get() -> None:
    state = _initial_state()
    key = q_key(state, Move((6, 10)))
    table = QTable()

    table.set(key, 0.5)
    table.set(key, 0.6)

    assert table.get(key) == 0.6
    assert table.size() == 1


def test_q_table_capacity_guard() -> None:
    state = _initial_state()
    key_one = q_key(state, Move((6, 10)))
    key_two = q_key(state, Move((8, 14)))
    key_three = q_key(state, Move((6, 12)))
    table = QTable(max_entries=2)

    table.set(key_one, 0.5)
    table.set(key_one, 0.6)
    table.set(key_two, -0.2)

    assert table.size() == 2
    with pytest.raises(TableCapacityError, match="cap"):
        table.set(key_three, 0.0)


def test_q_table_rejects_bad_cap() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        QTable(max_entries=0)

    with pytest.raises(ValueError, match="max_entries"):
        QTable(max_entries=True)


def test_q_table_rejects_non_finite() -> None:
    table = QTable()

    with pytest.raises(ValueError, match="finite"):
        table.set(1, float("nan"))

    with pytest.raises(ValueError, match="finite"):
        table.set(2, float("inf"))


def test_q_table_memory_estimate() -> None:
    assert QTable().estimated_memory_bytes() > 0


def test_q_table_clone_is_independent() -> None:
    table = QTable(max_entries=10)
    table.set(1, 0.25)
    table.set(2, -0.5)

    clone = table.clone()

    assert clone == table
    assert clone.max_entries == table.max_entries

    table.set(1, 0.75)
    table.set(3, 1.0)
    clone.set(2, 0.5)

    assert clone.get(1) == 0.25
    assert clone.get(2) == 0.5
    assert clone.get(3) == 0.0
    assert table.get(1) == 0.75
    assert table.get(2) == -0.5
    assert table.get(3) == 1.0


def test_q_table_clone_preserves_cap() -> None:
    empty = QTable(max_entries=2).clone()

    assert empty.size() == 0
    assert empty.max_entries == 2

    table = QTable(max_entries=2)
    table.set(1, 1.0)
    table.set(2, 2.0)
    clone = table.clone()

    clone.set(1, 3.0)

    with pytest.raises(TableCapacityError, match="cap"):
        clone.set(3, 0.0)

    assert clone.max_entries == 2
    assert table.get(1) == 1.0


def test_q_agent_picks_highest_value() -> None:
    state = _initial_state()
    table = QTable()
    best = Move((6, 10))
    table.set(q_key(state, best), 1.0)
    agent = QAgent(table)

    assert agent.table is table
    assert agent.choose_move(state) == best


def test_q_agent_tie_breaks_by_path() -> None:
    state = _initial_state()

    assert QAgent(QTable()).choose_move(state) == Move((6, 10))


def test_q_agent_returns_legal_move() -> None:
    state = _initial_state()

    assert QAgent(QTable()).choose_move(state) in state.legal_moves()


def test_q_agent_is_deterministic() -> None:
    state = _initial_state()
    agent = QAgent(QTable())

    assert agent.choose_move(state) == agent.choose_move(state)


def test_q_agent_rejects_finished_game() -> None:
    finished = GameState.from_board(
        _board_with({20: Piece.BLACK_KING})
    )

    with pytest.raises(ValueError, match="finished"):
        QAgent(QTable()).choose_move(finished)


def _q_table_artifact(
    tmp_path, *, max_entries: int = 1000
):
    metadata = {
        "config": {
            "alpha": 0.1,
            "epsilon_decay_fraction": 0.8,
            "epsilon_end": 0.05,
            "epsilon_start": 1.0,
            "episodes": 20,
            "gamma": 0.9,
            "max_table_entries": max_entries,
            "opponent": "random",
            "output_dir": "out",
            "seed": 7,
        },
        "package_version": "0.1.0",
        "python_version": "3.14.0",
        "seed": 7,
        "table_size": 2,
    }
    table = QTable(max_entries=max_entries)
    table.set(1, 0.25)
    table.set(2, -0.5)
    path = tmp_path / "q_table.json"
    table.save(path, metadata)
    return table, metadata, path


def test_q_table_save_load_round_trip(tmp_path) -> None:
    table, metadata, path = _q_table_artifact(tmp_path)

    loaded, loaded_metadata = QTable.load(path)

    assert loaded == table
    assert loaded_metadata == metadata
    assert loaded.get(1) == 0.25
    assert loaded.get(2) == -0.5


def test_q_table_json_schema(tmp_path) -> None:
    _, _, path = _q_table_artifact(tmp_path)

    document = json.loads(path.read_text(encoding="utf-8"))

    assert set(document) == {"format", "metadata", "table", "version"}
    assert document["format"] == "rlcheckers.qtable"
    assert document["version"] == 1
    assert set(document["table"]) == {"1", "2"}
    assert set(document["metadata"]) == {
        "config",
        "package_version",
        "python_version",
        "seed",
        "table_size",
    }


def test_q_table_save_is_byte_reproducible(tmp_path) -> None:
    table, metadata, path = _q_table_artifact(tmp_path)
    first = path.read_bytes()

    table.save(path, metadata)

    assert path.read_bytes() == first


def test_q_table_load_rejects_bad_format(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"format":"wrong","version":1,"metadata":{},"table":{}}',
        encoding="utf-8",
    )

    with pytest.raises(QTableError, match="format"):
        QTable.load(bad)


def test_q_table_load_uses_saved_cap(tmp_path) -> None:
    table, _, path = _q_table_artifact(tmp_path, max_entries=7)

    loaded, _ = QTable.load(path)

    assert loaded.max_entries == 7
    assert loaded == table
