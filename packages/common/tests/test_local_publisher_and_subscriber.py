"""
Tests for the local publisher and subscriber
"""

import unittest

from common.publishers.local_publisher import LocalPublisher
from common.subscribers.local_subscriber import LocalSubscriber
from common.position import Position


class TestLocalPublisherAndSubscriber(unittest.TestCase):
    def test_publish(self):
        publisher = LocalPublisher(("127.0.0.1", 5000))
        publisher.send(Position(0, 0))
        self.assertEqual(publisher.data["127.0.0.1:5000"], Position(0, 0))

    def test_subscribe(self):
        LocalPublisher.data["127.0.0.1:5000"] = Position(0, 0)
        subscriber = LocalSubscriber(("127.0.0.1", 5000), Position)
        self.assertEqual(subscriber.receive(), Position(0, 0))

    def test_publisher_subscribe(self):
        publisher = LocalPublisher(("127.0.0.1", 5000))
        subscriber = LocalSubscriber(("127.0.0.1", 5000), Position)
        publisher.send(Position(0, 0))
        self.assertEqual(subscriber.receive(), Position(0, 0))

    def test_publisher_subscriber_different_addresses(self):
        publisher = LocalPublisher(("127.0.0.1", 5000))
        subscriber = LocalSubscriber(("127.0.0.1", 5001), Position)
        publisher.send(Position(0, 0))
        self.assertIsNone(subscriber.receive())
