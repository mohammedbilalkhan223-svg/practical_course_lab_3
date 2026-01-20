import numpy as np
from mango import Agent, sender_addr
from src.sim_environment.messages import *
import asyncio
import logging
import random
from copy import deepcopy
from src.sim_environment.optimization_problem import SchedulingProblem
from src.sim_environment.devices.abstract import AbstractDevice
import pyswarms as ps
from matplotlib import pyplot as plt
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

        #own additions:
        self.device = device_state  # device object to access device information
        self.all_devices = []
        self.target = deepcopy(target)
        self.c_dev = c_dev

        # to be set accordingly during the initial scheduling!
        self.committed = [True]
        self.device_schedule = [0] * len(target)

        # various futures objects for control flow
        self.init_schedule_done = asyncio.Future()
        self.done = asyncio.Future()
        self.state_request_fut = asyncio.Future()
        self.all_replies_arrived = None

        # for dumb testing
        self.own_device_state = None
        self.counter = 0
        self.registered_for = {}
        self.parent = None
        self.agent_info = {}
        self.schedule_updated = asyncio.Future()
        self.evaluation_done = asyncio.Future()
        self.dev_c_op = {}
        self.GB_schedules = {}
        self.GB_cost = float('inf')
        self.proposed_schedules = None
        self.PSO_process = asyncio.Future()
        self.initial_evaluation_done = asyncio.Future()
        self.PSO_counter = 0
        self.GB_cost_it = []
        self.received_PSO_replies = []
        self.all_PSO_future = asyncio.Future()
        self.NoUpdateCounter = 0
        self.all_GB_schedules = {}
        self.all_GB_costs = {}
        self.best_schedule_found = asyncio.Future()
        self.msg_backlog = []
        self.rescheduling_done = asyncio.Future()
        self.original_target = deepcopy(target)

    """
    def on_register(self):
        self.schedule_instant_task(self.create_initial_schedule())
    """

    def on_start(self):
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
            if not self.done.done():
                self.done.set_result(True)

        if self.failed:
            # controller has exploded
            return

        if isinstance(content, TargetUpdateMsg) and is_observer:
            #only do this if its not already active or
            # we get an asyncio/scheduler error!
            #if self.target_update_task is not None and not self.target_update_task.done():
            #    self.target_update_task.cancel()

            #self.target_update_task = self.schedule_instant_task(self.handle_target_update(content, meta))
            print(self.aid, "received target update")


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
        if isinstance(content, NotifyReadyRequestMsg) and is_observer:
            self.schedule_instant_task(self.handle_ready_request(sender))

        if isinstance(content, StateReplyMsg) and is_device:
            self.schedule_instant_task(self.handle_state_reply(content))


        if isinstance(content, IdentifyAgentsMsg):
            self.schedule_instant_task(self.handle_identify_agents(content, sender, meta))

        if isinstance(content, NewGlobalBestMsg):
            if content.sender_aid not in self.received_PSO_replies:
                self.schedule_instant_task(self.handle_NewGlobalBestMsg(content, sender))
            else:
                print(self.aid, "already received msg from sender")

        if isinstance(content, InitialScheduleMsg):
            #if not self.schedule_updated.done():
                self.schedule_instant_task(self.handle_InitialScheduleMsg(content, sender))
            #else:
            #    print(self.aid, "received initial schedule but already got all")

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
        remaining_target = self.target[content.t:]
        await self.reschedule(remaining_target, content.t)

    ### Helper function
    async def forward_msg(self, content, sender):
        other_neighbors = [n for n in self.neighbors() if n != sender]  # forward message to other neighbors
        if other_neighbors:
            for neighbor in other_neighbors:  # send message only to others, not to sender not notify
                await self.send_message(content, neighbor)
        else:
            await self.send_message(content, sender)  # start sending it back to sender

    async def evaluate_schedule(self, schedules):
        print(self.aid, "evaluate_schedule, waiting for PSO future")
        await self.PSO_process
        c_total = await self.cost_fcn(schedules)  # calculating cost again bec. no cost for constraint violations
        print(self.aid, "c_total: ", c_total, "GB_cost: ", self.GB_cost)
        if c_total <= self.GB_cost:
            print(self.aid, "c_total smaller than GB_cost")
            self.GB_cost_it.append(c_total)  # appending new GB cost
            self.all_GB_costs[self.aid] = c_total
            self.all_GB_schedules[self.aid] = schedules
            msg = NewGlobalBestMsg(self.aid, GB_cost=self.all_GB_costs[self.aid],
                                   GB_schedules=self.all_GB_schedules[self.aid], PSO_iteration=self.PSO_counter)
            for neighbor in self.neighbors():
                print(self.aid, "sending msg to neighbor: ", neighbor)
                await self.send_message(msg, neighbor)
        elif c_total >= self.GB_cost:  # if nothing changed, send that no new GB found
            print(self.aid, "c_total greater than than GB_cost")
            msg = NewGlobalBestMsg(self.aid, GB_cost=self.GB_cost, GB_schedules=self.GB_schedules,
                                   PSO_iteration=self.PSO_counter)  # just sending old GB values
            for neighbor in self.neighbors():
                await self.send_message(msg, neighbor)

    async def find_new_GB(self):
        best_aid = min(self.all_GB_costs, key=self.all_GB_costs.get)
        best_cost = self.all_GB_costs[best_aid]
        best_schedule = self.all_GB_schedules[best_aid]
        if float(best_cost) >= float(self.GB_cost):
            #print(self.aid, best_schedule[self.aid][0], self.original_target)
            print(self.aid,
                  "No cheaper schedule found, I set best schedule found future and see if others send me cheaper schedule")
            if len(best_schedule[self.aid][0]) == len(self.original_target):
                print(self.aid, "within first optimization")
                if not self.best_schedule_found.done():
                    self.best_schedule_found.set_result(True)
            elif len(best_schedule[self.aid][0]) <= len(self.original_target):
                print(self.aid, "within rescheduling optimization")
                if not self.rescheduling_done.done():
                    self.rescheduling_done.set_result(True)

        elif float(best_cost) < float(self.GB_cost):
            self.GB_cost = best_cost
            self.GB_schedules = best_schedule
            self.all_PSO_future = asyncio.Future()
            self.PSO_process = asyncio.Future()
            print(self.aid, "find_new_GB for ", self.GB_schedules)
            await self.solve_PSO_decentral()

    async def cost_fcn(self, schedules):
        P_tot = [sum(schedules[aid][0][t] for aid in schedules) for t in range(len(self.target))]
        P_dev = [abs(P_tot[t] - self.target[t]) for t in range(len(self.target))]
        sum_c_op = sum(sum(abs(P) * self.dev_c_op[aid] for P in schedules[aid][0]) for aid in schedules)
        c_total = (sum(P_dev) * self.c_dev) + sum_c_op
        return c_total

    async def handle_InitialScheduleMsg(self, content, sender):
        self.dev_c_op[content.sender_aid] = content.c_op
        if content.sender_aid not in self.GB_schedules: #if sender_aid of schedule not in PB schedueles yet
            self.GB_schedules[content.sender_aid] = content.schedule  # saving received schedule as current PB
            await self.forward_msg(content, sender) #forward the msg
            if len(self.GB_schedules) == self.n_agents:
                print(self.aid, "Received as many schedueles as I know agents, setting future")
                if not self.schedule_updated.done():
                   self.schedule_updated.set_result(True) #all initial schedules arrived
                print(self.aid, "schedule updated future set")
        else:
            pass

    async def handle_NewGlobalBestMsg(self, content, sender):
        #print(self.aid, "received new global best msg", content)
        sender_aid = content.sender_aid
        PSO_iteration = content.PSO_iteration
        if PSO_iteration == self.PSO_counter: #check if this is still in the iteration
            if sender_aid not in [reply[0] for reply in self.received_PSO_replies]:
                print(self.aid, "received from new sender and correct PSO iteration ")
                self.all_PSO_future = asyncio.Future()
                self.received_PSO_replies.append([sender_aid, PSO_iteration])
                self.all_GB_schedules[sender_aid] =  content.GB_schedules
                self.all_GB_costs[sender_aid] = content.GB_cost
                await self.forward_msg(content, sender)
                print(self.aid, "length received replies: ", len(self.received_PSO_replies), self.n_agents)
                if len(self.received_PSO_replies) == (self.n_agents-1): #if
                    print(self.aid, "received all PSO replies")
                    if not self.all_PSO_future.done():
                        self.all_PSO_future.set_result(True)
                        print(self.aid, "received all PSO replies, start find new GB ")
                        await self.find_new_GB()

            elif content.GB_schedules == self.all_GB_schedules[sender_aid]: #received schedule already in GB schedules for the sender
                pass
        elif PSO_iteration != self.PSO_counter:
            if PSO_iteration < self.PSO_counter:
                pass
                #print(self.aid, "received an old msg", content)
            elif PSO_iteration > self.PSO_counter:
                print(self.aid, "received a msg from coming iteration", content)
                self.msg_backlog.append(content)
                print(self.aid, "msg saved to msg_backlog")

        elif self.best_schedule_found.done(): #Already ended search process because no change happened
            if content.GB_cost <= self.GB_cost: #received cost smaller than saved one
                self.best_schedule_found = asyncio.Future()
                self.init_schedule_done = asyncio.Future()
                self.all_PSO_future = asyncio.Future()
                print(self.aid, f"I thought I am done with my {self.GB_cost}, but someone else found cheaper {content.GB_cost}")
                self.all_GB_schedules[sender_aid] = content.GB_schedules
                self.PSO_counter = content.PSO_iteration
                await self.forward_msg(content, sender)
                if not self.all_PSO_future.done():
                    self.all_PSO_future.set_result(True)
                    print(self.aid, "start find new GB ")
                    await self.find_new_GB()
            else:
                await self.forward_msg(content, sender)

    async def send_to_neighbors(self, msg):
        for n in self.neighbors():
            await self.send_message(msg, n)
    async def get_device_state(self):
        self.state_request_fut = asyncio.Future()
        msg = StateRequestMsg()
        await self.send_message(msg, self.device_addr)
        await self.state_request_fut

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

    """
        Call your schedule solver here and save the initial schedule.
        """

    async def set_starting_schedule(self, target_length):
        await self.get_device_state()

        if isinstance(self.device_state, IdealBatteryState):
            self.own_device_state = "Battery"
        if isinstance(self.device_state, IdealFuelCellState):
            self.own_device_state = "FuelCell"
        if isinstance(self.device_state, IdealLoadState):
            self.own_device_state = "Load"
        devices = [self.device]
        num_agents = len(self.agent_info) + 1  # +1 because own agent not in list
        agent_target = [x / num_agents * np.random.uniform(0.8, 1.2) for x in self.target]
        c_dev = self.c_dev
        p_max = self.device_state.p_max
        p_min = self.device_state.p_min
        c_op = self.device_c_op
        init_schedule = [np.zeros(target_length, dtype=int)]
        #init_schedule = [np.random.uniform(p_min, p_max, target_length)]
        print(self.aid, "init_schedule: ", init_schedule)
        #init_schedule, init_cost = ED_solve(devices, self.committed, agent_target,c_dev)  # to ensure initial schedule meets all constraints we use ED solve
        # init_schedule = [0.5 * self.device_state.p_max for _ in range(len(self.target))]
        self.device_schedule = init_schedule
        self.GB_schedules[self.aid] = init_schedule
        self.dev_c_op[self.aid] = self.device_c_op
        msg = InitialScheduleMsg(init_schedule, self.dev_c_op[self.aid], sender_aid=self.aid)
        for neighbor in self.neighbors():
            await self.send_message(msg, neighbor)
        print(self.aid, "waiting for schedule updated future")
        if not self.schedule_updated.done():
            await self.schedule_updated  # wait until all initial schedules arrived
        print(self.aid, "running PSO")
        self.PSO_process = asyncio.Future()
        await self.solve_PSO_decentral()


    async def create_initial_schedule(self):
        #await self.get_device_state()
        #await asyncio.sleep(3)
        target_length = len(self.target)
        print(self.aid, "creating initial schedule")
        await self.set_starting_schedule(target_length)  # creates bit random but working initial schedule
        await self.best_schedule_found  # wait for PSO to find best schedule
        print(self.aid, "best schedule found ")
        self.device_schedule = self.GB_schedules[self.aid][0]
        self.update_my_device_schedule()
        # await self.update_device_schedule()
        if not self.init_schedule_done.done():
            self.init_schedule_done.set_result(True)
        # don't change this flag being set or the run script will hang
        #self.init_schedule_done.set_result(True)

    def constraint_cost(self, schedules):
        constraint_penalty = 0.0
        penalization = 1e6
        schedule = schedules[self.aid][0]
        if self.own_device_state == "Battery":
            '''- P_min <= P(i, t) <= P_max -> via bounds
            '''
            E0 = self.device_state.size * self.device_state.soc #E of device; E(i, 0) = size * soc
            Et = E0
            for t, Pt in enumerate(schedule):
                Et1 = Et-Pt #current energy in each step ; E(i, t + 1) = E(i, t) - P(i, t)
                if Et < 0 or Et > self.device_state.size: # 0 <= E(i, t) <= size
                    constraint_penalty += penalization #adding fixed penalization for violation
                E1t = Et #E from current time step saved for next round as E(t-1) -> important for E_T evaluation in next if ...
                Et = Et1 #setting current E for next rounds previous
                soc = Et / self.device_state.size
                if soc <0 or soc>1: #making sure soc stays within bounds
                    constraint_penalty += penalization
            if E1t != self.device_state.size * self.device_state.final_soc: #E(i, T) = size * final_soc ;
                constraint_penalty += penalization

            if Et != self.device_state.size * self.device_state.final_soc: #E(i, T + 1) = E(t=0)
                constraint_penalty += penalization


        elif self.own_device_state == "FuelCell":
            """    
            - 0 <= P(i, t) <= p_max -> via bounds 
            """
            F0 = self.device_state.fuel_amount #F(i, 0) = fuel_amount
            Ft = F0
            P1t = self.device_state.p_prev
            for t, Pt in enumerate(schedule):
                Ft1 = Ft - Pt  #F(i, t + 1) = F(i, t) - P(i, t)
                if Ft < 0 or Ft > self.device_state.fuel_amount: #F(i, t) >= 0 and <= fuel amount
                    constraint_penalty += penalization
                if abs(Pt - P1t) > self.device_state.change_max: #first: | P(i, 0) - p_prev | <= change_max; then ramp: | P(i, t + 1) - P(i, t) | <= change_max
                    constraint_penalty += penalization
                Ft = Ft1
                P1t = Pt

        return constraint_penalty

    def helper_PSO_cost_fcn(self, schedules):
        P_tot = [sum(schedules[aid][0][t] for aid in schedules) for t in range(len(self.target))]
        P_dev = [abs(self.target[t]- P_tot[t]) for t in range(len(self.target))]
        sum_c_dev = sum(P_dev)*self.c_dev
        sum_c_op = sum(sum(abs(P) * self.dev_c_op[aid] for P in schedules[aid][0]) for aid in schedules)
        c_total = sum_c_dev + sum_c_op
        penalty = self.constraint_cost(schedules)
        return c_total+penalty

    def PSO_cost_fcn(self, particles):
        costs = []
        for particle in particles:
            schedules = self.GB_schedules
            schedules[self.aid] = [particle.tolist()] #replacing own schedule with current position in schedules
            cost = self.helper_PSO_cost_fcn(schedules) #calculating cost with helper_cost_fcn
            costs.append(cost)
        return np.array(costs)

    def add_constraints(self):
        if self.own_device_state == "Load":
            p_min_bounds = np.full(len(self.target), self.device_state.p_min)
            p_max_bounds = np.full(len(self.target),self.device_state.p_max)
            bounds = (p_min_bounds, p_max_bounds)
        elif self.own_device_state == "Battery":
            p_min_bounds = np.full(len(self.target), self.device_state.p_min)
            p_max_bounds = np.full(len(self.target), self.device_state.p_max)
            bounds = (p_min_bounds, p_max_bounds)
        elif self.own_device_state == "FuelCell":
            p_min_bounds = np.full(len(self.target), self.device_state.p_min)
            p_max_bounds = np.full(len(self.target), self.device_state.p_max)
            bounds = (p_min_bounds, p_max_bounds)
        return bounds

    async def solve_PSO_decentral(self):
        self.PSO_counter += 1
        print(self.aid, f"---------------------------------------------------starting PSO solving, iteration {self.PSO_counter}------------------------------------------------------------------------------------")
        self.received_PSO_replies = []
        bounds = self.add_constraints()
        n_particles = 1000
        n_dimensions = len(self.target)
        hyp_param = {'c1': 1.7, #cognitiv parameter = how much each particle is influenced by own PB
                     'c2': 1.5, #social parameter = weights how much particle is influences by GB
                     'w': 0.1} # inertia parameter = particles precious velocity
        PSO_optimizer = ps.single.GlobalBestPSO(n_particles = n_particles,
                                                dimensions = n_dimensions,
                                                options = hyp_param,
                                                bounds = bounds)
        sugg_GB_cost, best_pos = PSO_optimizer.optimize(self.PSO_cost_fcn, iters = 200)
        best_pos = best_pos.tolist()
        self.device_schedule = [best_pos]
        sugg_GB_scheduels = self.GB_schedules
        sugg_GB_scheduels[self.aid] = [best_pos]
        self.all_GB_schedules[self.aid] = [best_pos]
        self.all_GB_costs[self.aid] = sugg_GB_cost
        if not self.PSO_process.done():
            self.PSO_process.set_result(True)
        print(self.aid, "PSO done, now to evaluate schedule")
        await self.evaluate_schedule(sugg_GB_scheduels)

    async def reschedule(self, remaining_target, t):
        await self.get_device_state()
        PSO_counter = 0
        self.target = remaining_target
        print(self.aid, "running PSO for rescheduling")
        self.PSO_process = asyncio.Future()
        await self.solve_PSO_decentral()
        await self.rescheduling_done
        updated_target = self.original_target
        updated_target[t:] = remaining_target
        self.target = updated_target
        self.device_schedule[t:] = self.GB_schedules[self.aid][:]
        self.update_my_device_schedule()
