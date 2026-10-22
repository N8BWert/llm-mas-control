"""
Main entrypoint for the game engine
"""

import argparse
import os

from common.agent_action import AgentActionRequest
from common.publishers.socket_publisher import SocketPublisher
from common.subscribers.socket_subscriber import SocketSubscriber
from rps.robotarium import Robotarium

from engine.gameplay_engine import GameplayEngine
from engine.level import Level

# The directory level files are stored in
LEVELS_DIR: str = f"{os.path.dirname(os.path.abspath(__file__))}/../../../../assets/levels/"


def parse_arguments() -> tuple[tuple[str, int], tuple[str, int], str]:
    parser = argparse.ArgumentParser(description="Run the game engine for Age of Ants.")
    parser.add_argument("--send-address", help="Address to send data to", type=str, default="localhost")
    parser.add_argument("--send-port", help="Port to send data to", type=int, default="8080")
    parser.add_argument("--bind-address", help="Address to bind to", type=str, default="localhost")
    parser.add_argument("--bind-port", help="Port to bind to", type=int, default="8081")
    parser.add_argument("-l", "--level", help="The name of the level to run", type=str, default="easy_level.json")
    args = parser.parse_args()
    return (args.send_address, int(args.send_port)), (args.bind_address, int(args.bind_port)), args.level


def main():
    send_address, bind_address, level_name = parse_arguments()
    level: Level
    with open(LEVELS_DIR + level_name, "r") as f:
        level = Level.from_json(f.read())
    print(level)
    publisher = SocketPublisher(send_address)
    subscriber = SocketSubscriber(bind_address, AgentActionRequest)
    robotarium = Robotarium(
        number_of_robots=level.max_agents,
        show_figure=False,
        skip_initialization=True,
        show_arena_boundaries=False,
        sim_in_real_time=True,
    )
    e = GameplayEngine(
        publisher,
        subscriber,
        robotarium,
        level
    )
    while True:
        e.tick()


if __name__ == "__main__":
    main()
