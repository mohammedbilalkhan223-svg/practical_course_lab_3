from src.sim_environment.optimization_problem import *
from copy import deepcopy
import sys

# Choose ideal vs HIL devices
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
else:
    from src.sim_environment.devices.hil import *

HIL_IP = "10.51.6.211"   # <-- set this to your Typhoon HIL IP

STEP_TIME_S = 1
SCENARIO_NR = 0
RNG_SEED = 1

# Unit scaling
unit = kW = 10**3

# HIL device limits / params
HIL_LOAD_P_MIN = -1 * 450 * unit

HIL_FUEL_AMOUNT = 100000 * unit
HIL_FUEL_P_MAX = 500 * unit
HIL_FUEL_CHANGE_MAX = 10 * unit
HIL_FUEL_P_PREV = None

HIL_BAT_SIZE = 1000 * 500
HIL_BAT_SOC_INIT = 0.5
HIL_BAT_P_MIN = -1.6 * 10**3 * unit
HIL_BAT_P_MAX = -1 * HIL_BAT_P_MIN  # symmetric assumption

# COM points (0-indexed)
L1_P_READ = 0
L1_P_SET  = 0

L2_P_READ = 1
L2_P_SET  = 1

B1_P_READ   = 2
B1_SOC_READ = 4
B1_P_SET    = 2

B2_P_READ   = 3
B2_SOC_READ = 5
B2_P_SET    = 3

F1_P_READ = 6
F1_P_SET  = 4

F2_P_READ = 7
F2_P_SET  = 5


def get_hil_device_specs(c_load, c_fuel, c_bat):
    l1 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L1_P_READ, L1_P_SET), c_load)
    l2 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L2_P_READ, L2_P_SET), c_load)
    b1 = IdealDevice(IdealBatteryState(HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX,
                                       B1_P_READ, B1_SOC_READ, B1_P_SET), c_bat)
    b2 = IdealDevice(IdealBatteryState(HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX,
                                       B2_P_READ, B2_SOC_READ, B2_P_SET), c_bat)
    f1 = IdealDevice(IdealFuelCellState(HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV,
                                        F1_P_READ, F1_P_SET), c_fuel)
    f2 = IdealDevice(IdealFuelCellState(HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV,
                                        F2_P_READ, F2_P_SET), c_fuel)
    return [l1, l2, b1, b2, f1, f2]


def make_fig2_adj(drop_rate: float, device_failure: list):
    """
    Figure-2 communication topology between controller agents (a1..a6).
    Indices: a1=0, a2=1, a3=2, a4=3, a5=4, a6=5

    Edges in Figure 2:
      a1-a2, a1-a3, a2-a3,
      a2-a4, a2-a5, a3-a5,
      a4-a6, a5-a6

    adj[i][j] (upper triangle) = packet drop probability on existing edge i-j
    -1 means no edge.
    """
    dr = float(drop_rate)

    adj = [
        [0,  -1, -1, -1, -1, -1],
        [0,   0, -1, -1, -1, -1],
        [0,   0,  0, -1, -1, -1],
        [0,   0,  0,  0, -1, -1],
        [0,   0,  0,  0,  0, -1],
        [0,   0,  0,  0,  0,  0],
    ]

    edges = [
        (0, 1), (0, 2), (1, 2),
        (1, 3), (1, 4),
        (2, 4),
        (3, 5), (4, 5),
    ]
    for i, j in edges:
        adj[i][j] = dr

    return adj


def topology_with_varied_droprates(drop_rates):

    adj = [
        [0, -1, -1, -1, -1, -1],
        [0, 0, -1, -1, -1, -1],
        [0, 0, 0, -1, -1, -1],
        [0, 0, 0, 0, -1, -1],
        [0, 0, 0, 0, 0, -1],
        [0, 0, 0, 0, 0, 0],
    ]

    # Default edges if not specified in drop_rates
    edges = [
        (0, 1), (0, 2), (1, 2),
        (1, 3), (1, 4),
        (2, 4),
        (3, 5), (4, 5),
    ]

    # Default drop rate if not specified for an edge
    default_drop_rate = 0.3

    # Apply drop rates to edges
    for edge in edges:
        # Use specified drop rate if exists, else use default
        drop_rate = drop_rates.get(edge, default_drop_rate)
        adj[edge[0]][edge[1]] = float(drop_rate)

    return adj

def get_hil_scenarios():
    # Common weights (keep consistent across all drop experiments)
    c_load  = 0.005
    c_other = 0.007
    c_dev   = 10
    max_rel_rand = 0.1

    # Target profile (use the one you had in Task 2)
    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]

    devices = get_hil_device_specs(c_load, c_other, c_other)

    # No failures in Task 4
    device_failure = [-1, -1, -1, -1, -1, -1]
    #device_failure = [-1, 7, -1, -1, -1, -1] #8 i)a1 failing
    #device_failure = [-1, -1, -1, -1, 5, -1] #8 ii) a5 failing
    #device_failure = [-1, -1, -1, 2, 2, -1] #8 iii) a4 & a5 failing
    #device_failure = [-1, -1, 2, -1, 2, -1] #8 iv) a3 and a5 failing
    d_fail_time = device_failure
    #controller_failure= [-1, -1, -1, -1, -1, -1]
    controller_failure = [7,-1, -1, -1, -1, -1] #8 i)a1 failing
    #controller_failure = [-1, -1, -1, -1, 5, -1] #8 ii) a5 failing
    #controller_failure = [-1, -1, -1, 2, 2, -1] #8 iii) a4 & a5 failing
    #controller_failure = [-1, -1, 2, -1, 2, -1] #8 iv) a3 and a5 failing
    c_fail_time = controller_failure
    # Task 4 focuses on packet drops between controller agents.
    # Keep HIL observer/device link drops disabled here.
    hil_drop_rate = [-1, -1, -1, -1, -1, -1]

    def make_scenario(p_drop_agent_edges: float):
        varied_drop_rates = {
            (0, 1): 0.05,  # Low drop rate between nodes 0 and 1
            (1, 2): 0.1,  # Higher drop rate between nodes 1 and 2
            (1, 4): 0.1,  # Even higher drop rate between nodes 3 and 5
            (2, 4): 0.9,
        }
        problem = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))
        #adjacency = make_fig2_adj(p_drop_agent_edges, device_failure)
        adjacency = topology_with_varied_droprates(varied_drop_rates)
        return (STEP_TIME_S, adjacency, problem, d_fail_time, hil_drop_rate, c_fail_time)

    # Scenario indices used by run_hil.py:
    s0 = make_scenario(0.0)  # baseline benchmark
    s1 = make_scenario(0.1)  # 10%
    s2 = make_scenario(0.3)  # 30%
    s3 = make_scenario(0.6)  # 60%


    return [s0, s1, s2, s3]
