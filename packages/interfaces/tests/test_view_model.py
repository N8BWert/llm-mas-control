"""
Tests for the view model sent to the browser.
"""

import unittest

import numpy as np

from common.agent_state import AgentState
from common.constraints import ConstraintState, ConstraintStatus, RectZone, RestrictedZone
from common.game_state import GameState

from interfaces.commands import CommandQueue
from interfaces.view_model import build_view


class TestViewModel(unittest.TestCase):
    def test_view_contents(self):
        queue = CommandQueue()
        queue.add([1], "mine", (3, 4))
        state = GameState(
            agent_states=[
                AgentState(0, np.array([0.1, 0.2]), False, role="scout"),
                AgentState(1, np.array([0.0, 0.0]), True, target=np.array([1.0, 1.0])),
            ],
            tile_states=np.zeros((4, 3), dtype=np.uint8),
            points=5,
            constraints=[RestrictedZone(id="r", zones=[RectZone(0, 0, 1, 1)])],
            constraint_statuses=[ConstraintStatus("r", ConstraintState.VIOLATED, [1], {1: 2.0})],
        )
        view = build_view(state, queue)
        self.assertEqual(view["points"], 5)
        self.assertEqual(view["agent_states"][0]["role"], "scout")
        self.assertFalse(view["agent_states"][0]["has_target"])
        self.assertEqual(view["agent_states"][1]["target"], {"x": 1.0, "y": 1.0})
        self.assertEqual(view["agent_states"][1]["plan"][0]["kind"], "mine")
        self.assertEqual(view["agent_states"][0]["plan"], [])
        self.assertEqual(len(view["tiles"]), 12)
        self.assertEqual(view["active_constraints"][0]["restricted_zone"]["zones"][0]["rect"]["x_max"], 1.0)
        self.assertEqual(view["constraint_statuses"][0]["state"], 2)
        self.assertEqual(view["constraint_statuses"][0]["timers"], {"1": 2.0})
        self.assertIn("x_min", view["arena"])
