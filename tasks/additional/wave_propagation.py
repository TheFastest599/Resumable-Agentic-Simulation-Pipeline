"""1D/2D wave equation solved with explicit finite differences."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    dimensions: int = int(payload.get("dimensions", 1))
    grid_size: int = int(payload.get("grid_size", 100))
    steps: int = int(payload.get("steps", 500))
    c: float = float(payload.get("wave_speed", 1.0))
    dt: float = float(payload.get("dt", 0.1))
    dx: float = 1.0

    # CFL stability: c*dt/dx <= 1
    if c * dt / dx > 1.0:
        dt = 0.9 * dx / c

    report_every = max(1, steps // 100)

    if dimensions == 1:
        u_prev = np.zeros(grid_size)
        u_curr = np.zeros(grid_size)
        # Gaussian pulse initial displacement
        x = np.arange(grid_size)
        u_curr = np.exp(-((x - grid_size // 4) ** 2) / (2 * (grid_size // 20) ** 2))
        u_prev = u_curr.copy()

        r = (c * dt / dx) ** 2
        for step in range(steps):
            u_next = np.zeros(grid_size)
            u_next[1:-1] = (2 * u_curr[1:-1] - u_prev[1:-1]
                            + r * (u_curr[2:] - 2 * u_curr[1:-1] + u_curr[:-2]))
            u_prev, u_curr = u_curr, u_next
            if step % report_every == 0:
                progress_cb((step + 1) / steps)

        progress_cb(1.0)
        return {
            "dimensions": 1,
            "grid_size": grid_size,
            "steps": steps,
            "wave_speed": c,
            "max_amplitude": float(np.abs(u_curr).max()),
            "final_field": u_curr.tolist(),
        }

    else:  # 2D
        u_prev = np.zeros((grid_size, grid_size))
        u_curr = np.zeros((grid_size, grid_size))
        cx, cy = grid_size // 4, grid_size // 4
        sigma = grid_size // 20
        Y, X = np.mgrid[:grid_size, :grid_size]
        u_curr = np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * sigma ** 2))
        u_prev = u_curr.copy()

        r = (c * dt / dx) ** 2
        for step in range(steps):
            lap = (
                np.roll(u_curr, 1, 0) + np.roll(u_curr, -1, 0) +
                np.roll(u_curr, 1, 1) + np.roll(u_curr, -1, 1) -
                4 * u_curr
            )
            u_next = 2 * u_curr - u_prev + r * lap
            u_next[0, :] = u_next[-1, :] = u_next[:, 0] = u_next[:, -1] = 0.0
            u_prev, u_curr = u_curr, u_next
            if step % report_every == 0:
                progress_cb((step + 1) / steps)

        progress_cb(1.0)
        return {
            "dimensions": 2,
            "grid_size": grid_size,
            "steps": steps,
            "wave_speed": c,
            "max_amplitude": float(np.abs(u_curr).max()),
            "final_field": u_curr.tolist(),
        }
