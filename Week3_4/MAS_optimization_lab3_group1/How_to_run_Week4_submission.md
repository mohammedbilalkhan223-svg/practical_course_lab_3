# Agent Template & Scenario Testing Notes
Use the run_hil file to run the different combinations. They are already included in the comments.
## Overview
For **Task 4**, use **decentral_agent_rescheduling** as agent template and the **hil_scenario_Fig2** with scenario 0 (DR 0,0), 1 (DR 0,1), 2 (DR 0,3), 3 (DR 0,6).
For **Task 5**, use **decentral_agent with hil_scenarios_Task5 (creates requested topologies, Scenario 0-8)
For **Task 6/7**, use *decentral_agent_task6* with scenarios hil_scenario_Fig2 and hil_scenarios_Task5 (for varying droprates within figure 2, use topology_with_varied_droprates for adjacency in line 177 of scenario)
For **Tasks 8 and 9**, use **`decentral_agent_rescheduling.py`** as the **agent template**.

For **Task 10**, there are **two setup options** depending on how you want the setpoint to behave after an event:

1. **`decentral_agent_rescheduling_Task10.py`**  
   - After the control/action window, the **setpoint returns back to `0`**.

2. **`decentral_agent_rescheduling_Task10_freez.py`**  
   - After the control/action window, the **setpoint freezes** and **returns back to the last set value** (i.e., holds the last point).

---

## Scenario Definitions & Testing
All scenario IDs / numbers required for testing **Tasks 8 to 10** are defined inside:

- **`hil_scenarios_Tasks.py`**

This file includes:

- The complete set of **scenario numbers for Tasks 8–10**
- The **benchmark scenario** used for reproducing/validating **Figure 2**

---

## Outputs & Plots
All generated plots are stored and kept as reference for:

- Comparing task behavior across scenarios
- Documenting observations and deviations
- Cross-checking against the benchmark (Figure 2)

These plots should be preserved as the baseline evidence for the results and discussion in the report.

