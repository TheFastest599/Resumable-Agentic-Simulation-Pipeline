"""2D heat diffusion simulation using explicit finite differences."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 50))
    steps: int = int(payload.get("steps", 500))
    alpha: float = float(payload.get("diffusion_coeff", 0.1))
    dt: float = 0.1
    dx: float = 1.0

    if alpha * dt / dx ** 2 > 0.25:
        alpha = 0.25 * dx ** 2 / dt

    grid = np.zeros((grid_size, grid_size))
    cx, cy = grid_size // 2, grid_size // 2
    grid[cx - 2:cx + 2, cy - 2:cy + 2] = 100.0

    report_every = max(1, steps // 100)
    for step in range(steps):
        laplacian = (
            np.roll(grid, 1, axis=0) + np.roll(grid, -1, axis=0) +
            np.roll(grid, 1, axis=1) + np.roll(grid, -1, axis=1) - 4 * grid
        ) / dx ** 2
        grid = grid + alpha * dt * laplacian
        grid[0, :] = grid[-1, :] = grid[:, 0] = grid[:, -1] = 0.0

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "grid_size": grid_size,
        "steps": steps,
        "diffusion_coeff": alpha,
        "max_temp": float(grid.max()),
        "mean_temp": float(grid.mean()),
        "final_grid": grid.tolist(),
    }
