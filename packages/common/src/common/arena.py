"""
The arena is the world-coordinate rectangle the tile grid is laid over.
Tile (i, j) has i along x and j along y, with (0, 0) at (x_min, y_min).
"""

from dataclasses import dataclass

from common.convertible import Convertible
import common.protos.constraint_pb2 as constraint_pb2

# The Robotarium testbed's usable area in meters
ROBOTARIUM_BOUNDS = (-1.6, -1.0, 1.6, 1.0)


@dataclass
class Arena(Convertible):
    x_min: float = ROBOTARIUM_BOUNDS[0]
    y_min: float = ROBOTARIUM_BOUNDS[1]
    x_max: float = ROBOTARIUM_BOUNDS[2]
    y_max: float = ROBOTARIUM_BOUNDS[3]

    def tile_size(self, width: int, height: int) -> tuple[float, float]:
        return (self.x_max - self.x_min) / width, (self.y_max - self.y_min) / height

    def tile_center(self, i: int, j: int, width: int, height: int) -> tuple[float, float]:
        tw, th = self.tile_size(width, height)
        return self.x_min + (i + 0.5) * tw, self.y_min + (j + 0.5) * th

    def tile_at(self, x: float, y: float, width: int, height: int) -> tuple[int, int]:
        tw, th = self.tile_size(width, height)
        i = min(max(int((x - self.x_min) // tw), 0), width - 1)
        j = min(max(int((y - self.y_min) // th), 0), height - 1)
        return i, j

    def clamp(self, x: float, y: float) -> tuple[float, float]:
        return min(max(x, self.x_min), self.x_max), min(max(y, self.y_min), self.y_max)

    def to_proto(self) -> constraint_pb2.Rect:
        return constraint_pb2.Rect(
            x_min=self.x_min, y_min=self.y_min, x_max=self.x_max, y_max=self.y_max
        )

    @classmethod
    def from_proto(cls, proto: constraint_pb2.Rect) -> "Arena":
        if proto.x_min == proto.x_max:
            return cls()
        return cls(x_min=proto.x_min, y_min=proto.y_min, x_max=proto.x_max, y_max=proto.y_max)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Arena":
        proto = constraint_pb2.Rect()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
