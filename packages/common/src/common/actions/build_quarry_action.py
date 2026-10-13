"""
Python representation of the build quarry action.
"""

from typing import ClassVar
from dataclasses import dataclass

import common.protos.actions.build_quarry_action_pb2 as build_quarry_action_pb2
from common.convertible import Convertible
from common.tile import Tile
from common.actions.action import Action


@dataclass
class BuildQuarryAction(Action, Convertible):
    """
    Action to build a quarry at a given tile 
    """
    # The number of ticks required to build a quarry
    TIME_TO_BUILD: ClassVar[int] = 30
    # The number of points required to build a quarry
    POINTS_TO_BUILD: ClassVar[int] = 100

    tile: Tile

    def time_left(self, current_tick: int) -> int:
        return max(0, self.TIME_TO_BUILD - current_tick)

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BuildQuarryAction):
            return False
        return self.tile == other.tile
