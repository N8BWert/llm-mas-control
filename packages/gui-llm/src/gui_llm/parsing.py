"""
The set of functions necessary for converting LLM language to game language.
"""

import json
import math
import re

from common.agent_action import (
    AgentAction,
    BuildFarmAction,
    BuildHouseAction,
    BuildQuarryAction,
    DropAction,
    FarmAction,
    MineAction,
    MoveAction,
    PickUpAction,
)
from common.game_state import GameState
from common.tile import Tile, TileOverlay, TileType
from gui_common.gui import AGENT_NAMES, GUI
from jsonschema import Draft202012Validator


# Level 1: JSON formatting
def parse_json_strict(text: str):
    """
    Parses the string as a JSON object.
    """
    assert isinstance(text, str)

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

def parse_json_lenient(text: str):
    """
    Parses the string as a JSON object,
    but also forgives any leading mess (in case the LLM bloviates).
    """
    assert isinstance(text, str)

    dec = json.JSONDecoder()
    starts = sorted({m.start() for m in re.finditer(r"^\{", text, re.M)})
    for pos in starts:
        if pos < 0:
            continue
        try:
            obj, _ = dec.raw_decode(text[pos:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None

# Level 2: Schema matching
def schema_errors(instance, schema):
    v = Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))]

# Level 3: Game semantics
GRID_COLUMNS = "ABCDEFGHIJ"
GRID_ROWS = 7
_CELL_RE = re.compile(r"^([A-Z])([0-9]+)$")

def is_cell(symbol):
    return _CELL_RE.match(symbol) is not None

def cell_in_bounds(cell):
    m = _CELL_RE.match(cell)
    return bool(m) and m.group(1) in GRID_COLUMNS and 1 <= int(m.group(2)) <= GRID_ROWS

ALLOWED_TARGETS = {
    "move": {"cell", "castle", "house", "farm", "quarry", "apple"},
    "pick_up": {"apple"},
    "drop": {"castle", "cell"},
    "build_farm": {"cell", "castle", "house", "farm", "quarry"},
    "build_house": {"cell", "castle", "house", "farm", "quarry"},
    "build_quarry": {"cell", "castle", "house", "farm", "quarry"},
    "farm": {"farm"},
    "mine": {"quarry"},
}
WORK_AFTER_BUILD = {"build_farm": "farm", "build_quarry": "mine"}

def reference_errors(state, out):
    errs = []
    ants = {a["id"]: a for a in state["ants"]}
    entities = {e["id"]: e for e in state["entities"]}
 
    # status consistency
    if out["status"] == "ok":
        if out["refusal_reason"] is not None:
            errs.append("status ok but refusal_reason is set")
        if not (out["cancels"] or out["orders"] or out["memory_notes"] is not None):
            errs.append("status ok but cancels, orders and memory_notes are all empty")
    else:
        if out["refusal_reason"] is None:
            errs.append("status refused but refusal_reason is null")
        for k in ("cancels", "orders", "unhandled"):
            if out[k]:
                errs.append(f"status refused but {k} is not empty")
 
    def check_subjects(subjects, where):
        for s in subjects:
            if s not in ants:
                errs.append(f"{where}: unknown subject {s}")
 
    # cancels
    for i, c in enumerate(out["cancels"]):
        where = f"cancels[{i}]"
        check_subjects(c["subjects"], where)
        if c["scope"] == "ids":
            if not c["command_ids"]:
                errs.append(f"{where}: scope ids needs command_ids")
            known = {q["cmd_id"] for a in c["subjects"] if a in ants for q in ants[a]["queue"]}
            for cid in c["command_ids"]:
                if cid not in known:
                    errs.append(f"{where}: command id {cid} not in the subjects' queues")
        elif c["command_ids"]:
            errs.append(f"{where}: command_ids must be [] unless scope is ids")
 
    # orders
    for i, o in enumerate(out["orders"]):
        where = f"orders[{i}]"
        check_subjects(o["subjects"], where)
        prev_action = None
        for j, s in enumerate(o["steps"]):
            sw = f"{where}.steps[{j}]"
            action, target = s["action"], s["target"]
            if o["loop"] and action.startswith("build_"):
                errs.append(f"{sw}: a loop cannot contain build steps (each pass would build again)")
            if target == "just_built":
                if WORK_AFTER_BUILD.get(prev_action) != action:
                    errs.append(f"{sw}: just_built must directly follow a matching build step")
            else:
                cls = None
                if target in entities:
                    cls = entities[target]["kind"]
                elif is_cell(target):
                    if cell_in_bounds(target):
                        cls = "cell"
                    else:
                        errs.append(f"{sw}: cell {target} is outside the grid (A1 to {GRID_COLUMNS[-1]}{GRID_ROWS})")
                else:
                    errs.append(f"{sw}: unknown target {target}")
                if cls is not None and cls not in ALLOWED_TARGETS[action]:
                    errs.append(f"{sw}: {action} cannot target a {cls} ({target})")
            prev_action = action
    return errs

