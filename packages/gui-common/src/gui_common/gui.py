"""
The abstract base class for the llm-mas-control GUI
"""

import os
from abc import ABC, abstractmethod

import numpy as np
import pygame
from common.agent_action import (
    AgentAction,
    AgentActionRequest,
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
from common.tile import Tile, TileOverlay, TileType

# The assets directory
ASSETS_DIR: str = f"{os.path.dirname(os.path.abspath(__file__))}/../../../../assets/sprites/"
# The name of each agent in the game
AGENT_NAMES: list[str] = [
    "Willy",
    "Rudy",
    "Chris",
    "Buzz",
    "Bob",
    "Levi",
    "Sally",
    "Sue",
    "Alice",
    "Zeke",
]


class GUI(ABC):
    """
    An abstract base class for the llm-mas-control GUI so we
    can reuse components as much as possible 
    """

    SCREEN_WIDTH: int = 2400
    SCREEN_HEIGHT: int = 1200
    WINDOW_TITLE: str = "Age of Ants"
    GAME_WIDTH: int = 1600
    GAME_HEIGHT: int = 970
    GAME_X_OFFSET: int = (SCREEN_WIDTH - GAME_WIDTH) // 2
    GAME_Y_OFFSET: int = 0
    GAME_PADDING: int = 10
    # GAME_Y_OFFSET: int = (SCREEN_HEIGHT - GAME_HEIGHT) // 2 - 50
    SIDEBAR_WIDTH: int = (SCREEN_WIDTH - GAME_WIDTH) // 2 - GAME_PADDING * 2
    SIDEBAR_HEIGHT: int = SCREEN_HEIGHT

    # The width of the robotarium testbed in meters
    ROBOTARIUM_WIDTH: float = 3.2 
    PIXELS_PER_METER_WIDTH: float = GAME_WIDTH / ROBOTARIUM_WIDTH
    ROBOT_WIDTH_PIXELS: float = 0.2 * PIXELS_PER_METER_WIDTH
    # The height of the robotarium testbed in meters
    ROBOTARIUM_HEIGHT: float = 2.0
    PIXELS_PER_METER_HEIGHT: float = GAME_HEIGHT / ROBOTARIUM_HEIGHT
    ROBOT_HEIGHT_PIXELS: float = 0.2 * PIXELS_PER_METER_HEIGHT

    BACKGROUND_BROWN: tuple[int, int, int] = (0x6b, 0x4f, 0x09)

    def __init__(
        self,
        game_state_subscriber: Subscriber,
        agent_action_publisher: Publisher,
    ):
        # Initialize pygame
        pygame.init()
        pygame.display.set_caption(self.WINDOW_TITLE)
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # The current state of the game
        self.game_state: GameState | None = None
        self.game_state_subscriber = game_state_subscriber

        # The publisher for the current agent action
        self.agent_action_publisher = agent_action_publisher
        self.agent_action_queue: list[list[AgentAction]] = [[] for _ in range(10)]
        self.agent_pixel_positions: list[tuple[int, int]] = [(0, 0) for _ in range(10)]

        # Load our tiles
        self.tile_type_surfaces, self.tile_overlay_surfaces = self._load_tiles()
        self.shadow_tile_surfaces = self._load_shadow_tiles()
        self.agent_surfaces = self._load_agents()
        self.icon_surfaces = self._load_icons()
        self.agent_font = pygame.font.Font(None, 24)
        self.selected_agents = set()

        self.running = False

    def run(self):
        self.running = True
        while self.running:
            # Update the game state from the subscriber
            self.game_state = self.game_state_subscriber.receive()
            if self.game_state is not None:
                alive_ids = set(agent_state.id for agent_state in self.game_state.agent_states)
                # Remove any agents from the action queue that are no longer alive
                for agent_id in range(len(self.agent_action_queue)):
                    if agent_id not in alive_ids:
                        self.agent_action_queue[agent_id] = []

            # Handle events from pygame
            for event in pygame.event.get():
                self.handle_input(event, self.game_state)

            # Fill the screen with a gray background
            self.screen.fill((50, 50, 50))

            # Draw the game state as received from the current publisher
            if self.game_state is not None:
                self._draw_game_state(self.game_state)
            else:
                # TODO: Draw loading screen
                pass

            if self.game_state is not None:
                self._draw_points_sidebar(self.game_state.points)
                self._draw_right_sidebar(self.agent_action_queue, self.game_state)
            else:
                self._draw_points_sidebar(0)

            # Publish the current actions for the agents to take
            self.publish_agent_actions(self.agent_action_publisher)

            if self.game_state is not None:
                self.tick(self.game_state)

            # Render the game and run at 30Hz
            pygame.display.flip()
            self.clock.tick(30)

    @abstractmethod
    def handle_input(self, event: pygame.event.Event, game_state: GameState | None):
        """
        Handle input events from the user interacting with pygame

        Args:
            event (pygame.event.Event): The event to handle
        """
        ...

    @abstractmethod
    def tick(self, game_state: GameState):
        """
        Update the GUI based on the current game state (this is mostly for removing
        actions from the queue when they are completed)

        Args:
            game_state (GameState): The current state of the game
        """
        ...

    def publish_agent_actions(self, publisher: Publisher):
        """
        Publish the current actions for the agents to take

        Args:
            publisher (Publisher): The publisher to use for publishing the actions
        """
        actions: list[AgentAction] = []
        for agent_actions in self.agent_action_queue:
            if agent_actions:
                actions.append(agent_actions[0])
        publisher.send(AgentActionRequest(agent_actions=actions))

    def _load_tiles(self) -> tuple[dict[TileType, list[pygame.Surface]], dict[TileOverlay, pygame.Surface | None]]:
        """
        Load the tile assets from the assets directory 

        Returns:
            A tuple containing two dictionaries: one for the tile types and one for the tile overlays.
        """
        tile_types: dict[TileType, list[pygame.Surface]] = {}
        for tile_type in TileType:
            if tile_type == TileType.EMPTY:
                tile_types[tile_type] = []
                filenames = [
                    tile_type.asset_name(0),
                    tile_type.asset_name(1)
                ]
                for filename in filenames:
                    img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
                    tile_types[tile_type].append(img)
            else:
                filename = tile_type.asset_name(0)
                img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
                tile_types[tile_type] = [img]

        tile_overlays: dict[TileOverlay, pygame.Surface | None] = {}
        for tile_overlay in TileOverlay:
            filename = tile_overlay.asset_name()
            if filename is not None:
                img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
                tile_overlays[tile_overlay] = img
            else:
                tile_overlays[tile_overlay] = None

        return tile_types, tile_overlays

    def _load_shadow_tiles(self) -> dict[TileType, pygame.Surface]:
        """
        Load the shadow form of each tile from the assets directory

        Returns:
            A dictionary mapping from tile types to the relative shadow tile type 
        """
        shadow_tiles: dict[TileType, pygame.Surface] = {}
        for tile_type in TileType:
            filename = tile_type.asset_name(0)
            img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()

            grayscale_img = pygame.transform.grayscale(img)
            shadow_tiles[tile_type] = grayscale_img
        return shadow_tiles

    def _load_agents(self) -> list[pygame.Surface]:
        """
        Load the agent assets from the assets directory 

        Returns:
            A list of pygame surfaces for the agents
        """
        agent_surfaces: list[pygame.Surface] = []

        # Load base ant image
        filename = f"Ant.png"
        img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
        agent_surfaces.append(img)

        # Load ant with apple image
        filename = f"AntWithApple.png"
        img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
        agent_surfaces.append(img)

        return agent_surfaces

    def _load_icons(self) -> dict[type, pygame.Surface]:
        """
        Loads the icons for each action the agents can take. 
        """
        actions = [
            BuildFarmAction,
            BuildHouseAction,
            BuildQuarryAction,
            DropAction,
            FarmAction,
            MineAction,
            MoveAction,
            PickUpAction
        ]
        icon_filenames = [
            "BuildFarmActionIcon.png",
            "BuildHouseActionIcon.png",
            "BuildQuarryActionIcon.png",
            "DropActionIcon.png",
            "FarmActionIcon.png",
            "MineActionIcon.png",
            "MoveActionIcon.png",
            "PickUpActionIcon.png"
        ]

        action_cards: dict[type, pygame.Surface] = {}
        for action, filename in zip(actions, icon_filenames):
            img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
            action_cards[action] = img
        return action_cards

    def _draw_game_state(self, game_state: GameState):
        """
        Draw the current state of the game where the screen is layed out such that tile (0, 0) is in the
        bottom left corner and tile (width - 1, height - 1) is in the top right corner. 
        """
        cell_w = self.GAME_WIDTH // game_state.width
        cell_h = self.GAME_HEIGHT // game_state.height

        self.shadow_farm_tiles = set()
        self.shadow_house_tiles = set()
        self.shadow_quarry_tiles = set()
        for agent_id in range(len(game_state.agent_states)):
            if self.agent_action_queue[agent_id]:
                match self.agent_action_queue[agent_id][0].action:
                    case BuildFarmAction(tile):
                        self.shadow_farm_tiles.add((tile.x, tile.y))
                    case BuildHouseAction(tile):
                        self.shadow_house_tiles.add((tile.x, tile.y))
                    case BuildQuarryAction(tile):
                        self.shadow_quarry_tiles.add((tile.x, tile.y))

        # Draw the tiles
        for x in range(game_state.width):
            for y in range(game_state.height):
                if (x, y) in self.shadow_farm_tiles and game_state.tile_states[x + y * game_state.width].tile_type != TileType.FARM:
                    surface_tile = [self.shadow_tile_surfaces[TileType.FARM]]
                elif (x, y) in self.shadow_house_tiles and game_state.tile_states[x + y * game_state.width].tile_type != TileType.HOUSE:
                    surface_tile = [self.shadow_tile_surfaces[TileType.HOUSE]]
                elif (x, y) in self.shadow_quarry_tiles and game_state.tile_states[x + y * game_state.width].tile_type != TileType.QUARRY:
                    surface_tile = [self.shadow_tile_surfaces[TileType.QUARRY]]
                else:
                    surface_tile = self.tile_type_surfaces[game_state.tile_states[x + y * game_state.width].tile_type]
                if len(surface_tile) > 1:
                    surface_tile = [surface_tile[x % 2]]
                surface_tile = pygame.transform.scale(
                    surface_tile[0],
                    (cell_w, cell_h)
                )
                self.screen.blit(surface_tile, (self.GAME_X_OFFSET + x * cell_w, self.GAME_Y_OFFSET + (game_state.height - 1 - y) * cell_h))

                overlay_tile = self.tile_overlay_surfaces[game_state.tile_states[x + y * game_state.width].tile_overlay]
                if overlay_tile is not None:
                    overlay_tile = pygame.transform.scale(overlay_tile, (cell_w, cell_h))
                    self.screen.blit(overlay_tile, (self.GAME_X_OFFSET + x * cell_w, self.GAME_Y_OFFSET + (game_state.height - 1 - y) * cell_h))

        # Draw vertical and horizontal lines
        for x in range(game_state.width + 1):
            pygame.draw.line(
                self.screen,
                (0, 0, 0),
                (self.GAME_X_OFFSET + x * cell_w, self.GAME_Y_OFFSET),
                (self.GAME_X_OFFSET + x * cell_w, self.GAME_Y_OFFSET + self.GAME_HEIGHT),
                2
            )
        for y in range(game_state.height + 1):
            pygame.draw.line(
                self.screen,
                (0, 0, 0),
                (self.GAME_X_OFFSET, self.GAME_Y_OFFSET + y * cell_h),
                (self.GAME_X_OFFSET + self.GAME_WIDTH, self.GAME_Y_OFFSET + y * cell_h),
                2
            )

        # Letters horizontal and numbers vertical
        for x in range(game_state.width):
            letter = chr(ord('A') + x)
            text = self.agent_font.render(letter, True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.GAME_X_OFFSET + x * cell_w + cell_w // 2, self.GAME_Y_OFFSET + self.GAME_HEIGHT + 10))
            self.screen.blit(text, text_rect)
        for y in range(game_state.height):
            number = str(y + 1)
            text = self.agent_font.render(number, True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.GAME_X_OFFSET - 10, self.GAME_Y_OFFSET + (game_state.height - 1 - y) * cell_h + cell_h // 2))
            self.screen.blit(text, text_rect)

        # Draw the agents
        for agent_state in game_state.agent_states:
            surface = self.agent_surfaces[1] if agent_state.carrying_apple else self.agent_surfaces[0]
            surface = pygame.transform.scale(surface, (self.ROBOT_WIDTH_PIXELS, self.ROBOT_HEIGHT_PIXELS))
            if -np.pi / 2 <= agent_state.orientation <= np.pi / 2:
                # Flip the image if the agent is facing right
                surface = pygame.transform.flip(surface, True, False)
                surface = pygame.transform.rotate(surface, np.degrees(agent_state.orientation))
            else:
                surface = pygame.transform.rotate(surface, np.degrees(agent_state.orientation + np.pi))
            # Draw the agent
            x = self.GAME_X_OFFSET + ((agent_state.position[0] + self.ROBOTARIUM_WIDTH / 2) * self.PIXELS_PER_METER_WIDTH) - self.ROBOT_WIDTH_PIXELS // 2
            y = self.GAME_HEIGHT + self.GAME_Y_OFFSET - ((agent_state.position[1] + self.ROBOTARIUM_HEIGHT / 2) * self.PIXELS_PER_METER_HEIGHT) - self.ROBOT_HEIGHT_PIXELS // 2
            self.screen.blit(surface, (x, y))
            self.agent_pixel_positions[agent_state.id] = (x, y)

            # Draw the agent's name
            rect = surface.get_rect(topleft=(x, y))
            self.screen.blit(surface, rect)
            shadow = self.agent_font.render(AGENT_NAMES[agent_state.id], True, (0, 0, 0))
            if agent_state.id in self.selected_agents:
                text = self.agent_font.render(AGENT_NAMES[agent_state.id], True, (255, 0, 0))
            else:
                text = self.agent_font.render(AGENT_NAMES[agent_state.id], True, (255, 255, 255))
            text_rect = text.get_rect(midbottom=(rect.centerx, rect.top+8))
            self.screen.blit(shadow, (text_rect.x + 1, text_rect.y + 1))
            self.screen.blit(text, text_rect)

    def _draw_points_sidebar(self, points: int):
        """
        Draw the points sidebar on the left side of the screen
        """

        sidebar_x = 0
        sidebar_y = 0

        # Draw the points text
        points_text = self.agent_font.render(f"Points: {points}", True, (255, 255, 255))
        points_rect = points_text.get_rect(center=(sidebar_x + self.SIDEBAR_WIDTH // 2, sidebar_y + 30))
        self.screen.blit(points_text, points_rect)

    def _draw_right_sidebar(self, agent_action_queue: list[list[AgentAction]], game_state: GameState):
        """
        Draw the right sidebar on the right side of the game with the queued agent actions
        for each agent. 

        Args:
            agent_action_queue (list[list[AgentAction]]): The queued agent actions for each agent
        """

        sidebar_x = self.GAME_X_OFFSET + self.GAME_WIDTH + self.GAME_PADDING
        sidebar_y = 0

        # Draw the actions for each agent
        for agent_id, actions in enumerate(agent_action_queue):
            # Draw a brown background rectangle for the agent
            agent_rect = pygame.Rect(
                sidebar_x,
                sidebar_y + agent_id * 60,
                self.SIDEBAR_WIDTH,
                50
            )
            pygame.draw.rect(self.screen, self.BACKGROUND_BROWN, agent_rect)
            # Check if agent is included in the game state
            if any(agent_state.id == agent_id for agent_state in game_state.agent_states):
                # draw the agent ID in the top left corner of the rectangle
                agent_id_text = self.agent_font.render(f"{AGENT_NAMES[agent_id]}:", True, (255, 255, 255))
                self.screen.blit(agent_id_text, (sidebar_x + 10, sidebar_y + agent_id * 60 + 20))
                # Draw the queued actions for the agent
                for action_id, action in enumerate(actions[:4]):
                    if action is not None:
                        # Draw the action icon
                        icon_surface = self.icon_surfaces[type(action.action)]
                        icon_surface = pygame.transform.scale(icon_surface, (30, 30))
                        self.screen.blit(icon_surface, (sidebar_x + 70 + action_id * 30, sidebar_y + agent_id * 60 + 10))
            else:
                # Draw the agent ID in the top left corner of the rectangle
                agent_id_text = self.agent_font.render(f"{agent_id}: (dead)", True, (255, 0, 0))
                self.screen.blit(agent_id_text, (sidebar_x + 10, sidebar_y + agent_id * 60 + 20))
