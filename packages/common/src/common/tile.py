"""
Tile type used to represent a single tile in the environment.
"""

from dataclasses import dataclass
from enum import IntEnum

import common.protos.tile_pb2 as tile_pb2
from common.convertible import Convertible


class TileState(IntEnum):
    """
    The state of a tile (i.e. what is currently on the tile)
    """
    EMPTY = 0
    CASTLE = 1
    FARM = 2
    QUARRY = 3
    WATER = 4
    APPLE = 5
    OBSCURED = 6


@dataclass
class Tile(Convertible):
    """
    Represents a single tile in the environment.
    """
    x: int
    y: int

    def to_proto(self) -> tile_pb2.Tile:
        return tile_pb2.Tile(
            x=self.x,
            y=self.y
        )

    @classmethod
    def from_proto(cls, proto: tile_pb2.Tile) -> "Tile":
        return cls(
            x=proto.x,
            y=proto.y
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Tile":
        proto = tile_pb2.Tile()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def within(
        self,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> bool:
        """
        Check that a given point (x, y) is within the bounds of this tile

        Args:
            x (float): The x-coordinate of the point to check.
            y (float): The y-coordinate of the point to check.
            width (float): The width of the tile.
            height (float): The height of the tile.

        Returns:
            bool: True if the point is within the bounds of the tile, False otherwise.
        """
        return self.x * width <= x <= (self.x + 1) * width and \
            self.y * height <= y <= (self.y + 1) * height
