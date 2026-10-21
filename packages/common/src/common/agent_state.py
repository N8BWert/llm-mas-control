"""
Represents the state of an agent, relayed by the game engine to the UIs
"""

import numpy as np

import common.protos.agent_state_pb2 as agent_state_pb2
from common.convertible import Convertible


class AgentState(Convertible):
    def __init__(
        self,
        id: int,
        position: np.typing.NDArray[np.float64],
        orientation: float,
        busy: bool,
        carrying_apple: bool
    ):
        self.id = id
        self.position = position
        self.orientation = orientation
        self.busy = busy
        self.carrying_apple = carrying_apple

    def to_proto(self) -> agent_state_pb2.AgentState:
        proto = agent_state_pb2.AgentState()
        proto.id = self.id
        proto.position.x=self.position[0]
        proto.position.y=self.position[1]
        proto.orientation = self.orientation
        proto.busy = self.busy
        proto.carrying_apple = self.carrying_apple
        return proto

    @classmethod
    def from_proto(cls, proto: agent_state_pb2.AgentState) -> "AgentState":
        id = proto.id
        position = np.array([proto.position.x, proto.position.y], dtype=np.float64)
        orientation = proto.orientation
        busy = proto.busy
        carrying_apple = proto.carrying_apple
        return cls(id=id, position=position, orientation=orientation, busy=busy, carrying_apple=carrying_apple)

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentState":
        proto = agent_state_pb2.AgentState()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def __repr__(self):
        return f"AgentState(id={self.id}, position={self.position}, orientation={self.orientation}, busy={self.busy}, carrying_apple={self.carrying_apple})"
