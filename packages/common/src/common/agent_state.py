"""
Represents the state of an agent, relayed by the game engine to the UIs
"""

from typing import Optional

import numpy as np

from common.convertible import Convertible
import common.protos.agent_state_pb2 as agent_state_pb2

class AgentState(Convertible):
    def __init__(
        self,
        id: int,
        position: np.typing.NDArray[np.float64],
        busy: bool,
        role: str = "",
        health: float = 1.0,
        current_action: str = "",
        action_time_remaining: float = 0.0,
        action_duration: float = 0.0,
        target: Optional[np.typing.NDArray[np.float64]] = None,
        failure: str = "",
        carrying: str = "",
    ):
        """
        Args:
            id (int): The agent's id.
            position (NDArray): The (x, y) position of the agent.
            busy (bool): Whether the agent is executing an action.
            role (str): The agent's role (e.g. "worker", "scout").
            health (float): 0.0 (destroyed) to 1.0 (full health).
            current_action (str): Kind of the current action ("" when idle).
            action_time_remaining (float): Seconds left on the timed part of the action.
            action_duration (float): Total seconds of the timed part of the action.
            target (Optional[NDArray]): Where the current action takes the agent.
            failure (str): Critical failure description ("" when healthy).
            carrying (str): Item being carried ("" when empty).
        """
        self.id = id
        self.position = position
        self.busy = busy
        self.role = role
        self.health = health
        self.current_action = current_action
        self.action_time_remaining = action_time_remaining
        self.action_duration = action_duration
        self.target = target
        self.failure = failure
        self.carrying = carrying

    def to_proto(self) -> agent_state_pb2.AgentState:
        proto = agent_state_pb2.AgentState()
        proto.id = self.id
        proto.position.x=self.position[0]
        proto.position.y=self.position[1]
        proto.busy = self.busy
        proto.role = self.role
        proto.health = self.health
        proto.current_action = self.current_action
        proto.action_time_remaining = self.action_time_remaining
        proto.action_duration = self.action_duration
        if self.target is not None:
            proto.has_target = True
            proto.target.x = self.target[0]
            proto.target.y = self.target[1]
        proto.failure = self.failure
        proto.carrying = self.carrying
        return proto

    @classmethod
    def from_proto(cls, proto: agent_state_pb2.AgentState) -> "AgentState":
        position = np.array([proto.position.x, proto.position.y], dtype=np.float64)
        target = (
            np.array([proto.target.x, proto.target.y], dtype=np.float64)
            if proto.has_target else None
        )
        return cls(
            id=proto.id,
            position=position,
            busy=proto.busy,
            role=proto.role,
            health=proto.health,
            current_action=proto.current_action,
            action_time_remaining=proto.action_time_remaining,
            action_duration=proto.action_duration,
            target=target,
            failure=proto.failure,
            carrying=proto.carrying,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentState":
        proto = agent_state_pb2.AgentState()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
