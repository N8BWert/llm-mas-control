"""
Zones are the areas of the arena that zone constraints refer to.
"""

import math
from dataclasses import dataclass
from typing import Union

from common.convertible import Convertible
import common.protos.constraint_pb2 as constraint_pb2


@dataclass
class RectZone(Convertible):
    """Axis-aligned rectangle in arena coordinates."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def to_dict(self) -> dict:
        return {"rect": [self.x_min, self.y_min, self.x_max, self.y_max]}

    def to_proto(self) -> constraint_pb2.Zone:
        return constraint_pb2.Zone(rect=constraint_pb2.Rect(
            x_min=self.x_min, y_min=self.y_min, x_max=self.x_max, y_max=self.y_max
        ))

    @classmethod
    def from_proto(cls, proto: constraint_pb2.Zone) -> "RectZone":
        r = proto.rect
        return cls(r.x_min, r.y_min, r.x_max, r.y_max)

    @classmethod
    def from_bytes(cls, data: bytes) -> "RectZone":
        proto = constraint_pb2.Zone()
        proto.ParseFromString(data)
        return cls.from_proto(proto)


@dataclass
class CircleZone(Convertible):
    """Circle in arena coordinates."""

    x: float
    y: float
    radius: float

    def contains(self, x: float, y: float) -> bool:
        return math.hypot(x - self.x, y - self.y) <= self.radius

    def to_dict(self) -> dict:
        return {"circle": [self.x, self.y, self.radius]}

    def to_proto(self) -> constraint_pb2.Zone:
        return constraint_pb2.Zone(circle=constraint_pb2.Circle(
            x=self.x, y=self.y, radius=self.radius
        ))

    @classmethod
    def from_proto(cls, proto: constraint_pb2.Zone) -> "CircleZone":
        c = proto.circle
        return cls(c.x, c.y, c.radius)

    @classmethod
    def from_bytes(cls, data: bytes) -> "CircleZone":
        proto = constraint_pb2.Zone()
        proto.ParseFromString(data)
        return cls.from_proto(proto)


Zone = Union[RectZone, CircleZone]


def zone_from_proto(proto: constraint_pb2.Zone) -> Zone:
    match proto.WhichOneof("shape"):
        case "rect":
            return RectZone.from_proto(proto)
        case "circle":
            return CircleZone.from_proto(proto)
        case _:
            raise ValueError("Zone has no shape")


def zone_from_dict(data: dict) -> Zone:
    """Parse {"rect": [x_min, y_min, x_max, y_max]} or {"circle": [x, y, radius]}."""
    if "rect" in data:
        return RectZone(*map(float, data["rect"]))
    if "circle" in data:
        return CircleZone(*map(float, data["circle"]))
    raise ValueError(f"Unknown zone: {data}")


def zones_containing(zones: list[Zone], x: float, y: float) -> bool:
    return any(zone.contains(x, y) for zone in zones)
