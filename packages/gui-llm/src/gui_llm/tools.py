"""
Tools the LLM can call to resolve references that its input alone can't settle.

Each tool only reads the snapshot the LLM was given, so it can't reveal anything the prompt withholds.
"""

import json
import random

from common.game_state import GameState
from common.tile import Tile

from gui_llm.parsing import (
    GRID_COLUMNS,
    GRID_ROWS,
    _free_neighbor,
    cell_in_bounds,
    cell_to_tile,
    is_cell,
    tile_distance,
    tile_to_cell,
)

_ORIGIN_SCHEMA = {
    "type": "string",
    "description": f"An ant name, an entity id, or a grid cell (A1 to {GRID_COLUMNS[-1]}{GRID_ROWS}).",
}

TOOLS = [
    {
        "name": "find_nearest",
        "description": (
            "Ranks ants or entities of one kind by distance from an origin, nearest first. The origin itself is "
            "left out. Use for 'the closest X to Y' when `proximity` doesn't settle it. Distance is in tiles and "
            "straight-line: it ignores water and other obstacles. Equal distances are real ties."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": _ORIGIN_SCHEMA,
                "kind": {
                    "type": "string",
                    "enum": ["ant", "idle_ant", "apple", "castle", "house", "farm", "quarry"],
                },
                "limit": {
                    "type": "integer",
                    "description": "How many results to return, at least 1. Anything tied with the last one is included too.",
                },
            },
            "required": ["origin", "kind", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "pick_ants",
        "description": (
            "Picks ants at random, preferring idle ones. Use when the player leaves the choice open ('any ant', "
            "'two ants'). Ask for everything you need in one call, since separate calls can pick the same ant. "
            "Returns fewer ants than requested if too few qualify."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "How many ants to pick, at least 1."},
                "require": {
                    "type": "string",
                    "enum": ["none", "idle", "carrying_apple", "not_carrying_apple"],
                },
            },
            "required": ["count", "require"],
            "additionalProperties": False,
        },
    },
    {
        "name": "free_cell_near",
        "description": (
            "Finds an empty grid cell at or next to an origin. Use when the player describes a place relative to "
            "something ('next to Bob') and the action needs a cell. Returns a null cell if there is none."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"origin": _ORIGIN_SCHEMA},
            "required": ["origin"],
            "additionalProperties": False,
        },
    },
]


class ToolError(Exception):
    """
    Bad tool input. The message goes back to the LLM so that it can correct itself.
    """


def _resolve_origin(origin: str, locations: dict[str, Tile]) -> Tile:
    if origin in locations:
        return locations[origin]
    if is_cell(origin) and cell_in_bounds(origin):
        return cell_to_tile(origin)
    raise ToolError(f"Unknown origin {origin}. Use an id from the input, or a cell from A1 to {GRID_COLUMNS[-1]}{GRID_ROWS}.")


def find_nearest(origin: str, kind: str, limit: int, state: dict, locations: dict[str, Tile]) -> dict:
    origin_tile = _resolve_origin(origin, locations)
    if kind == "ant":
        candidates = [ant["id"] for ant in state["ants"]]
    elif kind == "idle_ant":
        candidates = [ant["id"] for ant in state["ants"] if ant["idle"]]
    else:
        candidates = [entity["id"] for entity in state["entities"] if entity["kind"] == kind]
    ranked = sorted(
        ({"id": c, "distance": round(tile_distance(origin_tile, locations[c]), 2)} for c in candidates if c != origin),
        key=lambda result: (result["distance"], result["id"]),
    )
    kept = ranked[:max(limit, 1)]
    # Never hide a tie behind the limit, or the id order would quietly decide it
    return {"results": [r for r in ranked if kept and r["distance"] <= kept[-1]["distance"]]}


def pick_ants(count: int, require: str, state: dict) -> dict:
    requirements = {
        "none": lambda ant: True,
        "idle": lambda ant: ant["idle"],
        "carrying_apple": lambda ant: ant["carrying_apple"],
        "not_carrying_apple": lambda ant: not ant["carrying_apple"],
    }
    eligible = [ant for ant in state["ants"] if requirements[require](ant)]
    random.shuffle(eligible)
    eligible.sort(key=lambda ant: not ant["idle"])  # Stable, so it stays random among equals
    return {"ants": [ant["id"] for ant in eligible[:max(count, 1)]]}


def free_cell_near(origin: str, locations: dict[str, Tile], game_state: GameState) -> dict:
    tile = _free_neighbor(_resolve_origin(origin, locations), game_state)
    return {"cell": None if tile is None else tile_to_cell(tile)}


def execute_tool(
    name: str,
    tool_input: dict,
    state: dict,
    locations: dict[str, Tile],
    game_state: GameState,
) -> tuple[str, bool]:
    """
    Runs one tool call against the snapshot the LLM was given.

    Returns:
        The tool's result as a JSON string, and whether it is an error.
    """
    try:
        if name == "find_nearest":
            result = find_nearest(tool_input["origin"], tool_input["kind"], tool_input["limit"], state, locations)
        elif name == "pick_ants":
            result = pick_ants(tool_input["count"], tool_input["require"], state)
        elif name == "free_cell_near":
            result = free_cell_near(tool_input["origin"], locations, game_state)
        else:
            raise ToolError(f"Unknown tool {name}.")
    except ToolError as e:
        return json.dumps({"error": str(e)}), True
    return json.dumps(result), False
