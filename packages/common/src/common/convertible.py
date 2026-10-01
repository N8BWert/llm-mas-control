"""
Convertible interface used to convert objects to and from protobuf
representations of the object.
"""

from abc import ABC, abstractmethod
from google.protobuf.message import Message


class Convertible(ABC):
    @abstractmethod
    def to_proto(self) -> Message:
        """
        Converts the object to its protobuf representation.

        Returns:
            Message: The protobuf representation of the object.
        """
        ...

    def to_bytes(self) -> bytes:
        """
        Converts the object to its byte representation.

        Returns:
            bytes: The byte representation of the object.
        """
        return self.to_proto().SerializeToString()

    @classmethod
    @abstractmethod
    def from_proto(cls, proto: Message) -> "Convertible":
        """
        Converts the protobuf representation of the object back to the object.

        Args:
            proto (Message): The protobuf representation of the object.

        Returns:
            Convertible: The object represented by the protobuf.
        """
        ...

    @classmethod
    @abstractmethod
    def from_bytes(cls, data: bytes) -> "Convertible":
        """
        Converts the byte representation of the object back to the object.

        Args:
            data (bytes): The byte representation of the object.

        Returns:
            Convertible: The object represented by the bytes.
        """
        ...
