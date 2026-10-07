"""
Game State representation converted to and from the protobuf for
ease of use.
"""

import numpy as np
from typing import Optional

from common.convertible import Convertible
from common.agent_state import AgentState
from common.arena import Arena
from common.entity import Entity
from common.constraints import Constraint, ConstraintStatus
import common.protos.game_state_pb2 as game_state_pb2


class GameState(Convertible):
    """
    The current state of the game. 
    """

    def __init__(
        self,
        agent_states: list[AgentState],
        tile_states: np.typing.NDArray[np.uint8],
        width: Optional[int] = None,
        height: Optional[int] = None,
        points: int = 0,
        time_remaining: float = 0.0,
        elapsed_s: float = 0.0,
        round_index: int = 0,
        round_count: int = 0,
        round_name: str = "",
        game_over: bool = False,
        arena: Optional[Arena] = None,
        enemies: Optional[list[Entity]] = None,
        objectives: Optional[list[Entity]] = None,
        constraints: Optional[list[Constraint]] = None,
        constraint_statuses: Optional[list[ConstraintStatus]] = None,
    ):
        """
        Create a new GameState instance.

        Args:
            agent_states (list[AgentState]): The states of the agents in the game.
            tile_states (np.typing.NDArray[np.uint8]): The states of the tiles in the game
                (width, height).
            width (Optional[int], optional): The width of the game board. Defaults to None.
            height (Optional[int], optional): The height of the game board. Defaults to None.
            points (int, optional): The current points in the game. Defaults to 0.
            time_remaining (float): Seconds left in the current round.
            elapsed_s (float): Seconds since the current round started.
            round_index (int): Index of the current round.
            round_count (int): Total number of rounds.
            round_name (str): Display name of the current round.
            game_over (bool): Whether all rounds are finished.
            arena (Optional[Arena]): World bounds the tile grid spans.
            enemies (Optional[list[Entity]]): Enemy positions.
            objectives (Optional[list[Entity]]): Objective markers.
            constraints (Optional[list[Constraint]]): Currently active constraints.
            constraint_statuses (Optional[list[ConstraintStatus]]): Their live status.
        """
        self.agent_states = agent_states
        self.tile_states = tile_states
        self.points = points
        if width is None:
            width = tile_states.shape[0]
        if height is None:
            height = tile_states.shape[1]
        self.width = width
        self.height = height
        self.time_remaining = time_remaining
        self.elapsed_s = elapsed_s
        self.round_index = round_index
        self.round_count = round_count
        self.round_name = round_name
        self.game_over = game_over
        self.arena = arena or Arena()
        self.enemies = enemies or []
        self.objectives = objectives or []
        self.constraints = constraints or []
        self.constraint_statuses = constraint_statuses or []

    def to_proto(self) -> game_state_pb2.GameState:
        proto = game_state_pb2.GameState()
        proto.points = self.points
        proto.width = self.width
        proto.height = self.height
        proto.agent_states.extend([agent_state.to_proto() for agent_state in self.agent_states])
        proto.tiles.extend(self.tile_states.flatten())
        proto.time_remaining = self.time_remaining
        proto.elapsed_s = self.elapsed_s
        proto.round_index = self.round_index
        proto.round_count = self.round_count
        proto.round_name = self.round_name
        proto.game_over = self.game_over
        proto.arena.CopyFrom(self.arena.to_proto())
        proto.enemies.extend([e.to_proto() for e in self.enemies])
        proto.objectives.extend([o.to_proto() for o in self.objectives])
        proto.active_constraints.extend([c.to_proto() for c in self.constraints])
        proto.constraint_statuses.extend([s.to_proto() for s in self.constraint_statuses])
        return proto

    @classmethod
    def from_proto(cls, proto: game_state_pb2.GameState) -> "GameState":
        points = proto.points
        width = proto.width
        height = proto.height
        agent_states = [AgentState.from_proto(agent_state) for agent_state in proto.agent_states]
        tile_states = np.array(proto.tiles, dtype=np.uint8).reshape((width, height))
        return cls(
            agent_states=agent_states,
            tile_states=tile_states,
            width=width,
            height=height,
            points=points,
            time_remaining=proto.time_remaining,
            elapsed_s=proto.elapsed_s,
            round_index=proto.round_index,
            round_count=proto.round_count,
            round_name=proto.round_name,
            game_over=proto.game_over,
            arena=Arena.from_proto(proto.arena),
            enemies=[Entity.from_proto(e) for e in proto.enemies],
            objectives=[Entity.from_proto(o) for o in proto.objectives],
            constraints=[Constraint.from_proto(c) for c in proto.active_constraints],
            constraint_statuses=[ConstraintStatus.from_proto(s) for s in proto.constraint_statuses],
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "GameState":
        proto = game_state_pb2.GameState()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
