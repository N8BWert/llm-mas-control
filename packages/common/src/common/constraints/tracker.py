"""
The constraint tracker evaluates the active constraints each tick and applies
penalties. Penalties are edge-triggered: a violation is counted once when it
starts (e.g. when a robot enters a restricted zone), not on every tick it lasts.
"""

from dataclasses import dataclass, field
from typing import Iterable

from common.constraints.definitions import Constraint, ConstraintStatus


@dataclass
class _Record:
    violation_count: int = 0
    points_lost: int = 0
    previous_keys: set = field(default_factory=set)
    memory: dict = field(default_factory=dict)


class ConstraintTracker:
    def __init__(self, constraints: Iterable[Constraint] = ()):
        self.constraints: list[Constraint] = []
        self._records: dict[str, _Record] = {}
        self.set_constraints(constraints)

    def set_constraints(self, constraints: Iterable[Constraint]):
        """Replace the constraint set (e.g. at the start of a round). Totals are kept."""
        self.constraints = list(constraints)
        for constraint in self.constraints:
            self._records.setdefault(constraint.id, _Record())

    def active(self, t: float) -> list[Constraint]:
        return [c for c in self.constraints if c.is_active(t)]

    @property
    def total_points_lost(self) -> int:
        return sum(record.points_lost for record in self._records.values())

    @property
    def total_violations(self) -> int:
        return sum(record.violation_count for record in self._records.values())

    def update(self, t: float, dt: float, agents: Iterable) -> list[ConstraintStatus]:
        """
        Evaluate all constraints at round time t.

        Args:
            t (float): Seconds since the start of the round.
            dt (float): Seconds since the previous update.
            agents (Iterable): Objects with id, position, target, role, current_action
                (e.g. AgentState).

        Returns:
            list[ConstraintStatus]: Status of every currently active constraint.
        """
        agents = list(agents)
        statuses = []
        for constraint in self.constraints:
            record = self._records[constraint.id]
            if not constraint.is_active(t):
                record.previous_keys = set()
                record.memory = {}
                continue
            evaluation = constraint.evaluate(t, dt, agents, record.memory)
            new_violations = evaluation.violation_keys - record.previous_keys
            record.previous_keys = evaluation.violation_keys
            record.violation_count += len(new_violations)
            record.points_lost += len(new_violations) * constraint.penalty
            statuses.append(ConstraintStatus(
                constraint_id=constraint.id,
                state=evaluation.state,
                offending_robot_ids=evaluation.offending_robot_ids,
                timers=evaluation.timers,
                violation_count=record.violation_count,
                points_lost=record.points_lost,
                zone_counts=evaluation.zone_counts,
            ))
        return statuses
