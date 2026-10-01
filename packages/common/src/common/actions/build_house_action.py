"""
Python representation of the build house action.
"""

from dataclasses import dataclass

from common.tile import Tile
from common.convertible import Convertible
import common.protos.actions.build_house_action_pb2 as build_house_action_pb2


@dataclass
class BuildHouseAction(Convertible):
    """
    Action to build a house at a given tile 
    """
    
    tile: Tile

    def to_proto(self) -> build_house_action_pb2.BuildHouseAction:
        return build_house_action_pb2.BuildHouseAction(
            build_house_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: build_house_action_pb2.BuildHouseAction) -> "BuildHouseAction":
        return cls(tile=Tile.from_proto(proto.build_house_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "BuildHouseAction":
        proto = build_house_action_pb2.BuildHouseAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
