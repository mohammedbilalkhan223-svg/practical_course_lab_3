from dataclasses import dataclass
from mango.messages.codecs import json_serializable, JSON
from src.sim_environment.devices.abstract import AbstractState

import sys
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
else:
    from src.sim_environment.devices.hil import *

SCENARIO_CODEC = JSON()

# ------------------------------
# State serializers
# ------------------------------
SCENARIO_CODEC.add_serializer(*IdealBatteryState.__serializer__())
SCENARIO_CODEC.add_serializer(*IdealLoadState.__serializer__())
SCENARIO_CODEC.add_serializer(*IdealFuelCellState.__serializer__())

# ------------------------------
# Both
# ------------------------------
@json_serializable
@dataclass
class SetDoneMsg:
    pass

SCENARIO_CODEC.add_serializer(*SetDoneMsg.__serializer__())

# ------------------------------
# Device-side (Observer acting as “device gateway”)
# ------------------------------
@json_serializable
@dataclass
class StateRequestMsg:
    pass

SCENARIO_CODEC.add_serializer(*StateRequestMsg.__serializer__())


@json_serializable
@dataclass
class StateReplyMsg:
    state: AbstractState

SCENARIO_CODEC.add_serializer(*StateReplyMsg.__serializer__())


@json_serializable
@dataclass
class SetScheduleMsg:
    setpoints: list[float]

SCENARIO_CODEC.add_serializer(*SetScheduleMsg.__serializer__())


@json_serializable
@dataclass
class SetScheduleReplyMsg:
    ok: bool

SCENARIO_CODEC.add_serializer(*SetScheduleReplyMsg.__serializer__())


@json_serializable
@dataclass
class StepMsg:
    t: int

SCENARIO_CODEC.add_serializer(*StepMsg.__serializer__())


@json_serializable
@dataclass
class StepReplyMsg:
    t: int

SCENARIO_CODEC.add_serializer(*StepReplyMsg.__serializer__())


@json_serializable
@dataclass
class ResultLogRequestMsg:
    pass

SCENARIO_CODEC.add_serializer(*ResultLogRequestMsg.__serializer__())


@json_serializable
@dataclass
class ResultLogMsg:
    cumulative_cost: float
    power_setpoints: list[float]

SCENARIO_CODEC.add_serializer(*ResultLogMsg.__serializer__())

# ------------------------------
# Control-side
# ------------------------------
@json_serializable
@dataclass
class TargetUpdateMsg:
    t: int
    value: float

SCENARIO_CODEC.add_serializer(*TargetUpdateMsg.__serializer__())


@json_serializable
@dataclass
class NotifyReadyRequestMsg:
    pass

SCENARIO_CODEC.add_serializer(*NotifyReadyRequestMsg.__serializer__())


@json_serializable
@dataclass
class NotifyReadyMsg:
    pass

SCENARIO_CODEC.add_serializer(*NotifyReadyMsg.__serializer__())


@json_serializable
@dataclass
class FailControllerMsg:
    """Observer-triggered failure (used by scenario c_fail_time)."""
    pass

SCENARIO_CODEC.add_serializer(*FailControllerMsg.__serializer__())

# ============================================================
# Task 10 — Failure detection messages (NEW)
# ============================================================
@json_serializable
@dataclass
class HeartbeatPingMsg:
    sender_aid: str
    seq: int
    ts: float  # monotonic timestamp (seconds)

SCENARIO_CODEC.add_serializer(*HeartbeatPingMsg.__serializer__())


@json_serializable
@dataclass
class HeartbeatPongMsg:
    sender_aid: str
    seq: int
    ts: float  # monotonic timestamp (seconds)

SCENARIO_CODEC.add_serializer(*HeartbeatPongMsg.__serializer__())


@json_serializable
@dataclass
class AgentDownMsg:
    """Gossip message: a controller agent is considered dead/out-of-negotiation."""
    down_aid: str
    reported_by: str
    ts: float  # monotonic timestamp (seconds)

SCENARIO_CODEC.add_serializer(*AgentDownMsg.__serializer__())

