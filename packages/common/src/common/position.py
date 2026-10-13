"""
Position type used to represent coordinates in the environment.
"""

import numpy as np

import common.protos.position_pb2 as position_pb2
from common.convertible import Convertible


class Position(Convertible):
    """
    Represents a 2D position with x and y coordinates.
    """

    def __init__(self, x: float, y: float):
        self._data = np.array([x, y])

    @property
    def x(self) -> float:
        return self._data[0]

    @x.setter
    def x(self, value: float):
        self._data[0] = value

    @property
    def y(self) -> float:
        return self._data[1]

    @y.setter
    def y(self, value: float):
        self._data[1] = value

    def to_numpy(self) -> np.ndarray:
        return self._data.copy()

    @classmethod
    def from_numpy(cls, data: np.ndarray) -> "Position":
        return cls(x=data[0], y=data[1])

    def to_proto(self) -> position_pb2.Position:
        proto = position_pb2.Position()
        proto.x = self._data[0]
        proto.y = self._data[1]
        return proto

    @classmethod
    def from_proto(cls, proto: position_pb2.Position) -> "Position":
        return cls(x=proto.x, y=proto.y)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Position":
        proto = position_pb2.Position()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def __repr__(self) -> str:
        return f"Position(x={self.x}, y={self.y})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return False
        return np.array_equal(self._data, other._data)

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __add__(self, other: "Position") -> "Position":
        if not isinstance(other, Position):
            return NotImplemented
        return Position(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other: "Position") -> "Position":
        if not isinstance(other, Position):
            return NotImplemented
        return Position(x=self.x - other.x, y=self.y - other.y)

    def __mul__(self, scalar: float) -> "Position":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Position(x=self.x * scalar, y=self.y * scalar)

    def __truediv__(self, scalar: float) -> "Position":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Position(x=self.x / scalar, y=self.y / scalar)

    def __neg__(self) -> "Position":
        return Position(x=-self.x, y=-self.y)
