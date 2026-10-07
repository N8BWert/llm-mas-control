"""
Mapping between the action kind strings used by the UI / LLM and the
common action classes sent to the engine.

"move" targets are world coordinates (x, y); every other kind targets a
tile (i, j) of the map grid.
"""

from typing import Sequence

import numpy as np

from common.actions.build_farm_action import BuildFarmAction
from common.actions.build_house_action import BuildHouseAction
from common.actions.build_quarry_action import BuildQuarryAction
from common.actions.drop_action import DropAction
from common.actions.farm_action import FarmAction
from common.actions.mine_action import MineAction
from common.actions.move_action import MoveAction
from common.actions.pick_up_action import PickUpAction
from common.tile import Tile

TILE_ACTIONS = {
    "mine": MineAction,
    "farm": FarmAction,
    "pick_up": PickUpAction,
    "drop": DropAction,
    "build_farm": BuildFarmAction,
    "build_house": BuildHouseAction,
    "build_quarry": BuildQuarryAction,
}

ACTION_KINDS = ["move", *TILE_ACTIONS]


def make_action(kind: str, target: Sequence[float]):
    """Build the common action object for a kind and target."""
    if kind == "move":
        return MoveAction(np.array([float(target[0]), float(target[1])]))
    if kind in TILE_ACTIONS:
        return TILE_ACTIONS[kind](Tile(int(target[0]), int(target[1])))
    raise ValueError(f"Unknown action kind: {kind}")


def kind_of(action) -> str:
    if isinstance(action, MoveAction):
        return "move"
    for kind, cls in TILE_ACTIONS.items():
        if isinstance(action, cls):
            return kind
    raise ValueError(f"Unknown action: {action}")
