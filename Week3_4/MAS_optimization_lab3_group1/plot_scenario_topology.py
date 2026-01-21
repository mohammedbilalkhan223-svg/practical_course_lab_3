from run_hil import adjacency_to_topology
from scenarios.hil_scenarios_Task5 import get_hil_scenarios
import networkx as nx
import sys
import matplotlib.pyplot as plt

def main():
    if len(sys.argv) < 2:
        print("Need to specify the scenario id to plot as cmd argument.")
        return

    scenario_nr = int(sys.argv[1])
    _, adjacency, _, _, _, _ = get_hil_scenarios()[scenario_nr]

    G = adjacency_to_topology(adjacency)

    # relabel nodes
    # [0, 1, 2, 3, 4, 5] => [L1, L2, B1, B2, F1, F2]
    mapping = {
        0: "L1",
        1: "L2",
        2: "B1",
        3: "B2",
        4: "F1",
        5: "F2"
    }
    H = nx.relabel_nodes(G, mapping)

    # get loss_rate as edge label
    edge_labels = {}
    for u,v in H.edges:
        edge_labels[(u,v)] = H.edges[u,v]["loss_rate"]


    pos = nx.spring_layout(H)
    nx.draw_networkx(H, pos, with_labels=True)
    nx.draw_networkx_edge_labels(H, pos, edge_labels=edge_labels)
    plt.show()


if __name__ == "__main__":
    main()