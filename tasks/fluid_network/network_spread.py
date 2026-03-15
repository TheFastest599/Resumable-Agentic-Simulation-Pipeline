"""Network spread simulation (SIR on a random graph)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n_nodes: int = int(payload.get("n_nodes", 500))
    avg_degree: float = float(payload.get("avg_degree", 6.0))
    infection_prob: float = float(payload.get("infection_prob", 0.3))
    recovery_prob: float = float(payload.get("recovery_prob", 0.1))
    steps: int = int(payload.get("steps", 100))
    initial_infected: int = int(payload.get("initial_infected", 5))

    rng = np.random.default_rng()

    # Erdos-Renyi adjacency (sparse representation via adjacency list)
    p_edge = avg_degree / (n_nodes - 1)
    adj = [[] for _ in range(n_nodes)]
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if rng.random() < p_edge:
                adj[i].append(j)
                adj[j].append(i)

    # States: 0=S, 1=I, 2=R
    state = np.zeros(n_nodes, dtype=int)
    seeds = rng.choice(n_nodes, size=min(initial_infected, n_nodes), replace=False)
    state[seeds] = 1

    S_hist, I_hist, R_hist = [], [], []

    for step in range(steps):
        new_state = state.copy()
        for node in range(n_nodes):
            if state[node] == 1:  # infected
                # Try to infect susceptible neighbours
                for nb in adj[node]:
                    if state[nb] == 0 and rng.random() < infection_prob:
                        new_state[nb] = 1
                # Recover
                if rng.random() < recovery_prob:
                    new_state[node] = 2
        state = new_state
        S_hist.append(int((state == 0).sum()))
        I_hist.append(int((state == 1).sum()))
        R_hist.append(int((state == 2).sum()))
        progress_cb((step + 1) / steps)

    return {
        "n_nodes": n_nodes,
        "steps": steps,
        "peak_infected": int(max(I_hist)),
        "final_susceptible": S_hist[-1],
        "final_infected": I_hist[-1],
        "final_recovered": R_hist[-1],
        "S_history": S_hist,
        "I_history": I_hist,
        "R_history": R_hist,
    }
