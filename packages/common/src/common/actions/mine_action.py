"""
Python representation of the mine action.
"""

from typing import ClassVar
from dataclasses import dataclass

import common.protos.actions.mine_action_pb2 as mine_action_pb2
from common.convertible import Convertible
from common.tile import Tile
from common.actions.action import Action


@dataclass
class MineAction(Action, Convertible):
    """
    Action to mine at a given tile 
    """
    # The number of ticks required to mine
    TIME_TO_MINE: ClassVar[int] = 45

    tile: Tile

    def time_left(self, current_tick: int) -> int:
        return max(0, self.TIME_TO_MINE - current_tick)

    def to_proto(self) -> mine_action_pb2.MineAction:
        return mine_action_pb2.MineAction(
            mine_tile=self.tile.to_proto()
        )

    @classmethod
    def from_proto(cls, proto: mine_action_pb2.MineAction) -> "MineAction":
        return cls(tile=Tile.from_proto(proto.mine_tile))

    @classmethod
    def from_bytes(cls, data: bytes) -> "MineAction":
        proto = mine_action_pb2.MineAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MineAction):
            return False
        return self.tile == other.tile
