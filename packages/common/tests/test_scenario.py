"""
Tests for scenario loading and seeded constraint selection.
"""

import unittest
from pathlib import Path

from common.constraints import RestrictedZone
from common.scenario import Scenario
from common.tile import TileState

PILOT = Path(__file__).parents[2] / "interfaces" / "scenarios" / "pilot.json"

SCENARIO = {
    "seed": 3,
    "n_robots": 4,
    "grid": [8, 4],
    "tiles": [{"state": "QUARRY", "x": 1, "y": 1, "w": 2, "h": 2}],
    "rounds": [
        {
            "name": "A",
            "duration_s": 60,
            "constraints": [
                {"kind": "restricted_zone", "id": "fixed", "zones": [{"rect": [0, 0, 1, 1]}]}
            ],
            "pick": 1,
            "random_pool": [
                {"kind": "restricted_zone", "id": f"pool-{i}", "zones": [{"circle": [0, 0, 1]}]}
                for i in range(5)
            ],
        }
    ],
}


class TestScenario(unittest.TestCase):
    def test_from_dict(self):
        scenario = Scenario.from_dict(SCENARIO)
        self.assertEqual(scenario.n_robots, 4)
        self.assertEqual(scenario.grid, (8, 4))
        self.assertIsInstance(scenario.rounds[0].constraints[0], RestrictedZone)

    def test_tile_blocks(self):
        grid = Scenario.from_dict(SCENARIO).tile_grid()
        self.assertEqual(grid.shape, (8, 4))
        self.assertEqual((grid == TileState.QUARRY).sum(), 4)

    def test_random_pick_is_reproducible(self):
        first = [c.id for c in Scenario.from_dict(SCENARIO).round_constraints(0)]
        second = [c.id for c in Scenario.from_dict(SCENARIO).round_constraints(0)]
        self.assertEqual(first, second)
        self.assertEqual(first[0], "fixed")
        self.assertEqual(len(first), 2)

    def test_roles_cycle(self):
        scenario = Scenario(roles=["a", "b"])
        self.assertEqual([scenario.role_of(i) for i in range(3)], ["a", "b", "a"])

    def test_pilot_scenario_loads(self):
        scenario = Scenario.load(PILOT)
        self.assertEqual(len(scenario.rounds), 3)
        self.assertEqual(len(scenario.round_constraints(2)), 2)
