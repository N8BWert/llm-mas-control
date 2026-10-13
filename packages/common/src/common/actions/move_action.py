"""
Python representation of the move action.
"""

from typing import ClassVar
from dataclasses import dataclass

import numpy as np

import common.protos.actions.move_action_pb2 as move_action_pb2
from common.convertible import Convertible
from common.position import Position
from common.actions.action import Action


@dataclass
class MoveAction(Action, Convertible):
    """
    Action to move to a given position.
    """
    # The tolerance for determining if the agent has reached the goal position.
    TOLERANCE: ClassVar[float] = 0.01

    position: np.typing.NDArray[np.float64]


    def time_left(self, current_tick: int) -> int:
        return 0

    def to_proto(self) -> move_action_pb2.MoveAction:
        return move_action_pb2.MoveAction(
            goal_position = Position.from_numpy(self.position).to_proto()
        )

    @classmethod
    def from_proto(cls, proto: move_action_pb2.MoveAction) -> "MoveAction":
        return cls(position=Position.from_proto(proto.goal_position).to_numpy())

    @classmethod
    def from_bytes(cls, data: bytes) -> "MoveAction":
        proto = move_action_pb2.MoveAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MoveAction):
            return False
        return np.array_equal(self.position, other.position)
