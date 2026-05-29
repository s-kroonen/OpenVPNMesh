from enum import Enum


class NodeState(str, Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    ISOLATED = "isolated"


_current_state: NodeState = NodeState.FOLLOWER


def get_state() -> NodeState:
    return _current_state


def set_state(state: NodeState):
    global _current_state
    _current_state = state
