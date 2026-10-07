"""
Tests for the command queue: replace vs append, dispatching on idle,
completion detection, failures and emergency macros.
"""

import unittest

import numpy as np

from common.actions.move_action import MoveAction
from common.agent_state import AgentState
from common.arena import Arena
from common.game_state import GameState
from common.tile import TileState

from interfaces.commands import START_GRACE_S, CommandQueue, Status, castle_position


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def state(*agents, tiles=None):
    tiles = tiles if tiles is not None else np.zeros((32, 20), dtype=np.uint8)
    return GameState(agent_states=list(agents), tile_states=tiles, arena=Arena())


def agent(id, busy=False, x=0.0, y=0.0, failure=""):
    return AgentState(id=id, position=np.array([x, y]), busy=busy, failure=failure)


class TestCommandQueue(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.queue = CommandQueue(self.clock)

    def test_dispatch_starts_first_command(self):
        self.queue.add([0], "move", (1, 1))
        self.queue.add([0], "mine", (3, 4), append=True)
        actions = self.queue.dispatch(state(agent(0)))
        self.assertEqual(len(actions), 1)
        self.assertIsInstance(actions[0].action, MoveAction)
        plan = self.queue.plan(0)
        self.assertEqual([c["status"] for c in plan], ["in_progress", "waiting"])

    def test_next_command_after_robot_finishes(self):
        self.queue.add([0], "move", (1, 1))
        self.queue.add([0], "mine", (3, 4), append=True)
        self.queue.dispatch(state(agent(0)))
        self.assertEqual(self.queue.dispatch(state(agent(0, busy=True))), [])
        actions = self.queue.dispatch(state(agent(0, busy=False)))
        self.assertEqual(len(actions), 1)
        self.assertEqual(self.queue.snapshot()["history"][0]["status"], "done")

    def test_grace_period_for_instant_commands(self):
        self.queue.add([0], "move", (0, 0))
        self.queue.dispatch(state(agent(0)))
        self.queue.dispatch(state(agent(0)))
        self.assertEqual(self.queue.plan(0)[0]["status"], "in_progress")
        self.clock.t = START_GRACE_S + 0.1
        self.queue.dispatch(state(agent(0)))
        self.assertTrue(self.queue.is_idle(0))

    def test_replace_cancels_existing(self):
        self.queue.add([0], "move", (1, 1))
        self.queue.dispatch(state(agent(0)))
        self.queue.add([0], "move", (2, 2))
        actions = self.queue.dispatch(state(agent(0, busy=True)))
        self.assertEqual(len(actions), 1)
        np.testing.assert_allclose(actions[0].action.position, [2, 2])
        self.assertEqual(self.queue.snapshot()["history"][0]["status"], Status.CANCELLED.value)

    def test_multiple_robots(self):
        self.queue.add([0, 1, 2], "move", (1, 1))
        actions = self.queue.dispatch(state(agent(0), agent(1), agent(2)))
        self.assertEqual(sorted(a.agent_id for a in actions), [0, 1, 2])

    def test_failed_robot_queue_cleared(self):
        self.queue.add([0], "move", (1, 1))
        self.queue.dispatch(state(agent(0, failure="disabled")))
        self.assertTrue(self.queue.is_idle(0))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            self.queue.add([0], "fly", (1, 1))

    def test_emergency_stop_holds_position(self):
        self.queue.add([0], "move", (1, 1))
        s = state(agent(0, x=0.3, y=-0.2))
        self.queue.dispatch(s)
        self.queue.emergency("stop", s)
        [action] = self.queue.dispatch(s)
        np.testing.assert_allclose(action.action.position, [0.3, -0.2])

    def test_emergency_retreat_goes_home(self):
        tiles = np.zeros((32, 20), dtype=np.uint8)
        tiles[3, 10] = TileState.CASTLE
        s = state(agent(0, x=1.0), agent(1, x=1.2), tiles=tiles)
        self.queue.emergency("retreat", s)
        actions = self.queue.dispatch(s)
        home = np.array(castle_position(s))
        self.assertEqual(len(actions), 2)
        for action in actions:
            self.assertLess(np.linalg.norm(action.action.position - home), 0.25)

    def test_version_changes(self):
        version = self.queue.version
        self.queue.add([0], "move", (1, 1))
        self.assertNotEqual(self.queue.version, version)
