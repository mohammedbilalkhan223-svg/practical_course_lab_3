from src.sim_environment.optimization_problem import *
from copy import deepcopy
import sys

# ------------------------------
# Device backend selection
# ------------------------------
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
    STEP_TIME_S = 20
else:
    from src.sim_environment.devices.hil import *
    STEP_TIME_S = 12

# ------------------------------
# Global params
# ------------------------------
HIL_IP = "10.51.6.211"
STEP_TIME_S = 1
SCENARIO_NR = 0
RNG_SEED = 1

# ------------------------------
# HIL device specs (hardware)
# ------------------------------
unit = kW = 10**3

HIL_LOAD_P_MIN = -1 * 450 * unit

HIL_FUEL_AMOUNT = 100000 * unit
HIL_FUEL_P_MAX = 500 * unit
HIL_FUEL_CHANGE_MAX = 10 * unit
HIL_FUEL_P_PREV = None

HIL_BAT_SIZE = 1000 * 500
HIL_BAT_SOC_INIT = 0.5
HIL_BAT_P_MIN = -1.6 * 10**3 * unit
HIL_BAT_P_MAX = -1 * HIL_BAT_P_MIN  # symmetric assumption

# ------------------------------
# Com point mapping (0-indexed)
# ------------------------------
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
    l1 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L1_P_READ, L1_P_SET), c_load)
    l2 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L2_P_READ, L2_P_SET), c_load)
    b1 = IdealDevice(
        IdealBatteryState(
            HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX, B1_P_READ, B1_SOC_READ, B1_P_SET
        ),
        c_bat,
    )
    b2 = IdealDevice(
        IdealBatteryState(
            HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX, B2_P_READ, B2_SOC_READ, B2_P_SET
        ),
        c_bat,
    )
    f1 = IdealDevice(
        IdealFuelCellState(
            HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV, F1_P_READ, F1_P_SET
        ),
        c_fuel,
    )
    f2 = IdealDevice(
        IdealFuelCellState(
            HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV, F2_P_READ, F2_P_SET
        ),
        c_fuel,
    )
    return [l1, l2, b1, b2, f1, f2]


def _base_problem_and_target():
    # cost params (same as your Task3 scenarios)
    c_load = 0.005
    c_other = 0.007
    c_dev = 10
    max_rel_rand = 0.1

    # target used in your ring / fully / star scenarios
    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]

    devices = get_hil_device_specs(c_load, c_other, c_other)
    problem = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))
    return problem


def _ring_topology(drop_rate: float):
    # Ring (circle) topology: edges are (0-1-2-3-4-5-0)
    dr = drop_rate
    return [
        [0, dr, -1, -1, -1, dr],
        [0, 0, dr, -1, -1, -1],
        [0, 0, 0, dr, -1, -1],
        [0, 0, 0, 0, dr, -1],
        [0, 0, 0, 0, 0, dr],
        [0, 0, 0, 0, 0, 0],
    ]


def _no_hil_drops():
    # 0 means never drop observer->device state replies
    return [0, 0, 0, 0, 0, 0]


def _no_controller_failures():
    return [-1, -1, -1, -1, -1, -1]


