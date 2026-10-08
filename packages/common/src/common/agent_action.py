"""
Representation of an action taken by an agent (decoded
from a protobuf into a algebraic type for ease of use)
"""

from dataclasses import dataclass

import common.protos.agent_action_pb2 as agent_action_pb2
from common.actions.build_farm_action import BuildFarmAction
from common.actions.build_house_action import BuildHouseAction
from common.actions.build_quarry_action import BuildQuarryAction
from common.actions.drop_action import DropAction
from common.actions.farm_action import FarmAction
from common.actions.mine_action import MineAction
from common.actions.move_action import MoveAction
from common.actions.pick_up_action import PickUpAction
from common.convertible import Convertible


@dataclass
class AgentAction(Convertible):
    agent_id: int
    action: BuildFarmAction | \
    BuildHouseAction | \
    BuildQuarryAction | \
    DropAction | \
    FarmAction | \
    MineAction | \
    MoveAction | \
    PickUpAction

    def to_proto(self) -> agent_action_pb2.AgentAction:
        if not isinstance(self.action, Convertible):
            raise TypeError("Invalid proto type")
        action_proto = self.action.to_proto()
        match self.action:
            case BuildFarmAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    build_farm_action=action_proto
                )
            case BuildHouseAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    build_house_action=action_proto
                )
            case BuildQuarryAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    build_quarry_action=action_proto
                )
            case DropAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    drop_action=action_proto
                )
            case FarmAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    farm_action=action_proto
                )
            case MineAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    mine_action=action_proto
                )
            case MoveAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    move_action=action_proto
                )
            case PickUpAction(_):
                return agent_action_pb2.AgentAction(
                    agent_id=self.agent_id,
                    pick_up_action=action_proto
                )
            case _:
                raise ValueError("Unknown Action")

    @classmethod
    def from_proto(cls, proto: agent_action_pb2.AgentAction) -> "AgentAction":
        match proto.WhichOneof("action"):
            case "build_farm_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=BuildFarmAction.from_proto(proto.build_farm_action)
                )
            case "build_house_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=BuildHouseAction.from_proto(proto.build_house_action)
                )
            case "build_quarry_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=BuildQuarryAction.from_proto(proto.build_quarry_action)
                )
            case "drop_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=DropAction.from_proto(proto.drop_action)
                )
            case "farm_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=FarmAction.from_proto(proto.farm_action)
                )
            case "mine_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=MineAction.from_proto(proto.mine_action)
                )
            case "move_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=MoveAction.from_proto(proto.move_action)
                )
            case "pick_up_action":
                return cls(
                    agent_id=proto.agent_id,
                    action=PickUpAction.from_proto(proto.pick_up_action)
                )
            case _:
                raise ValueError("Unknown Action")

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentAction":
        proto = agent_action_pb2.AgentAction()
        proto.ParseFromString(data)
        return cls.from_proto(proto)


class AgentActionRequest(Convertible):
    def __init__(self, agent_actions: list[AgentAction]):
        self.agent_actions = agent_actions

    def to_proto(self) -> agent_action_pb2.AgentActionRequest:
        proto = agent_action_pb2.AgentActionRequest()
        for agent_action in self.agent_actions:
            proto.actions.append(agent_action.to_proto())
        return proto

    @classmethod
    def from_proto(cls, proto: agent_action_pb2.AgentActionRequest) -> "AgentActionRequest":
        return cls(
            agent_actions=[AgentAction.from_proto(action) for action in proto.actions]
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "AgentActionRequest":
        proto = agent_action_pb2.AgentActionRequest()
        proto.ParseFromString(data)
        return cls.from_proto(proto)
