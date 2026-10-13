"""
Python representation of the pick up action.
"""

from dataclasses import dataclass
from typing import ClassVar

import common.protos.actions.pick_up_action_pb2 as pick_up_action_pb2
from common.actions.action import Action
from common.convertible import Convertible
from common.tile import Tile


@dataclass
class PickUpAction(Action, Convertible):
    """
    Action to pick up an item at a given tile.
    """
    # The number of ticks required to pick up an item
    TIME_TO_PICK_UP: ClassVar[int] = 5

    tile: Tile

    def time_left(self, current_tick: int) -> int:
        return max(0, self.TIME_TO_PICK_UP - current_tick)

    def to_proto(self) -> pick_up_action_pb2.PickUpAction:
        return pick_up_action_pb2.PickUpAction(
            pick_up_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: pick_up_action_pb2.PickUpAction) -> "PickUpAction":
        return cls(tile=Tile.from_proto(proto.pick_up_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "PickUpAction":
        proto = pick_up_action_pb2.PickUpAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PickUpAction):
            return False
        return self.tile == other.tile
