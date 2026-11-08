"""
What the Lieutenant knows about the past: the game events since it last looked, and its earlier exchanges.
Each LLM request stands alone, so this is the only way anything carries over between them.
"""

from collections import deque

from common.game_state import GameState
from common.tile import Tile, TileOverlay, TileType
from gui_common.gui import AGENT_NAMES

from gui_llm.parsing import STRUCTURE_KINDS, entity_id

# Limits from input_schema.json
MAX_EVENTS: int = 10
MAX_EXCHANGES: int = 5

BUILT_TYPES = {TileType.HOUSE, TileType.FARM, TileType.QUARRY}


class EventLog:
    def __init__(self):
        self.events: deque[tuple[float, dict]] = deque(maxlen=MAX_EVENTS)
        self.tiles: list[tuple[TileType, TileOverlay]] | None = None
        self.carrying: dict[int, bool] = {}
        self.points: int = 0

    def observe(self, game_state: GameState, now: float):
        tiles = [(tile.tile_type, tile.tile_overlay) for tile in game_state.tile_states]
        carrying = {agent.id: agent.carrying_apple for agent in game_state.agent_states}

        if self.tiles is not None:
            self._diff_tiles(tiles, game_state.width, now)
            self._diff_agents(carrying, game_state.points, now)

        self.tiles = tiles
        self.carrying = carrying
        self.points = game_state.points

    def _diff_tiles(self, tiles: list[tuple[TileType, TileOverlay]], width: int, now: float):
        for index, (old, new) in enumerate(zip(self.tiles, tiles)):
            tile = Tile(index % width, index // width)

            if new[0] != old[0] and new[0] in BUILT_TYPES and old[0] != TileType.OBSCURED:
                self._add(now, "build_complete", entity=entity_id(STRUCTURE_KINDS[new[0]], tile))
            if new[1] != old[1]:
                if new[1] == TileOverlay.APPLE:
                    self._add(now, "apple_spawned", entity=entity_id("apple", tile))
                elif new[1] == TileOverlay.BIRD:
                    self._add(now, "bird_spawned", entity=entity_id("bird", tile))

    def _diff_agents(self, carrying: dict[int, bool], points: int, now: float):
        for agent_id in self.carrying.keys() - carrying.keys():
            self._add(now, "ant_carried_off", ant=AGENT_NAMES[agent_id])
        for agent_id in carrying.keys() - self.carrying.keys():
            self._add(now, "ant_respawned", ant=AGENT_NAMES[agent_id])
        if points > self.points:
            for agent_id, was_carrying in self.carrying.items():
                if was_carrying and carrying.get(agent_id) is False:
                    self._add(now, "apple_delivered", ant=AGENT_NAMES[agent_id], entity="castle")

    def _add(self, now: float, event_type: str, ant: str | None = None, entity: str | None = None):
        self.events.append((now, {"type": event_type, "ant": ant, "entity": entity}))

    def recent(self, now: float) -> list[dict]:
        """
        Returns:
            The last MAX_EVENTS events, however old, newest first.
        """
        return [{"seconds_ago": round(now - when, 1), **event} for when, event in reversed(self.events)]


class Memory:
    def __init__(self):
        self.notes: str = ""
        self.exchanges: deque[tuple[float, dict]] = deque(maxlen=MAX_EXCHANGES)

    def record(self, user_text: str, out: dict, now: float):
        """
        Remembers an exchange that the player saw the outcome of.
        """
        if out["memory_notes"] is not None:
            self.notes = out["memory_notes"]
        self.exchanges.append((now, {
            "user_text": user_text,
            "status": out["status"],
            "summary": out["summary"],
            "referenced": _referenced(out),
        }))

    def snapshot(self, now: float) -> dict:
        """
        Returns:
            The memory object of the LLM's input, newest exchange first.
        """
        return {
            "notes": self.notes,
            "recent_exchanges": [
                {"seconds_ago": round(now - when, 1), **exchange}
                for when, exchange in reversed(self.exchanges)
            ],
        }


def _referenced(out: dict) -> list[str]:
    """
    Attempt at deictics

    Returns:
        The ants, entities and cells an output touched, without repeats.
    """
    symbols = []
    for cancel in out["cancels"]:
        symbols.extend(cancel["subjects"])
    for order in out["orders"]:
        symbols.extend(order["subjects"])
        symbols.extend(step["target"] for step in order["steps"] if step["target"] != "just_built")
    return list(dict.fromkeys(symbols))
