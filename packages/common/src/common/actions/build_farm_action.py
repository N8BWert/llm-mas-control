"""
Python representation of the build farm action.
"""

from dataclasses import dataclass

from common.tile import Tile
from common.convertible import Convertible
import common.protos.actions.build_farm_action_pb2 as build_farm_action_pb2


@dataclass
class BuildFarmAction(Convertible):
    """
    Action to build a farm at a given tile 
    """

    tile: Tile

    def to_proto(self) -> build_farm_action_pb2.BuildFarmAction:
        return build_farm_action_pb2.BuildFarmAction(
            build_farm_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: build_farm_action_pb2.BuildFarmAction) -> "BuildFarmAction":
        return cls(tile=Tile.from_proto(proto.build_farm_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "BuildFarmAction":
        proto = build_farm_action_pb2.BuildFarmAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
