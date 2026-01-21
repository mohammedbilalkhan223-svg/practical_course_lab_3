from copy import deepcopy

from src.sim_environment.optimization_problem import SchedulingProblem
from scenarios.hil_scenarios_Task3 import get_hil_device_specs

# Define locally (same style as other scenario files)
unit = kW = 10**3
STEP_TIME_S = 1

# Required by run_hil.py
SCENARIO_NR = 0
RNG_SEED = 1


def apply_loss(base_adj, loss):
    """
    Apply packet loss to existing edges only.
    -1 edges remain disconnected
    """
    n = len(base_adj)
    adj = [row[:] for row in base_adj]
    for i in range(n):
        for j in range(n):
            if i >= j:
                continue
            if base_adj[i][j] != -1:
                adj[i][j] = loss
    return adj


def base_problem():
    c_load = 0.005
    c_other = 0.007
    c_dev = 10
    max_rel_rand = 0.1

    target = [0.9 * x * unit for x in
              [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]

    devices = get_hil_device_specs(c_load, c_other, c_other)
    return deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))


def get_hil_scenarios():
    # -------- BASE TOPOLOGIES --------

    # Ring
    ring = [
        [0, 0, -1, -1, -1, 0],
        [0, 0, 0, -1, -1, -1],
        [0, 0, 0, 0, -1, -1],
        [0, 0, 0, 0, 0, -1],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]

    # Fully connected
    full = [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]

    # Star (hub = agent 3)
    star = [
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
        [0, 0, 0, -1, 0, 0],
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
    ]

    losses = [0.30, 0.40, 0.60]
    scenarios = []

    # Ring
    for loss in losses:
        scenarios.append((STEP_TIME_S, apply_loss(ring, loss),
                          base_problem(), [-1]*6, [-1]*6, [-1]*6))

    # Fully connected
    for loss in losses:
        scenarios.append((STEP_TIME_S, apply_loss(full, loss),
                          base_problem(), [-1]*6, [-1]*6, [-1]*6))

    # Star
    for loss in losses:
        scenarios.append((STEP_TIME_S, apply_loss(star, loss),
                          base_problem(), [-1]*6, [-1]*6, [-1]*6))

    return scenarios
