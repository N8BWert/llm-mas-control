"""
Represents the state of an agent, relayed by the game engine to the UIs
"""

import numpy as np

from common.convertible import Convertible
import common.protos.agent_state_pb2 as agent_state_pb2

class AgentState(Convertible):
    def __init__(self, id: int, position: np.typing.NDArray[np.float64], busy: bool):
        self.id = id
        self.position = position
        self.busy = busy

    def to_proto(self) -> agent_state_pb2.AgentState:
        proto = agent_state_pb2.AgentState()
        proto.id = self.id
        proto.position.x=self.position[0]
        proto.position.y=self.position[1]
        proto.busy = self.busy
        return proto

    @classmethod
    def from_proto(cls, proto: agent_state_pb2.AgentState) -> "AgentState":
        id = proto.id
        position = np.array([proto.position.x, proto.position.y], dtype=np.float64)
        busy = proto.busy
        return cls(id=id, position=position, busy=busy)

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentState":
        proto = agent_state_pb2.AgentState()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
