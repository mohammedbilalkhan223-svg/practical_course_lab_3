import logging
import asyncio
import random
import multiprocessing
from mango import run_with_tcp, AgentAddress, create_tcp_container, activate, custom_topology, per_node

import sys
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
    from src.agent_setups.HIL_observer import DummyHILObserver as HILObserver
else:
    from src.sim_environment.devices.hil import *
    from src.agent_setups.HIL_observer import HILObserver

from src.sim_environment.optimization_problem import *

# -------------------
#from src.template_agents.decentral_agent_lab2 import DecentralAgent #to run agent from Lab 2 with Particle Swarm Optimization
from src.template_agents.decentral_agent_rescheduling import DecentralAgent #to run the 'normal' agent adjusted from Jens' agent
#from src.agent_setups.my_new_decentral_agent import DecentralAgent #Jens' agent
#from src.template_agents.decentral_agent_rescheduling_Task10 import DecentralAgent #adjusted agent for task 10 including countermeasures
#from src.template_agents.decentral_agent_rescheduling_Task10_freeze import DecentralAgent #adjusted agent for task 10 including countermeasures
#from src.template_agents.decentral_agent_rescheduling_task6 import DecentralAgent # To run agent with routing via least package drop path

from scenarios.hil_scenarios_Fig2 import get_hil_scenarios, SCENARIO_NR, RNG_SEED #Topology given in figure 2 in the instruction
#from scenarios.hil_scenarios_Tasks import get_hil_scenarios, SCENARIO_NR, RNG_SEED #to run all other scenarios
# -------------------

from src.sim_environment.messages import SCENARIO_CODEC, SetDoneMsg
import networkx as nx

import os
import json

# use cmd scenario number if it exists
if len(sys.argv) > 1:
    SCENARIO_NR = int(sys.argv[1])

HOST = "127.0.0.1"
OBS_PORT = 5555
CON_PORT = 5557

OBS_NAME = "Observer"
OBS_ADDR = AgentAddress((HOST, OBS_PORT), OBS_NAME)

def con_name(i):
    return f"con_{i}"


def con_addr(i):
    return AgentAddress((HOST, CON_PORT), con_name(i))


async def main():
    random.seed(1)

    step_time_s, _, problem, d_fail_time, hil_drop_rate, c_fail_time  = get_hil_scenarios()[SCENARIO_NR]

    c_proc = make_controllers_process()
    c_proc.start()

    await run_observer(step_time_s, problem, d_fail_time, hil_drop_rate, c_fail_time)

    # kill in case join does not work for some reason
    # to ensure termination
    c_proc.join(timeout=1)
    c_proc.kill()

    print("done")

def make_controllers_process():
    process = multiprocessing.Process(target=run_controllers)
    return process

def adjacency_to_topology(adjacency):
    # only look at top half of matrix because undirected graph
    out = nx.Graph()

    # create the nodes
    for i in range(len(adjacency)):
        out.add_node(i)

    # set the connections
    for i in range(len(adjacency)):
        for j in range(len(adjacency[i])):
            if i >= j:
                # not top half
                continue

            # -1 means no edge
            if adjacency[i][j] == -1:
                continue

            # NOTE: delays not in for now because they lead to weird bugs
            out.add_edge(i, j, loss_rate=adjacency[i][j], delay=0)

    return out


def run_controllers():
    async def controller_main():
        step_time_s, adjacency, problem, _, _, _ = get_hil_scenarios()[SCENARIO_NR]
        n_agents = len(problem.devices)
        container = create_tcp_container(addr=(HOST, CON_PORT), codec=SCENARIO_CODEC)
        controller_agents = []
        topo = custom_topology(adjacency_to_topology(adjacency))
        container.graph = topo.graph

        addr_to_node_id = {}

        for i, node in enumerate(per_node(topo)):
            d =  problem.devices[i]
            # OBS_ADDR is both observer and device, from the view of the agent
            a = DecentralAgent(OBS_ADDR, OBS_ADDR, d.state, d.c_op, problem.target, problem.c_dev, n_agents, step_time_s, RNG_SEED+i)
            controller_agents.append(a)
            container.register(a, suggested_aid=con_name(i))
            addr_to_node_id[a.addr] = i
            node.add(a)

        for a in topo.agents:
            a.addr_to_node_id = addr_to_node_id

        async with activate(container) as c1:
            # NOTE: debug message:
            for a in controller_agents:
                print(f"{a.aid} neighbors are: {a.neighbors()}")

            for a in controller_agents:
                await a.done

    asyncio.run(controller_main())

async def run_observer(step_time_s, problem, d_fail_time, hil_drop_rate, c_fail_time):
    container = create_tcp_container(addr=(HOST, OBS_PORT), codec=SCENARIO_CODEC)
    controller_addresses = [con_addr(i) for i in range(len(problem.devices))]
    # (self, device_addresses, controller_addresses, step_time_s, problem)
    obs = HILObserver(controller_addresses, step_time_s, problem, d_fail_time, hil_drop_rate, c_fail_time, RNG_SEED)
    container.register(obs, suggested_aid=OBS_NAME)

    async with activate(container) as c1:
        await asyncio.sleep(1)
        await obs.start_syncing()
        await obs.done

    obs.evaluate()
    plot_results(obs)

def plot_results(obs):
    import matplotlib.pyplot as plt

    devices, device_powers = obs.get_devices_and_powers()
    total_power, device_cost_list, schedule_cost_list, cumulative_cost = (
        obs.final_problem.get_cumulative_by_timestep(device_powers)
    )

    x = list(range(len(total_power)))
    plt.plot(x, obs.final_problem.target, label = "target power")
    plt.plot(x, total_power, label ="total power")
    plt.plot(x,  device_cost_list, label = "device costs")
    plt.plot(x, schedule_cost_list, label = "target costs")
    plt.plot(x, cumulative_cost, label = "total costs")
    plt.legend()
    plt.show()

    plt.cla()
    plt.plot(x, obs.final_problem.target, label = "target power")
    print(f"target: {obs.final_problem.target}")
    for i, schedule in enumerate(device_powers):
        added_string = ""
        if isinstance(devices[i].state, IdealBatteryState):
            added_string = "bat"
        if isinstance(devices[i].state, IdealLoadState):
            added_string = "load"
        if isinstance(devices[i].state, IdealFuelCellState):
            added_string = "fuel"

        l = f"device_{i}_{added_string}"
        plt.plot(x, schedule, label = l)
        print(f"schedule: {l} - {schedule}")
    plt.plot(x, total_power, label ="total power", linestyle = "--")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    asyncio.run(main())
