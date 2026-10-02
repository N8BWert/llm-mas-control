"""
The command queue holds every robot's upcoming commands. The engine only
knows each robot's current action, so the queue decides when to send the
next one: a robot's next command starts once its current one is finished
(the robot reports busy=False).

Both the RTS UI and the LLM agent add commands here, which gives the UI
"current and upcoming actions" per robot and the LLM command-queue panel.
"""

import itertools
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Optional

import numpy as np

from common.agent_action import AgentAction
from common.game_state import GameState
from common.tile import TileState

from interfaces.actions import ACTION_KINDS, make_action

# A command counts as finished if the robot never reported busy within this
# long after it was sent (e.g. a move to where the robot already is).
START_GRACE_S = 1.0
HISTORY_SIZE = 50
RETREAT_RADIUS = 0.2


class Status(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Command:
    id: int
    robot_id: int
    kind: str
    target: tuple[float, float]
    source: str = "user"
    status: Status = Status.WAITING
    created_at: float = 0.0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    seen_busy: bool = field(default=False, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "robot_id": self.robot_id,
            "kind": self.kind,
            "target": list(self.target),
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class CommandQueue:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._ids = itertools.count(1)
        self._pending: dict[int, deque[Command]] = {}
        self._current: dict[int, Command] = {}
        self._history: deque[Command] = deque(maxlen=HISTORY_SIZE)
        self.version = 0

    # --- adding and removing -------------------------------------------------

    def add(
        self,
        robot_ids: Iterable[int],
        kind: str,
        target: Iterable[float],
        append: bool = False,
        source: str = "user",
    ) -> list[Command]:
        """
        Queue a command for each robot. Without append, the robot's existing
        commands are cancelled and the new one starts on the next dispatch.
        """
        if kind not in ACTION_KINDS:
            raise ValueError(f"Unknown action kind: {kind}")
        target = tuple(float(v) for v in target)
        if len(target) != 2:
            raise ValueError("target must be [x, y]")
        commands = []
        for robot_id in robot_ids:
            if not append:
                self.clear([robot_id])
            command = Command(next(self._ids), int(robot_id), kind, target, source,
                              created_at=self._clock())
            self._pending.setdefault(command.robot_id, deque()).append(command)
            commands.append(command)
        self.version += 1
        return commands

    def clear(self, robot_ids: Optional[Iterable[int]] = None):
        """Cancel the current and waiting commands of the robots (all robots if None)."""
        ids = set(self._pending) | set(self._current) if robot_ids is None else set(robot_ids)
        for robot_id in ids:
            cancelled = list(self._pending.pop(robot_id, ()))
            if robot_id in self._current:
                cancelled.insert(0, self._current.pop(robot_id))
            for command in cancelled:
                self._finish(command, Status.CANCELLED)
        self.version += 1

    def emergency(self, kind: str, state: Optional[GameState]):
        """
        "stop": cancel everything and hold position.
        "retreat": cancel everything and send all robots home to the castle.
        """
        self.clear()
        if state is None:
            return
        robots = [a for a in state.agent_states if not a.failure]
        if kind == "stop":
            for agent in robots:
                self.add([agent.id], "move", agent.position, source="emergency")
        elif kind == "retreat":
            home = castle_position(state)
            for index, agent in enumerate(robots):
                angle = 2 * math.pi * index / max(len(robots), 1)
                target = state.arena.clamp(
                    home[0] + RETREAT_RADIUS * math.cos(angle),
                    home[1] + RETREAT_RADIUS * math.sin(angle),
                )
                self.add([agent.id], "move", target, source="emergency")
        else:
            raise ValueError(f"Unknown emergency: {kind}")

    # --- dispatching ---------------------------------------------------------

    def dispatch(self, state: GameState) -> list[AgentAction]:
        """Advance every robot's queue given the latest state; return actions to send."""
        now = self._clock()
        actions = []
        for agent in state.agent_states:
            current = self._current.get(agent.id)
            if agent.failure and (current or self._pending.get(agent.id)):
                self.clear([agent.id])
                continue
            if current is not None:
                if agent.busy:
                    current.seen_busy = True
                elif current.seen_busy or now - current.started_at > START_GRACE_S:
                    self._finish(self._current.pop(agent.id), Status.DONE)
                    current = None
            pending = self._pending.get(agent.id)
            if current is None and pending:
                command = pending.popleft()
                command.status = Status.IN_PROGRESS
                command.started_at = now
                self._current[agent.id] = command
                actions.append(AgentAction(agent.id, make_action(command.kind, command.target)))
                self.version += 1
        return actions

    def _finish(self, command: Command, status: Status):
        command.status = status
        command.finished_at = self._clock()
        self._history.appendleft(command)
        self.version += 1

    # --- views ---------------------------------------------------------------

    def plan(self, robot_id: int) -> list[dict]:
        """The robot's current command followed by its waiting ones."""
        commands = list(self._pending.get(robot_id, ()))
        if robot_id in self._current:
            commands.insert(0, self._current[robot_id])
        return [c.to_dict() for c in commands]

    def snapshot(self) -> dict:
        return {
            "in_progress": [c.to_dict() for c in self._current.values()],
            "waiting": [c.to_dict() for q in self._pending.values() for c in q],
            "history": [c.to_dict() for c in self._history],
        }

    def is_idle(self, robot_id: int) -> bool:
        return robot_id not in self._current and not self._pending.get(robot_id)


def castle_position(state: GameState) -> tuple[float, float]:
    castles = np.argwhere(state.tile_states == TileState.CASTLE)
    if len(castles) == 0:
        return (state.arena.x_min + state.arena.x_max) / 2, (state.arena.y_min + state.arena.y_max) / 2
    i, j = castles[0]
    return state.arena.tile_center(int(i), int(j), state.width, state.height)
