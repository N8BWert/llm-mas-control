"""
A local subscriber implementation that reads from the static
buffer that's held by the local publisher.
"""

from typing import Optional, Type

from common.convertible import Convertible
from common.publishers.local_publisher import LocalPublisher
from common.subscriber import Subscriber


class LocalSubscriber(Subscriber):
    """ 
    A local subscriber interface for local testing
    """

    def __init__(self, bind_address: tuple[str, int], cls: Type[Convertible]):
        super().__init__(cls)
        self.bind_address = f"{bind_address[0]}:{bind_address[1]}"

    def receive(self) -> Optional[Convertible]:
        return LocalPublisher.data.get(self.bind_address, None)
