"""Forest fire / percolation cellular automaton simulation."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 100))
    p_tree: float = float(payload.get("p_tree", 0.6))       # prob cell has a tree
    p_ignite: float = float(payload.get("p_ignite", 0.001)) # spontaneous ignition
    p_grow: float = float(payload.get("p_grow", 0.005))     # tree regrowth
    steps: int = int(payload.get("steps", 300))

    rng = np.random.default_rng()

    # States: 0=empty, 1=tree, 2=burning
    grid = (rng.random((grid_size, grid_size)) < p_tree).astype(np.int8)
    # Ignite a few seed cells
    grid[grid_size // 2, grid_size // 2] = 2

    burned_per_step = []
    tree_count_hist = []

    report_every = max(1, steps // 100)
    for step in range(steps):
        new_grid = grid.copy()

        burning = (grid == 2)
        trees = (grid == 1)
        empty = (grid == 0)

        # Burning cells turn to empty
        new_grid[burning] = 0

        # Trees adjacent to burning cells catch fire
        spread = (
            np.roll(burning, 1, 0) | np.roll(burning, -1, 0) |
            np.roll(burning, 1, 1) | np.roll(burning, -1, 1)
        )
        new_grid[trees & spread] = 2

        # Spontaneous ignition
        ignite_mask = trees & (rng.random((grid_size, grid_size)) < p_ignite)
        new_grid[ignite_mask] = 2

        # Regrowth
        grow_mask = empty & (rng.random((grid_size, grid_size)) < p_grow)
        new_grid[grow_mask] = 1

        grid = new_grid
        burned_per_step.append(int(burning.sum()))
        tree_count_hist.append(int((grid == 1).sum()))

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "grid_size": grid_size,
        "steps": steps,
        "p_tree": p_tree,
        "total_burned": int(sum(burned_per_step)),
        "peak_burning": int(max(burned_per_step)) if burned_per_step else 0,
        "final_tree_count": int((grid == 1).sum()),
        "final_burning": int((grid == 2).sum()),
        "burned_per_step": burned_per_step[::max(1, steps // 200)],
    }
