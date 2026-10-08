"""
A subscriber is meant to receive data from some outside
source.

Like the publisher I'm creating this interface so I
can work with local operations for testing because I don't
want to manage a ton of sockets.
"""

from abc import ABC, abstractmethod
from typing import Optional, Type

from common.convertible import Convertible


class Subscriber(ABC):
    """
    An abstract base class for subscribers to implement to
    standardize the way we talk across boundaries. 
    """

    def __init__(self, cls: Type[Convertible]):
        self.cls = cls

    @abstractmethod
    def receive(self) -> Optional[Convertible]:
        """
        Receive data from the subscriber.

        Returns:
            Optional[Convertible]: The data received from the subscriber,
            or None if no data is available.
        """
        ...
