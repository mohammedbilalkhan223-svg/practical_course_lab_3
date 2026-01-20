from dataclasses import dataclass
from mango import Agent, sender_addr
from src.sim_environment.messages import (
    TargetUpdateMsg,
    SetDoneMsg,
    SetScheduleMsg,
    SetScheduleReplyMsg,
    NotifyReadyRequestMsg,
    NotifyReadyMsg,
    StateRequestMsg,
    StateReplyMsg,
    FailControllerMsg,
    HeartbeatPingMsg,
    HeartbeatPongMsg,
    AgentDownMsg,
)
import asyncio
import logging
import random
from copy import deepcopy
import time

import sys
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
else:
    from src.sim_environment.devices.hil import *

import pyomo.environ as pyo

# renegotiation for single time step on target update
@dataclass
class FlexMsg:
    aid: str
    version: int
    schedule: list[float]


class DecentralAgent(Agent):
    def __init__(
        self, obs_addr, device_addr, device_state, device_c_op, target, c_dev, n_agents, step_time_s, seed=None
    ):
        super().__init__()
        self.rng = random.Random(seed)

        self.obs_addr = obs_addr
        self.device_addr = device_addr
        self.device_state = device_state
        self.target = deepcopy(target)
        self.device_schedule = [0] * len(target)
        self.c_dev = c_dev
        self.device_c_op = device_c_op
        self.n_agents = n_agents
        self.old_t = 0
        self.t = 0
        self.version = 0

        self.step_time_s = step_time_s
        self.addr_to_node_id = {}  # set outside after registering

        self.working_memory = {}
        self.current_loop_memory = {}

        self.init_schedule_done = asyncio.Future()
        self.done = asyncio.Future()
        self.state_request_fut = asyncio.Future()
        self.target_update_task = None
        self.failed = False

        # -------------------------------
        # Task 10: heartbeat + liveness
        # -------------------------------
        self.HEARTBEAT_PERIOD_S = max(0.2, 0.5 * self.step_time_s)
        self.HEARTBEAT_TIMEOUT_S = max(0.6, 2.0 * self.step_time_s)

        self.hb_seq = 0
        self.last_seen_by_aid: dict[str, float] = {}
        self.dead_aids: set[str] = set()

        self._hb_started = False
        self._hb_periodic_handle = None  # <-- important for clean shutdown

    def on_register(self):
        self.schedule_instant_task(self.create_initial_schedule())
        self.schedule_instant_task(self._start_heartbeat_when_ready())

    async def _start_heartbeat_when_ready(self):
        if self._hb_started:
            return
        await asyncio.sleep(0.5)
        for n in self.neighbors():
            self.last_seen_by_aid[n.aid] = time.monotonic()

        self._hb_started = True

        # IMPORTANT: pass the *function*, not a coroutine object
        self._hb_periodic_handle = self.schedule_periodic_task(
            coroutine_func=self.heartbeat_loop,
            delay=self.HEARTBEAT_PERIOD_S,
        )

    # -------------------------------
    # Topology loss/delay
    # -------------------------------
    def get_edge_loss_rate(self, sender):
        g = self.context._container.graph
        x = self.addr_to_node_id[self.addr]
        y = self.addr_to_node_id[sender]
        u = x if x < y else y
        v = x if x > y else y
        w = g.edges[u, v]["loss_rate"]
        return 0.0 if w is None or w < 0 else w

    def get_edge_delay(self, sender):
        g = self.context._container.graph
        x = self.addr_to_node_id[self.addr]
        y = self.addr_to_node_id[sender]
        u = x if x < y else y
        v = x if x > y else y
        d = g.edges[u, v]["delay"]
        return 0.0 if d is None or d < 0 else d

    # -------------------------------
    # Task 10: heartbeat loop
    # -------------------------------
    async def heartbeat_loop(self):
        if self.failed or self.done.done():
            return

        now = time.monotonic()
        self.hb_seq += 1

        # ping neighbors
        for n in self.neighbors():
            if n.aid in self.dead_aids:
                continue
            msg = HeartbeatPingMsg(sender_aid=self.aid, seq=self.hb_seq, ts=now)
            await self.send_message(msg, n)

        # check timeouts
        for n in self.neighbors():
            if n.aid in self.dead_aids:
                continue
            last = self.last_seen_by_aid.get(n.aid, None)
            if last is None:
                self.last_seen_by_aid[n.aid] = now
                continue
            if (now - last) > self.HEARTBEAT_TIMEOUT_S:
                await self._mark_agent_down(down_aid=n.aid, reported_by=self.aid, ts=now)

    async def _mark_agent_down(self, down_aid: str, reported_by: str, ts: float):
        if down_aid in self.dead_aids:
            return
        self.dead_aids.add(down_aid)

        # remove from memory so its schedule is ignored
        if down_aid in self.working_memory:
            del self.working_memory[down_aid]
        if down_aid in self.current_loop_memory:
            del self.current_loop_memory[down_aid]

        logging.warning(f"[Task10] {self.aid} detected {down_aid} as DOWN. Gossiping...")

        gossip = AgentDownMsg(down_aid=down_aid, reported_by=reported_by, ts=ts)
        await self.send_to_neighbors(gossip)

    # -------------------------------
    # Messaging
    # -------------------------------
    def handle_message(self, content, meta):
        sender = sender_addr(meta)

        is_neighbor = sender in self.neighbors()
        is_observer = sender == self.obs_addr
        is_device = sender == self.device_addr

        if not (is_neighbor or is_observer or is_device):
            logging.warning(f"Agent {self.aid} received message from invalid sender: {sender}")
            return

        if is_neighbor:
            self.last_seen_by_aid[sender.aid] = time.monotonic()

        # observer control
        if isinstance(content, FailControllerMsg) and is_observer:
            self.failed = True
            return

        if isinstance(content, SetDoneMsg) and is_observer:
            if not self.done.done():
                self.done.set_result(True)
            return

        if self.failed:
            return

        # heartbeat fast-path
        if isinstance(content, HeartbeatPingMsg) and is_neighbor:
            pong = HeartbeatPongMsg(sender_aid=self.aid, seq=content.seq, ts=time.monotonic())
            self.schedule_instant_message(pong, sender)
            return

        if isinstance(content, HeartbeatPongMsg) and is_neighbor:
            self.last_seen_by_aid[sender.aid] = time.monotonic()
            return

        if isinstance(content, AgentDownMsg) and is_neighbor:
            if content.down_aid not in self.dead_aids and content.down_aid != self.aid:
                self.schedule_instant_task(self._mark_agent_down(content.down_aid, content.reported_by, content.ts))
            return

        # existing logic
        if isinstance(content, TargetUpdateMsg) and is_observer:
            if self.target_update_task is not None and not self.target_update_task.done():
                self.target_update_task.cancel()
            self.target_update_task = self.schedule_instant_task(self.handle_target_update(content))

        if isinstance(content, NotifyReadyRequestMsg) and is_observer:
            self.schedule_instant_task(self.handle_ready_request(sender))

        if isinstance(content, StateReplyMsg) and is_device:
            self.schedule_instant_task(self.handle_state_reply(content))

        self.schedule_instant_task(self.handle_any_message(content, meta))

    async def handle_any_message(self, content, meta):
        sender = sender_addr(meta)
        is_neighbor = sender in self.neighbors()
        is_device = sender == self.device_addr

        if is_neighbor:
            if sender.aid in self.dead_aids:
                return

            # simulate link loss/delay for negotiation traffic
            w = self.get_edge_loss_rate(sender)
            if self.rng.random() <= w:
                return

            d = self.get_edge_delay(sender)
            if d > 0:
                await asyncio.sleep(d)

        if isinstance(content, SetScheduleReplyMsg):
            return

        if isinstance(content, FlexMsg):
            if content.aid in self.dead_aids:
                return
            if content.aid == self.aid:
                return
            if (content.aid in self.working_memory) and (self.working_memory[content.aid][0] >= content.version):
                return

            self.working_memory[content.aid] = (content.version, content.schedule)
            await self.send_to_neighbors(content)

    async def handle_ready_request(self, sender):
        await self.init_schedule_done
        await self.send_message(NotifyReadyMsg(), sender)

    async def handle_target_update(self, content):
        print(self.aid, "handle_target_update")
        await self.get_device_state_update()
        print(self.aid, "got device state update ")
        self.target[content.t] = content.value
        self.t = content.t
        print(self.aid, "await reschedule ")
        await self.reschedule()

    async def send_to_neighbors(self, msg):
        for n in self.neighbors():
            if n.aid in self.dead_aids:
                continue
            await self.send_message(msg, n)

    def update_my_device_schedule(self):
        self.schedule_instant_message(SetScheduleMsg(self.device_schedule), self.device_addr)

    async def handle_state_reply(self, content):
        self.device_state = content.state
        if not self.state_request_fut.done():
            self.state_request_fut.set_result(True)

    async def optimization_loop(self):
        print(self.aid, "optimization loop")
        self.publish()
        while not self.done.done():
            await self.perceive()
            self.update()
            self.publish()
            await asyncio.sleep(0.01)
        print(self.aid, "optimization done")

    def publish(self):
        self.version += 1
        msg = FlexMsg(self.aid, self.version, self.device_schedule)
        self.schedule_instant_task(self.send_to_neighbors(msg))

    # -------------------------------
    # Pyomo model
    # -------------------------------
    def add_fc_constraints(self, model, remaining_target):
        p_var = model.p_device
        n_steps = len(remaining_target)
        fuel_state = self.device_state

        model.fuel_var = pyo.Var(
            range(n_steps),
            domain=pyo.NonNegativeReals,
            bounds=(0, fuel_state.fuel_amount),
        )

        for t in range(n_steps - 1):
            model.problem_constraints.add(expr=model.fuel_var[t + 1] == model.fuel_var[t] - p_var[t])

        for t in range(n_steps):
            model.problem_constraints.add(expr=model.fuel_var[t] >= p_var[t])

        return model

    def add_load_constraints(self, model, remaining_target):
        return model

    def add_bat_constraints(self, model, remaining_target):
        p_var = model.p_device
        n_steps = len(remaining_target)
        bat_state = self.device_state

        model.bat_var = pyo.Var(range(n_steps), domain=pyo.NonNegativeReals, bounds=(0, bat_state.size))
        for t in range(n_steps - 1):
            model.problem_constraints.add(expr=model.bat_var[t + 1] == model.bat_var[t] - p_var[t])

        model.problem_constraints.add(expr=model.bat_var[0] == bat_state.soc * bat_state.size)
        model.problem_constraints.add(expr=model.bat_var[n_steps - 1] == bat_state.final_soc * bat_state.size)

        return model

    def add_problem_constraints(self, model, remaining_target):
        p_min = self.device_state.p_min
        p_max = self.device_state.p_max
        n_steps = len(remaining_target)

        model.problem_constraints = pyo.ConstraintList()
        model.p_device = pyo.Var(range(n_steps), domain=pyo.Reals, bounds=(p_min, p_max))

        model.problem_cost = pyo.Var(range(n_steps), domain=pyo.NonNegativeReals, initialize=0)
        model.device_cost = pyo.Var(range(n_steps), domain=pyo.NonNegativeReals, initialize=0)
        model.p_abs_diff = pyo.Var(range(n_steps), domain=pyo.NonNegativeReals, initialize=0)

        for t in range(n_steps):
            model.problem_constraints.add(expr=model.p_abs_diff[t] >= (model.p_device[t] - remaining_target[t]))
            model.problem_constraints.add(expr=model.p_abs_diff[t] >= -(model.p_device[t] - remaining_target[t]))
            model.problem_constraints.add(expr=model.problem_cost[t] == model.p_abs_diff[t] * self.c_dev)
            model.problem_constraints.add(expr=model.device_cost[t] == model.p_abs_diff[t] * self.device_c_op)

        obj_f = sum(model.problem_cost[t] + model.device_cost[t] for t in range(n_steps - 1))
        model.goal = pyo.Objective(expr=obj_f, sense=pyo.minimize)
        return model

    def get_pyomo_model(self, remaining_target):
        model = pyo.ConcreteModel()
        model = self.add_problem_constraints(model, remaining_target)

        if isinstance(self.device_state, IdealBatteryState):
            model = self.add_bat_constraints(model, remaining_target)
        if isinstance(self.device_state, IdealLoadState):
            model = self.add_load_constraints(model, remaining_target)
        if isinstance(self.device_state, IdealFuelCellState):
            model = self.add_fc_constraints(model, remaining_target)

        return model

    def update(self):
        target = self.target
        other_contributions = [0] * len(target)

        for aid, (ver, sched) in self.current_loop_memory.items():
            if aid in self.dead_aids:
                continue
            for i in range(len(target)):
                other_contributions[i] += sched[i]

        remaining_target = [x - y for x, y in zip(self.target, other_contributions)][self.t:]
        remaining_target.append(0)

        model = self.get_pyomo_model(remaining_target)
        pyo.SolverFactory("appsi_highs").solve(model)

        data = list(model.p_device.extract_values().values())[:-1]
        self.device_schedule[self.t:] = data
        self.update_my_device_schedule()

    async def perceive(self):
        while True:
            if self.current_loop_memory != self.working_memory:
                break
            if self.t > self.old_t:
                self.old_t = self.t
                break
            await asyncio.sleep(0.1)
        self.current_loop_memory = self.working_memory

    async def get_device_state_update(self):
        self.state_request_fut = asyncio.Future()
        await self.send_message(StateRequestMsg(), self.device_addr)
        await self.state_request_fut

    async def create_initial_schedule(self):
        self.schedule_instant_task(self.optimization_loop())
        await asyncio.sleep(5)
        self.init_schedule_done.set_result(True)

    async def reschedule(self):
         self.schedule_instant_task(self.optimization_loop())
         #print(self.aid, "waiting for 5 sec")
         #await asyncio.sleep(3)
         print(self.aid, "rescheduling done")