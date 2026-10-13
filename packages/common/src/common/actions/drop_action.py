"""
Python representation of the drop action.
"""

from dataclasses import dataclass
from typing import ClassVar

import common.protos.actions.drop_action_pb2 as drop_action_pb2
from common.actions.action import Action
from common.convertible import Convertible
from common.tile import Tile


@dataclass
class DropAction(Action, Convertible):
    """
    Action to drop an item at a given tile 
    """
    # The number of ticks required to drop an item
    TIME_TO_DROP: ClassVar[int] = 5

    tile: Tile

    def time_left(self, current_tick):
        return max(0, self.TIME_TO_DROP - current_tick)

    def to_proto(self) -> drop_action_pb2.DropAction:
        return drop_action_pb2.DropAction(
            drop_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: drop_action_pb2.DropAction) -> "DropAction":
        return cls(tile=Tile.from_proto(proto.drop_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "DropAction":
        proto = drop_action_pb2.DropAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DropAction):
            return False
        return self.tile == other.tile
