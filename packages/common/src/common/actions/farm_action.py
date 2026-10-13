"""
Python representation of the farm action.
"""

from typing import ClassVar
from dataclasses import dataclass

import common.protos.actions.farm_action_pb2 as farm_action_pb2
from common.convertible import Convertible
from common.tile import Tile
from common.actions.action import Action


@dataclass
class FarmAction(Action, Convertible):
    """
    Action to farm at a given tile 
    """
    # The number of ticks required to farm
    TIME_TO_FARM: ClassVar[int] = 30

    tile: Tile

    def time_left(self, current_tick: int) -> int:
        return max(0, self.TIME_TO_FARM - current_tick)

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FarmAction):
            return False
        return self.tile == other.tile
