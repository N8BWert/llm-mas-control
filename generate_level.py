"""
Generate a level for the game (we'll adjust the parameters manually, but this is a good starting point)
"""

import argparse
import random

from engine.level import Event, EventType, Level
from common.tile import Tile

# The spawn rates for the different tile overlay events (apples, bird_spawns, bird_lifespan)
SPAWN_RATES: dict[str, tuple[int, int, int]] = {
    "gathering": (150, 0, 0),
    "bronze": (900, 900, 900),
    "agricultural": (2700, 300, 200),
    "collapse": (0, 75, 150),
}

def parse_args() -> tuple[int, int, int, int, int, int, tuple[int, int], list[int], str]:
    parser = argparse.ArgumentParser(description="Generate a base level for the game")
    parser.add_argument("--width", help="The width of the level in tiles", type=int, default=10)
    parser.add_argument("--height", help="The height of the level in tiles", type=int, default=7)
    parser.add_argument("--start_agents", help="The number of agents to start with", type=int, default=5)
    parser.add_argument("--max_agents", help="The maximum number of agents for the level", type=int, default=10)
    parser.add_argument("--start_points", help="The number of points for the user to start with", type=int, default=100)
    parser.add_argument("--castle_tile", help="The tile for the castle (x,y)", type=str, default="1,1")
    parser.add_argument("--num-water-tiles", help="The number of water tiles to place in the level", type=int, default=4)
    parser.add_argument("--era-lengths", help="The length of each era in ticks (gathering, bronze, agricultural, collapse)", type=str, default="4500,4500,4500,4500")
    parser.add_argument("output", help="The output file for the level", type=str)
    args = parser.parse_args()
    return (
        args.width,
        args.height,
        args.start_agents,
        args.max_agents,
        args.start_points,
        args.num_water_tiles,
        tuple(map(int, args.castle_tile.split(","))),
        list(map(int, args.era_lengths.split(","))),
        args.output
    )

def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))

def generate_water_tiles(width: int, height: int, castle_tile: tuple[int, int], num_water_tiles: int) -> list[Tile]:
    water_tiles: list[Tile] = []
    while len(water_tiles) < num_water_tiles:
        position = (random.randint(0, width - 1), random.randint(0, height - 1))
        if position not in water_tiles and position != castle_tile:
            water_tiles.append(Tile(*position))
    return water_tiles

