"""
Tests for the input system to ensure it is working properly 
"""

import unittest

from common.actions.build_farm_action import BuildFarmAction
from common.actions.farm_action import FarmAction
from common.agent_action import AgentAction, AgentActionRequest
from common.publishers.local_publisher import LocalPublisher
from common.subscribers.local_subscriber import LocalSubscriber
from common.tile import Tile
from engine.input_system import InputSystem


class TestInputSystem(unittest.TestCase):
    def test_receive_new_agent_actions(self):
        publisher = LocalPublisher(("127.0.0.1", 5000))
        subscriber = LocalSubscriber(("127.0.0.1", 5000), AgentActionRequest)
        input_system = InputSystem(
            subscriber,
            10
        )
        request = AgentActionRequest([
            AgentAction(0, FarmAction(Tile(x=0, y=0))),
            AgentAction(1, FarmAction(Tile(x=0, y=0))),
            AgentAction(2, FarmAction(Tile(x=0, y=0)))
        ])
        publisher.send(request)
        actions = input_system.get_agent_actions()
        self.assertEqual(actions[0], AgentAction(0, FarmAction(Tile(x=0, y=0))))
        self.assertEqual(actions[1], AgentAction(1, FarmAction(Tile(x=0, y=0))))
        self.assertEqual(actions[2], AgentAction(2, FarmAction(Tile(x=0, y=0))))
        for i in range(3, 9):
            self.assertEqual(actions[i], None)

    def test_receive_new_agent_actions_override_existing_actions(self):
        publisher = LocalPublisher(("127.0.0.1", 5000))
        subscriber = LocalSubscriber(("127.0.0.1", 5000), AgentActionRequest)
        input_system = InputSystem(
            subscriber,
            10
        )
        for i in range(3):
            input_system.agent_actions[i] = AgentAction(
                i,
                BuildFarmAction(Tile(x=0, y=0))
            )
        request = AgentActionRequest([
            AgentAction(0, FarmAction(Tile(x=0, y=0))),
            AgentAction(1, FarmAction(Tile(x=0, y=0))),
        ])
        publisher.send(request)
        actions = input_system.get_agent_actions()
        for i in range(2):
            self.assertEqual(actions[i], AgentAction(i, FarmAction(Tile(x=0, y=0))))
        self.assertEqual(actions[2], AgentAction(2, BuildFarmAction(Tile(x=0,y=0))))
        for i in range(3, 9):
            self.assertEqual(actions[i], None)

    def test_receive_new_agent_action(self):
        publisher = LocalPublisher(("127.0.0.1", 5000))
        subscriber = LocalSubscriber(("127.0.0.1", 5000), AgentActionRequest)
        input_system = InputSystem(
            subscriber,
            1
        )
        request = AgentActionRequest([
            AgentAction(0, FarmAction(Tile(x=0,y=0))),
            AgentAction(1, FarmAction(Tile(x=0,y=0)))
        ])
        publisher.send(request)
        actions = input_system.get_agent_actions()
        self.assertEqual(len(actions), 2)
        for i in range(2):
            self.assertEqual(actions[i], AgentAction(i, FarmAction(Tile(x=0,y=0))))

    def test_clear_agent_action(self):
        subscriber = LocalSubscriber(("127.0.0.1", 5000), AgentActionRequest)
        input_system = InputSystem(
            subscriber,
            10
        )
        for i in range(10):
            input_system.agent_actions[i] = AgentAction(i, FarmAction(Tile(x=0,y=0)))
        input_system.clear_agent_actions([0, 2, 4, 6, 8])
        for i in range(10):
            if i % 2 == 0:
                self.assertEqual(input_system.agent_actions[i], None)
            else:
                self.assertEqual(input_system.agent_actions[i], AgentAction(i, FarmAction(Tile(x=0,y=0))))


