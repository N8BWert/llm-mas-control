"""
The local publisher is a mock of the publisher interface
that has no real network communication and simply stores
published data for the subscribers
"""

from common.publisher import Publisher
from common.convertible import Convertible


class LocalPublisher(Publisher):
    data: dict[str, Convertible] = {}

    def __init__(self, send_address: tuple[str, int]):
        self.send_address = f"{send_address[0]}:{send_address[1]}"
        LocalPublisher.data[self.send_address] = None

    def send(self, data: Convertible):
        LocalPublisher.data[self.send_address] = data
