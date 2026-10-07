"""
A scenario describes a whole game session: the map, the robots, the game
rules (speeds, action durations, points) and the rounds with their constraint
schedules. Scenarios are plain JSON so the same file can be reused across
participants and across interfaces for clean comparisons.

Random constraints are drawn from a round's random_pool with a generator
seeded by (seed, round index), so every run of the same file draws the same ones.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import numpy as np

from common.arena import Arena
from common.constraints import Constraint
from common.entity import Entity
from common.tile import TileState


@dataclass
class EnemySpec:
    """An enemy that patrols back and forth along a list of waypoints."""
    id: int
    path: list[tuple[float, float]]
    speed: float = 0.05
    label: str = ""
    radius: float = 0.2


@dataclass
class RoundSpec:
    name: str
    duration_s: float
    constraints: list[Constraint] = field(default_factory=list)
    random_pool: list[Constraint] = field(default_factory=list)
    pick: int = 0


@dataclass
class Scenario:
    name: str = "default"
    seed: int = 0
    n_robots: int = 6
    robot_speed: float = 0.15
    roles: list[str] = field(default_factory=lambda: ["worker"])
    arena: Arena = field(default_factory=Arena)
    grid: tuple[int, int] = (32, 20)
    home: tuple[float, float] = (0.0, 0.0)
    tiles: list[tuple[TileState, int, int]] = field(default_factory=list)
    enemies: list[EnemySpec] = field(default_factory=list)
    objectives: list[Entity] = field(default_factory=list)
    action_durations: dict[str, float] = field(default_factory=dict)
    action_points: dict[str, int] = field(default_factory=dict)
    item_points: dict[str, int] = field(default_factory=dict)
    rounds: list[RoundSpec] = field(default_factory=lambda: [RoundSpec("Round 1", 120.0)])

    def role_of(self, robot_id: int) -> str:
        return self.roles[robot_id % len(self.roles)]

    def tile_grid(self) -> np.typing.NDArray[np.uint8]:
        grid = np.zeros(self.grid, dtype=np.uint8)
        for state, i, j in self.tiles:
            grid[i, j] = state
        return grid

    def round_constraints(self, index: int) -> list[Constraint]:
        spec = self.rounds[index]
        rng = random.Random(f"{self.seed}-{index}")
        drawn = rng.sample(spec.random_pool, min(spec.pick, len(spec.random_pool)))
        return spec.constraints + drawn

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        data = dict(data)
        if "arena" in data:
            data["arena"] = Arena(*data["arena"])
        if "grid" in data:
            data["grid"] = tuple(data["grid"])
        if "home" in data:
            data["home"] = tuple(data["home"])
        if "tiles" in data:
            data["tiles"] = _parse_tiles(data["tiles"])
        if "enemies" in data:
            data["enemies"] = [
                EnemySpec(**{**e, "path": [tuple(p) for p in e["path"]]})
                for e in data["enemies"]
            ]
        if "objectives" in data:
            data["objectives"] = [
                Entity(id=o["id"], kind=o.get("kind", "objective"),
                       x=o["position"][0], y=o["position"][1], label=o.get("label", ""))
                for o in data["objectives"]
            ]
        if "rounds" in data:
            data["rounds"] = [
                RoundSpec(
                    name=r["name"],
                    duration_s=r["duration_s"],
                    constraints=[Constraint.from_dict(c) for c in r.get("constraints", [])],
                    random_pool=[Constraint.from_dict(c) for c in r.get("random_pool", [])],
                    pick=r.get("pick", 0),
                )
                for r in data["rounds"]
            ]
        data.pop("description", None)
        return cls(**data)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Scenario":
        with open(path) as f:
            return cls.from_dict(json.load(f))


def _parse_tiles(entries: list[dict]) -> list[tuple[TileState, int, int]]:
    """
    Each entry is {"state": "QUARRY", "x": 3, "y": 4} with optional "w"/"h"
    to fill a block of tiles.
    """
    tiles = []
    for entry in entries:
        state = TileState[entry["state"]]
        for i in range(entry["x"], entry["x"] + entry.get("w", 1)):
            for j in range(entry["y"], entry["y"] + entry.get("h", 1)):
                tiles.append((state, i, j))
    return tiles
