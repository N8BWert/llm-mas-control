"""
The gameplay engine is responsible for maintaining the gameplay-aspect state
of the game.  This involves the non-physical aspects such as score, non-player
items, ...  It also wraps around the Robotarium to provide physics updates
for the player characters.
"""

import os

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
from common.agent_state import AgentState
from common.game_state import GameState
from common.publisher import Publisher
from common.subscriber import Subscriber
from common.tile import Tile, TileOverlay, TileState, TileType
from matplotlib.axes import Axes
from PIL import Image
from rps.robotarium import Robotarium
from rps.utilities.barrier_certificates import create_si_barrier_certificate
from rps.utilities.transformations import create_si_to_uni_mapping

from engine.controller import SingleAgentController
from engine.input_system import InputSystem

# The number of points you gain per apple
POINTS_PER_APPLE: int = 500
# The assets directory
ASSETS_DIR: str = f"{os.path.dirname(os.path.abspath(__file__))}/../../../../assets/"


class GameplayEngine:
    """
    The gameplay engine is responsible for maintaining the gameplay state of the
    game.
    """

    def __init__(
        self,
        publisher: Publisher,
        subscriber: Subscriber,
        robotarium: Robotarium,
        start_agents: int = 5,
        castle_tile: tuple[int, int] = (3, 3),
        tiles: tuple[int, int] = (20, 32),
    ):
        """
        Initialize the gameplay engine

        Args:
            castle_tile (tuple[int, int]): The coordinates of the castle tile.
            tiles (tuple[int, int]): The dimensions of the game tiles.
            robotarium (Robotarium): The robotarium physics engine.
        """
        # The robotarium physics engine for state updates
        self.robotarium = robotarium
        self.controller = SingleAgentController(kp=1.0, magnitude_limit=0.15)
        self.si_to_uni, self.uni_to_si = create_si_to_uni_mapping()
        self.barrier_certificate = create_si_barrier_certificate(barrier_gain=1.0, magnitude_limit=0.15)

        # The number of points the player has
        self.points = 0

        # The tiles in the game engine
        self.tiles_x = tiles[0]
        self.tiles_y = tiles[1]
        self.tile_width = 3.2 / self.tiles_x
        self.tile_height = 2.0 / self.tiles_y
        self.tiles = [TileState(tile_type=TileType.EMPTY, tile_overlay=TileOverlay.NONE)] * (tiles[0] * tiles[1])
        self.tiles[castle_tile[0] * self.tiles_x + castle_tile[1]] = TileState(tile_type=TileType.CASTLE, tile_overlay=TileOverlay.NONE)
        self.castle_tile = Tile(castle_tile[0], castle_tile[1])
        # Did the tiles update (if so we need to redraw the tiles)
        self.tiles_updated = True

        # The number of agents currently accessible in the game
        self.agents = start_agents
        self.max_agents = self.robotarium.number_of_robots
        # What agents are carrying apples
        self.agent_carrying = [False] * self.max_agents
        # The input system for handling user inputs
        self.input_system = InputSystem(subscriber)
        # The current action for each agent and how many ticks they have been executing it
        self.current_actions: list[list[AgentAction, int] | None] = [None] * self.max_agents
        # The publisher for broadcasting the current game state
        self.game_state_publisher = publisher

    def draw(self):
        """
        Draw the current gameplay state onto the robotarium figure
        """
        # Draw the tiles
        if self.robotarium.show_figure and self.tiles_updated:
            for x in range(self.tiles_x):
                for y in range(self.tiles_y):
                    self._draw_tile(
                        self.robotarium._axes_handle,
                        Tile(x, y),
                        self.tiles[x + self.tiles_x * y],
                        self.tile_width,
                        self.tile_height
                    )
        self.tiles_updated = False

    def tick(self):
        """
        Advance the gameplay by one tick, processing all current actions and updating the game state accordingly.
        """
        # Get the current pose of robots form the robotarium
        x = self.robotarium.get_poses()
        x_si = self.uni_to_si(x)
        dxi = np.zeros((2, self.max_agents))

        # Decode the most recent actions for each agent (overriding our current actions
        # if they are new)
        new_actions = self.input_system.get_agent_actions()
        if new_actions is not None:
            for robot_id, action in enumerate(new_actions):
                if action is None:
                    self.current_actions[robot_id] = None
                else:
                    if action != self.current_actions[robot_id]:
                        self.current_actions[robot_id] = [action, 0]

        # Decode movement and update the timestep from the current actions of each robot
        for robot_id in range(self.agents):
            if self.current_actions[robot_id] is None:
                continue
            action, _ = self.current_actions[robot_id]
            # TODO: This match-case statement is super ugly.  I should probably clean it up at some point
            match action.action:
                case BuildFarmAction(farm_tile):
                    if farm_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Increment the build counter
                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            # Wait until we have the necessary points to build the farm
                            if self.points < BuildFarmAction.POINTS_TO_BUILD:
                                self.current_actions[robot_id][1] -= 1
                                continue
                            # The action is finished
                            self._build_farm(farm_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], farm_tile.center(self.tile_width, self.tile_height))
                case BuildHouseAction(house_tile):
                    if house_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Increment the build counter
                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            if self.points < BuildHouseAction.POINTS_TO_BUILD:
                                self.current_actions[robot_id][1] -= 1
                                continue
                            # The action is finished
                            self._build_house(house_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], house_tile.center(self.tile_width, self.tile_height))
                case BuildQuarryAction(quarry_tile):
                    if quarry_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Increment the build counter
                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            if self.points < BuildQuarryAction.POINTS_TO_BUILD:
                                self.current_actions[robot_id][1] -= 1
                                continue
                            # The action is finished
                            self._build_quarry(quarry_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], quarry_tile.center(self.tile_width, self.tile_height))
                case DropAction(drop_tile):
                    if drop_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Short circuit if we're not carrying anything
                        if not self.agent_carrying[robot_id]:
                            self.current_actions[robot_id] = None
                            continue

                        # Increment the drop action counter
                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            # The action is finished
                            self._drop_item(robot_id, drop_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], drop_tile.center(self.tile_width, self.tile_height))
                case FarmAction(farm_tile):
                    if farm_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Short circuit if we're not at a farm tile
                        if self.tiles[farm_tile.x * self.tiles_x + farm_tile.y].tile_type != TileType.FARM:
                            self.current_actions[robot_id] = None
                            continue

                        # Increment the farm action counter
                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            # The action is finished
                            self._farm(farm_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], farm_tile.center(self.tile_width, self.tile_height))
                case MineAction(mine_tile):
                    if mine_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Short circuit if we're not at a quarry tile
                        if self.tiles[mine_tile.x * self.tiles_x + mine_tile.y].tile_type != TileType.QUARRY:
                            self.current_actions[robot_id] = None
                            continue

                        # Increment the mine action counter
                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            # The action is finished
                            self._mine(mine_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], mine_tile.center(self.tile_width, self.tile_height))
                case PickUpAction(pickup_tile):
                    if pickup_tile.within(x_si[0, robot_id], x_si[1, robot_id], self.tile_width, self.tile_height):
                        # Short circuit if there's nothing on the tile to pickup
                        if self.tiles[pickup_tile.x * self.tiles_x + pickup_tile.y].tile_overlay != TileOverlay.APPLE:
                            self.current_actions[robot_id] = None
                            continue

                        self.current_actions[robot_id][1] += 1
                        if action.time_left(self.current_actions[robot_id][1]) == 0:
                            # The action is finished
                            self._pickup_item(robot_id, pickup_tile)
                            self.current_actions[robot_id] = None
                    else:
                        dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], pickup_tile.center(self.tile_width, self.tile_height))
                case MoveAction(goal_position):
                    # Move the agent towards the goal position using the single agent controller
                    self.current_actions[robot_id][1] += 1
                    dxi[:, robot_id] = self.controller.apply(x_si[:, robot_id], goal_position)
                    if np.linalg.norm(x_si[:, robot_id] - goal_position) < MoveAction.TOLERANCE:
                        self.current_actions[robot_id] = None
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
        self._publish_game_state(x_si)

    def _publish_game_state(self, x: np.ndarray):
        """
        Publish the current state of the game 

        Args:
            x_si (np.ndarray): The (x,y,theta) poses of each robot
        """
        agent_states: list[AgentState] = []
        for robot_id in range(self.agents):
            agent_states.append(AgentState(
                robot_id,
                x[:2, robot_id],
                x[2, robot_id],
                self.current_actions[robot_id] is not None,
                self.agent_carrying[robot_id]
            ))
        game_state = GameState(
            agent_states,
            self.tiles,
            self.tile_width,
            self.tile_height,
            self.points
        )
        self.game_state_publisher.send(game_state)

    def _build_farm(self, farm_tile: Tile):
        """
        Build a farm on the given tile 

        Args:
            farm_tile (Tile): The tile on which to build the farm
        """
        self.tiles[farm_tile.x * self.tiles_x + farm_tile.y] = TileState(
            tile_type=TileType.FARM,
            tile_overlay=TileOverlay.NONE
        )
        self.points -= BuildFarmAction.POINTS_TO_BUILD
        self.tiles_updated = True

    def _build_house(self, house_tile: Tile):
        """
        Build a house on the given tile

        Args:
            house_tile (Tile): The tile on which to build the house 
        """
        self.tiles[house_tile.x * self.tiles_x + house_tile.y] = TileState(
            tile_type=TileType.HOUSE,
            tile_overlay=TileOverlay.NONE
        )
        self.points -= BuildHouseAction.POINTS_TO_BUILD
        self.agents += 1
        self.current_actions[self.agents - 1] = [MoveAction(
            position = self.castle_tile.center(self.tiles_width, self.tile_height)
        )]
        self.tiles_updated = True

    def _build_quarry(self, quarry_tile: Tile):
        """
        Build a quarry on the given tile

        Args:
            quarry_tile (Tile): The tile on which to build the quarry
        """
        self.tiles[quarry_tile.x * self.tiles_x + quarry_tile.y] = TileState(
            tile_type=TileType.QUARRY,
            tile_overlay=TileOverlay.NONE
        )
        self.points -= BuildQuarryAction.POINTS_TO_BUILD
        self.tiles_updated = True

    def _farm(self, farm_tile: Tile):
        if self.tiles[farm_tile.x * self.tiles_x + farm_tile.y].tile_overlay == TileOverlay.NONE:
            self.tiles[farm_tile.x * self.tiles_x + farm_tile.y].tile_overlay = TileOverlay.APPLE
            self.tiles_updated = True
        else:
            # Scan the surrounding adjacent tiles to spawn the apple
            for x in (farm_tile.x - 1, farm_tile.x + 1):
                for y in (farm_tile.y - 1, farm_tile.y + 1):
                    if 0 <= x < self.tiles_x and 0 <= y < self.tiles_y:
                        if self.tiles[x * self.tiles_x + y].tile_overlay == TileOverlay.NONE:
                            self.tiles[x * self.tiles_x + y].tile_overlay = TileOverlay.APPLE
                            self.tiles_updated = True
                            return

    def _mine(self, quarry_tile: Tile):
        apples_to_spawn = 2

        # Try to spawn an apple in the quarry
        if self.tiles[quarry_tile.x * self.tiles_x + quarry_tile.y].tile_overlay == TileOverlay.NONE:
            self.tiles[quarry_tile.x * self.tiles_x + quarry_tile.y].tile_overlay = TileOverlay.APPLE
            self.tiles_updated = True
            apples_to_spawn -= 1

        # Try to spawn apples in the surrounding adjacent tiles
        for x in (quarry_tile.x - 1, quarry_tile.x + 1):
            for y in (quarry_tile.y - 1, quarry_tile.y + 1):
                if 0 <= x < self.tiles_x and 0 <= y < self.tiles_y:
                    if self.tiles[x * self.tiles_x + y].tile_overlay == TileOverlay.NONE and apples_to_spawn > 0:
                        self.tiles[x * self.tiles_x + y].tile_overlay = TileOverlay.APPLE
                        self.tiles_updated = True
                        apples_to_spawn -= 1
                        if apples_to_spawn == 0:
                            return

    def _drop_item(self, robot_id: int, drop_tile: Tile):
        if drop_tile == self.castle_tile:
            self.points += POINTS_PER_APPLE
            self.agent_carrying[robot_id] = False
        elif self.tiles[drop_tile.x * self.tiles_x + drop_tile.y].tile_overlay == TileOverlay.NONE:
            self.tiles[drop_tile.x * self.tiles_x + drop_tile.y].tile_overlay = TileOverlay.APPLE
            self.agent_carrying[robot_id] = False

    def _pickup_item(self, robot_id: int, pickup_tile: Tile):
        if self.tiles[pickup_tile.x * self.tiles_x + pickup_tile.y].tile_overlay == TileOverlay.APPLE:
            self.agent_carrying[robot_id] = True
            self.tiles[pickup_tile.x * self.tiles_x + pickup_tile.y].tile_overlay = TileOverlay.NONE

    def _draw_tile(
        self,
        axes: Axes,
        tile: Tile,
        tile_state: TileState,
        width: float,
        height: float,
    ):
        """
        Draws a single tile on the given axes.

        Args:
            axes (Axes): The axes to draw the tile on.
            tile (Tile): The tile to draw.
            tile_state (TileState): The state of the tile.
            width (float): The width of the tile.
            height (float): The height of the tile.
        """
        # Draw the base tile
        img = Image.open(ASSETS_DIR + tile_state.tile_type.asset_name(tile.x + tile.y * self.tiles_x))
        arr = np.asarray(img)
        axes.imshow(
            arr,
            extent=(
                (tile.x * width) - 1.6,
                ((tile.x + 1) * width) - 1.6,
                (tile.y * height) - 1.0,
                ((tile.y + 1) * height) - 1.0
            ),
            origin="upper",
            zorder=0,
            interpolation="nearest",
            aspect="auto"
        )

        overlay_file = tile_state.tile_overlay.asset_name()
        if overlay_file is not None:
            img = Image.open(ASSETS_DIR + overlay_file)
            arr = np.asarray(img)
            axes.imshow(
                arr,
                extent=(
                    (tile.x * width) - 1.6,
                    ((tile.x + 1) * width) - 1.6,
                    (tile.y * height) - 1.0,
                    ((tile.y + 1) * height) - 1.0
                ),
                origin="upper",
                zorder=1,
                interpolation="nearest",
                aspect="auto"
            )
