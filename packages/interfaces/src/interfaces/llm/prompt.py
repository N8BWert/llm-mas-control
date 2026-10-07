"""
Turns the UI view (the same JSON the browser renders) into compact text the
LLM can reason about, including every active constraint and its live status.
"""

from collections import defaultdict

from common.arena import Arena
from common.tile import TileState

STATE_NAMES = {0: "ok", 1: "WARNING", 2: "VIOLATED"}

SYSTEM_PROMPT = """\
You command a swarm of real ground robots in a real-time strategy game.
The human operator gives you an overarching strategy; you turn it into concrete
robot commands using the tools. Follow the strategy, maximize score, and never
violate active constraints: every violation costs points.

Game rules:
- Robots do nothing until commanded. A commanded robot drives to its target and
  then performs a timed action there.
- mine at a QUARRY tile gives stone, farm at a FARM tile gives food, pick_up at an
  APPLE tile gives an apple. A robot carries one item at a time.
- drop at the CASTLE tile scores the carried item.
- build_farm / build_quarry turn an EMPTY tile into a FARM / QUARRY; build_house on
  an EMPTY tile scores points directly.
- Enemies damage robots that come close; a robot at 0 health is disabled.

Use append=true to chain commands for a robot (e.g. mine, then drop).
Only command robots that need new orders; robots with a plan keep executing it.
Briefly explain your reasoning in plain text, then call the tools."""


def _xy(position: dict) -> str:
    return f"({position.get('x', 0.0):.2f}, {position.get('y', 0.0):.2f})"


def describe_state(view: dict) -> str:
    arena = Arena(**view["arena"]) if view.get("arena") else Arena()
    width, height = view["width"], view["height"]
    tw, th = arena.tile_size(width, height)
    lines = [
        f"Score: {view['points']}. Round {view['round_index'] + 1}/{view['round_count']} "
        f"'{view['round_name']}', {view['time_remaining']:.0f}s remaining.",
        f"Arena: x in [{arena.x_min}, {arena.x_max}], y in [{arena.y_min}, {arena.y_max}] meters. "
        f"Tile grid {width}x{height}, each tile {tw:.2f}x{th:.2f} m; "
        f"tile (i, j) is centered at x = {arena.x_min} + (i + 0.5) * {tw:.2f}, "
        f"y = {arena.y_min} + (j + 0.5) * {th:.2f}.",
        "",
        "Map features (tile indices):",
    ]
    features = defaultdict(list)
    for index, state in enumerate(view["tiles"]):
        if state != TileState.EMPTY:
            features[TileState(state).name].append(f"({index // height},{index % height})")
    for name, tiles in sorted(features.items()):
        lines.append(f"- {name}: {' '.join(tiles)}")

    lines += ["", "Robots:"]
    for agent in view["agent_states"]:
        parts = [f"- robot {agent['id']} ({agent['role'] or 'robot'}) at {_xy(agent['position'])}",
                 f"health {agent['health']:.0%}"]
        if agent["failure"]:
            parts.append(f"FAILURE: {agent['failure']}")
        elif agent["current_action"]:
            parts.append(f"doing {agent['current_action']}")
        else:
            parts.append("idle")
        if agent["carrying"]:
            parts.append(f"carrying {agent['carrying']}")
        queued = len(agent.get("plan", [])) - (1 if agent["current_action"] else 0)
        if queued > 0:
            parts.append(f"{queued} more command(s) queued")
        lines.append(", ".join(parts))

    if view.get("enemies"):
        lines += ["", "Enemies:"]
        lines += [f"- {e['label'] or 'enemy'} at {_xy(e['position'])}" for e in view["enemies"]]
    if view.get("objectives"):
        lines += ["", "Objectives:"]
        lines += [f"- {o['label'] or 'objective'} at {_xy(o['position'])}" for o in view["objectives"]]

    statuses = {s["constraint_id"]: s for s in view.get("constraint_statuses", [])}
    lines += ["", "Active constraints:"]
    if not view.get("active_constraints"):
        lines.append("- none")
    for constraint in view.get("active_constraints", []):
        status = statuses.get(constraint["id"], {})
        line = (
            f"- [{STATE_NAMES[status.get('state', 0)]}] {constraint['label']}: "
            f"{constraint['description']} Penalty {constraint['penalty']} per violation; "
            f"{status.get('violation_count', 0)} violation(s) so far."
        )
        if status.get("offending_robot_ids"):
            line += f" Offending robots: {status['offending_robot_ids']}."
        if status.get("timers"):
            timers = ", ".join(f"robot {k}: {v:.0f}s" for k, v in status["timers"].items())
            line += f" Time left: {timers}."
        lines.append(line)
    return "\n".join(lines)


def build_messages(strategy: str, view: dict, reason: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Operator strategy: {strategy}\n\n"
                f"Why you are being asked now: {reason}\n\n"
                f"Current game state:\n{describe_state(view)}"
            ),
        },
    ]
