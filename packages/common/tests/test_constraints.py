"""
Tests for constraint zones, evaluation, the tracker's edge-triggered
penalties, and proto/dict round trips.
"""

import unittest
import numpy as np

from common.agent_state import AgentState
from common.constraints import (
    ActivityInterval,
    CircleZone,
    Constraint,
    ConstraintState,
    ConstraintStatus,
    ConstraintTracker,
    OccupationZone,
    RectZone,
    RestrictedZone,
    RoleRestriction,
    TimedEntryZone,
)
from common.game_state import GameState


def agent(id, x, y, target=None):
    return AgentState(
        id=id,
        position=np.array([x, y]),
        busy=target is not None,
        target=None if target is None else np.array(target),
    )


class TestZones(unittest.TestCase):
    def test_rect_contains(self):
        zone = RectZone(0, 0, 1, 1)
        self.assertTrue(zone.contains(0.5, 0.5))
        self.assertFalse(zone.contains(1.5, 0.5))

    def test_circle_contains(self):
        zone = CircleZone(0, 0, 0.5)
        self.assertTrue(zone.contains(0.3, 0.3))
        self.assertFalse(zone.contains(0.4, 0.4))


class TestRestrictedZone(unittest.TestCase):
    def setUp(self):
        self.constraint = RestrictedZone(id="r", penalty=5, zones=[RectZone(0, 0, 1, 1)])
        self.tracker = ConstraintTracker([self.constraint])

    def test_ok_outside(self):
        [status] = self.tracker.update(0, 0.1, [agent(0, 2, 2)])
        self.assertEqual(status.state, ConstraintState.OK)

    def test_warning_when_heading_in(self):
        [status] = self.tracker.update(0, 0.1, [agent(0, 2, 2, target=(0.5, 0.5))])
        self.assertEqual(status.state, ConstraintState.WARNING)

    def test_penalty_is_edge_triggered(self):
        for _ in range(5):
            [status] = self.tracker.update(0, 0.1, [agent(0, 0.5, 0.5)])
        self.assertEqual(status.state, ConstraintState.VIOLATED)
        self.assertEqual(status.offending_robot_ids, [0])
        self.assertEqual(status.violation_count, 1)
        self.assertEqual(status.points_lost, 5)

        # Leaving and re-entering counts as a new violation
        self.tracker.update(0, 0.1, [agent(0, 2, 2)])
        [status] = self.tracker.update(0, 0.1, [agent(0, 0.5, 0.5)])
        self.assertEqual(status.violation_count, 2)
        self.assertEqual(self.tracker.total_points_lost, 10)

    def test_each_robot_counts(self):
        [status] = self.tracker.update(0, 0.1, [agent(0, 0.5, 0.5), agent(1, 0.2, 0.2)])
        self.assertEqual(status.violation_count, 2)

    def test_inactive_constraint_has_no_status(self):
        constraint = RestrictedZone(id="late", active_from_s=30, zones=[RectZone(0, 0, 1, 1)])
        tracker = ConstraintTracker([constraint])
        self.assertEqual(tracker.update(10, 0.1, [agent(0, 0.5, 0.5)]), [])
        self.assertEqual(len(tracker.update(31, 0.1, [agent(0, 0.5, 0.5)])), 1)


class TestOccupationZone(unittest.TestCase):
    def test_grace_period_then_violation(self):
        constraint = OccupationZone(id="o", grace_s=5, zones=[RectZone(0, 0, 1, 1)])
        tracker = ConstraintTracker([constraint])
        [status] = tracker.update(1, 0.1, [agent(0, 2, 2)])
        self.assertEqual(status.state, ConstraintState.WARNING)
        self.assertEqual(status.violation_count, 0)
        [status] = tracker.update(6, 0.1, [agent(0, 2, 2)])
        self.assertEqual(status.state, ConstraintState.VIOLATED)
        self.assertEqual(status.violation_count, 1)
        self.assertEqual(status.zone_counts, [0])

    def test_occupied(self):
        constraint = OccupationZone(id="o", grace_s=0, min_robots=2, zones=[RectZone(0, 0, 1, 1)])
        tracker = ConstraintTracker([constraint])
        [status] = tracker.update(1, 0.1, [agent(0, 0.5, 0.5), agent(1, 0.6, 0.6)])
        self.assertEqual(status.state, ConstraintState.OK)
        self.assertEqual(status.zone_counts, [2])


class TestTimedEntryZone(unittest.TestCase):
    def test_dwell_timer_warning_and_violation(self):
        constraint = TimedEntryZone(id="t", max_dwell_s=1.0, zones=[CircleZone(0, 0, 1)])
        tracker = ConstraintTracker([constraint])
        inside = [agent(3, 0, 0)]
        [status] = tracker.update(0, 0.5, inside)
        self.assertEqual(status.state, ConstraintState.OK)
        self.assertAlmostEqual(status.timers[3], 0.5)
        [status] = tracker.update(0, 0.3, inside)
        self.assertEqual(status.state, ConstraintState.WARNING)
        [status] = tracker.update(0, 0.3, inside)
        self.assertEqual(status.state, ConstraintState.VIOLATED)
        self.assertEqual(status.violation_count, 1)

    def test_leaving_resets_dwell(self):
        constraint = TimedEntryZone(id="t", max_dwell_s=1.0, zones=[CircleZone(0, 0, 1)])
        tracker = ConstraintTracker([constraint])
        tracker.update(0, 0.9, [agent(0, 0, 0)])
        tracker.update(0, 0.1, [agent(0, 5, 5)])
        [status] = tracker.update(0, 0.5, [agent(0, 0, 0)])
        self.assertEqual(status.state, ConstraintState.OK)


