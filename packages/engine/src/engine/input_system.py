"""
The input system handles inputs (in the form of protobuf user commands).
These inputs are then translated into agent actions, which are relayed from the input
system to the physics and gameplay engines.
"""

import struct
import socket
import threading
from typing import Optional

from common.agent_action import AgentActionRequest, AgentAction
from common.subscriber import Subscriber


class InputSystem:
    """
    The input system is responsible for receiving user commands from
    the respective user interface.  It then processes these commands
    and sends the current agent actions to the gameplay engine.
    """

    def __init__(self, subscriber: Subscriber, num_robots: int = 10):
        self.subscriber = subscriber
        self.agent_actions: list[Optional[AgentAction]] = [None] * num_robots

    def get_agent_actions(self) -> list[AgentAction]:
        """
        Retrieve the current actions for all agents.

        Returns:
            list[AgentAction]: The current actions for all agents.
        """
        data: AgentActionRequest | None = self.subscriber.receive()
        if data is not None:
            for action in data.agent_actions:
                if 0 <= action.agent_id < len(self.agent_actions):
                    pass
            
        return self.agent_actions
