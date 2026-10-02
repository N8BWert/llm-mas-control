"""
The gameplay engine is responsible for maintaining the gameplay-aspect state
of the game.  This involves the non-physical aspects such as score, non-player
items, ...  It also wraps around the Robotarium to provide physics updates
for the player characters.
"""

import numpy as np
from typing import Optional
from enum import IntEnum

from rps.robotarium import Robotarium
from rps.utilities.controllers import create_si_position_controller
from rps.utilities.transformations import create_si_to_uni_mapping
from rps.utilities.barrier_certificates import create_si_barrier_certificate

from common.agent_action import (
    AgentAction,
    BuildFarmAction,
    BuildHouseAction,
    BuildQuarryAction,
    DropAction,
    FarmAction,
    MineAction,
    MoveAction,
    PickUpAction
)
from common.game_state import GameState


class TileState(IntEnum):
    """
    The possible states of a tile in the game.
    """
    EMPTY = 0
    CASTLE = 1
    FARM = 2
    QUARRY = 3
    WATER = 4
    APPLE = 5
    OBSCURED = 6


class GameplayEngine:
    """
    The gameplay engine is responsible for maintaining the gameplay state of the
    game.
    """

    def __init__(
        self,
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
        # The current action for each agent
        self.current_actions: list[Optional[AgentAction]] = [None for _ in range(max_agents)]

    def set_agent_actions(self, agent_ids: list[int], actions: list[AgentAction]):
        """
        Set the current actions for the specified agents.

        Args:
            agent_ids (list[int]): The IDs of the agents to set actions for.
            actions (list[AgentAction]): The actions to assign to the agents.
        """
        for agent_id, action in zip(agent_ids, actions):
            self.current_actions[agent_id] = action

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
        for i in range(self.agents):
            match self.current_actions[i]:
                case MoveAction(goal_position):
                    # TODO: Process the move action for the agent
                    pass
                case FarmAction(farm_tile):
                    # TODO: Process the farm action for the agent
                    pass
                case _:
                    # No action or unrecognized action for the agent
                    pass

        # Apply the barrier certificate to the desired control inputs and update
        # the physics engine
        dxi = self.barrier_certificate(dxi, x_si)
        dxu = self.si_to_uni(dxi, x)
        self.robotarium.set_velocities(np.arange(self.max_agents), dxu)

        # Update the graphics of the robotarium
        self.draw()
        self.robotarium.step()

    def get_game_state(self) -> GameState:
        """
        Retrieve the current state of the game.

        Returns:
            GameState: The current state of the game.
        """
        agent_positions = self.uni_to_si(self.robotarium.get_poses())
        return GameState(
            agent_positions=agent_positions,
            points=self.points,
            tile_states=self.tiles.copy()
        )
