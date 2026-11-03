from __future__ import annotations

from collections import Counter

import pytest

from rlcheckers.agents import Agent, make_agent
from rlcheckers.evaluation.arena import (
    STANDARD_OPENINGS,
    ArenaError,
    GameOutcome,
    derive_game_seed,
    derive_side_seed,
    opening_state,
    outcome_for,
    play_matchup,
)
from rlcheckers.game.board import Board, Side
from rlcheckers.game.moves import Move
from rlcheckers.game.state import GameState, Outcome


class FirstLegalAgent:
    def choose_move(self, state: GameState) -> Move:
        return state.legal_moves()[0]


def first_legal(seed: int) -> Agent:
    return FirstLegalAgent()


def test_standard_openings_are_legal() -> None:
    for moves in STANDARD_OPENINGS:
        opening_state(moves)


def test_standard_openings_are_distinct() -> None:
    keys = {
        opening_state(moves).board.state_key for moves in STANDARD_OPENINGS
    }
    assert len(keys) == 5


def test_standard_opening_state_keys() -> None:
    expected = (
        (Side.BLACK, 235602448969, 0),
        (Side.WHITE, 785358295113, 1),
        (Side.WHITE, 785360355913, 1),
        (Side.BLACK, 235206119497, 2),
        (Side.BLACK, 235554996809, 2),
    )

    for index, moves in enumerate(STANDARD_OPENINGS):
        state = opening_state(moves)
        side, key, no_progress = expected[index]
        assert state.board.side_to_move is side
        assert state.board.state_key == key
        assert state.no_progress_plies == no_progress
        assert state.position_keys[-1] == key


def test_standard_openings_are_not_terminal() -> None:
    for moves in STANDARD_OPENINGS:
        assert opening_state(moves).is_terminal is False


def test_opening_state_preserves_prefix_history() -> None:
    assert opening_state(STANDARD_OPENINGS[3]).position_keys == (
        Board.initial().state_key,
        opening_state((Move((6, 10)),)).board.state_key,
        235206119497,
    )


def test_matchup_plays_requested_games() -> None:
    result = play_matchup(first_legal, first_legal, seed=7, games=10)
    assert result.agent_name == "agent"
    assert result.opponent_name == "opponent"
    assert len(result.games) == 10


def test_matchup_assigns_sequential_indices() -> None:
    result = play_matchup(first_legal, first_legal, seed=7, games=10)
    assert [game.game_index for game in result.games] == list(range(10))


def test_matchup_pairs_openings() -> None:
    result = play_matchup(first_legal, first_legal, seed=7, games=10)
    assert [game.pair_index for game in result.games] == [
        0,
        0,
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        4,
    ]
    assert [game.opening_index for game in result.games] == [
        0,
        0,
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        4,
    ]


def test_matchup_alternates_colours() -> None:
    result = play_matchup(first_legal, first_legal, seed=7, games=10)
    assert [game.agent_colour for game in result.games] == [
        Side.BLACK,
        Side.WHITE,
    ] * 5


def test_matchup_swaps_agent_colours() -> None:
    agent_sides: list[Side] = []
    opponent_sides: list[Side] = []

    class TrackingAgent:
        def __init__(self, log: list[Side]) -> None:
            self.log = log

        def choose_move(self, state: GameState) -> Move:
            self.log.append(state.board.side_to_move)
            return state.legal_moves()[0]

    play_matchup(
        lambda seed: TrackingAgent(agent_sides),
        lambda seed: TrackingAgent(opponent_sides),
        seed=7,
        games=10,
    )

    assert set(agent_sides) == {Side.BLACK, Side.WHITE}
    assert set(opponent_sides) == {Side.BLACK, Side.WHITE}


def test_matchup_distributes_openings_evenly() -> None:
    result = play_matchup(first_legal, first_legal, seed=7, games=10)
    assert Counter(game.opening_index for game in result.games) == {
        0: 2,
        1: 2,
        2: 2,
        3: 2,
        4: 2,
    }
    assert Counter(game.agent_colour for game in result.games) == {
        Side.BLACK: 5,
        Side.WHITE: 5,
    }

    longer = play_matchup(first_legal, first_legal, seed=7, games=20)
    assert Counter(game.opening_index for game in longer.games) == {
        index: 4 for index in range(5)
    }
    assert all(game.plies > 0 for game in longer.games)
    assert all(game.outcome in tuple(GameOutcome) for game in longer.games)


def test_matchup_same_seed_is_reproducible() -> None:
    first = play_matchup(
        lambda seed: make_agent("random", seed),
        lambda seed: make_agent("greedy", seed),
        seed=7,
        games=10,
    )
    second = play_matchup(
        lambda seed: make_agent("random", seed),
        lambda seed: make_agent("greedy", seed),
        seed=7,
        games=10,
    )
    assert first == second


def test_outcome_for_perspective() -> None:
    assert outcome_for(Outcome.BLACK_WIN, Side.BLACK) is GameOutcome.WIN
    assert outcome_for(Outcome.BLACK_WIN, Side.WHITE) is GameOutcome.LOSS
    assert outcome_for(Outcome.WHITE_WIN, Side.WHITE) is GameOutcome.WIN
    assert outcome_for(Outcome.WHITE_WIN, Side.BLACK) is GameOutcome.LOSS
    assert outcome_for(Outcome.DRAW, Side.BLACK) is GameOutcome.DRAW
    assert outcome_for(Outcome.DRAW, Side.WHITE) is GameOutcome.DRAW

    with pytest.raises(ValueError, match="ongoing"):
        outcome_for(Outcome.ONGOING, Side.BLACK)


def test_matchup_rejects_illegal_move() -> None:
    class IllegalAgent:
        def choose_move(self, state: GameState) -> Move:
            return Move((0, 6))

    with pytest.raises(ArenaError, match="illegal"):
        play_matchup(
            lambda seed: IllegalAgent(),
            lambda seed: IllegalAgent(),
            seed=7,
            games=10,
        )


def test_matchup_rejects_bad_seed() -> None:
    with pytest.raises(TypeError, match="seed"):
        play_matchup(first_legal, first_legal, seed="7", games=10)


def test_matchup_rejects_bad_games() -> None:
    for games in (0, 9, 11, -10, True):
        with pytest.raises((TypeError, ValueError), match="games"):
            play_matchup(first_legal, first_legal, seed=7, games=games)


def test_matchup_rejects_duplicate_openings() -> None:
    with pytest.raises(ValueError, match="opening"):
        play_matchup(
            first_legal,
            first_legal,
            seed=7,
            games=4,
            openings=((), ()),
        )


def test_seed_helpers_are_stable() -> None:
    game_seed = derive_game_seed(7, 0, 0, Side.BLACK)
    assert game_seed == derive_game_seed(7, 0, 0, Side.BLACK)
    assert game_seed != derive_game_seed(7, 1, 0, Side.BLACK)


def test_side_seeds_differ() -> None:
    game_seed = derive_game_seed(7, 0, 0, Side.BLACK)
    assert derive_side_seed(game_seed, Side.BLACK) != derive_side_seed(
        game_seed, Side.WHITE
    )
