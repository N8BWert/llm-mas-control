"""
Python representation of the build house action.
"""

from dataclasses import dataclass
from typing import ClassVar

import common.protos.actions.build_house_action_pb2 as build_house_action_pb2
from common.actions.action import Action
from common.convertible import Convertible
from common.tile import Tile


@dataclass
class BuildHouseAction(Action, Convertible):
    """
    Action to build a house at a given tile 
    """
    # The number of ticks required to build a house
    TIME_TO_BUILD: ClassVar[int] = 10
    # The number of points required to build a house
    POINTS_TO_BUILD: ClassVar[int] = 100
    
    tile: Tile

    def time_left(self, current_tick: int) -> int:
        return max(0, self.TIME_TO_BUILD - current_tick)

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BuildHouseAction):
            return False
        return self.tile == other.tile
