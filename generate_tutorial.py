"""
Generate the tutorial level for the game.
"""

import random

from common.tile import Tile
from engine.level import Event, EventType, Level


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))

def main():
    width = 10
    height = 7
    start_agents = 5
    max_agents = 10
    castle_tile = (1, 1)
    start_farm_tile = (width - castle_tile[0] - 1, height - castle_tile[1] - 1)
    start_points = 1000
    water_tiles = [(3, 3), (3, 4), (4, 3), (4, 4)]

    # Generate apple spawn events
    events: list[Event] = []
    for i in range(100):
        tick = i * 30 * 10
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        while (x, y) in [(7, 2), (7, 1), (6, 1), (6, 2)] or (x, y) == castle_tile or (x, y) == start_farm_tile:
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
        events.append(Event(
            tick,
            EventType.SPAWN_APPLE,
            Tile(x, y)
        ))

    # Generate bird spawn events
    events.append(Event(tick=600, event_type=EventType.SPAWN_BIRD, tile=Tile(7, 2)))
    events.append(Event(tick=600, event_type=EventType.SPAWN_BIRD, tile=Tile(7, 1)))
    events.append(Event(tick=600, event_type=EventType.SPAWN_BIRD, tile=Tile(6, 1)))
    events.append(Event(tick=600, event_type=EventType.SPAWN_BIRD, tile=Tile(6, 2)))
    events = sorted(events, key=lambda e: e.tick)

    level = Level(
        events=events,
        water_tiles=[Tile(x, y) for x, y in water_tiles],
        width=width,
        height=height,
        start_agents=start_agents,
        max_agents=max_agents,
        castle_tile=Tile(*castle_tile),
        starting_farm_tile=Tile(*start_farm_tile),
        start_points=start_points
    )

    with open("./assets/levels/tutorial.json", "w") as f:
        f.write(level.to_json(indent=4))


if __name__ == "__main__":
    main()
