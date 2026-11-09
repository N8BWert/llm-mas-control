"""
A simple GUI for LLM-based multi-agent control
"""

import html
import json
import threading
import time
from pathlib import Path

import pygame
import pygame_gui
from anthropic import Anthropic
from common.game_state import GameState
from common.publisher import Publisher
from common.subscriber import Subscriber
from dotenv import load_dotenv
from gui_common.gui import AGENT_NAMES, GUI

from gui_llm.memory import EventLog, Memory
from gui_llm.parsing import (
    build_llm_input,
    output_to_actions,
    parse_json_lenient,
    parse_json_strict,
    reference_errors,
    schema_errors,
)
from gui_llm.sequencer import Sequencer
from gui_llm.tools import TOOLS, execute_tool

# The number of attempts the LLM gets to produce a valid response
MAX_LLM_ATTEMPTS: int = 2
# The number of turns the LLM can spend calling tools before it must answer
MAX_TOOL_TURNS: int = 4


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
        self.prompt_history: list[str] = []  # unused for now
        self.response_history: list[str] = []  # unused for now
        self.event_log = EventLog()
        self.memory = Memory()
        self.sequencer = Sequencer(len(self.agent_action_queue))

        # The log of previous chat messages, scrollable
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

        HERE = Path(__file__).resolve().parent
        self.system_prompt = (HERE / "schemae" / "system_prompt.md").read_text()
        self.input_schema = json.loads((HERE / "schemae" / "input_schema.json").read_text())
        self.output_schema = json.loads((HERE / "schemae" / "output_schema.json").read_text())

        load_dotenv()
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY
        self.base_kwargs = {
            "model":"claude-haiku-5-5",
            "max_tokens":4000,
        }
        # Set while a request is in flight; the worker hands its outcome back through llm_result
        self.llm_busy: bool = False
        self.llm_result: dict | None = None

    def handle_input(self, event: pygame.event.Event, game_state: GameState | None):
        """
        Handling all pygame window events.
        For LLM GUI, we're just trying to capture whenever the user submits something to the LLM. 
        """
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
            return  # Don't forward the key, the text box would add a newline
        self.gui_manager.process_events(event)

    def tick(self, game_state: GameState):
        """
        Every tick
        1. Log what changed in the game
        2. Check for llm completion
        3. Advance the sequencer and mirror it into the action queues
        4. Draw the GUI
        """
        self.event_log.observe(game_state, time.monotonic())
        # Parse LLM output
        if self.llm_result is not None:
            result, self.llm_result = self.llm_result, None
            self._handle_llm_result(result)
        # Sequencing
        self.sequencer.update(game_state)
        self.sequencer.sync(self.agent_action_queue)
        # GUI
        self.gui_manager.update(self.clock.get_time() / 1000.0)
        self.gui_manager.draw_ui(self.screen)

    def _post_message(self, sender: str, message: str):
        """
        Append a message to the chat log.
        """
        self.chat_log.append_html_text(f"<b>{sender}:</b> {html.escape(message)}<br>")

    def _submit(self):
        """
        Remit a command to the LLM.
        """
        message = self.entry.get_text().strip()
        if not message:
            pass
        else:
            if self.game_state is None:
                self._post_message("LLM", "Still waiting for the game to start.")
            elif self.llm_busy or self.llm_result is not None:  # A waiting result isn't in memory yet
                self._post_message("LLM", "Still working on your last order.")
            else:
                self._post_message("You", message)
                self.prompt_history.append(message)
                self.entry.set_text("")

                now = time.monotonic()
                state, entity_tiles, locations = build_llm_input(
                    message,
                    self.game_state,
                    self.agent_action_queue,
                    self.event_log.recent(now),
                    self.memory.snapshot(now),
                    self.sequencer.looping_ids(),
                )
                self.llm_busy = True
                threading.Thread(
                    target=self._query_llm,
                    args=(state, entity_tiles, locations, self.game_state),
                    daemon=True,
                ).start()
        self.entry.focus()

    def _query_llm(self, state: dict, entity_tiles: dict, locations: dict, game_state: GameState):
        """
        Proper usage: raise llm_busy=True, then run this on a thread.
        This just queries the LLM asynchronously (should I use promises?).
        Once a return occurs, tick() will parse it on the next frame.
        """
        try:
            messages = [{"role": "user", "content": json.dumps(state)}]
            tool_turns = 0
            attempts = 0
            # Every request either spends a tool turn or a validation attempt
            for _ in range(MAX_TOOL_TURNS + MAX_LLM_ATTEMPTS):
                response = self.client.messages.create(
                    **self.base_kwargs,
                    system=self.system_prompt,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice={"type": "auto" if tool_turns < MAX_TOOL_TURNS else "none"},
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "tool_use":
                    tool_turns += 1
                    messages.append({"role": "user", "content": self._run_tools(response, state, locations, game_state)})
                    continue
                if response.stop_reason != "end_turn":
                    self.llm_result = {"error": f"The LLM stopped early ({response.stop_reason})."}
                    return

                attempts += 1
                text = "".join(block.text for block in response.content if block.type == "text")
                self.response_history.append(text)
                out, actions, errors = self._parse_llm_response(text, state, entity_tiles, game_state)
                if not errors:
                    self.llm_result = {"out": out, "actions": actions, "user_text": state["request"]["text"]}
                    return
                if attempts >= MAX_LLM_ATTEMPTS:
                    self.llm_result = {"error": "I couldn't turn that into a valid order: " + "; ".join(errors)}
                    return
                messages.append({
                    "role": "user",
                    "content": "Your response was rejected. Respond again with the corrected JSON object only. Errors:\n"
                        + "\n".join(errors),
                })
            self.llm_result = {"error": "The LLM didn't finish answering."}
        except Exception as e:  # Anything uncaught would die silently on this thread
            self.llm_result = {"error": f"The LLM request failed: {e}"}
        finally:
            self.llm_busy = False

    def _run_tools(self, response, state: dict, locations: dict, game_state: GameState) -> list[dict]:
        """
        Runs every tool call in a response.

        Returns:
            One tool_result block per call, to send back together in a single message.
        """
        results = []
        for block in response.content:
            if block.type == "tool_use":
                content, is_error = execute_tool(block.name, block.input, state, locations, game_state)
                self.response_history.append(json.dumps({"tool": block.name, "input": block.input, "result": content}))
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                })
        return results

    def _parse_llm_response(self, text: str, state: dict, entity_tiles: dict, game_state: GameState):
        """
        Returns:
            The parsed output, its translated actions, and why it was rejected (if it was).
        """
        out = parse_json_strict(text)
        if out is None:
            out = parse_json_lenient(text)
        if out is None:
            return None, None, ["The response is not a JSON object."]
        errors = schema_errors(out, self.output_schema) or reference_errors(state, out)
        if errors:
            return out, None, errors
        try:
            return out, output_to_actions(out, entity_tiles, game_state), []
        except ValueError as e:
            return out, None, [str(e)]

    def _handle_llm_result(self, result: dict):
        """
        Turns LLM output into actions for the ants.
        """
        if "error" in result:
            self._post_message("LLM", result["error"])
            return

        out = result["out"]
        self.memory.record(result["user_text"], out, time.monotonic())
        for cancel in out["cancels"]:
            for name in cancel["subjects"]:
                agent_id = AGENT_NAMES.index(name)
                if cancel["scope"] == "all":
                    self.sequencer.cancel_all(agent_id)
                elif cancel["scope"] == "current":
                    self.sequencer.cancel_current(agent_id)
                else:
                    self.sequencer.cancel_ids(agent_id, cancel["command_ids"])
        for agent_id, mode, loop, actions in result["actions"]:
            if mode == "replace":
                self.sequencer.replace(agent_id, actions, loop)
            else:
                self.sequencer.append(agent_id, actions, loop)

        self._post_message("LLM", out["summary"])
        for unhandled in out["unhandled"]:
            self._post_message("LLM", f"Skipped: {unhandled}")
