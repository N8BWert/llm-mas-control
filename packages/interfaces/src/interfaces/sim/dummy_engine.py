"""
A stand-in for the real engine so the interfaces can be developed and tested
without robots. It follows the testing rules in design.md:

* N robots (from the scenario) on a 2D playfield, each with a fixed speed
* robots do nothing until commanded
* a commanded robot drives to its target, then performs a timed action
* constraints are evaluated with the shared ConstraintTracker and penalties
  are deducted from the score

It speaks the same protocol as the real engine: it receives
AgentActionRequest through a Subscriber and publishes GameState through a
Publisher.
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from common.agent_action import AgentActionRequest
from common.agent_state import AgentState
from common.constraints import ConstraintTracker
from common.entity import Entity
from common.game_state import GameState
from common.publisher import Publisher
from common.scenario import EnemySpec, Scenario
from common.subscriber import Subscriber
from common.tile import TileState

from interfaces.actions import kind_of

log = logging.getLogger(__name__)

ARRIVAL_EPS = 1e-3
ENEMY_DAMAGE_PER_S = 0.1
DEFAULT_ACTION_S = 3.0

# kind -> (tile states it can be performed on, item gained, tile it turns into)
TILE_RULES: dict[str, tuple[set[TileState], str, Optional[TileState]]] = {
    "mine": ({TileState.QUARRY}, "stone", None),
    "farm": ({TileState.FARM}, "food", None),
    "pick_up": ({TileState.APPLE}, "apple", None),
    "drop": ({TileState.CASTLE}, "", None),
    "build_farm": ({TileState.EMPTY}, "", TileState.FARM),
    "build_quarry": ({TileState.EMPTY}, "", TileState.QUARRY),
    "build_house": ({TileState.EMPTY}, "", None),
}


@dataclass
class Robot:
    id: int
    role: str
    x: float
    y: float
    health: float = 1.0
    kind: str = ""
    target: Optional[tuple[float, float]] = None
    tile: Optional[tuple[int, int]] = None
    working: bool = False
    work_left: float = 0.0
    work_total: float = 0.0
    carrying: str = ""
    failure: str = ""

    def clear_action(self):
        self.kind, self.target, self.tile = "", None, None
        self.working, self.work_left, self.work_total = False, 0.0, 0.0


class Enemy:
    """Patrols back and forth along its waypoints."""

    def __init__(self, spec: EnemySpec):
        self.spec = spec
        self.x, self.y = spec.path[0]
        self.next_index = 1 if len(spec.path) > 1 else 0
        self.direction = 1

    def step(self, dt: float):
        if len(self.spec.path) < 2:
            return
        tx, ty = self.spec.path[self.next_index]
        dist = math.hypot(tx - self.x, ty - self.y)
        travel = self.spec.speed * dt
        if dist <= travel:
            self.x, self.y = tx, ty
            if not 0 <= self.next_index + self.direction < len(self.spec.path):
                self.direction *= -1
            self.next_index += self.direction
        else:
            self.x += (tx - self.x) / dist * travel
            self.y += (ty - self.y) / dist * travel


class DummyEngine:
    def __init__(self, scenario: Scenario, subscriber: Subscriber, publisher: Publisher):
        self.scenario = scenario
        self.subscriber = subscriber
        self.publisher = publisher
        self.reset()

    def reset(self):
        s = self.scenario
        self.tiles = s.tile_grid()
        self.robots = [self._spawn(i) for i in range(s.n_robots)]
        self.enemies = [Enemy(spec) for spec in s.enemies]
        self.round_index = 0
        self.elapsed = 0.0
        self.earned = 0
        self.game_over = False
        self.tracker = ConstraintTracker(s.round_constraints(0))
        self.statuses = []
        # Subscribers keep their last value; never replay a request from before the reset.
        self._last_request: Optional[AgentActionRequest] = self.subscriber.receive()

    def _spawn(self, robot_id: int) -> Robot:
        hx, hy = self.scenario.home
        angle = 2 * math.pi * robot_id / max(self.scenario.n_robots, 1)
        x, y = self.scenario.arena.clamp(hx + 0.25 * math.cos(angle), hy + 0.25 * math.sin(angle))
        return Robot(id=robot_id, role=self.scenario.role_of(robot_id), x=x, y=y)

    @property
    def points(self) -> int:
        return self.earned - self.tracker.total_points_lost

    @property
    def current_round(self):
        return self.scenario.rounds[self.round_index]

    # --- commands ------------------------------------------------------------

    def _apply_requests(self):
        request = self.subscriber.receive()
        if request is None or request is self._last_request:
            return
        self._last_request = request
        for agent_action in request.agent_actions:
            if 0 <= agent_action.agent_id < len(self.robots):
                self.assign(self.robots[agent_action.agent_id], agent_action.action)

    def assign(self, robot: Robot, action):
        if robot.failure or self.game_over:
            return
        robot.clear_action()
        robot.kind = kind_of(action)
        if robot.kind == "move":
            robot.target = self.scenario.arena.clamp(*map(float, action.position))
        else:
            robot.tile = (action.tile.x, action.tile.y)
            robot.target = self._tile_center(*robot.tile)

    def _tile_center(self, i: int, j: int) -> tuple[float, float]:
        w, h = self.scenario.grid
        return self.scenario.arena.tile_center(i, j, w, h)

    # --- simulation ----------------------------------------------------------

    def tick(self, dt: float):
        if not self.game_over:
            self._apply_requests()
            self.elapsed += dt
            for robot in self.robots:
                self._step_robot(robot, dt)
            for enemy in self.enemies:
                enemy.step(dt)
            self._apply_enemy_damage(dt)
            self.statuses = self.tracker.update(self.elapsed, dt, self.agent_states())
            if self.elapsed >= self.current_round.duration_s:
                self._next_round()
        self.publisher.send(self.game_state())

    def _step_robot(self, robot: Robot, dt: float):
        if robot.failure or not robot.kind:
            return
        if robot.working:
            robot.work_left -= dt
            if robot.work_left <= 0:
                self._complete(robot)
            return
        tx, ty = robot.target
        dist = math.hypot(tx - robot.x, ty - robot.y)
        travel = self.scenario.robot_speed * dt
        if dist > travel + ARRIVAL_EPS:
            robot.x += (tx - robot.x) / dist * travel
            robot.y += (ty - robot.y) / dist * travel
            return
        robot.x, robot.y = tx, ty
        if robot.kind == "move":
            robot.clear_action()
        else:
            robot.working = True
            robot.work_total = self.scenario.action_durations.get(robot.kind, DEFAULT_ACTION_S)
            robot.work_left = robot.work_total

    def _complete(self, robot: Robot):
        allowed, item, becomes = TILE_RULES[robot.kind]
        i, j = robot.tile
        tile = TileState(self.tiles[i, j])
        if tile in allowed:
            if robot.kind == "drop":
                if robot.carrying:
                    self.earned += self.scenario.item_points.get(robot.carrying, 0)
                    robot.carrying = ""
            elif item:
                if not robot.carrying:
                    robot.carrying = item
            else:
                self.earned += self.scenario.action_points.get(robot.kind, 0)
                if becomes is not None:
                    self.tiles[i, j] = becomes
        robot.clear_action()

    def _apply_enemy_damage(self, dt: float):
        for robot in self.robots:
            if robot.failure:
                continue
            for enemy in self.enemies:
                if math.hypot(enemy.x - robot.x, enemy.y - robot.y) <= enemy.spec.radius:
                    robot.health = max(robot.health - ENEMY_DAMAGE_PER_S * dt, 0.0)
            if robot.health <= 0:
                robot.failure = "disabled"
                robot.clear_action()

    def _next_round(self):
        if self.round_index + 1 >= len(self.scenario.rounds):
            self.game_over = True
            for robot in self.robots:
                robot.clear_action()
            return
        self.round_index += 1
        self.elapsed = 0.0
        self.tracker.set_constraints(self.scenario.round_constraints(self.round_index))

    # --- state ---------------------------------------------------------------

    def _timing(self, robot: Robot) -> tuple[float, float]:
        """(seconds remaining, total seconds) of the robot's timed action."""
        if robot.working:
            return robot.work_left, robot.work_total
        if robot.kind in TILE_RULES:
            total = self.scenario.action_durations.get(robot.kind, DEFAULT_ACTION_S)
            return total, total
        return 0.0, 0.0

    def agent_states(self) -> list[AgentState]:
        states = []
        for r in self.robots:
            remaining, total = self._timing(r)
            states.append(AgentState(
                id=r.id,
                position=np.array([r.x, r.y]),
                busy=bool(r.kind),
                role=r.role,
                health=r.health,
                current_action=r.kind,
                action_time_remaining=remaining,
                action_duration=total,
                target=None if r.target is None else np.array(r.target),
                failure=r.failure,
                carrying=r.carrying,
            ))
        return states

    def game_state(self) -> GameState:
        w, h = self.scenario.grid
        return GameState(
            agent_states=self.agent_states(),
            tile_states=self.tiles.copy(),
            width=w,
            height=h,
            points=self.points,
            time_remaining=0.0 if self.game_over else max(self.current_round.duration_s - self.elapsed, 0.0),
            elapsed_s=self.elapsed,
            round_index=self.round_index,
            round_count=len(self.scenario.rounds),
            round_name=self.current_round.name,
            game_over=self.game_over,
            arena=self.scenario.arena,
            enemies=[Entity(e.spec.id, "enemy", e.x, e.y, e.spec.label) for e in self.enemies],
            objectives=self.scenario.objectives,
            constraints=self.tracker.active(self.elapsed),
            constraint_statuses=self.statuses,
        )

    # --- run loops -----------------------------------------------------------

    async def run_async(self, hz: float = 30.0):
        last = time.monotonic()
        while True:
            now = time.monotonic()
            self.tick(min(now - last, 0.1))
            last = now
            await asyncio.sleep(1.0 / hz)

    def run_forever(self, hz: float = 30.0):
        last = time.monotonic()
        while True:
            now = time.monotonic()
            self.tick(min(now - last, 0.1))
            last = now
            time.sleep(1.0 / hz)


def main() -> None:
    """Run the dummy engine as its own process over sockets."""
    from common.publishers.socket_publisher import SocketPublisher
    from common.subscribers.socket_subscriber import SocketSubscriber

    from interfaces.config import settings
    from interfaces.engine_link import LazyPublisher

    logging.basicConfig(level=logging.INFO)
    engine = DummyEngine(
        Scenario.load(settings.scenario),
        SocketSubscriber(("0.0.0.0", settings.action_port), AgentActionRequest),
        LazyPublisher(lambda: SocketPublisher((settings.engine_host, settings.state_port))),
    )
    log.info("Dummy engine listening for actions on :%d", settings.action_port)
    engine.run_forever(settings.engine_hz)


if __name__ == "__main__":
    main()
