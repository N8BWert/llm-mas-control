"""
The socket publisher implements the publisher interface and sends
data over a network socket.
"""

import struct
import socket

from common.publisher import Publisher
from common.convertible import Convertible


class SocketPublisher(Publisher):
    """
    The socket publisher implements the publisher interface and sends
    data over a network socket.
    """

    def __init__(
        self,
        send_address: tuple[str, int]
    ):
        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        self.socket.connect(send_address)

    def send(self, data: Convertible):
        proto = data.to_proto()
        proto_bytes = proto.SerializeToString()
        header = struct.pack(">I", len(proto_bytes))
        self.socket.sendall(header + proto_bytes)
