"""
Tool (function-calling) schemas the LLM uses to command robots, and the
code that turns a tool call into command-queue entries.
"""

from interfaces.actions import ACTION_KINDS
from interfaces.commands import CommandQueue

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "queue_command",
            "description": (
                "Give one or more robots a command. For 'move', x and y are world "
                "coordinates in meters. For every other action, x and y are the integer "
                "tile indices (i, j) of the tile to act on; the robot drives there itself. "
                "With append=false the robots' existing commands are replaced; with "
                "append=true the command is added to the end of their queue."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "robot_ids": {"type": "array", "items": {"type": "integer"}},
                    "action": {"type": "string", "enum": ACTION_KINDS},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "append": {"type": "boolean", "default": False},
                },
                "required": ["robot_ids", "action", "x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_commands",
            "description": "Cancel all current and queued commands of the given robots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "robot_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["robot_ids"],
            },
        },
    },
]


def apply_tool_call(name: str, args: dict, queue: CommandQueue, robot_ids: set[int]) -> str:
    """
    Apply one tool call to the queue.

    Args:
        name (str): Tool name.
        args (dict): Parsed tool arguments.
        queue (CommandQueue): Queue to add commands to.
        robot_ids (set[int]): Ids of robots that exist and can take commands.

    Returns:
        str: Human-readable summary for the LLM log.

    Raises:
        ValueError: If the call is invalid.
    """
    ids = [int(i) for i in args.get("robot_ids", [])]
    unknown = [i for i in ids if i not in robot_ids]
    if unknown:
        raise ValueError(f"Unknown or unavailable robots: {unknown}")
    if not ids:
        raise ValueError("No robots given")
    if name == "queue_command":
        kind = args["action"]
        target = (float(args["x"]), float(args["y"]))
        if kind != "move":
            target = (round(target[0]), round(target[1]))
        append = bool(args.get("append", False))
        queue.add(ids, kind, target, append=append, source="llm")
        verb = "queued" if append else "assigned"
        return f"{verb} {kind} at {target} to robots {ids}"
    if name == "clear_commands":
        queue.clear(ids)
        return f"cleared commands of robots {ids}"
    raise ValueError(f"Unknown tool: {name}")