def get_hil_scenarios():
    scenarios = []

    # -----------------------------------
    # s0: dummy 100% packet loss
    # -----------------------------------
    c_load = 0.005
    c_other = 0.007
    c_dev = 10
    max_rel_rand = 0.0
    target = [0.5 * x * unit for x in [0, 0, 0, 60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    devices = get_hil_device_specs(c_load, c_other, c_other)
    p0 = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))

    adj0 = [
        [0, 1, 1, 1, 1, 1],
        [0, 0, 1, 1, 1, 1],
        [0, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0],
    ]
    d_fail_time0 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate0 = _no_hil_drops()
    c_fail_time0 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj0, p0, d_fail_time0, hil_drop_rate0, c_fail_time0))

    # -----------------------------------
    # s1: fully connected, no losses (but adjacency all zeros means "all edges present with 0 loss" in your code)
    # -----------------------------------
    p1 = _base_problem_and_target()
    adj1 = [[0, 0, 0, 0, 0, 0] for _ in range(6)]
    d_fail_time1 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate1 = _no_hil_drops()
    c_fail_time1 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj1, p1, d_fail_time1, hil_drop_rate1, c_fail_time1))

    # -----------------------------------
    # s2: ring with small losses (0.1)
    # -----------------------------------
    p2 = _base_problem_and_target()
    adj2 = _ring_topology(0.1)
    d_fail_time2 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate2 = _no_hil_drops()
    c_fail_time2 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj2, p2, d_fail_time2, hil_drop_rate2, c_fail_time2))

    # -----------------------------------
    # s3: ring with major losses (0.7)
    # -----------------------------------
    p3 = _base_problem_and_target()
    adj3 = _ring_topology(0.7)
    d_fail_time3 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate3 = _no_hil_drops()
    c_fail_time3 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj3, p3, d_fail_time3, hil_drop_rate3, c_fail_time3))

    # -----------------------------------
    # Task 3 baseline scenarios (your existing s4..s6)
    # -----------------------------------
    # s4: ring, no losses
    p4 = _base_problem_and_target()
    adj4 = _ring_topology(0.0)
    d_fail_time4 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate4 = _no_hil_drops()
    c_fail_time4 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj4, p4, d_fail_time4, hil_drop_rate4, c_fail_time4))

    # s5: fully connected, no losses
    p5 = _base_problem_and_target()
    adj5 = [[0, 0, 0, 0, 0, 0] for _ in range(6)]
    d_fail_time5 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate5 = _no_hil_drops()
    c_fail_time5 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj5, p5, d_fail_time5, hil_drop_rate5, c_fail_time5))

    # s6: star, no losses (node 3 is hub in your original)
    p6 = _base_problem_and_target()
    adj6 = [
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
        [0, 0, 0, -1, 0, 0],
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
    ]
    d_fail_time6 = [-1, -1, -1, -1, -1, -1]
    hil_drop_rate6 = _no_hil_drops()
    c_fail_time6 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, adj6, p6, d_fail_time6, hil_drop_rate6, c_fail_time6))

    # =====================================================================
    # Task 9 — Device Failures (no packet drops)
    # Topology: Figure 2 (use ring no-loss baseline here)
    # Devices: 0=L1, 1=L2, 2=B1, 3=B2, 4=F1, 5=F2
    # d_fail_time[i] == timestep when device i fails (holds last power)
    # =====================================================================

    base_adj = _ring_topology(0.0)
    base_hil_drop = _no_hil_drops()
    base_c_fail = _no_controller_failures()

    # Choose two failure timings to analyze timing impact:
    # - early: t=1 (almost from start)
    # - mid:   t=6 (mid of your 13-step target)
    EARLY_T = 1
    MID_T = 6

    # --- s7: Battery failure (both batteries) early ---
    p7 = _base_problem_and_target()
    d_fail_time7 = [-1, -1, EARLY_T, EARLY_T, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p7, d_fail_time7, base_hil_drop, base_c_fail))

    # --- s8: Battery failure (both batteries) mid ---
    p8 = _base_problem_and_target()
    d_fail_time8 = [-1, -1, MID_T, MID_T, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p8, d_fail_time8, base_hil_drop, base_c_fail))

    # --- s9: Load failure (both loads) early ---
    p9 = _base_problem_and_target()
    d_fail_time9 = [EARLY_T, EARLY_T, -1, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p9, d_fail_time9, base_hil_drop, base_c_fail))

    # --- s10: Load failure (both loads) mid ---
    p10 = _base_problem_and_target()
    d_fail_time10 = [MID_T, MID_T, -1, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p10, d_fail_time10, base_hil_drop, base_c_fail))

    # --- s11: Fuel failure (both fuel cells) early ---
    p11 = _base_problem_and_target()
    d_fail_time11 = [-1, -1, -1, -1, EARLY_T, EARLY_T]
    scenarios.append((STEP_TIME_S, base_adj, p11, d_fail_time11, base_hil_drop, base_c_fail))

    # --- s12: Fuel failure (both fuel cells) mid ---
    p12 = _base_problem_and_target()
    d_fail_time12 = [-1, -1, -1, -1, MID_T, MID_T]
    scenarios.append((STEP_TIME_S, base_adj, p12, d_fail_time12, base_hil_drop, base_c_fail))

    return scenarios
