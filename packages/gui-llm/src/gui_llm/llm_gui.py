"""
A simple GUI for LLM-based multi-agent control
"""

import pygame
from common.game_state import GameState
from common.publisher import Publisher
from common.subscriber import Subscriber
from gui_common.gui import GUI

from dotenv import load_dotenv
from anthropic import Anthropic
from pathlib import Path
import json


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

        HERE = Path(__file__).resolve().parent
        self.system_prompt = (HERE / "schemae" / "system_prompt.md").read_text()
        self.input_schema = json.loads((HERE / "schemae" / "input_schema.json").read_text())
        self.output_schema = json.loads((HERE / "schemae" / "output_schema.json").read_text())

        load_dotenv()
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY
        self.base_kwargs = {
            "model":"claude-haiku-5-5",
            "max_tokens":1500,
        }

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
