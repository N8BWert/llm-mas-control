"""
Constraint definitions. Each kind knows how to serialize itself (proto and
scenario JSON) and how to evaluate itself against the current agent states.
The ConstraintTracker owns the bookkeeping (memory, edge-triggered penalties).
"""

import math
from dataclasses import dataclass, field, fields
from enum import IntEnum
from typing import Any, ClassVar, Iterable, Optional, Type

from common.convertible import Convertible
from common.constraints.zone import Zone, zone_from_dict, zone_from_proto, zones_containing
import common.protos.constraint_pb2 as constraint_pb2


class ConstraintState(IntEnum):
    OK = constraint_pb2.CONSTRAINT_OK
    WARNING = constraint_pb2.CONSTRAINT_WARNING
    VIOLATED = constraint_pb2.CONSTRAINT_VIOLATED


@dataclass
class Evaluation:
    """
    Result of evaluating one constraint for one tick.

    violation_keys identifies each distinct ongoing violation (usually a robot
    id). The tracker penalizes a key only when it first appears.
    """
    state: ConstraintState = ConstraintState.OK
    offending_robot_ids: list[int] = field(default_factory=list)
    timers: dict[int, float] = field(default_factory=dict)
    zone_counts: list[int] = field(default_factory=list)
    violation_keys: set = field(default_factory=set)


