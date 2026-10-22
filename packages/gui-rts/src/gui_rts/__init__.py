"""
Entrypoint for the rts GUI package.
"""

import argparse

import numpy as np
from common.agent_state import AgentState
from common.game_state import GameState
from common.publishers.local_publisher import LocalPublisher
from common.publishers.socket_publisher import SocketPublisher
from common.subscribers.local_subscriber import LocalSubscriber
from common.subscribers.socket_subscriber import SocketSubscriber
from common.tile import TileOverlay, TileState, TileType

from gui_rts.rts_gui import RtsGui


def parse_arguments() -> tuple[tuple[str, int], tuple[str, int]]:
    parser = argparse.ArgumentParser(description="Run the RTS GUI for Age of Ants.")
    parser.add_argument("--send-address", help="Address to send data to", type=str, default="localhost")
    parser.add_argument("--send-port", help="Port to send data to", type=int, default="8081")
    parser.add_argument("--bind-address", help="Address to bind to", type=str, default="localhost")
    parser.add_argument("--bind-port", help="Port to bind to", type=int, default="8080")
    args = parser.parse_args()
    return (args.send_address, int(args.send_port)), (args.bind_address, int(args.bind_port))

def main():
    # tile_states = [TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.NONE) for _ in range(8 * 4)]
    # tile_states[0 + (8 * 0)] = TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.BIRD)
    # tile_states[1 + (8 * 0)] = TileState(tile_type=TileType.WATER, tile_overlay=TileOverlay.BIRD)
    # tile_states[2 + (8 * 0)] = TileState(tile_type=TileType.QUARRY, tile_overlay=TileOverlay.BIRD)
    # tile_states[1 + (8 * 1)] = TileState(tile_type=TileType.FARM, tile_overlay=TileOverlay.BIRD)
    # tile_states[2 + (8 * 2)] = TileState(tile_type=TileType.HOUSE, tile_overlay=TileOverlay.BIRD)
    # tile_states[3 + (8 * 3)] = TileState(tile_type=TileType.CASTLE, tile_overlay=TileOverlay.NONE)
    # tile_states[4 + (8 * 0)] = TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.APPLE)
    # tile_states[5 + (8 * 1)] = TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.APPLE)
    # tile_states[6 + (8 * 2)] = TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.APPLE)
    # tile_states[7 + (8 * 3)] = TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.APPLE)
    # agents = [AgentState(id=i, position=np.array([-1.5 + 0.25 * i, -0.9 + 0.25 * i]), orientation=-3*np.pi/4, busy=True, carrying_apple=True) for i in range(8)]
    # start_game_state = GameState(
    #     agent_states=agents,
    #     tile_states=tile_states,
    #     width=8,
    #     height=4,
    #     points=0
    # )
    send_address, bind_address = parse_arguments()
    # test_publisher = LocalPublisher(bind_address)
    # test_publisher.send(start_game_state)
    # publisher = LocalPublisher(send_address)
    # subscriber = LocalSubscriber(bind_address, GameState)
    publisher = SocketPublisher(send_address)
    subscriber = SocketSubscriber(bind_address, GameState)
    gui = RtsGui(subscriber, publisher)
    gui.run()


if __name__ == "__main__":
    main()
