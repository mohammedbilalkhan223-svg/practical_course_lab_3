from src.sim_environment.optimization_problem import *
from copy import deepcopy
import sys

# ============================================================
# Device backend selection
# ============================================================
if len(sys.argv) > 2 and sys.argv[2] == "ideal":
    from src.sim_environment.devices.ideal import *
else:
    from src.sim_environment.devices.hil import *

# ============================================================
# Global params
# ============================================================
HIL_IP = "10.51.6.211"
STEP_TIME_S = 15
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


# ============================================================
# Device specs
# ============================================================
def get_hil_device_specs(c_load, c_fuel, c_bat):
    l1 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L1_P_READ, L1_P_SET), c_load)
    l2 = IdealDevice(IdealLoadState(HIL_LOAD_P_MIN, L2_P_READ, L2_P_SET), c_load)
    b1 = IdealDevice(
        IdealBatteryState(
            HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX,
            B1_P_READ, B1_SOC_READ, B1_P_SET
        ),
        c_bat
    )
    b2 = IdealDevice(
        IdealBatteryState(
            HIL_BAT_SIZE, HIL_BAT_SOC_INIT, HIL_BAT_P_MIN, HIL_BAT_P_MAX,
            B2_P_READ, B2_SOC_READ, B2_P_SET
        ),
        c_bat
    )
    f1 = IdealDevice(
        IdealFuelCellState(
            HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV,
            F1_P_READ, F1_P_SET
        ),
        c_fuel
    )
    f2 = IdealDevice(
        IdealFuelCellState(
            HIL_FUEL_AMOUNT, HIL_FUEL_P_MAX, HIL_FUEL_CHANGE_MAX, HIL_FUEL_P_PREV,
            F2_P_READ, F2_P_SET
        ),
        c_fuel
    )
    return [l1, l2, b1, b2, f1, f2]


def _base_problem_and_target():
    # keep your original weights
    c_load  = 0.005
    c_other = 0.007
    c_dev   = 10
    max_rel_rand = 0.1

    # keep your original target
    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    devices = get_hil_device_specs(c_load, c_other, c_other)
    return deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))


def _ring_topology(drop_rate: float):
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


