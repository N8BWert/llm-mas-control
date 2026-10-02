"""
Tests for the LLM tool calls, prompt and planning loop (with a fake completion).
"""

import asyncio
import json
import unittest
from types import SimpleNamespace

import numpy as np

from common.agent_state import AgentState
from common.constraints import ConstraintStatus, ConstraintState, RectZone, RestrictedZone
from common.game_state import GameState

from interfaces.commands import CommandQueue
from interfaces.llm.agent import LlmAgent
from interfaces.llm.prompt import build_messages, describe_state
from interfaces.llm.tools import apply_tool_call
from interfaces.view_model import build_view


def make_view(queue: CommandQueue, constraints=(), statuses=()) -> dict:
    state = GameState(
        agent_states=[
            AgentState(0, np.array([0.0, 0.0]), False, role="worker"),
            AgentState(1, np.array([0.5, 0.5]), False, role="scout"),
            AgentState(2, np.array([0.5, -0.5]), False, failure="disabled"),
        ],
        tile_states=np.zeros((32, 20), dtype=np.uint8),
        constraints=list(constraints),
        constraint_statuses=list(statuses),
    )
    return build_view(state, queue)


def tool_call(name: str, **args):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def fake_completion(content: str, calls: list):
    calls_made = []

    async def completion(**kwargs):
        calls_made.append(kwargs)
        message = SimpleNamespace(content=content, tool_calls=calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    return completion, calls_made


class TestTools(unittest.TestCase):
    def test_queue_command_rounds_tile_targets(self):
        queue = CommandQueue()
        apply_tool_call("queue_command", {"robot_ids": [0], "action": "mine", "x": 3.4, "y": 7.6}, queue, {0})
        self.assertEqual(queue.plan(0)[0]["target"], [3, 8])
        self.assertEqual(queue.plan(0)[0]["source"], "llm")

    def test_move_keeps_world_coordinates_and_append(self):
        queue = CommandQueue()
        apply_tool_call("queue_command", {"robot_ids": [0], "action": "move", "x": 0.25, "y": -0.5}, queue, {0})
        apply_tool_call(
            "queue_command", {"robot_ids": [0], "action": "move", "x": 1, "y": 1, "append": True}, queue, {0}
        )
        self.assertEqual([c["target"] for c in queue.plan(0)], [[0.25, -0.5], [1.0, 1.0]])

    def test_clear_commands(self):
        queue = CommandQueue()
        queue.add([0], "move", (0, 0))
        apply_tool_call("clear_commands", {"robot_ids": [0]}, queue, {0})
        self.assertTrue(queue.is_idle(0))

    def test_invalid_calls_raise(self):
        queue = CommandQueue()
        with self.assertRaises(ValueError):
            apply_tool_call("queue_command", {"robot_ids": [9], "action": "move", "x": 0, "y": 0}, queue, {0})
        with self.assertRaises(ValueError):
            apply_tool_call("queue_command", {"robot_ids": [], "action": "move", "x": 0, "y": 0}, queue, {0})
        with self.assertRaises(ValueError):
            apply_tool_call("explode", {"robot_ids": [0]}, queue, {0})


class TestPrompt(unittest.TestCase):
    def test_describes_robots_and_constraints(self):
        constraint = RestrictedZone(id="r", label="No-go", zones=[RectZone(0, 0, 1, 1)])
        status = ConstraintStatus("r", ConstraintState.VIOLATED, [1])
        text = describe_state(make_view(CommandQueue(), [constraint], [status]))
        self.assertIn("No-go", text)
        self.assertIn("worker", text)
        self.assertIn("disabled", text.lower())

    def test_messages_include_strategy_and_reason(self):
        messages = build_messages("mine stone", make_view(CommandQueue()), "robots idle")
        self.assertEqual(messages[0]["role"], "system")
        joined = " ".join(m["content"] for m in messages)
        self.assertIn("mine stone", joined)
        self.assertIn("robots idle", joined)


class TestAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.queue = CommandQueue()
        self.published = []

        async def broadcast(message):
            self.published.append(message)

        self.broadcast = broadcast

    def agent(self, completion):
        return LlmAgent(self.queue, "fake-model", replan_s=1000, broadcast=self.broadcast, completion=completion)

    async def test_strategy_triggers_plan_and_applies_tool_calls(self):
        completion, calls = fake_completion(
            "Sending robot 0 to mine.",
            [
                tool_call("queue_command", robot_ids=[0], action="mine", x=3, y=4),
                tool_call("queue_command", robot_ids=[2], action="move", x=0, y=0),
            ],
        )
        agent = self.agent(completion)
        agent.observe(make_view(self.queue))
        await agent.set_strategy("mine stone")
        await agent._task
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model"], "fake-model")
        self.assertEqual(self.queue.plan(0)[0]["kind"], "mine")
        roles = [entry["role"] for entry in agent.snapshot()["log"]]
        self.assertEqual(roles, ["operator", "llm", "action", "error"])
        self.assertEqual(agent.status, "idle")
        self.assertEqual(self.published[-1]["type"], "llm")

    async def test_new_constraint_triggers_replan(self):
        completion, calls = fake_completion("", [])
        agent = self.agent(completion)
        agent.observe(make_view(self.queue))
        await agent.set_strategy("explore")
        await agent._task
        constraint = RestrictedZone(id="r", label="No-go", zones=[RectZone(0, 0, 1, 1)])
        agent.observe(make_view(self.queue, [constraint]))
        await agent._task
        self.assertEqual(len(calls), 2)

    async def test_halt_pauses_until_new_strategy(self):
        completion, calls = fake_completion("", [])
        agent = self.agent(completion)
        agent.observe(make_view(self.queue))
        await agent.set_strategy("explore")
        await agent._task
        agent.halt("Emergency stop")
        self.assertTrue(agent.paused)
        constraint = RestrictedZone(id="r", zones=[RectZone(0, 0, 1, 1)])
        agent.observe(make_view(self.queue, [constraint]))
        self.assertEqual(len(calls), 1)
        await agent.set_strategy("resume")
        await agent._task
        self.assertFalse(agent.paused)
        self.assertEqual(len(calls), 2)

    async def test_completion_error_is_reported(self):
        async def failing(**kwargs):
            raise RuntimeError("no API key")

        agent = self.agent(failing)
        agent.observe(make_view(self.queue))
        await agent.set_strategy("go")
        await agent._task
        self.assertEqual(agent.status, "error")
        self.assertIn("no API key", agent.error)


if __name__ == "__main__":
    unittest.main()
