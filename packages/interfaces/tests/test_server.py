"""
End-to-end tests: the FastAPI app with the in-process dummy engine, driven
over the WebSocket like the browser does.
"""

import json
import unittest

from fastapi.testclient import TestClient

from interfaces.config import Settings
from interfaces.server import create_app


def receive_until(ws, message_type, predicate=lambda data: True, limit=200):
    for _ in range(limit):
        message = json.loads(ws.receive_text())
        if message["type"] == message_type and predicate(message["data"]):
            return message
    raise AssertionError(f"No {message_type} message matched")


class TestServer(unittest.TestCase):
    def setUp(self):
        self.app = create_app(Settings(engine="dummy", web_dist="/nonexistent"))

    def test_config(self):
        with TestClient(self.app) as client:
            config = client.get("/api/config").json()
            self.assertEqual(config["mode"], "rts")
            self.assertIn("mine", config["action_kinds"])

    def test_state_broadcast(self):
        with TestClient(self.app) as client, client.websocket_connect("/ws") as ws:
            state = receive_until(ws, "state")["data"]
            self.assertEqual(len(state["agent_states"]), 6)
            self.assertEqual(state["round_name"], "Warm-up")
            self.assertIn("plan", state["agent_states"][0])
            self.assertEqual(len(state["tiles"]), state["width"] * state["height"])

    def test_command_moves_robot(self):
        with TestClient(self.app) as client, client.websocket_connect("/ws") as ws:
            receive_until(ws, "state")
            ws.send_json({"type": "command", "robot_ids": [0],
                          "action": {"kind": "move", "target": [0.0, 0.0]}})
            queue = receive_until(ws, "queue", lambda d: d["in_progress"])["data"]
            self.assertEqual(queue["in_progress"][0]["robot_id"], 0)
            receive_until(ws, "state", lambda d: d["agent_states"][0]["busy"])

    def test_invalid_message_returns_error(self):
        with TestClient(self.app) as client, client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "command", "robot_ids": [0],
                          "action": {"kind": "fly", "target": [0, 0]}})
            receive_until(ws, "error")

    def test_emergency_stop(self):
        with TestClient(self.app) as client, client.websocket_connect("/ws") as ws:
            receive_until(ws, "state")
            ws.send_json({"type": "emergency", "kind": "stop"})
            queue = receive_until(ws, "queue", lambda d: d["in_progress"])["data"]
            self.assertTrue(all(c["source"] == "emergency" for c in queue["in_progress"]))

    def test_restart(self):
        with TestClient(self.app) as client:
            self.assertTrue(client.post("/api/restart").json()["ok"])