class TestActivityInterval(unittest.TestCase):
    def test_timer_runs_outside_base_and_resets_inside(self):
        constraint = ActivityInterval(id="a", max_active_s=1.0, base_zone=CircleZone(0, 0, 0.2))
        tracker = ConstraintTracker([constraint])
        away = [agent(0, 1, 1)]
        [status] = tracker.update(0, 0.5, away)
        self.assertEqual(status.state, ConstraintState.OK)
        self.assertAlmostEqual(status.timers[0], 0.5)
        [status] = tracker.update(0, 0.3, away)
        self.assertEqual(status.state, ConstraintState.WARNING)
        [status] = tracker.update(0, 0.3, away)
        self.assertEqual(status.state, ConstraintState.VIOLATED)
        self.assertEqual(status.violation_count, 1)
        [status] = tracker.update(0, 0.1, [agent(0, 0, 0)])
        self.assertEqual(status.state, ConstraintState.OK)
        self.assertAlmostEqual(status.timers[0], 1.0)


class TestRoleRestriction(unittest.TestCase):
    def robot(self, role, action, remaining, duration=4.0):
        return AgentState(0, np.array([0.0, 0.0]), True, role=role, current_action=action,
                          action_time_remaining=remaining, action_duration=duration)

    def setUp(self):
        self.tracker = ConstraintTracker([
            RoleRestriction(id="r", action_kinds=["mine"], allowed_roles=["miner"]),
        ])

    def test_allowed_role_is_ok(self):
        [status] = self.tracker.update(0, 0.1, [self.robot("miner", "mine", 2.0)])
        self.assertEqual(status.state, ConstraintState.OK)

    def test_assignment_warns_and_work_violates(self):
        [status] = self.tracker.update(0, 0.1, [self.robot("scout", "mine", 4.0)])
        self.assertEqual(status.state, ConstraintState.WARNING)
        [status] = self.tracker.update(0, 0.1, [self.robot("scout", "mine", 3.9)])
        self.assertEqual(status.state, ConstraintState.VIOLATED)
        self.assertEqual(status.offending_robot_ids, [0])

    def test_other_actions_are_ok(self):
        [status] = self.tracker.update(0, 0.1, [self.robot("scout", "farm", 1.0)])
        self.assertEqual(status.state, ConstraintState.OK)


class TestSerialization(unittest.TestCase):
    CONSTRAINTS = [
        RestrictedZone(id="a", zones=[RectZone(0, 0, 1, 1), CircleZone(1, 1, 0.2)]),
        OccupationZone(id="b", min_robots=2, grace_s=3, zones=[RectZone(0, 0, 1, 1)]),
        TimedEntryZone(id="c", max_dwell_s=7, active_from_s=10, active_until_s=20,
                       zones=[CircleZone(0, 0, 1)]),
        ActivityInterval(id="d", max_active_s=30, base_zone=RectZone(-1, -1, 0, 0)),
        ActivityInterval(id="e", max_active_s=30),
        RoleRestriction(id="f", action_kinds=["mine", "farm"], allowed_roles=["miner"]),
    ]

    def test_proto_round_trip(self):
        for constraint in self.CONSTRAINTS:
            self.assertEqual(Constraint.from_bytes(constraint.to_bytes()), constraint)

    def test_dict_round_trip(self):
        for constraint in self.CONSTRAINTS:
            self.assertEqual(Constraint.from_dict(constraint.to_dict()), constraint)

    def test_from_dict(self):
        constraint = Constraint.from_dict({
            "kind": "restricted_zone", "id": "x", "penalty": 20,
            "zones": [{"rect": [0, 0, 1, 1]}],
        })
        self.assertIsInstance(constraint, RestrictedZone)
        self.assertEqual(constraint.penalty, 20)
        self.assertIn("No robot may enter", constraint.description)

    def test_status_round_trip(self):
        status = ConstraintStatus("x", ConstraintState.WARNING, [1], {1: 2.5}, 3, 30, [1, 0])
        self.assertEqual(ConstraintStatus.from_bytes(status.to_bytes()), status)

    def test_game_state_carries_constraints(self):
        constraint = RestrictedZone(id="a", zones=[RectZone(0, 0, 1, 1)])
        state = GameState(
            agent_states=[agent(0, 0.5, 0.5)],
            tile_states=np.zeros((4, 3), dtype=np.uint8),
            constraints=[constraint],
            constraint_statuses=[ConstraintStatus("a", ConstraintState.VIOLATED, [0])],
            time_remaining=12.5,
        )
        decoded = GameState.from_bytes(state.to_bytes())
        self.assertEqual(decoded.constraints, [constraint])
        self.assertEqual(decoded.constraint_statuses[0].offending_robot_ids, [0])
        self.assertEqual(decoded.time_remaining, 12.5)
        self.assertEqual(decoded.tile_states.shape, (4, 3))
