"""
The engine link is the interface's only connection to the engine. It reads
the latest GameState from a common Subscriber and sends AgentActionRequests
through a common Publisher, so Local (in-process) and Socket transports are
interchangeable.
"""

import logging
from typing import Callable, Optional

from common.agent_action import AgentAction, AgentActionRequest
from common.convertible import Convertible
from common.game_state import GameState
from common.publisher import Publisher
from common.publishers.local_publisher import LocalPublisher
from common.publishers.socket_publisher import SocketPublisher
from common.subscriber import Subscriber
from common.subscribers.local_subscriber import LocalSubscriber
from common.subscribers.socket_subscriber import SocketSubscriber

log = logging.getLogger(__name__)

LOCAL_STATE_ADDRESS = ("local", 5100)
LOCAL_ACTION_ADDRESS = ("local", 5101)


class LazyPublisher(Publisher):
    """
    Creates the wrapped publisher on first send and recreates it after a
    connection error, so either side of a socket link can start first.
    """

    def __init__(self, factory: Callable[[], Publisher]):
        self._factory = factory
        self._publisher: Optional[Publisher] = None

    def send(self, data: Convertible) -> bool:
        try:
            if self._publisher is None:
                self._publisher = self._factory()
            self._publisher.send(data)
            return True
        except OSError as error:
            if self._publisher is not None:
                log.warning("Publisher disconnected: %s", error)
            self._publisher = None
            return False


class EngineLink:
    def __init__(self, subscriber: Subscriber, publisher: Publisher):
        self.subscriber = subscriber
        self.publisher = publisher

    def latest_state(self) -> Optional[GameState]:
        return self.subscriber.receive()

    def send(self, actions: list[AgentAction]) -> bool:
        if not actions:
            return True
        result = self.publisher.send(AgentActionRequest(actions))
        return result is not False


def local_link() -> EngineLink:
    return EngineLink(
        LocalSubscriber(LOCAL_STATE_ADDRESS, GameState),
        LocalPublisher(LOCAL_ACTION_ADDRESS),
    )


def socket_link(engine_host: str, state_port: int, action_port: int) -> EngineLink:
    return EngineLink(
        SocketSubscriber(("0.0.0.0", state_port), GameState),
        LazyPublisher(lambda: SocketPublisher((engine_host, action_port))),
    )
