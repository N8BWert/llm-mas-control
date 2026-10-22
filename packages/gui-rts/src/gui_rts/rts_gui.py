"""
A simple RTS-style GUI for Age of Ants
"""

import os

import pygame
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
from common.tile import Tile
from gui_common.gui import GUI

# The assets directory
ASSETS_DIR: str = f"{os.path.dirname(os.path.abspath(__file__))}/../../../../assets/sprites/"


class RtsGui(GUI):
    """
    A simple rts-style GUI for Age of Ants. 
    """

    ACTION_BAR_X: int = GUI.GAME_X_OFFSET
    ACTION_BAR_Y: int = GUI.GAME_Y_OFFSET + GUI.GAME_HEIGHT
    ACTION_BAR_WIDTH: int = GUI.GAME_WIDTH
    ACTION_BAR_HEIGHT: int = GUI.SCREEN_HEIGHT - ACTION_BAR_Y
    BUSY_WAIT_TICKS: int = 60

    def __init__(
        self,
        game_state_subscriber: Subscriber,
        game_action_publisher: Publisher,
    ):
        super().__init__(game_state_subscriber, game_action_publisher)
        self.actions = [
            BuildFarmAction,
            BuildHouseAction,
            BuildQuarryAction,
            DropAction,
            FarmAction,
            MineAction,
            MoveAction,
            PickUpAction
        ]
        self.card_surfaces = self._load_action_cards()
        self.waited_ticks = [0 for _ in range(len(self.agent_action_queue))]
        self.selected_card: int | None = None

    def handle_input(self, event: pygame.event.Event, game_state: GameState | None):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and (event.button == 2 or event.button == 3):
            # Right or Middle Click: Deselect all agents and cards
            self.selected_agents = []
            self.selected_card = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            mods = pygame.key.get_mods()

            # Check for a click in the game area
            if self.GAME_X_OFFSET <= x <= self.GAME_X_OFFSET + self.GAME_WIDTH and \
                    self.GAME_Y_OFFSET <= y <= self.GAME_Y_OFFSET + self.GAME_HEIGHT:
                if (agent_id := self._clicking_agent(x, y)) is not None:
                    if mods & pygame.KMOD_SHIFT:
                        # Shift + Left Click: Add the agent to the list of selected agents
                        if agent_id not in self.selected_agents:
                            self.selected_agents.append(agent_id)
                    else:
                        # Left Click: Select only this agent
                        self.selected_agents = [agent_id]
                elif self.selected_card is not None and self.selected_agents:
                    # Select the tile in the game area and set thea action
                    # for the selected agents to take on that tile
                    if self.actions[self.selected_card] == MoveAction:
                        position = self._pixel_to_position(x, y)
                        action = self.actions[self.selected_card](position)
                        for agent_id in self.selected_agents:
                            self.agent_action_queue[agent_id] = [AgentAction(agent_id=agent_id, action=action)]
                    elif (tile := self._clicking_tile(x, y, game_state)) is not None:
                        action = self.actions[self.selected_card](tile)
                        for agent_id in self.selected_agents:
                            self.agent_action_queue[agent_id] = [AgentAction(agent_id=agent_id, action=action)]
            elif self.ACTION_BAR_X <= x <= self.ACTION_BAR_X + self.ACTION_BAR_WIDTH and \
                    self.ACTION_BAR_Y <= y <= self.ACTION_BAR_Y + self.ACTION_BAR_HEIGHT:
                # Check for a click in the action bar
                card_width = self.ACTION_BAR_WIDTH // len(self.card_surfaces)
                card_index = (x - self.ACTION_BAR_X) // card_width
                if card_index < len(self.card_surfaces):
                    if self.selected_card == card_index:
                        # Deselect the card if it was already selected
                        self.selected_card = None
                    else:
                        # Select the card
                        self.selected_card = card_index
            else:
                # Clicked somewhere else, deselect all agents and cards
                self.selected_agents = []
                self.selected_card = None


    def tick(self, game_state: GameState):
        self._draw_action_bar()

    def _load_action_cards(self) -> dict[type, pygame.Surface]:
        """
        Load the different action executable cards for the agents to take. 
        """
        card_filenames = [
            "BuildFarmActionCard.png",
            "BuildHouseActionCard.png",
            "BuildQuarryActionCard.png",
            "DropActionCard.png",
            "FarmActionCard.png",
            "MineActionCard.png",
            "MoveActionCard.png",
            "PickUpActionCard.png"
        ]

        action_cards: dict[type, pygame.Surface] = {}
        for action, filename in zip(self.actions, card_filenames):
            img = pygame.image.load(ASSETS_DIR + filename).convert_alpha()
            action_cards[action] = img
        return action_cards

    def _draw_action_bar(self):
        """
        Draw the bottom action bar onto the screen that contains the actions
        that the agents can take. 
        """
        card_width = self.ACTION_BAR_WIDTH // len(self.card_surfaces)
        for i, (_, card_surface) in enumerate(self.card_surfaces.items()):
            if self.selected_card == i:
                # Draw a border around the selected card
                border_rect = pygame.Rect(
                    self.ACTION_BAR_X + i * card_width,
                    self.ACTION_BAR_Y,
                    card_width,
                    self.ACTION_BAR_HEIGHT
                )
                pygame.draw.rect(self.screen, (255, 255, 0), border_rect, 5)
            tile = pygame.transform.scale(card_surface, (card_width, self.ACTION_BAR_HEIGHT))
            x = self.ACTION_BAR_X + i * (self.ACTION_BAR_WIDTH // len(self.card_surfaces))
            y = self.ACTION_BAR_Y
            self.screen.blit(tile, (x, y))

    def _clicking_agent(self, x: int, y: int) -> int | None:
        """
        Check if the user is clicking on an agent in the game area. 
        Returns the agent ID if so, otherwise None. 
        """
        for agent_id, pixel_position in enumerate(self.agent_pixel_positions):
            agent_x, agent_y = pixel_position
            agent_rect = pygame.Rect(agent_x, agent_y, 50, 50)
            if agent_rect.collidepoint(x, y):
                return agent_id
        return None

    def _clicking_tile(self, x: int, y: int, game_state: GameState) -> Tile | None:
        """
        Check if the user is clicking on a tile in the game area. 
        Returns the tile if so, otherwise None. 
        """
        cell_w = self.GAME_WIDTH / game_state.width
        cell_h = self.GAME_HEIGHT / game_state.height
        x_index = int((x - self.GAME_X_OFFSET) // cell_w)
        y_index = int((y - self.GAME_Y_OFFSET) // cell_h)

        if 0 <= x_index < game_state.width and 0 <= y_index < game_state.height:
            return Tile(x_index, game_state.height - 1 - y_index)
        return None

    def _pixel_to_position(self, x: int, y: int) -> tuple[float, float]:
        """
        Convert pixel coordinates to game coordinates. 
        """
        x = (x - self.GAME_X_OFFSET) / self.PIXELS_PER_METER_WIDTH - 1.6
        y = (y - self.GAME_Y_OFFSET) / self.PIXELS_PER_METER_HEIGHT - 1.0
        return x, -y
