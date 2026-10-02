"""
The state broadcast system sends the current game state via protobuf to the various frontends
for rendering.
"""

import struct
import socket

from common.game_state import GameState

class StateBroadcastSystem:
    """
    The state broadcast system broadcasts the current game state via protobuf
    to all connected frontends for rendering purposes.
    """

    def __init__(self, host: str, port: int):
        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        self.socket.connect((host, port))

    def broadcast_state(self, game_state: GameState):
        """
        Broadcast the current game state to all connected frontends.

        Args:
            game_state (GameState): The current state of the game.
        """
        output = game_state.to_proto()
        serialized_data = output.SerializeToString()
        header = struct.pack(">I", len(serialized_data))
        self.socket.sendall(header + serialized_data)
