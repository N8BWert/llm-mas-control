"""
Socket implementation for subscribing to data over a
python network socket
"""

import socket
import struct
import threading
from typing import Optional, Type

from common.convertible import Convertible
from common.subscriber import Subscriber


class SocketSubscriber(Subscriber):
    def __init__(self, bind_address: tuple[str, int], cls: Type[Convertible]):
        super().__init__(cls)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(bind_address)
        self.socket.listen()
        self.event = threading.Event()

        self.data: Optional[Convertible] = None

        self._lock = threading.Lock()
        self.child_threads: list[threading.Thread] = []
        self.client_sockets: list[socket.socket] = []

        self.socket_thread = threading.Thread(target=self._socket_thread, daemon=True)
        self.socket_thread.start()

    def __del__(self):
        self.stop()

    def stop(self):
        if self.event.is_set():
            return  # already stopped
        self.event.set()

        # shutdown() is what actually wakes threads blocked in accept()/recv()
        self._close_socket(self.socket)
        with self._lock:
            clients = list(self.client_sockets)
            threads = list(self.child_threads)
        for s in clients:
            self._close_socket(s)

        current = threading.current_thread()
        for t in threads + [self.socket_thread]:
            if t is not current and t.is_alive():
                t.join(timeout=2)

    @staticmethod
    def _close_socket(s: socket.socket):
        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # not connected / already closed
        try:
            s.close()
        except OSError:
            pass

    def receive(self) -> Optional[Convertible]:
        return self.data

    def _socket_thread(self):
        while not self.event.is_set():
            try:
                client_socket, _ = self.socket.accept()
            except OSError:
                break  # listening socket was closed by stop()

            client_thread = threading.Thread(
                target=self._client_thread, args=(client_socket,), daemon=True
            )
            with self._lock:
                self.client_sockets.append(client_socket)
                self.child_threads.append(client_thread)
            client_thread.start()

    def _recv_exactly(self, sock: socket.socket, n: int) -> Optional[bytes]:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return None  # peer closed
            buf.extend(chunk)
        return bytes(buf)

    def _client_thread(self, client_socket: socket.socket):
        try:
            while not self.event.is_set():
                header = self._recv_exactly(client_socket, 4)
                if header is None:
                    break
                (length,) = struct.unpack('>I', header)
                payload = self._recv_exactly(client_socket, length)
                if payload is None:
                    break
                self.data = self.cls.from_bytes(payload)
        except:
            pass
        finally:
            self._close_socket(client_socket)
            with self._lock:
                if client_socket in self.client_sockets:
                    self.client_sockets.remove(client_socket)
