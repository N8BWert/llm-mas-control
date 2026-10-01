"""
Python representation of the mine action.
"""

from dataclasses import dataclass

from common.tile import Tile
from common.convertible import Convertible
import common.protos.actions.mine_action_pb2 as mine_action_pb2


@dataclass
class MineAction(Convertible):
    """
    Action to mine at a given tile 
    """

    tile: Tile

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
