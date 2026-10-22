"""
A simple GUI for LLM-based multi-agent control
"""

import pygame
from common.game_state import GameState
from common.publisher import Publisher
from common.subscriber import Subscriber
from gui_common.gui import GUI


class LLMGui(GUI):
    """
    A simple GUI for LLM-based multi-agent control. 
    """

    def __init__(
        self,
        game_state_subscriber: Subscriber,
        game_action_publisher: Publisher,
    ):
        super().__init__(game_state_subscriber, game_action_publisher)
        self.current_prompt: str = ""

    def handle_input(self, event: pygame.event.Event, game_state: GameState | None):
        pass

    def tick(self, game_state: GameState):
        for agent_state in game_state.agent_states:
            # Pop the most recent action if the agent is no longer busy
            if not agent_state.busy and self.agent_action_queue[agent_state.id]:
                self.agent_action_queue[agent_state.id].pop(0)
        self._draw_llm_bar()

    def _draw_llm_bar(self):
        """
        Draw the bottom LLM bar onto the screen that contains the actions
        that the agents can take. 
        """
        pass
