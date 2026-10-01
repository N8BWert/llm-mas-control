"""
Python representation of the build quarry action.
"""

from dataclasses import dataclass

from common.tile import Tile
from common.convertible import Convertible
import common.protos.actions.build_quarry_action_pb2 as build_quarry_action_pb2


@dataclass
class BuildQuarryAction(Convertible):
    """
    Action to build a quarry at a given tile 
    """

    tile: Tile

    def to_proto(self) -> build_quarry_action_pb2.BuildQuarryAction:
        return build_quarry_action_pb2.BuildQuarryAction(
            build_quarry_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: build_quarry_action_pb2.BuildQuarryAction) -> "BuildQuarryAction":
        return cls(tile=Tile.from_proto(proto.build_quarry_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "BuildQuarryAction":
        proto = build_quarry_action_pb2.BuildQuarryAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
