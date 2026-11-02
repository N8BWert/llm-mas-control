"""
Main entrypoint for the game engine
"""

import argparse
import os

import numpy as np
from common.agent_action import AgentActionRequest
from common.publishers.socket_publisher import SocketPublisher
from common.subscribers.socket_subscriber import SocketSubscriber
from rps.robotarium import Robotarium

from engine.gameplay_engine import GameplayEngine
from engine.level import Level

# The directory level files are stored in
LEVELS_DIR: str = f"{os.path.dirname(os.path.abspath(__file__))}/../../../../assets/levels/"
# The offscreen locations for each robot to move to when not in use
OFFSCREEN_LOCATIONS: list[np.ndarray] = [
    np.array([-1.5, 1.1, -np.pi/2]),
    np.array([-1.2, 1.1, -np.pi/2]),
    np.array([-0.9, 1.1, -np.pi/2]),
    np.array([-0.6, 1.1, -np.pi/2]),
    np.array([-0.3, 1.1, -np.pi/2]),
    np.array([0.0, 1.1, -np.pi/2]),
    np.array([0.3, 1.1, -np.pi/2]),
    np.array([0.6, 1.1, -np.pi/2]),
    np.array([0.9, 1.1, -np.pi/2]),
    np.array([1.2, 1.1, -np.pi/2]),
    np.array([1.5, 1.1, -np.pi/2]),
    np.array([-1.5, -1.1, np.pi/2]),
    np.array([-1.2, -1.1, np.pi/2]),
    np.array([-0.9, -1.1, np.pi/2]),
    np.array([-0.6, -1.1, np.pi/2]),
    np.array([-0.3, -1.1, np.pi/2]),
    np.array([0.0, -1.1, np.pi/2]),
    np.array([0.3, -1.1, np.pi/2]),
    np.array([0.6, -1.1, np.pi/2]),
    np.array([0.9, -1.1, np.pi/2]),
    np.array([1.2, -1.1, np.pi/2]),
    np.array([1.5, -1.1, np.pi/2]),
]


def parse_arguments() -> tuple[tuple[str, int], tuple[str, int], str, int]:
    parser = argparse.ArgumentParser(description="Run the game engine for Age of Ants.")
    parser.add_argument("--send-address", help="Address to send data to", type=str, default="localhost")
    parser.add_argument("--send-port", help="Port to send data to", type=int, default="8080")
    parser.add_argument("--bind-address", help="Address to bind to", type=str, default="localhost")
    parser.add_argument("--bind-port", help="Port to bind to", type=int, default="8081")
    parser.add_argument("-l", "--level", help="The name of the level to run", type=str, default="easy_level.json")
    parser.add_argument("-s", "--seed", help="The random seed to use for the level", type=int, default=0)
    args = parser.parse_args()
    return (args.send_address, int(args.send_port)), (args.bind_address, int(args.bind_port)), args.level, args.seed

def generate_start_poses(level: Level, seed: int, spacing: float = 0.5, width: float = 3.0, height: float = 1.8) -> np.ndarray:
    """
    Generate N random well-spaced poses inside a rectangle
    """
    rng = np.random.default_rng(seed)
    accepted = []
    max_attempts = 10000
    for _ in range(max_attempts):
        if len(accepted) == level.start_agents:
            break

        candidate = np.array([
            (rng.random() - 0.5) * width,
            (rng.random() - 0.5) * height
        ])
        if not accepted or np.all(np.linalg.norm(np.array(accepted) - candidate, axis=1) >= spacing):
            accepted.append(candidate)
    poses = np.zeros((3, level.max_agents))
    poses[:2, :level.start_agents] = np.array(accepted).T
    poses[2, :level.start_agents] = rng.random(level.start_agents) * 2 * np.pi - np.pi
    poses[:, level.start_agents:level.max_agents] = np.array(OFFSCREEN_LOCATIONS[:level.max_agents - level.start_agents]).T
    return poses

def main():
    send_address, bind_address, level_name, seed = parse_arguments()
    level: Level
    with open(LEVELS_DIR + level_name, "r") as f:
        level = Level.from_json(f.read())
    print(level)
    initial_conditions = generate_start_poses(level, seed)
    publisher = SocketPublisher(send_address)
    subscriber = SocketSubscriber(bind_address, AgentActionRequest)
    robotarium = Robotarium(
        number_of_robots=level.max_agents,
        initial_conditions=initial_conditions,
        show_figure=True,
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
