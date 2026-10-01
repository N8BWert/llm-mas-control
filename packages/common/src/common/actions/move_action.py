"""
Python representation of the move action.
"""

import numpy as np
from dataclasses import dataclass

from common.position import Position
from common.convertible import Convertible
import common.protos.actions.move_action_pb2 as move_action_pb2


@dataclass
class MoveAction(Convertible):
    """
    Action to move to a given position.
    """

    position: np.typing.NDArray[np.float64]

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
