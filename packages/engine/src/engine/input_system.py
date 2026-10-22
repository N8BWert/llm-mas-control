"""
The input system handles inputs (in the form of protobuf user commands).
These inputs are then translated into agent actions, which are relayed from the input
system to the physics and gameplay engines.
"""

from common.agent_action import AgentAction, AgentActionRequest
from common.subscriber import Subscriber


class InputSystem:
    """
    The input system is responsible for receiving user commands from
    the respective user interface.  It then processes these commands
    and sends the current agent actions to the gameplay engine.
    """

    def __init__(self, subscriber: Subscriber, num_robots: int = 10):
        self.subscriber = subscriber
        self.agent_actions: list[AgentAction] | None = None

    def get_agent_actions(self) -> list[AgentAction] | None:
        """
        Retrieve the current actions for all agents.

        Returns:
            list[AgentAction]: The current actions for all agents.
        """
        data: AgentActionRequest | None = self.subscriber.receive()
        if data is not None:
            self.agent_actions = data.agent_actions
        return self.agent_actions

    def clear_agent_actions(self, ids: list[int]):
        """
        Clear the current agent actions for the given agents

        Args:
            ids (list[int]): The id of each agent to clear the
                action of 
        """
        for id in ids:
            self.agent_actions[id] = None

