"""Chemical species diffusion in 2D."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 50))
    steps: int = int(payload.get("steps", 300))
    D: float = float(payload.get("diffusion_coeff", 0.1))
    dt: float = 0.1
    dx: float = 1.0

    if D * dt / dx ** 2 > 0.25:
        D = 0.25 * dx ** 2 / dt

    C = np.zeros((grid_size, grid_size))
    cx, cy = grid_size // 2, grid_size // 2
    C[cx - 3:cx + 3, cy - 3:cy + 3] = 1.0

    report_every = max(1, steps // 100)
    for step in range(steps):
        lap = (
            np.roll(C, 1, 0) + np.roll(C, -1, 0) +
            np.roll(C, 1, 1) + np.roll(C, -1, 1) - 4 * C
        ) / dx ** 2
        C = C + D * dt * lap
        C[0, :] = C[-1, :] = C[:, 0] = C[:, -1] = 0.0

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "grid_size": grid_size,
        "steps": steps,
        "diffusion_coeff": D,
        "max_concentration": float(C.max()),
        "total_mass": float(C.sum()),
        "final_grid": C.tolist(),
    }