# ============================================================
# Figure 2 topology helpers
# ============================================================
def make_fig2_adj(drop_rate: float, device_failure: list):
    """
    Figure-2 communication topology between controller agents (a1..a6).
    Indices: a1=0, a2=1, a3=2, a4=3, a5=4, a6=5

    Edges in Figure 2:
      a1-a2, a1-a3, a2-a3,
      a2-a4, a2-a5, a3-a5,
      a4-a6, a5-a6
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

    edges = [
        (0, 1), (0, 2), (1, 2),
        (1, 3), (1, 4),
        (2, 4),
        (3, 5), (4, 5),
    ]

    default_drop_rate = 0.3
    for edge in edges:
        drop_rate = drop_rates.get(edge, default_drop_rate)
        adj[edge[0]][edge[1]] = float(drop_rate)

    return adj


# ============================================================
# SCENARIOS
# ============================================================
def get_hil_scenarios():
    scenarios = []

    # -----------------------------------
    # s0: dummy 100% packet loss
    # -----------------------------------
    c_load = 0.005
    c_other = 0.007
    c_dev = 10
    max_rel_rand = 0.0
    target0 = [0.5 * x * unit for x in [0, 0, 0, 60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    devices0 = get_hil_device_specs(c_load, c_other, c_other)
    p0 = deepcopy(SchedulingProblem(target0, devices0, c_dev, max_rel_rand))

    adj0 = [
        [0, 1, 1, 1, 1, 1],
        [0, 0, 1, 1, 1, 1],
        [0, 0, 0, 1, 1, 1],
        [0, 0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0],
    ]
    scenarios.append((STEP_TIME_S, adj0, p0, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # -----------------------------------
    # s1: fully connected, no losses
    # -----------------------------------
    p1 = _base_problem_and_target()
    adj1 = [[0, 0, 0, 0, 0, 0] for _ in range(6)]
    scenarios.append((STEP_TIME_S, adj1, p1, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # -----------------------------------
    # s2: ring with small losses (0.1)
    # -----------------------------------
    p2 = _base_problem_and_target()
    adj2 = _ring_topology(0.1)
    scenarios.append((STEP_TIME_S, adj2, p2, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # -----------------------------------
    # s3: ring with major losses (0.7)
    # -----------------------------------
    p3 = _base_problem_and_target()
    adj3 = _ring_topology(0.7)
    scenarios.append((STEP_TIME_S, adj3, p3, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # -----------------------------------
    # s4: ring, no losses
    # -----------------------------------
    p4 = _base_problem_and_target()
    adj4 = _ring_topology(0.0)
    scenarios.append((STEP_TIME_S, adj4, p4, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # -----------------------------------
    # s5: fully connected, no losses
    # -----------------------------------
    p5 = _base_problem_and_target()
    adj5 = [[0, 0, 0, 0, 0, 0] for _ in range(6)]
    scenarios.append((STEP_TIME_S, adj5, p5, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # -----------------------------------
    # s6: star, no losses (node 3 hub)
    # -----------------------------------
    p6 = _base_problem_and_target()
    adj6 = [
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
        [0, 0, 0, -1, 0, 0],
        [-1, -1, -1, 0, -1, -1],
        [-1, -1, -1, 0, -1, -1],
    ]
    scenarios.append((STEP_TIME_S, adj6, p6, [-1]*6, _no_hil_drops(), _no_controller_failures()))

    # =====================================================================
    # s7: FIGURE 2 BENCHMARK (no drops, no failures)  <-- NEW
    # =====================================================================
    p7 = _base_problem_and_target()
    fig2_benchmark_adj = make_fig2_adj(0.0, [-1]*6)
    d_fail_time7 = [-1]*6
    hil_drop_rate7 = _no_hil_drops()
    c_fail_time7 = _no_controller_failures()
    scenarios.append((STEP_TIME_S, fig2_benchmark_adj, p7, d_fail_time7, hil_drop_rate7, c_fail_time7))

    # =====================================================================
    # Task 4 — Figure 2 (packet drops between controller agents)
    # keep your varied_drop_rates logic exactly
    # =====================================================================
    c_load  = 0.005
    c_other = 0.007
    c_dev   = 10
    max_rel_rand = 0.1
    target = [0.9 * x * unit for x in [60, 40, 20, 0, -20, -40, -60, -80, -100, 0, 0, 0, 0]]
    devices = get_hil_device_specs(c_load, c_other, c_other)

    d_fail_time = [-1]*6
    hil_drop_rate = [-1]*6

    controller_failure = [7, -1, 5, -1, 5, -1]  # keep your manual switching
    c_fail_time = controller_failure

    def make_fig2_drop_scenario():
        varied_drop_rates = {
            (0, 1): 0.05,
            (1, 2): 0.1,
            (1, 4): 0.1,
            (2, 4): 0.9,
        }
        problem = deepcopy(SchedulingProblem(target, devices, c_dev, max_rel_rand))
        adjacency = topology_with_varied_droprates(varied_drop_rates)
        return (STEP_TIME_S, adjacency, problem, d_fail_time, hil_drop_rate, c_fail_time)

    s8 = make_fig2_drop_scenario()
    s9 = make_fig2_drop_scenario()
    s10 = make_fig2_drop_scenario()
    s11 = make_fig2_drop_scenario()
    scenarios.extend([s8, s9, s10, s11])

    # =====================================================================
    # Task 9 — Device Failures (NO packet drops) - FIGURE 2
    # =====================================================================
    base_adj = make_fig2_adj(0.0, [-1]*6)
    base_hil_drop = _no_hil_drops()
    base_c_fail = _no_controller_failures()

    EARLY_T = 1
    MID_T = 6

    # s12: Battery failure (both batteries) early
    p12 = _base_problem_and_target()
    d_fail_time12 = [-1, -1, EARLY_T, EARLY_T, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p12, d_fail_time12, base_hil_drop, base_c_fail))

    # s13: Battery failure (both batteries) mid
    p13 = _base_problem_and_target()
    d_fail_time13 = [-1, -1, MID_T, MID_T, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p13, d_fail_time13, base_hil_drop, base_c_fail))

    # s14: Load failure (both loads) early
    p14 = _base_problem_and_target()
    d_fail_time14 = [EARLY_T, EARLY_T, -1, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p14, d_fail_time14, base_hil_drop, base_c_fail))

    # s15: Load failure (both loads) mid
    p15 = _base_problem_and_target()
    d_fail_time15 = [MID_T, MID_T, -1, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p15, d_fail_time15, base_hil_drop, base_c_fail))

    # s16: Fuel failure (both fuel cells) early
    p16 = _base_problem_and_target()
    d_fail_time16 = [-1, -1, -1, -1, EARLY_T, EARLY_T]
    scenarios.append((STEP_TIME_S, base_adj, p16, d_fail_time16, base_hil_drop, base_c_fail))

    # s17: Fuel failure (both fuel cells) mid
    p17 = _base_problem_and_target()
    d_fail_time17 = [-1, -1, -1, -1, MID_T, MID_T]
    scenarios.append((STEP_TIME_S, base_adj, p17, d_fail_time17, base_hil_drop, base_c_fail))

    # =====================================================================
    # Task 10 — Controller Failures (NO packet drops) - FIGURE 2
    # =====================================================================
    base_hil_drop = _no_hil_drops()
    base_d_fail = [-1]*6

    # s18: controller 0 fails early
    p18 = _base_problem_and_target()
    c_fail_time18 = [EARLY_T, -1, -1, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p18, base_d_fail, base_hil_drop, c_fail_time18))

    # s19: controller 0 fails mid-run
    p19 = _base_problem_and_target()
    c_fail_time19 = [MID_T, -1, -1, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p19, base_d_fail, base_hil_drop, c_fail_time19))

    # s20: controller 2 fails early
    p20 = _base_problem_and_target()
    c_fail_time20 = [-1, -1, EARLY_T, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p20, base_d_fail, base_hil_drop, c_fail_time20))

    # s21: controller 2 fails mid-run
    p21 = _base_problem_and_target()
    c_fail_time21 = [-1, -1, MID_T, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p21, base_d_fail, base_hil_drop, c_fail_time21))

    # s22: two neighboring controllers fail
    p22 = _base_problem_and_target()
    c_fail_time22 = [-1, 1, 3, -1, -1, -1]
    scenarios.append((STEP_TIME_S, base_adj, p22, base_d_fail, base_hil_drop, c_fail_time22))

    # =====================================================================
    # Task 8 — Controller Agent Failures (NO packet drops) - FIGURE 2
    # =====================================================================
    def cfail(*failed_ids, t):
        arr = [-1]*6
        for i in failed_ids:
            arr[i] = t
        return arr

    # s23/s24: controller 1 fails early/mid
    p23 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p23, base_d_fail, base_hil_drop, cfail(1, t=EARLY_T)))
    p24 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p24, base_d_fail, base_hil_drop, cfail(1, t=MID_T)))

    # s25/s26: controller 5 fails early/mid
    p25 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p25, base_d_fail, base_hil_drop, cfail(5, t=EARLY_T)))
    p26 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p26, base_d_fail, base_hil_drop, cfail(5, t=MID_T)))

    # s27/s28: controllers 4 and 5 fail early/mid
    p27 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p27, base_d_fail, base_hil_drop, cfail(4, 5, t=EARLY_T)))
    p28 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p28, base_d_fail, base_hil_drop, cfail(4, 5, t=MID_T)))

    # s29/s30: controllers 3 and 5 fail early/mid
    p29 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p29, base_d_fail, base_hil_drop, cfail(3, 5, t=EARLY_T)))
    p30 = _base_problem_and_target()
    scenarios.append((STEP_TIME_S, base_adj, p30, base_d_fail, base_hil_drop, cfail(3, 5, t=MID_T)))

    return scenarios

