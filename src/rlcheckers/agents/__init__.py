"""Agents that choose moves."""

from rlcheckers.agents.greedy_agent import GreedyAgent, material_balance
from rlcheckers.agents.protocol import Agent, AgentFactory
from rlcheckers.agents.q_agent import (
    QAgent,
    QTable,
    QTableError,
    TableCapacityError,
    q_key,
)
from rlcheckers.agents.random_agent import (
    MAX_GAME_PLIES,
    RandomAgent,
    play_random_game,
)

AGENT_NAMES = ("greedy", "random")


def make_agent(name: str, seed: int) -> Agent:
    """Return an agent by registry name."""
    if name == "random":
        return RandomAgent(seed=seed)
    if name == "greedy":
        return GreedyAgent()
    raise ValueError(f"unknown agent: {name!r}")


__all__ = [
    "AGENT_NAMES",
    "MAX_GAME_PLIES",
    "Agent",
    "AgentFactory",
    "GreedyAgent",
    "QAgent",
    "QTable",
    "QTableError",
    "RandomAgent",
    "TableCapacityError",
    "make_agent",
    "material_balance",
    "play_random_game",
    "q_key",
]
