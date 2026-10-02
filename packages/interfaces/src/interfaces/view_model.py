"""
Builds the JSON the browser renders: the engine's GameState (converted with
protobuf's json_format so the proto stays the single schema) plus each
robot's command plan from the queue.
"""

from google.protobuf.json_format import MessageToDict

from common.game_state import GameState

from interfaces.commands import CommandQueue


def build_view(state: GameState, queue: CommandQueue) -> dict:
    view = MessageToDict(
        state.to_proto(),
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
        use_integers_for_enums=True,
    )
    for agent in view["agent_states"]:
        agent["plan"] = queue.plan(agent["id"])
    return view
