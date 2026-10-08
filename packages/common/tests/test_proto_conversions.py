"""
Tests to ensure conversions from protobuf to python objects and
vice versa is working
"""

import unittest

import common.protos.agent_action_pb2 as agent_action_pb2
import common.protos.agent_state_pb2 as agent_state_pb2
import common.protos.game_state_pb2 as game_state_pb2
import common.protos.position_pb2 as position_pb2
import common.protos.tile_pb2 as tile_pb2
import numpy as np
from common.actions.build_farm_action import BuildFarmAction
from common.actions.build_house_action import BuildHouseAction
from common.actions.build_quarry_action import BuildQuarryAction
from common.actions.drop_action import DropAction
from common.actions.farm_action import FarmAction
from common.actions.mine_action import MineAction
from common.actions.move_action import MoveAction
from common.actions.pick_up_action import PickUpAction
from common.agent_action import AgentAction, AgentActionRequest
from common.agent_state import AgentState
from common.game_state import GameState
from common.position import Position
from common.protos.actions import (
    build_farm_action_pb2,
    build_house_action_pb2,
    build_quarry_action_pb2,
    drop_action_pb2,
    farm_action_pb2,
    mine_action_pb2,
    move_action_pb2,
    pick_up_action_pb2,
)
from common.tile import Tile


