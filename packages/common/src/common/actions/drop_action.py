"""
Python representation of the drop action.
"""

from dataclasses import dataclass

from common.tile import Tile
from common.convertible import Convertible
import common.protos.actions.drop_action_pb2 as drop_action_pb2


@dataclass
class DropAction(Convertible):
    """
    Action to drop an item at a given tile 
    """

    tile: Tile

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
