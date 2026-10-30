"""
A simple GUI for LLM-based multi-agent control
"""

import pygame
import pygame_gui
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
        self.gui_manager = pygame_gui.UIManager((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        self.current_prompt: str = ""
        self.events = []
        self.prompt_history: list[str] = []
        self.response_history: list[str] = []

        # THe log of previous chat messages, scrollable
        self.chat_log = pygame_gui.elements.UITextBox(
            html_text="<i>Welcome to the Age of Ants!</i><br>",
            relative_rect=pygame.Rect(10, 50, self.SIDEBAR_WIDTH - 10, self.SIDEBAR_HEIGHT - 300),
            manager=self.gui_manager,
        )

        # Input line and send button
        self.entry = pygame_gui.elements.UITextEntryBox(
            relative_rect=pygame.Rect(10, self.SIDEBAR_HEIGHT - 240, self.SIDEBAR_WIDTH - 50, 230),
            manager=self.gui_manager,
        )
        self.send_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.SIDEBAR_WIDTH - 40, self.SIDEBAR_HEIGHT - 240, 40, 230),
            text=">",
            manager=self.gui_manager,
        )

    def handle_input(self, event: pygame.event.Event, game_state: GameState | None):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.entry:
            self._submit()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.send_button:
            self._submit()
        elif (event.type == pygame.KEYDOWN
            and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
            and self.entry.is_focused
            and not (event.mod & pygame.KMOD_SHIFT)
        ):
            self._submit()
        self.gui_manager.process_events(event)

    def tick(self, game_state: GameState):
        for agent_state in game_state.agent_states:
            # Pop the most recent action if the agent is no longer busy
            if not agent_state.busy and self.agent_action_queue[agent_state.id]:
                self.agent_action_queue[agent_state.id].pop(0)
        self.gui_manager.update(self.clock.get_time() / 1000.0)
        self.gui_manager.draw_ui(self.screen)

    def _post_message(self, sender: str, message: str):
        self.chat_log.html_text += f"<b>{sender}:</b> {message}<br>"
        self.chat_log.rebuild()

    def _submit(self):
        message = self.entry.get_text().strip()
        if message:
            self._post_message("You", message)
            self.prompt_history.append(message)
            self.entry.set_text("")

            # TODO: Get the response from the LLM and add it to the response history
            response = f"Response to: {message}"
            self.response_history.append(response)
            self._post_message("LLM", response)
        self.entry.focus()
