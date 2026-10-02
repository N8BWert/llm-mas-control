"""
A non-player map element such as an enemy or an objective marker.
"""

from dataclasses import dataclass

from common.convertible import Convertible
import common.protos.entity_pb2 as entity_pb2


@dataclass
class Entity(Convertible):
    id: int
    kind: str
    x: float
    y: float
    label: str = ""

    def to_proto(self) -> entity_pb2.Entity:
        proto = entity_pb2.Entity(id=self.id, kind=self.kind, label=self.label)
        proto.position.x = self.x
        proto.position.y = self.y
        return proto

    @classmethod
    def from_proto(cls, proto: entity_pb2.Entity) -> "Entity":
        return cls(
            id=proto.id,
            kind=proto.kind,
            x=proto.position.x,
            y=proto.position.y,
            label=proto.label,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Entity":
        proto = entity_pb2.Entity()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
