"""
Python representation of the pick up action.
"""

from dataclasses import dataclass

import common.protos.actions.pick_up_action_pb2 as pick_up_action_pb2
from common.convertible import Convertible
from common.tile import Tile


@dataclass
class PickUpAction(Convertible):
    """
    Action to pick up an item at a given tile.
    """

    tile: Tile

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
