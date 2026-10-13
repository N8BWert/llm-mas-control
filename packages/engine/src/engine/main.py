"""
Main entrypoint for the game engine
"""

import argparse

import numpy as np
from common.publishers.socket_publisher import SocketPublisher
from common.subscribers.socket_subscriber import SocketSubscriber
from rps.robotarium import Robotarium

from engine.gameplay_engine import GameplayEngine


def main(
    send_address: tuple[str, int],
    bind_address: tuple[str, int],
    num_robots: int
):
    publisher = SocketPublisher(send_address)
    subscriber = SocketSubscriber(bind_address)
    robotarium = Robotarium(
        number_of_robots=num_robots,
        show_figure=True,
        skip_initialization=True,
        show_arena_boundaries=False,
    )
    e = GameplayEngine(
        publisher,
        subscriber,
        robotarium,
        castle_tile = (1, 1),
        tiles = (8, 4)
    )
    while True:
        e.tick()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-address", help="Address to send data to", type=str, default="localhost")
    parser.add_argument("--send-port", help="Port to send data to", type=int, default="8080")
    parser.add_argument("--bind-address", help="Address to bind to", type=str, default="localhost")
    parser.add_argument("--bind-port", help="Port to bind to", type=int, default="8081")
    parser.add_argument("--num-robots", help="The maximum number of robots for the game", type=int, default=10)
    args = parser.parse_args()
    main(
        (args.send_address, int(args.send_port)),
        (args.bind_address, int(args.bind_port)),
        args.num_robots
    )
