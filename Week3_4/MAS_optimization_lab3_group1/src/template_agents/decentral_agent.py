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
    FailControllerMsg
)
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

"""
New decentral agent with some hacky things to make topology edge weight tracking work:
- assumes all decentral agents run in the same container
- stores topology.graph object in the container
- adds weights to the edges as packet drop rates for the agents
- agents keep track of their own ID in that networkx graph via the node_id field
- edge weight can then be gotten for an arbitrary sender via the get_edge_weight function
"""

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
        self.target_update_task = None
        self.failed = False

        # NOTE: controller agents have access to the step time now to consider it
        # in their predictions on how device states will evolve
        self.step_time_s = step_time_s

        self.addr_to_node_id = {} # gets set outside after registering

        # NOTE:
        # neighbors can now be accessed by
        # self.neighbors() -> using mangos topology feature

        # various futures objects for control flow
        self.init_schedule_done = asyncio.Future()
        self.done = asyncio.Future()
        self.state_request_fut = asyncio.Future()
        self.info_collection_fut = None

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
            self.failed = True
            return
        
        if isinstance(content, SetDoneMsg) and is_observer:
            self.done.set_result(True)

        if self.failed:
            # controller has exploded
            return

        if isinstance(content, TargetUpdateMsg) and is_observer:
            # only do this if its not already active or
            # we get an asyncio/scheduler error!
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
            # will become relevant in lab 3
            pass


    async def handle_ready_request(self, sender):
        await self.init_schedule_done
        msg = NotifyReadyMsg()
        await self.send_message(msg, sender)

    async def handle_target_update(self, content, meta):
        # NOTE: if your implemented logic does not need an explicit
        # reschedule call, you can comment this out and remove the 
        # reschedule method.
        await self.get_device_state_update()
        self.target[content.t] = content.value
        self.t = content.t
        remaining_target = self.target[content.t :]
        await self.reschedule(remaining_target, content.t)

    async def send_to_neighbors(self, msg):
        for n in self.neighbors():
            await self.send_message(msg, n)

    def update_my_device_schedule(self):
        msg = SetScheduleMsg(self.device_schedule)
        self.schedule_instant_message(msg, self.device_addr)

    async def handle_state_reply(self, content):
        self.device_state = content.state
        if not self.state_request_fut.done():
            self.state_request_fut.set_result(True)

    # NOTE: new convenience method to get the device state in one function call
    async def get_device_state_update(self):
        self.state_request_fut = asyncio.Future()     
        msg = StateRequestMsg()
        await self.send_message(msg, self.device_addr)
        await self.state_request_fut

    async def create_initial_schedule(self):
        # TODO implement your initial schedule computation

        # don't change this flag being set or the run script will hang
        self.init_schedule_done.set_result(True)

    async def reschedule(self, remaining_target, t):
        # TODO
        # Add your rescheduling logic as necessary
        self.update_my_device_schedule()
