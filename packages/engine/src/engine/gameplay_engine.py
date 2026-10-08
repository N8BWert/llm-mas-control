"""
The gameplay engine is responsible for maintaining the gameplay-aspect state
of the game.  This involves the non-physical aspects such as score, non-player
items, ...  It also wraps around the Robotarium to provide physics updates
for the player characters.
"""

import numpy as np
from common.agent_action import (
    AgentAction,
    BuildFarmAction,
    BuildHouseAction,
    BuildQuarryAction,
    DropAction,
    FarmAction,
    MineAction,
    MoveAction,
    PickUpAction,
)
from common.game_state import GameState
from common.publisher import Publisher
from common.subscriber import Subscriber
from common.tile import TileState
from rps.robotarium import Robotarium
from rps.utilities.barrier_certificates import create_si_barrier_certificate
from rps.utilities.controllers import create_si_position_controller
from rps.utilities.transformations import create_si_to_uni_mapping

from engine.input_system import InputSystem


class GameplayEngine:
    """
    The gameplay engine is responsible for maintaining the gameplay state of the
    game.
    """

    def __init__(
        self,
        publisher,
        subscriber,
        max_agents: int = 10,
        castle_tile: tuple[int, int] = (3, 3),
        tiles: tuple[int, int] = (20, 32),
    ):
        """
        Initialize the gameplay engine

        Args:
            castle_tile (tuple[int, int]): The coordinates of the castle tile.
            tiles (tuple[int, int]): The dimensions of the game tiles.
        """
        # The robotarium physics engine for state updates
        self.robotarium = Robotarium(
            number_of_robots=max_agents,
            show_figure=True,
            initial_conditions=None,
            sim_in_real_time=True,
            skip_initialization=True,
            show_arena_boundaries=False,
        )
        self.controller = create_si_position_controller()
        self.si_to_uni, self.uni_to_si = create_si_to_uni_mapping()
        self.barrier_certificate = create_si_barrier_certificate(barrier_gain=1.0, magnitude_limit=0.15)
        # The number of points the player has
        self.points = 0
        # The tiles in the game engine
        self.tiles = np.zeros(tiles, dtype=int)
        self.tiles[castle_tile[0], castle_tile[1]] = TileState.CASTLE
        # The number of agents currently accessible in the game
        self.agents = 1
        self.max_agents = max_agents
        # The input system for handling user inputs
        self.input_system = InputSystem(subscriber)
        # The publisher for broadcasting the current game state
        self.game_state_publisher = publisher

    def draw(self):
        """
        Draw the current gameplay state onto the robotarium figure
        """
        pass

    def tick(self):
        """
        Advance the gameplay by one tick, processing all current actions and updating the game state accordingly.
        """
        # Get the current pose of robots form the robotarium
        x = self.robotarium.get_poses()
        x_si = self.uni_to_si(x)
        dxi = np.zeros((2, self.max_agents))

        # Find the current action for each robot in the game
        actions = self.input_system.get_agent_actions()
        for action in actions:
            if action is None:
                continue
            match action.action:
                case MoveAction(goal_position):
                    # TODO: Create a single agent controller to streamline this
                    # P Controller with a gain of 0.8
                    dxi[action.agent_id] = 0.8 * (goal_position - x_si[:, action.agent_id])
                    # TODO: Normalize control inputs
                case _:
                    pass

        # Apply the barrier certificate to the desired control inputs and update
        # the physics engine
        dxi = self.barrier_certificate(dxi, x_si)
        dxu = self.si_to_uni(dxi, x)
        self.robotarium.set_velocities(np.arange(self.max_agents), dxu)

        # Update the graphics of the robotarium
        self.draw()
        self.robotarium.step()

        # Publish the current state of the game
        self._publish_game_state()

    def _publish_game_state(self):
        """
        Publish the current state of the game 
        """
        # TODO:
