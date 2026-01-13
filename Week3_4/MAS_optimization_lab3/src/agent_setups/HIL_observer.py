from dataclasses import dataclass
from typing import Dict
from mango import Agent, sender_addr
from mango.messages.codecs import json_serializable
import asyncio
import copy
import random
import numpy as np
from src.sim_environment.optimization_problem import SchedulingProblem
from src.sim_environment.messages import (
    TargetUpdateMsg,
    SetDoneMsg,
    NotifyReadyRequestMsg,
    NotifyReadyMsg,
    SetScheduleMsg,
    StateRequestMsg,
    StateReplyMsg,
    SetScheduleReplyMsg,
    FailControllerMsg
)
import sys
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
else:
    from src.sim_environment.devices.hil import *
from src.sim_environment.hil_controller import ComObject
from scenarios.hil_scenarios import HIL_IP, unit
import logging


class HILObserver(Agent):
    def __init__(self, controller_addresses, step_time_s, problem, d_fail_time, hil_drop_rates, c_fail_time, seed=None):
        super().__init__()

        self.problem_rng = random.Random(seed)
        self.drop_rng = random.Random(seed + 1)

        self.controller_addresses = controller_addresses
        self.step_time_s = step_time_s
        self.n_steps = len(problem.target)
        self.original_target = copy.deepcopy(problem.target)
        self.randomized_target = copy.deepcopy(problem.target)
        self.max_rel_rand = problem.max_rel_rand
        self.steps_done = 0
        self.done = asyncio.Future()
        self.c_dev = problem.c_dev
        self.rp = None
        self.final_problem = copy.deepcopy(problem)

        self.ready_controllers = {addr: False for addr in self.controller_addresses}
        self.all_controllers_ready = asyncio.Future()

        self.devices = problem.devices

        # device failure and drop params
        self.failed_devices = [False] * len(controller_addresses)
        self.d_fail_time = d_fail_time
        self.hil_drop_rates = hil_drop_rates
        self.c_fail_time = c_fail_time

        self.attempted_powers = {i:[] for i in range(len(controller_addresses))}

        self.controller_schedules = [[0] * len(problem.target) for _ in range(len(controller_addresses))]

        # get ourselves a nice com object
        self.co = ComObject(conn_ip=HIL_IP)  # all default params

        # some convenience dicts to map corresponding things to each other
        self.con_addr_to_id = {
            addr: i for i, addr in enumerate(controller_addresses)
        }

    def on_register(self):
        print("starting client")
        self.co.client.start()

    async def shutdown(self):
        self.co.client.stop()
        await super().shutdown()

    def handle_message(self, content, meta):
        sender = sender_addr(meta)

        if isinstance(content, NotifyReadyMsg):
            self.ready_controllers[sender] = True
            if all(self.ready_controllers.values()):
                self.all_controllers_ready.set_result(True)

        # --------------------------------------------------
        # SetScheduleMsg set things in the HIL and
        # set things in our local device
        # --------------------------------------------------
        if isinstance(content, SetScheduleMsg):
            self.schedule_instant_task(self.handle_set_schedule_msg(content, sender))
            return

        # --------------------------------------------------
        # state request messages read something in the HIL
        # set things in our local device
        # --------------------------------------------------
        if isinstance(content, StateRequestMsg):
            self.schedule_instant_task(self.handle_state_request_msg(content, sender))
            return

    async def handle_set_schedule_msg(self, content, sender):
        index = self.con_addr_to_id[sender]
        self.controller_schedules[index] = content.setpoints

        # reply
        msg = SetScheduleReplyMsg(True)
        await self.send_message(msg, sender)

    async def handle_state_request_msg(self, content, sender):
        index = self.con_addr_to_id[sender]
        await self.update_device_from_HIL(index)

        # NOTE: We never drop this on the last time step to avoid a nasty looking
        # but harmless asyncio error on shutdown that may confuse people.
        if self.steps_done < self.n_steps - 1:
            # potentially drop the answer
            if self.drop_rng.random() <= self.hil_drop_rates[index]:
                return

        # answer with newly updated state
        msg = StateReplyMsg(self.devices[index].state)
        await self.send_message(msg, sender)

    #------------------------------------------------
    # HIL interface functions
    #------------------------------------------------
    def interrogate(self):
        co = self.co
        ok = co.connection.interrogation(co.addr_recv, co.cause, co.qualifier, wait_for_response=True)
        if not ok:
            logging.warning("Did not get a response from HIL device on interrogation.")
        return ok

    async def update_device_from_HIL(self, index):
        if not self.co.connection.is_connected:
            logging.warning("Observer-update_device_from_HIL: C104 client is not connected.")
            return

        # - read HIL state
        #   - current nominal power (absolute)
        #   - for batteries: current SOC (relative)
        # - update state object of the device
        if isinstance(self.devices[index].state, IdealBatteryState):
            await self.update_HIL_state_bss(index)
        elif isinstance(self.devices[index].state, IdealLoadState):
            await self.update_HIL_state_load(index)
        elif isinstance(self.devices[index].state, IdealFuelCellState):
            await self.update_HIL_state_fuel(index)
        else:
            logging.error(f"Tried to update a device from HIL that is of unknown type: {type(self.devices[index].state)}")

    # NOTE: These functions have some hard coded indices to map the correct
    # measurement points to the device indices since battery devices contain 2 points.
    # There are ways to cleanly abstract this but since the example system is expected to
    # only ever contain these 6 devices it is not necessary for now.
    async def update_HIL_state_bss(self, index):
        p_index = self.devices[index].state.p_read
        soc_index = self.devices[index].state.soc_read
        
        # do the actual query
        ok = self.interrogate()
        if not ok:
            # nothing to update
            return

        p = self.co.recv_points[p_index].value * unit
        soc = self.co.recv_points[soc_index].value / 100

        self.devices[index].state.set_power(p)
        self.devices[index].state.soc = soc # get percent value from HIL

    async def update_HIL_state_load(self, index):
        p_index = self.devices[index].state.p_read

        # do the actual query
        ok = self.interrogate()
        if not ok:
            # nothing to update
            return

        p = -1 * self.co.recv_points[p_index].value * unit
        self.devices[index].state.set_power(p)

    async def update_HIL_state_fuel(self, index):
        p_index = self.devices[index].state.p_read
        
        # do the actual query
        # technically pure copy paste from load but for later implementations
        # we may actually have fuel amount to query from the HIL
        ok = self.interrogate()
        if not ok:
            # nothing to update
            return

        p = self.co.recv_points[p_index].value * unit
        # print(f"read a p value for fuel {index}: {p}")
        self.devices[index].state.set_power(p)

    async def set_HIL_power(self, index, p):
        # NOTE: Power setpoints are relative values x in [0,1] 
        # and interpreted by the device as:
        # x * <device_nominal_power>
        # need to be a bit careful with signs here, nominal powers in HIL are always positive!
        if not self.co.connection.is_connected:
            logging.warning("Observer-set_HIL_power: C104 client is not connected.")
            return
        
        p_set = self.devices[index].state.p_set

        if isinstance(self.devices[index].state, IdealBatteryState):
            # NOTE: automatically switches sign for us.
            # CAREFUL: Assumes that p_max = -p_min for batteries!
            self.co.send_points[p_set].value = p / self.devices[index].state.p_max
        elif isinstance(self.devices[index].state, IdealLoadState):
            self.co.send_points[p_set].value = p / self.devices[index].state.p_min
        elif isinstance(self.devices[index].state, IdealFuelCellState):
           self.co.send_points[p_set].value = p / self.devices[index].state.p_max
           # print(f"Trying to set fuel cell {index} to {p}")
        else:
            logging.error(f"Tried to set power on HIL from device of unknown type: {type(self.devices[index].state)}")

        # send out the new setpoint
        self.co.send_points[p_set].transmit()

    #------------------------------------------------
    #------------------------------------------------

    def randomize(self, index):
        og_value = self.original_target[index]
        if og_value == 0:
            return 0

        # random number in (-max_rel, +max_rel)  * og_value
        random_offset = og_value * 2 * (0.5 - self.problem_rng.random()) * self.max_rel_rand
        new_value = og_value + random_offset

        self.randomized_target[index] = new_value
        return new_value

    async def randomize_and_step(self):
        if self.steps_done == self.n_steps:
            return

        # randomize
        new_value = self.randomize(self.steps_done)
        # send information messages
        msg = TargetUpdateMsg(self.steps_done, new_value)
        for addr in self.controller_addresses:
            await self.send_message(msg, addr)

        # wait half step time
        await asyncio.sleep(0.3 * self.step_time_s)

        for i, d in enumerate(self.devices):
            # if controller has not failed, update the power value properly
            # otherwise it remains the same as the old vlaue
            if not self.failed_devices[i]:
                new_p = self.controller_schedules[i][self.steps_done]
                # NOTE: not setting this directly but indirectly from HIL now
                # so the reported power is what was actually set by the HIL device.
                # d.set_output_power(new_p)
                await self.set_HIL_power(i, new_p)
                self.attempted_powers[i].append(new_p)

        await asyncio.sleep(0.1 * self.step_time_s)
        
        for i in range(len(self.devices)):
            await self.update_device_from_HIL(i)

        await asyncio.sleep(0.1 * self.step_time_s)

        for d in self.devices:
            d.step()

        # termination condition
        self.steps_done += 1
        if self.steps_done == self.n_steps:
            # terminate all other agents
            for addr in self.controller_addresses:
                msg = SetDoneMsg()
                await self.send_message(msg, addr)

            self.done.set_result(True)

        for i, t in enumerate(self.d_fail_time):
            if t == self.steps_done:
                # note the device down as failed
                # it will no longer update its power value
                print(f"Failing device {i}")
                self.failed_devices[i] = True

        for i, t in enumerate(self.c_fail_time):
            if t == self.steps_done:
                # send the controller the failure msg
                msg = FailControllerMsg()
                self.schedule_instant_message(msg, self.controller_addresses[i])

        

    async def wait_for_agents_ready(self):
        for addr in self.controller_addresses:
            msg = NotifyReadyRequestMsg()
            await self.send_message(msg, addr)

        await self.all_controllers_ready

    async def start_syncing(self):
        # wait for controller agents to be done with their init
        await self.wait_for_agents_ready()

        # schedule randomization
        self.schedule_periodic_task(
            coroutine_func=self.randomize_and_step, delay=self.step_time_s
        )

    def evaluate(self):
        self.final_problem.target = self.randomized_target
        total_device_costs = sum([x.cumulative_cost for x in self.devices])
        total_diff_cost = self.final_problem.dev_cost_function(self.randomized_target, [x.stepped_powers for x in self.devices])
        total_commitment_costs = sum([x.commitment_cost for x in self.devices if any(x.stepped_powers)])
        
        total_cost = total_device_costs + total_diff_cost + total_commitment_costs

        print(f"Total deviation cost was: {total_diff_cost}")
        print(f"Total device cost was: {total_device_costs}")
        print(f"Total commitment cost was: {total_commitment_costs}")
        print(f"Total cost after randomization was: {total_cost}")

        def check_soc_constraint(devices):
            for d in devices:
                if not isinstance(d.state, IdealBatteryState):
                    continue

                if not np.isclose(sum(d.stepped_powers), 0, atol=0.01):
                    print(f"Invalid SOC power diff: {sum(d.stepped_powers)}")
                    return False

            return True

        dev, dp = self.get_devices_and_powers()
        soc_con = check_soc_constraint(dev)

        print("Attempted scheduels were:")
        print(self.attempted_powers)

        return total_cost, soc_con

    def get_devices_and_powers(self):
        devices = self.devices
        powers = [d.stepped_powers for d in self.devices]
        return devices, powers


class DummyHILObserver(HILObserver):

    # replace all the HIL things with doing nothing
    async def update_device_from_HIL(self, index):
        pass

    async def get_HIL_state(self, index):
        pass

    async def set_HIL_power(self, index, p):
        self.devices[index].set_output_power(p)