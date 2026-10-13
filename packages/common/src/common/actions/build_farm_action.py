"""
Python representation of the build farm action.
"""

from dataclasses import dataclass
from typing import ClassVar

import common.protos.actions.build_farm_action_pb2 as build_farm_action_pb2
from common.actions.action import Action
from common.convertible import Convertible
from common.tile import Tile


@dataclass
class BuildFarmAction(Action, Convertible):
    """
    Action to build a farm at a given tile 
    """
    # The number of ticks required to build a farm
    TIME_TO_BUILD: ClassVar[int] = 15
    # The number of points required to build a farm
    POINTS_TO_BUILD: ClassVar[int] = 100

    tile: Tile

    def time_left(self, current_tick: int) -> int:
        return max(0, self.TIME_TO_BUILD - current_tick)

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BuildFarmAction):
            return False
        return self.tile == other.tile
