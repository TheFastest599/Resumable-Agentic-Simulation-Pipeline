"""Conway's Game of Life cellular automaton."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 100))
    steps: int = int(payload.get("steps", 200))
    initial_density: float = float(payload.get("initial_density", 0.3))
    pattern: str = payload.get("pattern", "random")  # "random", "glider", "blinker"

    rng = np.random.default_rng()

    if pattern == "glider":
        grid = np.zeros((grid_size, grid_size), dtype=bool)
        glider = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
        for r, c in glider:
            grid[r + 2, c + 2] = True
    elif pattern == "blinker":
        grid = np.zeros((grid_size, grid_size), dtype=bool)
        mid = grid_size // 2
        grid[mid, mid - 1:mid + 2] = True
    else:
        grid = rng.random((grid_size, grid_size)) < initial_density

    population_hist = [int(grid.sum())]
    report_every = max(1, steps // 100)

    for step in range(steps):
        # Count live neighbours (sum of 8 shifts)
        neighbours = sum(
            np.roll(np.roll(grid, dr, 0), dc, 1)
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr, dc) != (0, 0)
        )
        birth = (~grid) & (neighbours == 3)
        survive = grid & ((neighbours == 2) | (neighbours == 3))
        grid = birth | survive
        population_hist.append(int(grid.sum()))

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    ds = max(1, steps // 200)
    return {
        "grid_size": grid_size,
        "steps": steps,
        "pattern": pattern,
        "initial_population": population_hist[0],
        "final_population": population_hist[-1],
        "max_population": int(max(population_hist)),
        "min_population": int(min(population_hist)),
        "population_history": population_hist[::ds],
        "final_grid": grid.astype(int).tolist(),
    }
