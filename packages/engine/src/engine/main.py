"""
Main entrypoint for the game engine
"""

import argparse
from common.actions.move_action import MoveAction
from common.agent_action import AgentAction, AgentActionRequest
from common.game_state import GameState
import numpy as np
from common.publishers.local_publisher import LocalPublisher
from common.subscribers.local_subscriber import LocalSubscriber
# from common.publishers.socket_publisher import SocketPublisher
# from common.subscribers.socket_subscriber import SocketSubscriber
from rps.robotarium import Robotarium

from engine.gameplay_engine import GameplayEngine


def main(
    send_address: tuple[str, int],
    bind_address: tuple[str, int],
    num_robots: int
):
    # publisher = SocketPublisher(send_address)
    publisher = LocalPublisher(send_address)
    # subscriber = SocketSubscriber(bind_address)
    subscriber = LocalSubscriber(bind_address, AgentActionRequest)
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
    test_publisher = LocalPublisher(bind_address)
    test_subscriber = LocalSubscriber(send_address, GameState)
    while True:
        test_publisher.send(AgentActionRequest([
            AgentAction(1, MoveAction(np.array([-1.2, 0.0]))),
            AgentAction(2, MoveAction(np.array([1.0, 0.0]))),
            AgentAction(3, MoveAction(np.array([0.0, 0.5]))),
            AgentAction(4, MoveAction(np.array([0.0, -0.5])))
        ]))
        e.tick()
        game_state: GameState | None = test_subscriber.receive()
        if game_state is not None:
            print(game_state)


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