# Level 4: Translation between the game and the LLM's symbols
ACTION_TYPES = {
    "move": MoveAction,
    "pick_up": PickUpAction,
    "drop": DropAction,
    "build_farm": BuildFarmAction,
    "build_house": BuildHouseAction,
    "build_quarry": BuildQuarryAction,
    "farm": FarmAction,
    "mine": MineAction,
}
ACTION_NAMES = {action_type: name for name, action_type in ACTION_TYPES.items()}
STRUCTURE_KINDS = {
    TileType.CASTLE: "castle",
    TileType.HOUSE: "house",
    TileType.FARM: "farm",
    TileType.QUARRY: "quarry",
}
OVERLAY_KINDS = {TileOverlay.APPLE: "apple", TileOverlay.BIRD: "bird"}

# How far apart two objects can be and still count as "close".
PROXIMITY_RADIUS = 3.5

def tile_distance(a: Tile, b: Tile) -> float:
    """
    The Euclidean distance between two tiles, in tiles.
    """
    return math.hypot(a.x - b.x, a.y - b.y)

def tile_to_cell(tile: Tile) -> str:
    return f"{GRID_COLUMNS[tile.x]}{tile.y + 1}"

def cell_to_tile(cell: str) -> Tile:
    return Tile(GRID_COLUMNS.index(cell[0]), int(cell[1:]) - 1)

def _tile_size(game_state: GameState) -> tuple[float, float]:
    return GUI.ROBOTARIUM_WIDTH / game_state.width, GUI.ROBOTARIUM_HEIGHT / game_state.height

