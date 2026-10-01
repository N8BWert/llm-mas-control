"""
A publisher is meant to send data in one direction.

I'm intentionally creating a publisher interface so I can
test local operations of the engine without having to create
a ton of sockets
"""

from abc import ABC, abstractmethod

from common.convertible import Convertible


class Publisher(ABC):
    """
    The interface contract for things that send data in one direction
    out of a system. 
    """

    @abstractmethod
    def send(self, data: Convertible):
        """
        Send data in one direction.

        Args:
            data (Convertible): The data to be sent.
        """
        ...
