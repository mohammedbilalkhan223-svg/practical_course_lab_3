from src.sim_environment.optimization_problem import *
from copy import deepcopy
import sys

#------------------------------
# Other sim params also moved here so they are all in one place!
#------------------------------
# NOTE: switch these two imports to swap between linear devices on python side
# and pure data container devices that get updated from HIL (and do nothing otherwise!)
# from src.sim_environment.devices.hil import *

if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
    STEP_TIME_S = 5
else:
    from src.sim_environment.devices.hil import *
    STEP_TIME_S = 12

HIL_IP = "10.51.6.211"
#STEP_TIME_S = 5

SCENARIO_NR = 0
RNG_SEED = 1

#------------------------------
# Set HIL device specs according to what is running "in hardware" here.
# New controllers still use the same p_min, p_max, soc, etc.
#------------------------------
# Unit parameter is here to be used by the observer to correctly
# translate values it reads/writes to the HIL.
unit = kW = 10**3

HIL_LOAD_P_MIN = -1 * 450 * unit

HIL_FUEL_AMOUNT = 100000 * unit
HIL_FUEL_P_MAX = 500 * unit
HIL_FUEL_CHANGE_MAX = 10 * unit
HIL_FUEL_P_PREV = None

HIL_BAT_SIZE = 1000 * 500 
HIL_BAT_SOC_INIT = 0.5
HIL_BAT_P_MIN = -1.6 * 10**3 * unit

# NOTE: We need this assumption to hold for the implemented HIL communication to
# function properly. Asymmetric nominal powers are not covered at the moment.
HIL_BAT_P_MAX = -1 * HIL_BAT_P_MIN

# COM point parameters for each device on the HIL
# P_READ and P_SET are the com points for reading power values and setting power outputs
# SOC_READ is the com point for reading battery SOCs
# Note that these are 0-indexed (they are the indices in the python com_object list)
# so they are offset by -1 from the info object addresses in the HIL
L1_P_READ = 0
L1_P_SET = 0

L2_P_READ = 1
L2_P_SET = 1

B1_P_READ = 2
B1_SOC_READ = 4
B1_P_SET = 2

B2_P_READ = 3
B2_SOC_READ = 5
B2_P_SET = 3

F1_P_READ = 6
F1_P_SET = 4

F2_P_READ = 7
F2_P_SET = 5


def get_hil_device_specs(c_load, c_fuel, c_bat):
    #------------------------------
    # Make the device objects.
    #------------------------------
    l1 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L1_P_READ, L1_P_SET), c_load)
    l2 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L2_P_READ, L2_P_SET), c_load)
    b1 = IdealDevice(IdealBatteryState(HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX, B1_P_READ, B1_SOC_READ, B1_P_SET), c_bat)
    b2 = IdealDevice(IdealBatteryState(HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX, B2_P_READ, B2_SOC_READ, B2_P_SET), c_bat)
    f1 = IdealDevice(IdealFuelCellState(HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV, F1_P_READ, F1_P_SET), c_fuel)
    f2 = IdealDevice(IdealFuelCellState(HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV, F2_P_READ, F2_P_SET), c_fuel)
    return [l1, l2,  b1, b2, f1, f2]
    #return [l1, b1, f1]


def get_hil_scenarios():
    #-----------------------------------
    # dummy scenario, 100% packet loss rates between agents
    #-----------------------------------
    c_load = 0.005
    c_other = 0.007
    c_dev = 0.1

    target = [0.5 * x * unit for x in [0, 0, 0, 60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    c_dev = 10
    max_rel_rand = 0.0
    devices = get_hil_device_specs(c_load, c_other, c_other)

    p0 = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))

    # Adjacency matrix of the scenario. adj[i][j] corresponds to the edge between node i and j in the topology.
    # Only the top half of the matrix is considered because the topology graph is undirected.
    # Agents may not be their own neighbors.
    #
    # The value of adj[i][j] denotes the package loss probability of the edge between 0 and 1.
    # If adj[i][j] = -1, then no edge exists between i,j.
    # Here: we have a fully connected topology with 100% package loss rate on all edges.
    adj0 = [
        [0, 1, 1, 1, 1, 1],
        [0, 0, 1, 1, 1, 1],
        [0, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0]
    ]
    # device i will stop changing power output after this time step
    # -1 means its never stopped
    d_fail_time0 = [-1, -1, -1, -1, -1, -1]

    # drop rate for hil device state requests
    hil_drop_rate0 = [0, 0, 0, 0, 0, 0]

    # controller i will stop working after this time step
    # -1 means its never stopped
    c_fail_time0 = [-1, -1, -1, -1, -1, -1]

    s0 = (STEP_TIME_S, adj0, p0, d_fail_time0, hil_drop_rate0, c_fail_time0)

    #-----------------------------------
    # dummy scenario, no losses
    #-----------------------------------
    c_load = 0.005
    c_other = 0.007
    c_dev = 0.1

    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    c_dev = 10
    max_rel_rand = 0.1
    devices = get_hil_device_specs(c_load, c_other, c_other)

    p1 = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))


    adj1 = [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0]
    ]
    """
    adj1 = [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]
    """
    d_fail_time1 = [-1, -1, -1, -1, -1, -1]
    #d_fail_time1 = [-1, -1, -1]
    hil_drop_rate1 = [-1, -1, -1, -1, -1, -1]
    #hil_drop_rate1 = [-1, -1, -1]
    c_fail_time1 = [-1, -1, -1, -1, -1, -1]
    #c_fail_time1 = [-1, -1, -1]

    s1 = (STEP_TIME_S, adj1, p1, d_fail_time1, hil_drop_rate1, c_fail_time1)

    #-----------------------------------
    # circle topology with some losses
    #-----------------------------------
    c_load = 0.005
    c_other = 0.007
    c_dev = 0.1

    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    c_dev = 10
    max_rel_rand = 0.0
    devices = get_hil_device_specs(c_load, c_other, c_other)

    p2 = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))

    dr = 0.1
    adj2 = [
        [0, dr, -1, -1, -1, dr],
        [0, 0, dr, -1, -1, -1],
        [0, 0, 0, dr, -1, -1],
        [0, 0, 0, 0, dr, -1],
        [0, 0, 0, 0, 0, dr],
        [0, 0, 0, 0, 0, 0],
    ]

    d_fail_time2 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate2 = [-1, -1, -1, -1, -1, -1]
    c_fail_time2 = [-1, -1, -1, -1, -1, -1]

    s2 = (STEP_TIME_S, adj2, p2, d_fail_time2, hil_drop_rate2, c_fail_time2)

    #-----------------------------------
    # circle topology with major losses
    #-----------------------------------
    c_load = 0.005
    c_other = 0.007
    c_dev = 0.1

    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    c_dev = 10
    max_rel_rand = 0.0
    devices = get_hil_device_specs(c_load, c_other, c_other)

    p3 = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))

    dr = 0.7
    adj3 = [
        [0, dr, -1, -1, -1, dr],
        [0, 0, dr, -1, -1, -1],
        [0, 0, 0, dr, -1, -1],
        [0, 0, 0, 0, dr, -1],
        [0, 0, 0, 0, 0, dr],
        [0, 0, 0, 0, 0, 0],
    ]

    d_fail_time3 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate3 = [-1, -1, -1, -1, -1, -1]
    c_fail_time3 = [-1, -1, -1, -1, -1, -1]

    s3 = (STEP_TIME_S, adj3, p3, d_fail_time3, hil_drop_rate3, c_fail_time3)

    return [s0, s1, s2, s3]