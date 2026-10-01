"""
Tests for the socket publisher and subscriber
"""

import unittest
import time

from common.publishers.socket_publisher import SocketPublisher
from common.subscribers.socket_subscriber import SocketSubscriber
from common.position import Position


class testSocketPublisherAndSubscriber(unittest.TestCase):
    def setUp(self):
        self.subscriber = SocketSubscriber(("127.0.0.1", 9000), Position)
        self.publisher = SocketPublisher(("127.0.0.1", 9000))

    def tearDown(self):
        self.subscriber.stop()

    def test_publish_subscribe(self):
        self.publisher.send(Position(0, 0))
        time.sleep(0.1)
        self.assertEqual(self.subscriber.receive(), Position(0, 0))
