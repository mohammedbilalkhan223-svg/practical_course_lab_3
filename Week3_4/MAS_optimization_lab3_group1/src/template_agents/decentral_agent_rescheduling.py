from dataclasses import dataclass
from mango import Agent, sender_addr
from src.sim_environment.messages import *
import asyncio
import logging
import random
from copy import deepcopy
from src.sim_environment.optimization_problem import SchedulingProblem
from src.sim_environment.devices.abstract import AbstractDevice
import sys
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
else:
    from src.sim_environment.devices.hil import *
import pyomo.environ as pyo

"""
New decentral agent with some hacky things to make topology edge weight tracking work:
- assumes all decentral agents run in the same container
- stores topology.graph object in the container
- adds weights to the edges as packet drop rates for the agents
- agents keep track of their own ID in that networkx graph via the node_id field
- edge weight can then be gotten for an arbitrary sender via the get_edge_weight function
"""

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

        self.obs_addr = obs_addr # for message legitimacy checking only, don't send messages here
        self.device_addr = device_addr
        self.device_state = device_state
        self.target = deepcopy(target)
        self.device_schedule = [0] * len(target)
        self.c_dev = c_dev
        self.device_c_op = device_c_op
        self.n_agents = n_agents  # total number of agents
        self.old_t = 0
        self.t = 0
        self.version = 0
        self.original_target = deepcopy(target)

        self.step_time_s = step_time_s

        self.addr_to_node_id = {} # gets set outside after registering

        # NOTE:
        # neighbors can now be accessed by
        # self.neighbors() -> using mangos topology feature

        self.working_memory = {}
        self.current_loop_memory = {}

        # various futures objects for control flow
        self.init_schedule_done = asyncio.Future()
        self.done = asyncio.Future()
        self.state_request_fut = asyncio.Future()
        self.info_collection_fut = None
        self.target_update_task = None
        self.failed = False
        self._opt_task = None

    def _start_optimization_loop(self):
        # start only if not already running
        if self._opt_task is not None and not self._opt_task.done():
            return
        self._opt_task = self.schedule_instant_task(self.optimization_loop())

    def _stop_optimization_loop(self):
        if self._opt_task is None:
            return
        try:
            if not self._opt_task.done():
                self._opt_task.cancel()
        except Exception:
            pass
    def on_register(self):
        self.schedule_instant_task(self.create_initial_schedule())

    def get_edge_loss_rate(self, sender):
        # hacky way of storing this in the container
        g = self.context._container.graph

        # get node id for sender and receiver
        x = self.addr_to_node_id[self.addr]
        y = self.addr_to_node_id[sender]

        # order values because of how networkx creates nodes
        u = x if x < y else y
        v = x if x > y else y

        return g.edges[u,v]["loss_rate"]

    def get_edge_delay(self, sender):
        # hacky way of storing this in the container
        g = self.context._container.graph

        # get node id for sender and receiver
        x = self.addr_to_node_id[self.addr]
        y = self.addr_to_node_id[sender]

        # order values because of how networkx creates nodes
        u = x if x < y else y
        v = x if x > y else y

        return g.edges[u,v]["delay"]

    def handle_message(self, content, meta):
        sender = sender_addr(meta)

        is_neighbor = sender in self.neighbors()
        is_observer = sender == self.obs_addr
        is_device = sender == self.device_addr

        if not (is_neighbor or is_observer or is_device):
            # reject because its not a neighbor, observer, or our device
            logging.warning(f"Agent {self.aid} receveived message from invalid sender address: {sender}")
            return

        # -------------------------------------
        # Do not change these messages or the run script will hang.
        # Observer messages are never delayed or dropped.
        # Device messages are delayed or dropped on the device side.
        # -------------------------------------
        if isinstance(content, FailControllerMsg) and is_observer:
            print(self.aid, "controller failed")
            self.failed = True
            # ✅ MINIMAL FIX: stop optimization so shutdown doesn't explode
            self._stop_optimization_loop()
            return

        if isinstance(content, SetDoneMsg) and is_observer:
            if not self.done.done():
                self.done.set_result(True)
            # ✅ MINIMAL FIX: stop optimization so shutdown doesn't explode
            self._stop_optimization_loop()
            return

        if self.failed:
            # controller has exploded
            return

        if isinstance(content, TargetUpdateMsg) and is_observer:
            # only do this if its not already active or
            # we get an asyncio/scheduler error!
            print(self.aid, "received target update")
            if self.target_update_task is not None and not self.target_update_task.done():
                self.target_update_task.cancel()
            self.target_update_task = self.schedule_instant_task(self.handle_target_update(content, meta))


        if isinstance(content, NotifyReadyRequestMsg) and is_observer:
            self.schedule_instant_task(self.handle_ready_request(sender))
        
        if isinstance(content, StateReplyMsg) and is_device:
            self.schedule_instant_task(self.handle_state_reply(content))

        # -------------------------------------
        # Added a generic message handler to schedule here
        # so we can add delays in there.
        # Calling previous scheduling logic now happens in that function.
        # -------------------------------------
        self.schedule_instant_task(self.handle_any_message(content, meta))

    async def handle_any_message(self, content, meta):
        sender = sender_addr(meta)

        is_neighbor = sender in self.neighbors()
        is_observer = sender == self.obs_addr
        is_device = sender == self.device_addr
        # -------------------------------------
        # Handle packet losses and connection drops
        # -------------------------------------
        if is_neighbor:
            w = self.get_edge_loss_rate(sender) # probability between 0 and 1
            if self.rng.random() <= w:
                # packet got lost
                return

            d = self.get_edge_delay(sender)
            await asyncio.sleep(d)


        if isinstance(content, SetScheduleReplyMsg):
            # nothing for now
            pass


        if isinstance(content, FlexMsg):
            if content.aid == self.aid:
                return

            if (
                content.aid in self.working_memory.keys()
                and self.working_memory[content.aid][0] >= content.version
            ):
                return

            # we now know its a new message for our knowledge base
            self.working_memory[content.aid] = (content.version, content.schedule)
            await self.send_to_neighbors(content)


    async def handle_ready_request(self, sender):
        await self.init_schedule_done
        msg = NotifyReadyMsg()
        await self.send_message(msg, sender)

    async def handle_target_update(self, content, meta):
        # NOTE: if your implemented logic does not need an explicit
        # reschedule call, you can comment this out and remove the 
        # reschedule method.
        self.target = self.original_target
        await self.get_device_state_update()
        self.target[content.t] = content.value
        self.t = content.t
        remaining_target = self.target[content.t :]
        self.schedule_instant_task(self.reschedule())
        #self.schedule_instant_task(self.optimization_loop())

    async def send_to_neighbors(self, msg):
        #print(self.aid, "sending to neighbors")
        for n in self.neighbors():
            await self.send_message(msg, n)

    def update_my_device_schedule(self):
        msg = SetScheduleMsg(self.device_schedule)
        self.schedule_instant_message(msg, self.device_addr)

    async def handle_state_reply(self, content):
        self.device_state = content.state
        if not self.state_request_fut.done():
            self.state_request_fut.set_result(True)

    async def optimization_loop(self):
        print(self.aid, "optimization loop started")
        self.publish()
        while not self.done.done():
            await self.perceive()
            # update and publish are notably not
            # interruptible to prevent changes in data
            # during optimization step
            self.update()
            self.publish()
            print(self.aid, "optimization loop finished")
            await asyncio.sleep(0.01)


    def publish(self):
        self.version += 1
        msg = FlexMsg(self.aid, self.version, self.device_schedule)
        self.schedule_instant_task(self.send_to_neighbors(msg))


    def update(self):
        print(self.aid, "update")
        target = self.target
        other_contributions = [0] * len(target)
        for k in self.current_loop_memory.keys():
            for i in range(len(target)):
                other_contributions[i] += self.current_loop_memory[k][1][i]
        remaining_target = [x - y for x, y in zip(self.target, other_contributions)][
            self.t :
        ]
        remaining_target.append(0)

        model = self.get_pyomo_model(remaining_target)
        #pyo.SolverFactory("appsi_highs").solve(model)
        pyo.SolverFactory('gurobi').solve(model)
        data = list(model.p_device.extract_values().values())
        # remove last value as it was only dummy for soc constraint
        data = data[:-1]
        self.device_schedule[self.t:] = data
        self.update_my_device_schedule()

    async def perceive(self):
        # just busy wait for new information while passing control
        while True:
            if self.current_loop_memory != self.working_memory:
                break

            if self.t > self.old_t:
                self.old_t = self.t
                break

            await asyncio.sleep(0.1)

        # snapshot memory for this loop to not have to deal with
        # changes during processing
        self.current_loop_memory = self.working_memory

    # NOTE: new convenience method to get the device state in one function call
    async def get_device_state_update(self):
        self.state_request_fut = asyncio.Future()     
        msg = StateRequestMsg()
        await self.send_message(msg, self.device_addr)
        await self.state_request_fut

    '''
    async def create_initial_schedule(self):
        # schedule our infinitely running optimization loop
        # wait a couple seconds for first schedule
        # then return
        self.schedule_instant_task(self.optimization_loop())
        await asyncio.sleep(5)

        # don't change this flag being set or the run script will hang
        self.init_schedule_done.set_result(True)

    async def reschedule(self):
         # Add your rescheduling logic as necessary
         #await self.get_device_state_update()
         self.schedule_instant_task(self.optimization_loop())
         await asyncio.sleep(5)
         #await asyncio.sleep(5)'''

    async def create_initial_schedule(self):
        # schedule our infinitely running optimization loop
        # wait a couple seconds for first schedule
        # then return
        self._start_optimization_loop()
        await asyncio.sleep(5)
        self.init_schedule_done.set_result(True)

    async def reschedule(self):
        self._stop_optimization_loop()
        await asyncio.sleep(5)  # yield so cancel can propagate
        self._start_optimization_loop()
        print(self.aid, "rescheduling done")

    def add_fc_constraints(self, model, remaining_target):
        p_var = model.p_device
        n_steps = len(remaining_target)
        fuel_state = self.device_state

        model.fuel_var = pyo.Var(
            range(n_steps),
            domain=pyo.NonNegativeReals,
            bounds=(0, fuel_state.fuel_amount),
        )

        # fuel evolution constraint
        for t in range(n_steps - 1):
            model.problem_constraints.add(expr=model.fuel_var[t + 1] == model.fuel_var[t] - p_var[t])

        for t in range(n_steps):
            # no magic with fuel
            model.problem_constraints.add(expr=model.fuel_var[t] >= p_var[t])

        return model

    def add_load_constraints(self, model, remaining_target):
        # nothing to do here
        return model

    def add_bat_constraints(self, model, remaining_target):
        # soc evolution
        p_var = model.p_device
        n_steps = len(remaining_target)
        bat_state = self.device_state

        model.bat_var = pyo.Var(
            range(n_steps),
            domain=pyo.NonNegativeReals,
            bounds=(0, bat_state.size),
            )
        for t in range(n_steps - 1):
            model.problem_constraints.add(
                expr=model.bat_var[t + 1] == model.bat_var[t] - p_var[t])

        model.problem_constraints.add(expr=model.bat_var[0] == bat_state.soc * bat_state.size)
        model.problem_constraints.add(expr=model.bat_var[n_steps-1] == bat_state.final_soc * bat_state.size)

        return model

    def add_problem_constraints(self, model, remaining_target):
        # problem constraints
        p_min = self.device_state.p_min
        p_max = self.device_state.p_max
        n_steps = len(remaining_target)
        model.problem_constraints = pyo.ConstraintList()
        model.p_device = pyo.Var(range(n_steps), domain=pyo.Reals, bounds=(p_min, p_max))

        model.problem_cost = pyo.Var(
            range(n_steps), domain=pyo.NonNegativeReals, initialize=0
        )
        model.device_cost = pyo.Var(
            range(n_steps), domain=pyo.NonNegativeReals, initialize=0
        )

        model.p_abs_diff = pyo.Var(
            range(n_steps), domain=pyo.NonNegativeReals, initialize=0
        )
        for t in range(n_steps):
            # NOTE: this abs construction works only because we are minimizing costs!
            model.problem_constraints.add(
                expr=model.p_abs_diff[t] >= (model.p_device[t] - remaining_target[t])
            )
            model.problem_constraints.add(
                expr=model.p_abs_diff[t] >= -(model.p_device[t] - remaining_target[t])
            )
            model.problem_constraints.add(
                expr=model.problem_cost[t] == model.p_abs_diff[t] * self.c_dev
            )
            model.problem_constraints.add(
                expr=model.device_cost[t] == model.p_abs_diff[t] * self.device_c_op
            )

        obj_f = sum(model.problem_cost[t] + model.device_cost[t] for t in range(n_steps-1))
        model.goal = pyo.Objective(expr=obj_f)

        return model

    def get_pyomo_model(self, remaining_target):
        model = pyo.ConcreteModel()
        model = self.add_problem_constraints(model, remaining_target)

        # device constraints
        if isinstance(self.device_state, IdealBatteryState):
            model = self.add_bat_constraints(model, remaining_target)
        if isinstance(self.device_state, IdealLoadState):
            model = self.add_load_constraints(model, remaining_target)
        if isinstance(self.device_state, IdealFuelCellState):
            model = self.add_fc_constraints(model, remaining_target)

        return model