class TestProtoConversions(unittest.TestCase):
    def test_position_to_proto(self):
        pos = Position(x=1.0, y=2.0)
        proto = pos.to_proto()
        self.assertEqual(proto.x, 1.0)
        self.assertEqual(proto.y, 2.0)

    def test_position_from_proto(self):
        proto = position_pb2.Position(x=1.0, y=2.0)
        pos = Position.from_proto(proto)
        self.assertEqual(pos.x, 1.0)
        self.assertEqual(pos.y, 2.0)

    def test_tile_to_proto(self):
        tile = Tile(x=1, y=2)
        proto = tile.to_proto()
        self.assertEqual(proto.x, 1)
        self.assertEqual(proto.y, 2)

    def test_tile_from_proto(self):
        proto = tile_pb2.Tile(x=1, y=2)
        tile = Tile.from_proto(proto)
        self.assertEqual(tile.x, 1)
        self.assertEqual(tile.y, 2)

    def test_agent_state_to_proto(self):
        agent_state = AgentState(id=1, position=np.array([1.0, 2.0], dtype=np.float64), busy=False)
        proto = agent_state.to_proto()
        self.assertEqual(proto.id, 1)
        self.assertEqual(proto.position.x, 1.0)
        self.assertEqual(proto.position.y, 2.0)
        self.assertEqual(proto.busy, False)

    def test_agent_state_from_proto(self):
        proto = agent_state_pb2.AgentState(id=1, position=position_pb2.Position(x=1.0, y=2.0), busy=False)
        agent_state = AgentState.from_proto(proto)
        self.assertEqual(agent_state.id, 1)
        self.assertTrue(np.array_equal(agent_state.position, np.array([1.0, 2.0], dtype=np.float64)))
        self.assertEqual(agent_state.busy, False)

    def test_game_state_to_proto(self):
        game_state = GameState(
            agent_states = [
                AgentState(id=1, position=np.array([1.0, 2.0], dtype=np.float64), busy=False),
                AgentState(id=2, position=np.array([3.0, 4.0], dtype=np.float64), busy=False)
            ],
            tile_states = np.array([[0, 1], [2, 3]], dtype=np.uint8),
            width = 2,
            height = 2,
            points = 10,
        )
        proto = game_state.to_proto()
        self.assertEqual(proto.points, 10)
        self.assertEqual(proto.width, 2)
        self.assertEqual(proto.height, 2)
        self.assertEqual(len(proto.agent_states), 2)
        self.assertEqual(proto.agent_states[0].id, 1)
        self.assertEqual(proto.agent_states[0].position.x, 1.0)
        self.assertEqual(proto.agent_states[0].position.y, 2.0)
        self.assertEqual(proto.agent_states[1].id, 2)
        self.assertEqual(proto.agent_states[1].position.x, 3.0)
        self.assertEqual(proto.agent_states[1].position.y, 4.0)
        self.assertEqual(list(proto.tiles), [0, 1, 2, 3])

    def test_proto_to_game_state(self):
        proto = game_state_pb2.GameState()
        proto.points = 10
        proto.width = 2
        proto.height = 2
        proto.agent_states.add(id=1, position=position_pb2.Position(x=1.0, y=2.0), busy=False)
        proto.agent_states.add(id=2, position=position_pb2.Position(x=3.0, y=4.0), busy=False)
        proto.tiles.extend([tile_pb2.TileState.EMPTY, tile_pb2.TileState.CASTLE, tile_pb2.TileState.FARM, tile_pb2.TileState.QUARRY])
        game_state = GameState.from_proto(proto)
        self.assertEqual(game_state.points, 10)
        self.assertEqual(game_state.width, 2)
        self.assertEqual(game_state.height, 2)
        self.assertEqual(len(game_state.agent_states), 2)
        self.assertTrue(np.array_equal(game_state.agent_states[0].position, np.array([1.0, 2.0], dtype=np.float64)))
        self.assertTrue(np.array_equal(game_state.agent_states[1].position, np.array([3.0, 4.0] , dtype=np.float64)))
        self.assertTrue(np.array_equal(game_state.tile_states, np.array([[0, 1], [2, 3]], dtype=np.uint8)))

    def test_build_farm_action_to_proto(self):
        tile = Tile(x=1, y=2)
        build_farm_action = BuildFarmAction(tile=tile)
        proto = build_farm_action.to_proto()
        self.assertEqual(proto.build_farm_tile.x, 1)
        self.assertEqual(proto.build_farm_tile.y, 2)

    def test_proto_to_build_farm_action(self):
        proto = build_farm_action_pb2.BuildFarmAction()
        proto.build_farm_tile.x = 1
        proto.build_farm_tile.y = 2
        build_farm_action = BuildFarmAction.from_proto(proto)
        self.assertEqual(build_farm_action.tile.x, 1)
        self.assertEqual(build_farm_action.tile.y, 2)

    def test_build_house_action_to_proto(self):
        tile = Tile(x=1, y=2)
        build_house_action = BuildHouseAction(tile=tile)
        proto = build_house_action.to_proto()
        self.assertEqual(proto.build_house_tile.x, 1)
        self.assertEqual(proto.build_house_tile.y, 2)

    def test_proto_to_build_house_action(self):
        proto = build_house_action_pb2.BuildHouseAction()
        proto.build_house_tile.x = 1
        proto.build_house_tile.y = 2
        build_house_action = BuildHouseAction.from_proto(proto)
        self.assertEqual(build_house_action.tile.x, 1)
        self.assertEqual(build_house_action.tile.y, 2)

    def test_build_quarry_action_to_proto(self):
        tile = Tile(x=1, y=2)
        build_quarry_action = BuildQuarryAction(tile=tile)
        proto = build_quarry_action.to_proto()
        self.assertEqual(proto.build_quarry_tile.x, 1)
        self.assertEqual(proto.build_quarry_tile.y, 2)

    def test_proto_to_build_quarry_action(self):
        proto = build_quarry_action_pb2.BuildQuarryAction()
        proto.build_quarry_tile.x = 1
        proto.build_quarry_tile.y = 2
        build_quarry_action = BuildQuarryAction.from_proto(proto)
        self.assertEqual(build_quarry_action.tile.x, 1)
        self.assertEqual(build_quarry_action.tile.y, 2)

    def test_drop_action_to_proto(self):
        tile = Tile(x=1, y=2)
        drop_action = DropAction(tile=tile)
        proto = drop_action.to_proto()
        self.assertEqual(proto.drop_tile.x, 1)
        self.assertEqual(proto.drop_tile.y, 2)

    def test_proto_to_drop_action(self):
        proto = drop_action_pb2.DropAction()
        proto.drop_tile.x = 1
        proto.drop_tile.y = 2
        drop_action = DropAction.from_proto(proto)
        self.assertEqual(drop_action.tile.x, 1)
        self.assertEqual(drop_action.tile.y, 2)

    def test_farm_action_to_proto(self):
        tile = Tile(x=1, y=2)
        farm_action = FarmAction(tile=tile)
        proto = farm_action.to_proto()
        self.assertEqual(proto.farm_tile.x, 1)
        self.assertEqual(proto.farm_tile.y, 2)

    def test_proto_to_farm_action(self):
        proto = farm_action_pb2.FarmAction()
        proto.farm_tile.x = 1
        proto.farm_tile.y = 2
        farm_action = FarmAction.from_proto(proto)
        self.assertEqual(farm_action.tile.x, 1)
        self.assertEqual(farm_action.tile.y, 2)

    def test_mine_action_to_proto(self):
        tile = Tile(x=1, y=2)
        mine_action = MineAction(tile=tile)
        proto = mine_action.to_proto()
        self.assertEqual(proto.mine_tile.x, 1)
        self.assertEqual(proto.mine_tile.y, 2)

    def test_proto_to_mine_action(self):
        proto = mine_action_pb2.MineAction()
        proto.mine_tile.x = 1
        proto.mine_tile.y = 2
        mine_action = MineAction.from_proto(proto)
        self.assertEqual(mine_action.tile.x, 1)
        self.assertEqual(mine_action.tile.y, 2)

    def test_pick_up_action_to_proto(self):
        tile = Tile(x=1, y=2)
        pick_up_action = PickUpAction(tile=tile)
        proto = pick_up_action.to_proto()
        self.assertEqual(proto.pick_up_tile.x, 1)
        self.assertEqual(proto.pick_up_tile.y, 2)

    def test_proto_to_pick_up_action(self):
        proto = pick_up_action_pb2.PickUpAction()
        proto.pick_up_tile.x = 1
        proto.pick_up_tile.y = 2
        pick_up_action = PickUpAction.from_proto(proto)
        self.assertEqual(pick_up_action.tile.x, 1)
        self.assertEqual(pick_up_action.tile.y, 2)

    def test_move_action_to_proto(self):
        move_action = MoveAction(position=np.array([1.0, 2.0]))
        proto = move_action.to_proto()
        self.assertEqual(proto.goal_position.x, 1)
        self.assertEqual(proto.goal_position.y, 2)

    def test_proto_to_move_action(self):
        proto = move_action_pb2.MoveAction()
        proto.goal_position.x = 1
        proto.goal_position.y = 2
        move_action = MoveAction.from_proto(proto)
        self.assertEqual(move_action.position[0], 1)
        self.assertEqual(move_action.position[1], 2)

    def test_agent_action_to_proto(self):
        tile = Tile(x=1, y=2)
        agent_action = AgentAction(agent_id=1, action=BuildFarmAction(tile=tile))
        proto = agent_action.to_proto()
        self.assertEqual(proto.agent_id, 1)
        self.assertEqual(proto.build_farm_action.build_farm_tile.x, 1)
        self.assertEqual(proto.build_farm_action.build_farm_tile.y, 2)

    def test_agent_action_to_proto_unknown_action(self):
        agent_action = AgentAction(agent_id=1, action=None)
        with self.assertRaises(TypeError):
            agent_action.to_proto()

    def test_proto_to_agent_action(self):
        proto = agent_action_pb2.AgentAction()
        proto.agent_id = 1
        proto.build_farm_action.build_farm_tile.x = 1
        proto.build_farm_action.build_farm_tile.y = 2
        agent_action = AgentAction.from_proto(proto)
        self.assertEqual(agent_action.agent_id, 1)
        self.assertEqual(agent_action.action.tile.x, 1)
        self.assertEqual(agent_action.action.tile.y, 2)

    def test_agent_action_request_to_proto(self):
        agent_action_request = AgentActionRequest([
            AgentAction(agent_id=1, action=BuildFarmAction(tile=Tile(x=1, y=2))),
            AgentAction(agent_id=1, action=BuildHouseAction(tile=Tile(x=1, y=2))),
            AgentAction(agent_id=1, action=BuildQuarryAction(tile=Tile(x=1, y=2)))
        ])
        proto = agent_action_request.to_proto()
        self.assertEqual(len(proto.actions), 3)
        self.assertEqual(proto.actions[0].build_farm_action.build_farm_tile.x, 1)
        self.assertEqual(proto.actions[0].build_farm_action.build_farm_tile.y, 2)
        self.assertEqual(proto.actions[1].build_house_action.build_house_tile.x, 1)
        self.assertEqual(proto.actions[1].build_house_action.build_house_tile.y, 2)
        self.assertEqual(proto.actions[2].build_quarry_action.build_quarry_tile.x, 1)
        self.assertEqual(proto.actions[2].build_quarry_action.build_quarry_tile.y, 2)

    def test_proto_to_agent_action_request(self):
        proto = agent_action_pb2.AgentActionRequest()
        proto.actions.add().agent_id = 1
        proto.actions[0].build_farm_action.build_farm_tile.x = 1
        proto.actions[0].build_farm_action.build_farm_tile.y = 2
        proto.actions.add().agent_id = 1
        proto.actions[1].build_house_action.build_house_tile.x = 1
        proto.actions[1].build_house_action.build_house_tile.y = 2
        proto.actions.add().agent_id = 1
        proto.actions[2].build_quarry_action.build_quarry_tile.x = 1
        proto.actions[2].build_quarry_action.build_quarry_tile.y = 2
        agent_action_request = AgentActionRequest.from_proto(proto)
        self.assertEqual(len(agent_action_request.agent_actions), 3)
        self.assertEqual(agent_action_request.agent_actions[0].action.tile.x, 1)
        self.assertEqual(agent_action_request.agent_actions[0].action.tile.y, 2)
        self.assertEqual(agent_action_request.agent_actions[1].action.tile.x, 1)
        self.assertEqual(agent_action_request.agent_actions[1].action.tile.y, 2)
        self.assertEqual(agent_action_request.agent_actions[2].action.tile.x, 1)
        self.assertEqual(agent_action_request.agent_actions[2].action.tile.y, 2)

if __name__ == "__main__":
    unittest.main()