@dataclass(kw_only=True)
class Constraint(Convertible):
    """
    Common fields of every constraint. Subclasses set KIND to their proto
    oneof field name and implement evaluate().
    """
    KIND: ClassVar[str] = ""
    WARN_FRACTION: ClassVar[float] = 0.75

    id: str
    label: str = ""
    description: str = ""
    difficulty: str = "easy"
    penalty: int = 10
    active_from_s: float = 0.0
    active_until_s: float = math.inf

    def __post_init__(self):
        if not self.label:
            self.label = self.KIND.replace("_", " ").title()
        if not self.description:
            self.description = self.describe()

    def is_active(self, t: float) -> bool:
        return self.active_from_s <= t < self.active_until_s

    def describe(self) -> str:
        """Plain-language description used by the UI and the LLM prompt."""
        return self.label

    def evaluate(self, t: float, dt: float, agents: Iterable, memory: dict) -> Evaluation:
        raise NotImplementedError

    # --- serialization -----------------------------------------------------

    def _kind_proto(self) -> Any:
        raise NotImplementedError

    @classmethod
    def _kind_kwargs(cls, proto: Any) -> dict:
        raise NotImplementedError

    def to_proto(self) -> constraint_pb2.Constraint:
        proto = constraint_pb2.Constraint(
            id=self.id,
            label=self.label,
            description=self.description,
            difficulty=self.difficulty,
            penalty=self.penalty,
            active_from_s=self.active_from_s,
            active_until_s=0.0 if math.isinf(self.active_until_s) else self.active_until_s,
        )
        getattr(proto, self.KIND).CopyFrom(self._kind_proto())
        return proto

    @classmethod
    def from_proto(cls, proto: constraint_pb2.Constraint) -> "Constraint":
        kind = proto.WhichOneof("kind")
        if kind not in CONSTRAINT_KINDS:
            raise ValueError(f"Unknown constraint kind: {kind}")
        sub = CONSTRAINT_KINDS[kind]
        return sub(
            id=proto.id,
            label=proto.label,
            description=proto.description,
            difficulty=proto.difficulty,
            penalty=proto.penalty,
            active_from_s=proto.active_from_s,
            active_until_s=proto.active_until_s or math.inf,
            **sub._kind_kwargs(getattr(proto, kind)),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Constraint":
        proto = constraint_pb2.Constraint()
        proto.ParseFromString(data)
        return cls.from_proto(proto)

    def to_dict(self) -> dict:
        data: dict[str, Any] = {"kind": self.KIND}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "zones":
                value = [zone.to_dict() for zone in value]
            elif isinstance(value, Convertible) and hasattr(value, "to_dict"):
                value = value.to_dict()
            elif isinstance(value, float) and math.isinf(value):
                continue
            data[f.name] = value
        return data

    @staticmethod
    def from_dict(data: dict) -> "Constraint":
        """Parse a scenario-file constraint: {"kind": "restricted_zone", ...}."""
        data = dict(data)
        kind = data.pop("kind")
        if kind not in CONSTRAINT_KINDS:
            raise ValueError(f"Unknown constraint kind: {kind}")
        if "zones" in data:
            data["zones"] = [zone_from_dict(z) for z in data["zones"]]
        if "base_zone" in data:
            data["base_zone"] = zone_from_dict(data["base_zone"])
        return CONSTRAINT_KINDS[kind](**data)


def _zones_text(zones: list[Zone]) -> str:
    parts = []
    for zone in zones:
        d = zone.to_dict()
        if "rect" in d:
            x0, y0, x1, y1 = d["rect"]
            parts.append(f"rectangle x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}]")
        else:
            x, y, r = d["circle"]
            parts.append(f"circle at ({x:.2f},{y:.2f}) radius {r:.2f}")
    return "; ".join(parts)


@dataclass(kw_only=True)
class RestrictedZone(Constraint):
    KIND: ClassVar[str] = "restricted_zone"

    zones: list[Zone] = field(default_factory=list)

    def describe(self) -> str:
        return f"No robot may enter: {_zones_text(self.zones)}."

    def evaluate(self, t, dt, agents, memory) -> Evaluation:
        offending, heading_in = [], False
        for agent in agents:
            if zones_containing(self.zones, agent.position[0], agent.position[1]):
                offending.append(agent.id)
            elif agent.target is not None and zones_containing(self.zones, agent.target[0], agent.target[1]):
                heading_in = True
        if offending:
            state = ConstraintState.VIOLATED
        elif heading_in:
            state = ConstraintState.WARNING
        else:
            state = ConstraintState.OK
        return Evaluation(state, offending, violation_keys=set(offending))

    def _kind_proto(self):
        return constraint_pb2.RestrictedZone(zones=[z.to_proto() for z in self.zones])

    @classmethod
    def _kind_kwargs(cls, proto):
        return {"zones": [zone_from_proto(z) for z in proto.zones]}


@dataclass(kw_only=True)
class OccupationZone(Constraint):
    KIND: ClassVar[str] = "occupation_zone"

    zones: list[Zone] = field(default_factory=list)
    min_robots: int = 1
    grace_s: float = 10.0

    def describe(self) -> str:
        return (
            f"At least {self.min_robots} robot(s) must stay inside each of: "
            f"{_zones_text(self.zones)}."
        )

    def evaluate(self, t, dt, agents, memory) -> Evaluation:
        agents = list(agents)
        counts = [
            sum(zone.contains(a.position[0], a.position[1]) for a in agents)
            for zone in self.zones
        ]
        empty = {i for i, c in enumerate(counts) if c < self.min_robots}
        in_grace = t - self.active_from_s < self.grace_s
        if empty and not in_grace:
            return Evaluation(ConstraintState.VIOLATED, zone_counts=counts,
                              violation_keys={("zone", i) for i in empty})
        if empty:
            return Evaluation(ConstraintState.WARNING, zone_counts=counts)
        return Evaluation(ConstraintState.OK, zone_counts=counts)

    def _kind_proto(self):
        return constraint_pb2.OccupationZone(
            zones=[z.to_proto() for z in self.zones],
            min_robots=self.min_robots,
            grace_s=self.grace_s,
        )

    @classmethod
    def _kind_kwargs(cls, proto):
        return {
            "zones": [zone_from_proto(z) for z in proto.zones],
            "min_robots": proto.min_robots,
            "grace_s": proto.grace_s,
        }


@dataclass(kw_only=True)
class TimedEntryZone(Constraint):
    KIND: ClassVar[str] = "timed_entry_zone"

    zones: list[Zone] = field(default_factory=list)
    max_dwell_s: float = 10.0

    def describe(self) -> str:
        return (
            f"A robot may stay at most {self.max_dwell_s:.0f}s at a time inside: "
            f"{_zones_text(self.zones)}."
        )

    def evaluate(self, t, dt, agents, memory) -> Evaluation:
        dwell: dict[int, float] = memory.setdefault("dwell", {})
        result = Evaluation()
        warn = False
        for agent in agents:
            if zones_containing(self.zones, agent.position[0], agent.position[1]):
                dwell[agent.id] = dwell.get(agent.id, 0.0) + dt
                result.timers[agent.id] = max(self.max_dwell_s - dwell[agent.id], 0.0)
                if dwell[agent.id] > self.max_dwell_s:
                    result.offending_robot_ids.append(agent.id)
                elif dwell[agent.id] > self.WARN_FRACTION * self.max_dwell_s:
                    warn = True
            else:
                dwell.pop(agent.id, None)
        result.violation_keys = set(result.offending_robot_ids)
        if result.offending_robot_ids:
            result.state = ConstraintState.VIOLATED
        elif warn:
            result.state = ConstraintState.WARNING
        return result

    def _kind_proto(self):
        return constraint_pb2.TimedEntryZone(
            zones=[z.to_proto() for z in self.zones], max_dwell_s=self.max_dwell_s
        )

    @classmethod
    def _kind_kwargs(cls, proto):
        return {
            "zones": [zone_from_proto(z) for z in proto.zones],
            "max_dwell_s": proto.max_dwell_s,
        }


@dataclass(kw_only=True)
class ActivityInterval(Constraint):
    """Robots must return to base_zone to refuel at least every max_active_s."""
    KIND: ClassVar[str] = "activity_interval"

    max_active_s: float = 60.0
    base_zone: Optional[Zone] = None

    def describe(self) -> str:
        base = _zones_text([self.base_zone]) if self.base_zone else "base"
        return f"Each robot must return to base ({base}) at least every {self.max_active_s:.0f}s."

    def evaluate(self, t, dt, agents, memory) -> Evaluation:
        active: dict[int, float] = memory.setdefault("active", {})
        result = Evaluation()
        warn = False
        for agent in agents:
            if self.base_zone is not None and self.base_zone.contains(agent.position[0], agent.position[1]):
                active[agent.id] = 0.0
            else:
                active[agent.id] = active.get(agent.id, 0.0) + dt
            result.timers[agent.id] = max(self.max_active_s - active[agent.id], 0.0)
            if active[agent.id] > self.max_active_s:
                result.offending_robot_ids.append(agent.id)
            elif active[agent.id] > self.WARN_FRACTION * self.max_active_s:
                warn = True
        result.violation_keys = set(result.offending_robot_ids)
        if result.offending_robot_ids:
            result.state = ConstraintState.VIOLATED
        elif warn:
            result.state = ConstraintState.WARNING
        return result

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.base_zone is None:
            data.pop("base_zone")
        return data

    def _kind_proto(self):
        proto = constraint_pb2.ActivityInterval(max_active_s=self.max_active_s)
        if self.base_zone is not None:
            proto.base_zone.CopyFrom(self.base_zone.to_proto())
        return proto

    @classmethod
    def _kind_kwargs(cls, proto):
        base = zone_from_proto(proto.base_zone) if proto.HasField("base_zone") else None
        return {"max_active_s": proto.max_active_s, "base_zone": base}


@dataclass(kw_only=True)
class RoleRestriction(Constraint):
    """
    Only robots with one of allowed_roles may perform action_kinds. Assigning
    such an action to another robot is a warning; starting the work is a violation.
    """
    KIND: ClassVar[str] = "role_restriction"

    action_kinds: list[str] = field(default_factory=list)
    allowed_roles: list[str] = field(default_factory=list)

    def describe(self) -> str:
        actions = ", ".join(a.replace("_", " ") for a in self.action_kinds)
        return f"Only {' or '.join(self.allowed_roles)} robots may {actions}."

    def evaluate(self, t, dt, agents, memory) -> Evaluation:
        offending, assigned = [], False
        for agent in agents:
            if agent.current_action not in self.action_kinds or agent.role in self.allowed_roles:
                continue
            working = 0 < agent.action_duration and agent.action_time_remaining < agent.action_duration
            if working:
                offending.append(agent.id)
            else:
                assigned = True
        if offending:
            state = ConstraintState.VIOLATED
        elif assigned:
            state = ConstraintState.WARNING
        else:
            state = ConstraintState.OK
        return Evaluation(state, offending, violation_keys=set(offending))

    def _kind_proto(self):
        return constraint_pb2.RoleRestriction(action_kinds=self.action_kinds, allowed_roles=self.allowed_roles)

    @classmethod
    def _kind_kwargs(cls, proto):
        return {"action_kinds": list(proto.action_kinds), "allowed_roles": list(proto.allowed_roles)}


CONSTRAINT_KINDS: dict[str, Type[Constraint]] = {
    cls.KIND: cls
    for cls in (RestrictedZone, OccupationZone, TimedEntryZone, ActivityInterval, RoleRestriction)
}


@dataclass
class ConstraintStatus(Convertible):
    """Live status of one active constraint, as reported by the engine."""
    constraint_id: str
    state: ConstraintState = ConstraintState.OK
    offending_robot_ids: list[int] = field(default_factory=list)
    timers: dict[int, float] = field(default_factory=dict)
    violation_count: int = 0
    points_lost: int = 0
    zone_counts: list[int] = field(default_factory=list)

    def to_proto(self) -> constraint_pb2.ConstraintStatus:
        proto = constraint_pb2.ConstraintStatus(
            constraint_id=self.constraint_id,
            state=int(self.state),
            offending_robot_ids=self.offending_robot_ids,
            violation_count=self.violation_count,
            points_lost=self.points_lost,
            zone_counts=self.zone_counts,
        )
        for robot_id, seconds in self.timers.items():
            proto.timers[robot_id] = seconds
        return proto

    @classmethod
    def from_proto(cls, proto: constraint_pb2.ConstraintStatus) -> "ConstraintStatus":
        return cls(
            constraint_id=proto.constraint_id,
            state=ConstraintState(proto.state),
            offending_robot_ids=list(proto.offending_robot_ids),
            timers=dict(proto.timers),
            violation_count=proto.violation_count,
            points_lost=proto.points_lost,
            zone_counts=list(proto.zone_counts),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "ConstraintStatus":
        proto = constraint_pb2.ConstraintStatus()
        proto.ParseFromString(data)
        return cls.from_proto(proto)


def find_constraint(constraints: Iterable[Constraint], constraint_id: str) -> Optional[Constraint]:
    return next((c for c in constraints if c.id == constraint_id), None)
