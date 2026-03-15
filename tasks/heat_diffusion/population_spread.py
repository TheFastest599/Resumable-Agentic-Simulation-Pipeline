"""Population diffusion-limited spread on a 2D grid (Fisher-KPP)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 60))
    steps: int = int(payload.get("steps", 200))
    D: float = float(payload.get("diffusion_coeff", 0.05))
    growth_rate: float = float(payload.get("growth_rate", 0.01))
    carrying_capacity: float = float(payload.get("carrying_capacity", 1.0))
    dt: float = 0.5
    dx: float = 1.0

    if D * dt / dx ** 2 > 0.25:
        D = 0.25 * dx ** 2 / dt

    P = np.zeros((grid_size, grid_size))
    cx, cy = grid_size // 2, grid_size // 2
    P[cx - 2:cx + 2, cy - 2:cy + 2] = 0.1

    report_every = max(1, steps // 100)
    for step in range(steps):
        lap = (
            np.roll(P, 1, 0) + np.roll(P, -1, 0) +
            np.roll(P, 1, 1) + np.roll(P, -1, 1) - 4 * P
        ) / dx ** 2
        P = P + dt * (D * lap + growth_rate * P * (1 - P / carrying_capacity))
        P = np.clip(P, 0, carrying_capacity)

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "grid_size": grid_size,
        "steps": steps,
        "total_population": float(P.sum()),
        "occupied_cells": int((P > 0.05).sum()),
        "max_density": float(P.max()),
        "final_grid": P.tolist(),
    }
