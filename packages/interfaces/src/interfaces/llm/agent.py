"""
The LLM agent turns the operator's strategy into robot commands. It plans
when the strategy changes, when a new constraint becomes active, and
periodically while robots sit idle. Plans are single LiteLLM completions with
tool calls; each tool call becomes command-queue entries.
"""

import asyncio
import json
import logging
import time
from collections import deque
from typing import Awaitable, Callable, Optional

from interfaces.commands import CommandQueue
from interfaces.llm.prompt import build_messages
from interfaces.llm.tools import TOOLS, apply_tool_call

log = logging.getLogger(__name__)

LOG_SIZE = 50


async def _litellm_completion(**kwargs):
    import litellm

    return await litellm.acompletion(**kwargs)


class LlmAgent:
    def __init__(
        self,
        queue: CommandQueue,
        model: str,
        replan_s: float,
        broadcast: Callable[[dict], Awaitable[None]],
        completion: Callable[..., Awaitable] = _litellm_completion,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.queue = queue
        self.model = model
        self.replan_s = replan_s
        self._broadcast = broadcast
        self._completion = completion
        self._clock = clock
        self.reset()

    def reset(self):
        if getattr(self, "_task", None) is not None:
            self._task.cancel()
        self.strategy = ""
        self.paused = False
        self.status = "idle"
        self.error = ""
        self.log: deque[dict] = deque(maxlen=LOG_SIZE)
        self._task: Optional[asyncio.Task] = None
        self._view: Optional[dict] = None
        self._known_constraints: set[str] = set()
        self._last_plan = -float("inf")

    def snapshot(self) -> dict:
        return {
            "model": self.model,
            "strategy": self.strategy,
            "paused": self.paused,
            "status": self.status,
            "error": self.error,
            "log": list(self.log),
        }

    def _note(self, role: str, text: str):
        self.log.append({"t": time.time(), "role": role, "text": text})

    async def _publish(self):
        await self._broadcast({"type": "llm", "data": self.snapshot()})

    # --- operator input ------------------------------------------------------

    async def set_strategy(self, text: str):
        self.strategy = text.strip()
        self.paused = False
        self._note("operator", self.strategy)
        await self._publish()
        if self.strategy:
            self.request_plan("The operator gave a new strategy.")

    def halt(self, reason: str):
        """Stop planning (e.g. on an emergency) until a new strategy is given."""
        if self._task is not None:
            self._task.cancel()
            self._task = None
        if self.strategy and not self.paused:
            self.paused = True
            self.status = "paused"
            self._note("system", f"{reason}: planning paused until a new strategy is given.")
            asyncio.ensure_future(self._publish())

    # --- planning ------------------------------------------------------------

    def observe(self, view: dict):
        """Called every tick with the latest view; triggers re-plans when needed."""
        self._view = view
        constraint_ids = {c["id"] for c in view.get("active_constraints", [])}
        new_constraints = constraint_ids - self._known_constraints
        self._known_constraints = constraint_ids
        if not self.strategy or self.paused or view.get("game_over"):
            return
        if new_constraints:
            names = [c["label"] for c in view["active_constraints"] if c["id"] in new_constraints]
            self.request_plan(f"New constraint(s) became active: {', '.join(names)}.")
        elif self._idle_robots(view) and self._clock() - self._last_plan >= self.replan_s:
            self.request_plan(f"Robots {self._idle_robots(view)} are idle with no commands.")

    def _idle_robots(self, view: dict) -> list[int]:
        return [
            a["id"] for a in view["agent_states"]
            if not a["failure"] and not a["busy"] and self.queue.is_idle(a["id"])
        ]

    def request_plan(self, reason: str):
        if self._view is None or (self._task is not None and not self._task.done()):
            return
        self._last_plan = self._clock()
        self._task = asyncio.create_task(self._plan(reason))

    async def _plan(self, reason: str):
        view = self._view
        self.status = "planning"
        self.error = ""
        await self._publish()
        try:
            response = await self._completion(
                model=self.model,
                messages=build_messages(self.strategy, view, reason),
                tools=TOOLS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            if message.content:
                self._note("llm", message.content.strip())
            available = {a["id"] for a in view["agent_states"] if not a["failure"]}
            for call in message.tool_calls or []:
                try:
                    args = json.loads(call.function.arguments or "{}")
                    summary = apply_tool_call(call.function.name, args, self.queue, available)
                    self._note("action", summary)
                except (ValueError, KeyError, json.JSONDecodeError) as error:
                    self._note("error", f"Rejected {call.function.name}: {error}")
            self.status = "idle"
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.warning("LLM planning failed: %s", error)
            self.status = "error"
            self.error = str(error)
        finally:
            self._last_plan = self._clock()
        await self._publish()