def generate_apple_events(era_lengths: list[int], castle_tile: tuple[int, int], width: int, height: int) -> list[Event]:
    game_length = sum(era_lengths)
    apple_events: list[Event] = []

    # Generate the apple events for the gathering age
    if SPAWN_RATES["gathering"][0] > 0:
        gathering_apples = int(era_lengths[0] / SPAWN_RATES["gathering"][0])
        for i in range(gathering_apples):
            # Add a bit of noise on the spawn time
            tick = clamp(i * SPAWN_RATES["gathering"][0] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position == castle_tile:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            apple_events.append(Event(tick=tick, event_type=EventType.SPAWN_APPLE, tile=Tile(*position)))

    # Generate the apple events for the bronze age
    if SPAWN_RATES["bronze"][0] > 0:
        bronze_apples = int(era_lengths[1] / SPAWN_RATES["bronze"][0])
        for i in range(bronze_apples):
            tick = clamp(era_lengths[0] + i * SPAWN_RATES["bronze"][0] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position == castle_tile:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            apple_events.append(Event(tick=tick, event_type=EventType.SPAWN_APPLE, tile=Tile(*position)))

    # Generate the apple events for the agricultural age
    if SPAWN_RATES["agricultural"][0] > 0:
        agricultural_apples = int(era_lengths[2] / SPAWN_RATES["agricultural"][0])
        for i in range(agricultural_apples):
            tick = clamp(era_lengths[0] + era_lengths[1] + i * SPAWN_RATES["agricultural"][0] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position == castle_tile:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            apple_events.append(Event(tick=tick, event_type=EventType.SPAWN_APPLE, tile=Tile(*position)))

    # Generate the apple events for the collapse age
    if SPAWN_RATES["collapse"][0] > 0:
        collapse_apples = int(era_lengths[3] / SPAWN_RATES["collapse"][0])
        for i in range(collapse_apples):
            tick = clamp(era_lengths[0] + era_lengths[1] + era_lengths[2] + i * SPAWN_RATES["collapse"][0] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position == castle_tile:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            apple_events.append(Event(tick=tick, event_type=EventType.SPAWN_APPLE, tile=Tile(*position)))

    return apple_events

def generate_bird_events(era_lengths: list[int], castle_tile: tuple[int, int], width: int, height: int) -> list[Event]:
    game_length = sum(era_lengths)
    bird_events: list[Event] = []

    banned_tiles = [
        (castle_tile[0] - 1, castle_tile[1] - 1),
        (castle_tile[0] - 1, castle_tile[1]),
        (castle_tile[0] - 1, castle_tile[1] + 1),
        (castle_tile[0], castle_tile[1] - 1),
        (castle_tile[0], castle_tile[1]),
        (castle_tile[0], castle_tile[1] + 1),
        (castle_tile[0] + 1, castle_tile[1] - 1),
        (castle_tile[0] + 1, castle_tile[1]),
        (castle_tile[0] + 1, castle_tile[1] + 1),
    ]

    # Generate the bird events for the gathering age
    if SPAWN_RATES["gathering"][1] > 0:
        gathering_birds = int(era_lengths[0] / SPAWN_RATES["gathering"][1])
        for i in range(gathering_birds):
            tick = clamp(i * SPAWN_RATES["gathering"][1] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position in banned_tiles:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            bird_events.append(Event(tick=tick, event_type=EventType.SPAWN_BIRD, tile=Tile(*position)))
            bird_events.append(Event(tick=clamp(tick + SPAWN_RATES["gathering"][2], 0, game_length), event_type=EventType.REMOVE_BIRD, tile=Tile(*position)))

    # Generate the bird events for the bronze age
    if SPAWN_RATES["bronze"][1] > 0:
        bronze_birds = int(era_lengths[1] / SPAWN_RATES["bronze"][1])
        for i in range(bronze_birds):
            tick = clamp(era_lengths[0] + i * SPAWN_RATES["bronze"][1] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position in banned_tiles:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            bird_events.append(Event(tick=tick, event_type=EventType.SPAWN_BIRD, tile=Tile(*position)))
            bird_events.append(Event(tick=clamp(tick + SPAWN_RATES["bronze"][2], 0, game_length), event_type=EventType.REMOVE_BIRD, tile=Tile(*position)))

    # Generate the bird events for the agricultural age
    if SPAWN_RATES["agricultural"][1] > 0:
        agricultural_birds = int(era_lengths[2] / SPAWN_RATES["agricultural"][1])
        for i in range(agricultural_birds):
            tick = clamp(era_lengths[0] + era_lengths[1] + i * SPAWN_RATES["agricultural"][1] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position in banned_tiles:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            bird_events.append(Event(tick=tick, event_type=EventType.SPAWN_BIRD, tile=Tile(*position)))
            bird_events.append(Event(tick=clamp(tick + SPAWN_RATES["agricultural"][2], 0, game_length), event_type=EventType.REMOVE_BIRD, tile=Tile(*position)))

    # Generate the bird events for the collapse age
    if SPAWN_RATES["collapse"][1] > 0:
        collapse_birds = int(era_lengths[3] / SPAWN_RATES["collapse"][1])
        for i in range(collapse_birds):
            tick = clamp(era_lengths[0] + era_lengths[1] + era_lengths[2] + i * SPAWN_RATES["collapse"][1] + random.randint(-10, 10), 0, game_length)
            position = (random.randint(0, width - 1), random.randint(0, height - 1))
            while position in banned_tiles:
                position = (random.randint(0, width - 1), random.randint(0, height - 1))
            bird_events.append(Event(tick=tick, event_type=EventType.SPAWN_BIRD, tile=Tile(*position)))
            bird_events.append(Event(tick=clamp(tick + SPAWN_RATES["collapse"][2], 0, game_length), event_type=EventType.REMOVE_BIRD, tile=Tile(*position)))

    return bird_events

def main():
    args = parse_args()
    width, height, start_agents, max_agents, start_points, num_water_tiles, castle_tile, era_lengths, output_file = args

    # Generate the initial apples for the level (8 apples)
    initial_apples: list[tuple[int, int]] = []
    while len(initial_apples) < 8:
        position = (random.randint(0, width - 1), random.randint(0, height - 1))
        if position not in initial_apples and position != castle_tile:
            initial_apples.append(position)
    initial_apple_events = [Event(tick=0, event_type=EventType.SPAWN_APPLE, tile=Tile(x, y)) for x, y in initial_apples]

    apple_events = generate_apple_events(era_lengths, castle_tile, width, height)
    bird_events = generate_bird_events(era_lengths, castle_tile, width, height)
    events = sorted(initial_apple_events + apple_events + bird_events, key=lambda e: e.tick)

    level = Level(
        events=events,
        water_tiles=generate_water_tiles(width, height, Tile(*castle_tile), num_water_tiles),
        width=width,
        height=height,
        start_agents=start_agents,
        max_agents=max_agents,
        castle_tile=Tile(*castle_tile),
        start_points=start_points
    )
    # Save the level to a JSON file
    with open(output_file, "w") as f:
        f.write(level.to_json(indent=4))


if __name__ == "__main__":
    main()