def _position_to_tile(position, game_state: GameState) -> Tile:
    tile_width, tile_height = _tile_size(game_state)
    x = int((position[0] + GUI.ROBOTARIUM_WIDTH / 2) // tile_width)
    y = int((position[1] + GUI.ROBOTARIUM_HEIGHT / 2) // tile_height)
    return Tile(min(game_state.width - 1, max(0, x)), min(game_state.height - 1, max(0, y)))

def cmd_id(agent_action: AgentAction) -> str:
    return f"cmd_{id(agent_action)}"

def _queued_command(agent_action: AgentAction, active: bool, in_loop: bool, game_state: GameState) -> dict:
    action = agent_action.action
    tile = _position_to_tile(action.position, game_state) if isinstance(action, MoveAction) else action.tile
    return {
        "cmd_id": cmd_id(agent_action),
        "action": ACTION_NAMES[type(action)],
        "target": tile_to_cell(tile),
        "status": "active" if active else "queued",
        "in_loop": in_loop,
    }

def entity_id(kind: str, tile: Tile) -> str:
    return "castle" if kind == "castle" else f"{kind}_{tile_to_cell(tile)}"

def build_llm_input(
    text: str,
    game_state: GameState,
    queues: list[list[AgentAction]],
    events: list[dict],
    memory: dict,
    looping: set[int],
) -> tuple[dict, dict[str, Tile], dict[str, Tile]]:
    """
    Snapshots the game as the input_schema.json object the LLM expects.
    `looping` holds the id() of every queued action that is part of a loop.

    Returns:
        The LLM input, the tile of each entity id in it (needed to translate the output),
        and the tile of each ant and entity id in it (needed to answer tool calls).
    """
    ants = []
    locations: dict[str, Tile] = {}
    for agent in game_state.agent_states:
        name = AGENT_NAMES[agent.id]
        queue = queues[agent.id]
        ants.append({
            "id": name,
            "idle": not agent.busy and not queue,
            "carrying_apple": agent.carrying_apple,
            "queue": [_queued_command(a, i == 0, id(a) in looping, game_state) for i, a in enumerate(queue)],
        })
        locations[name] = _position_to_tile(agent.position, game_state)

    entities = []
    entity_tiles: dict[str, Tile] = {}
    for y in range(game_state.height):
        for x in range(game_state.width):
            tile = Tile(x, y)
            tile_state = game_state.tile_states[x + y * game_state.width]
            kinds = [STRUCTURE_KINDS.get(tile_state.tile_type), OVERLAY_KINDS.get(tile_state.tile_overlay)]
            for kind in filter(None, kinds):
                symbol = entity_id(kind, tile)
                entities.append({"id": symbol, "kind": kind})
                entity_tiles[symbol] = tile
    locations.update(entity_tiles)

    proximity = {
        a: [b for b, b_tile in locations.items()
            if b != a and tile_distance(a_tile, b_tile) <= PROXIMITY_RADIUS]
        for a, a_tile in locations.items()
    }

    state = {
        "request": {"id": "0", "text": text},
        "game": {"points": game_state.points},
        "ants": ants,
        "entities": entities,
        "proximity": proximity,
        "events": events,
        "memory": memory,
    }
    return state, entity_tiles, locations

def _free_neighbor(tile: Tile, game_state: GameState) -> Tile | None:
    for y in range(max(tile.y - 1, 0), min(tile.y + 2, game_state.height)):
        for x in range(max(tile.x - 1, 0), min(tile.x + 2, game_state.width)):
            tile_state = game_state.tile_states[x + y * game_state.width]
            if tile_state.tile_type == TileType.EMPTY and tile_state.tile_overlay == TileOverlay.NONE:
                return Tile(x, y)
    return None

def output_to_actions(out: dict, entity_tiles: dict[str, Tile], game_state: GameState) -> list[tuple[int, str, bool, list[AgentAction]]]:
    """
    Translates validated LLM orders into a (agent id, mode, loop, actions) tuple per ant per order.

    Raises:
        ValueError: If a step can't be placed on the map.
    """
    tile_width, tile_height = _tile_size(game_state)
    translated = []
    for order in out["orders"]:
        steps: list[tuple[str, Tile]] = []
        last_built = None
        for step in order["steps"]:
            action, target = step["action"], step["target"]
            if target == "just_built":
                tile = last_built
            elif target in entity_tiles:
                tile = entity_tiles[target]
            else:
                tile = cell_to_tile(target)
            if action.startswith("build_"):
                if target in entity_tiles:
                    tile = _free_neighbor(tile, game_state)
                    if tile is None:
                        raise ValueError(f"{action}: no empty tile next to {target}")
                last_built = tile
            steps.append((action, tile))

        for name in order["subjects"]:
            agent_id = AGENT_NAMES.index(name)
            actions = []
            for action, tile in steps:
                goal = tile.center(tile_width, tile_height) if action == "move" else tile
                actions.append(AgentAction(agent_id=agent_id, action=ACTION_TYPES[action](goal)))
            translated.append((agent_id, order["mode"], order["loop"], actions))
    return translated
