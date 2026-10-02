"""
Tests for the dummy engine: movement, timed actions, scoring, constraint
penalties and round progression, all over the Local pub/sub link.
"""

import unittest

from common.agent_action import AgentAction, AgentActionRequest
from common.publishers.local_publisher import LocalPublisher
from common.scenario import Scenario
from common.subscribers.local_subscriber import LocalSubscriber

from interfaces.actions import make_action
from interfaces.engine_link import LOCAL_ACTION_ADDRESS, LOCAL_STATE_ADDRESS, local_link
from interfaces.sim.dummy_engine import DummyEngine

SCENARIO = {
    "n_robots": 2,
    "robot_speed": 0.5,
    "grid": [32, 20],
    "home": [-1.25, 0.05],
    "tiles": [
        {"state": "CASTLE", "x": 3, "y": 10},
        {"state": "QUARRY", "x": 20, "y": 10},
    ],
    "action_durations": {"mine": 1.0, "drop": 0.5},
    "item_points": {"stone": 10},
    "rounds": [
        {
            "name": "R1",
            "duration_s": 100,
            "constraints": [
                {"kind": "restricted_zone", "id": "no-go", "penalty": 7,
                 "zones": [{"rect": [0.5, 0.5, 1.0, 1.0]}]}
            ],
        },
        {"name": "R2", "duration_s": 5},
    ],
}


def make_engine():
    engine = DummyEngine(
        Scenario.from_dict(SCENARIO),
        LocalSubscriber(LOCAL_ACTION_ADDRESS, AgentActionRequest),
        LocalPublisher(LOCAL_STATE_ADDRESS),
    )
    return engine, local_link()


def run(engine, seconds, dt=0.05):
    for _ in range(int(seconds / dt)):
        engine.tick(dt)


class TestDummyEngine(unittest.TestCase):
    def test_idle_until_commanded(self):
        engine, link = make_engine()
        start = (engine.robots[0].x, engine.robots[0].y)
        run(engine, 1)
        self.assertEqual((engine.robots[0].x, engine.robots[0].y), start)
        self.assertFalse(link.latest_state().agent_states[0].busy)

    def test_move_reaches_target(self):
        engine, link = make_engine()
        link.send([AgentAction(0, make_action("move", (0.0, 0.0)))])
        engine.tick(0.05)
        self.assertTrue(link.latest_state().agent_states[0].busy)
        run(engine, 5)
        state = link.latest_state().agent_states[0]
        self.assertFalse(state.busy)
        self.assertAlmostEqual(state.position[0], 0.0)
        self.assertAlmostEqual(state.position[1], 0.0)

    def test_mine_then_drop_scores(self):
        engine, link = make_engine()
        link.send([AgentAction(0, make_action("mine", (20, 10)))])
        run(engine, 6)
        self.assertEqual(engine.robots[0].carrying, "stone")
        link.send([AgentAction(0, make_action("drop", (3, 10)))])
        run(engine, 6)
        self.assertEqual(engine.robots[0].carrying, "")
        self.assertEqual(link.latest_state().points, 10)

    def test_action_on_wrong_tile_does_nothing(self):
        engine, link = make_engine()
        link.send([AgentAction(0, make_action("mine", (10, 2)))])
        run(engine, 6)
        self.assertEqual(engine.robots[0].carrying, "")
        self.assertFalse(engine.robots[0].kind)

    def test_restricted_zone_penalty(self):
        engine, link = make_engine()
        link.send([AgentAction(1, make_action("move", (0.75, 0.75)))])
        run(engine, 6)
        state = link.latest_state()
        self.assertEqual(state.points, -7)
        self.assertEqual(state.constraint_statuses[0].offending_robot_ids, [1])

    def test_same_request_applied_once(self):
        engine, link = make_engine()
        link.send([AgentAction(0, make_action("move", (0.0, 0.0)))])
        run(engine, 5)
        engine.robots[0].x = -1.0
        run(engine, 1)
        self.assertEqual(engine.robots[0].x, -1.0)

    def test_reset_does_not_replay_last_request(self):
        engine, link = make_engine()
        link.send([AgentAction(0, make_action("move", (0.0, 0.0)))])
        engine.tick(0.05)
        engine.reset()
        engine.tick(0.05)
        self.assertEqual(engine.robots[0].kind, "")

    def test_rounds_advance_to_game_over(self):
        engine, link = make_engine()
        run(engine, 101, dt=0.1)
        state = link.latest_state()
        self.assertEqual(state.round_index, 1)
        self.assertEqual(state.round_name, "R2")
        self.assertEqual(state.constraints, [])
        run(engine, 6, dt=0.1)
        self.assertTrue(link.latest_state().game_over)
