"""
The socket publisher implements the publisher interface and sends
data over a network socket.
"""

import queue
import socket
import struct
import threading

from common.convertible import Convertible
from common.publisher import Publisher


class SocketPublisher(Publisher):
    """
    The socket publisher implements the publisher interface and sends
    data over a network socket.
    """

    def __init__(
        self,
        send_address: tuple[str, int],
        connect_timeout: float = 1.0,
        send_timeout: float = 0.5,
        retry_interval: float = 1.0,
    ):
        self.send_address = send_address
        self.connect_timeout = connect_timeout
        self.send_timeout = send_timeout
        self.retry_interval = retry_interval

        self.queue = queue.Queue(maxsize=1)
        self.connected = threading.Event()
        self.stop_event = threading.Event()

        self.send_thread = threading.Thread(
            target=self._run,
            name="SocketPublisherSender",
            daemon=True
        )
        self.send_thread.start()

    def __del__(self):
        self.close()

    def _try_connect(self) -> socket.socket | None:
        """
        Try to connect to the send address

        Returns:
            A socket object if the connection is successful, None otherwise.

        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.connect_timeout)
            sock.connect(self.send_address)
            return sock
        except:
            sock.close()
            return None

    def _clear_queue(self):
        """
        Clear the message queue.
        """
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    def _run(self):
        sock: socket.socket | None = None

        while not self.stop_event.is_set():
            if sock is None:
                sock = self._try_connect()
                if sock is None:
                    self.stop_event.wait(self.retry_interval)
                    continue
                self._clear_queue()
                self.connected.set()

            try:
                payload = self.queue.get(timeout=0.2)
            except:
                continue

            try:
                sock.sendall(payload)
                print("SENDING")
            except:
                self.connected.clear()
                try:
                    sock.close()
                except:
                    pass
                sock = None

        self.connected.clear()
        if sock is not None:
            try:
                sock.close()
            except:
                pass

    def send(self, data: Convertible):
        if not self.connected.is_set():
            return

        proto = data.to_proto()
        proto_bytes = proto.SerializeToString()
        header = struct.pack(">I", len(proto_bytes))
        payload = header + proto_bytes

        try:
            self.queue.put_nowait(payload)
        except:
            pass

    def close(self):
        self.stop_event.set()
        self.send_thread.join(timeout=self.connect_timeout + 1.0)
