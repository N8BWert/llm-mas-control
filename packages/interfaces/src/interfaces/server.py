"""
FastAPI app: the WebSocket endpoint the browser talks to, a small HTTP API,
and (when built) the static frontend.

Every tick the server reads the latest GameState from the engine link, lets
the command queue dispatch the next actions, broadcasts the view to all
browsers and lets the LLM agent observe it.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated, Literal, Optional, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from common.agent_action import AgentActionRequest
from common.game_state import GameState
from common.publishers.local_publisher import LocalPublisher
from common.scenario import Scenario
from common.subscribers.local_subscriber import LocalSubscriber

from interfaces.actions import ACTION_KINDS
from interfaces.commands import CommandQueue
from interfaces.config import Settings, settings as default_settings
from interfaces.engine_link import (
    LOCAL_ACTION_ADDRESS,
    LOCAL_STATE_ADDRESS,
    EngineLink,
    local_link,
    socket_link,
)
from interfaces.hub import Hub
from interfaces.llm.agent import LlmAgent
from interfaces.sim.dummy_engine import DummyEngine
from interfaces.view_model import build_view

log = logging.getLogger(__name__)


# --- client -> server messages -------------------------------------------------

class ActionSpec(BaseModel):
    kind: str
    target: list[float]


class CommandMessage(BaseModel):
    type: Literal["command"]
    robot_ids: list[int]
    action: ActionSpec
    append: bool = False


class EmergencyMessage(BaseModel):
    type: Literal["emergency"]
    kind: Literal["stop", "retreat"]


class StrategyMessage(BaseModel):
    type: Literal["strategy"]
    text: str


class ClearMessage(BaseModel):
    type: Literal["clear"]
    robot_ids: Optional[list[int]] = None


ClientMessage = TypeAdapter(Annotated[
    Union[CommandMessage, EmergencyMessage, StrategyMessage, ClearMessage],
    Field(discriminator="type"),
])


# --- application context -------------------------------------------------------

class Context:
    def __init__(self, config: Settings):
        self.config = config
        self.hub = Hub()
        self.queue = CommandQueue()
        self.engine: Optional[DummyEngine] = None
        self.link: Optional[EngineLink] = None
        self.state: Optional[GameState] = None
        self.agent = LlmAgent(self.queue, config.llm_model, config.llm_replan_s, self.hub.broadcast)
        self._queue_version = -1

    def start_engine(self) -> list[asyncio.Task]:
        tasks = []
        if self.config.engine == "dummy":
            self.link = local_link()
            self.engine = DummyEngine(
                Scenario.load(self.config.scenario),
                LocalSubscriber(LOCAL_ACTION_ADDRESS, AgentActionRequest),
                LocalPublisher(LOCAL_STATE_ADDRESS),
            )
            tasks.append(asyncio.create_task(self.engine.run_async(self.config.engine_hz)))
        else:
            c = self.config
            self.link = socket_link(c.engine_host, c.state_port, c.action_port)
        tasks.append(asyncio.create_task(self.tick_loop()))
        return tasks

    async def tick_loop(self):
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("Tick failed")
            await asyncio.sleep(1.0 / self.config.tick_hz)

    async def tick(self):
        state = self.link.latest_state()
        if state is not None:
            self.state = state
            self.link.send(self.queue.dispatch(state))
            view = build_view(state, self.queue)
            await self.hub.broadcast({"type": "state", "data": view})
            self.agent.observe(view)
        if self.queue.version != self._queue_version:
            self._queue_version = self.queue.version
            await self.hub.broadcast({"type": "queue", "data": self.queue.snapshot()})

    async def handle(self, websocket: WebSocket, raw: dict):
        try:
            message = ClientMessage.validate_python(raw)
            if isinstance(message, CommandMessage):
                self.queue.add(message.robot_ids, message.action.kind, message.action.target,
                               append=message.append, source="user")
            elif isinstance(message, EmergencyMessage):
                self.agent.halt(f"Emergency {message.kind}")
                self.queue.emergency(message.kind, self.state)
            elif isinstance(message, StrategyMessage):
                await self.agent.set_strategy(message.text)
            elif isinstance(message, ClearMessage):
                self.queue.clear(message.robot_ids)
        except (ValidationError, ValueError) as error:
            await self.hub.send(websocket, {"type": "error", "data": {"message": str(error)}})

    def restart(self):
        if self.engine is None:
            raise ValueError("Restart is only available with the dummy engine")
        self.queue.clear()
        self.agent.reset()
        self.engine.scenario = Scenario.load(self.config.scenario)
        self.engine.reset()


def create_app(config: Settings = default_settings) -> FastAPI:
    ctx = Context(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = ctx.start_engine()
        yield
        for task in tasks:
            task.cancel()

    app = FastAPI(title="Swarm interfaces", lifespan=lifespan)
    app.state.ctx = ctx

    @app.get("/api/config")
    def get_config():
        return {
            "mode": config.mode,
            "engine": config.engine,
            "video_url": config.video_url,
            "llm_model": config.llm_model,
            "action_kinds": ACTION_KINDS,
        }

    @app.post("/api/restart")
    def restart():
        ctx.restart()
        return {"ok": True}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ctx.hub.connect(websocket)
        await ctx.hub.send(websocket, {"type": "queue", "data": ctx.queue.snapshot()})
        await ctx.hub.send(websocket, {"type": "llm", "data": ctx.agent.snapshot()})
        try:
            while True:
                await ctx.handle(websocket, await websocket.receive_json())
        except WebSocketDisconnect:
            ctx.hub.disconnect(websocket)

    if config.web_dist.is_dir():
        app.mount("/", StaticFiles(directory=config.web_dist, html=True), name="web")

    return app


app = create_app()
