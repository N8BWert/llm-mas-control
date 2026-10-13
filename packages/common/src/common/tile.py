"""
Tile type used to represent a single tile in the environment.
"""

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

import common.protos.tile_pb2 as tile_pb2
from common.convertible import Convertible


class TileType(IntEnum):
    """
    The type of a tile (i.e. what kind of terrain it is)
    """
    EMPTY = 0
    CASTLE = 1
    HOUSE = 2
    FARM = 3
    QUARRY = 4
    WATER = 5
    OBSCURED = 6

    def asset_name(self, idx: int) -> str:
        match self:
            case TileType.EMPTY:
                if idx % 2 == 0:
                    return "Grass1.png"
                else:
                    return "Grass2.png"
            case TileType.CASTLE:
                return "Castle.png"
            case TileType.HOUSE:
                return "House.png"
            case TileType.FARM:
                return "Farm.png"
            case TileType.QUARRY:
                return "Quarry.png"
            case TileType.WATER:
                return "Water.png"
            case TileType.OBSCURED:
                return "Obscured.png"


class TileOverlay(IntEnum):
    """
    The overlay of a tile (i.e. what is currently on top of the tile)
    """
    NONE = 0
    APPLE = 1
    BIRD = 2

    def asset_name(self) -> str | None:
        match self:
            case TileOverlay.NONE:
                return None
            case TileOverlay.APPLE:
                return "Apple.png"
            case TileOverlay.BIRD:
                return "BirdShadow.png"


@dataclass
class TileState(Convertible):
    tile_type: TileType
    tile_overlay: TileOverlay

    def to_proto(self) -> tile_pb2.TileState:
        return tile_pb2.TileState(
            tile_type=self.tile_type,
            tile_overlay=self.tile_overlay
        )

    @classmethod
    def from_proto(cls, proto: tile_pb2.TileState) -> "TileState":
        return cls(
            tile_type=TileType(proto.tile_type),
            tile_overlay=TileOverlay(proto.tile_overlay)
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "TileState":
        proto = tile_pb2.TileState()
        proto.ParseFromString(data)
        return cls.from_proto(proto)


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

    def center(
        self,
        width: float,
        height: float
    ):
        """
        Get the center of the tile.

        Args:
            width (float): The width of the tile.
            height (float): The height of the tile.

        Returns:
            np.ndarray: The center of the tile.
        """
        return np.array([(self.x + 0.5) * width, (self.y + 0.5) * height])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tile):
            return False
        return self.x == other.x and self.y == other.y
