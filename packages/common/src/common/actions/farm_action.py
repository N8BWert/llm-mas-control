"""
Python representation of the farm action.
"""

from dataclasses import dataclass

from common.tile import Tile
from common.convertible import Convertible
import common.protos.actions.farm_action_pb2 as farm_action_pb2


@dataclass
class FarmAction(Convertible):
    """
    Action to farm at a given tile 
    """

    tile: Tile

    def to_proto(self) -> farm_action_pb2.FarmAction:
        return farm_action_pb2.FarmAction(
            farm_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: farm_action_pb2.FarmAction) -> "FarmAction":
        return cls(tile=Tile.from_proto(proto.farm_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "FarmAction":
        proto = farm_action_pb2.FarmAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
