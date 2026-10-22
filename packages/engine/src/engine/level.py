"""
Level abstraction to represent a game level and when things spawn
"""

from dataclasses import dataclass
from enum import IntEnum

from common.tile import Tile
from dataclasses_json import dataclass_json


class EventType(IntEnum):
    """
    The type of event to occur in a game level 
    """
    SPAWN_APPLE = 0
    SPAWN_BIRD = 1
    REMOVE_BIRD = 2


@dataclass_json
@dataclass
class Event:
    """
    An event that occurs at a specific time in a game level 
    """
    # The tick for the event (in 30ths of a second)
    tick: int
    # The type of event
    event_type: EventType
    # The tile to spawn the event on
    tile: Tile


@dataclass_json
@dataclass
class Level:
    """
    A game level that contains a list of events to occur at specific times
    """
    # The list of events to occur in the level
    events: list[Event]
    # The list of water tiles to place in the level
    water_tiles: list[Tile]
    # The width of the level in tiles
    width: int = 32
    # The height of the level in tiles
    height: int = 20
    # The number of agents to start with
    start_agents: int = 5
    # The maximum number of agents for the level
    max_agents: int = 10
    # The tile for the castle
    castle_tile: Tile = Tile(3, 3)
    # The number of points for the user to start with
    start_points: int = 100
