"""
Game State representation converted to and from the protobuf for
ease of use.
"""

from typing import Optional

import numpy as np

import common.protos.game_state_pb2 as game_state_pb2
from common.agent_state import AgentState
from common.convertible import Convertible


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

    def to_proto(self) -> game_state_pb2.GameState:
        proto = game_state_pb2.GameState()
        proto.points = self.points
        proto.width = self.width
        proto.height = self.height
        proto.agent_states.extend([agent_state.to_proto() for agent_state in self.agent_states])
        proto.tiles.extend(self.tile_states.flatten())
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
            points=points
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "GameState":
        proto = game_state_pb2.GameState()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
