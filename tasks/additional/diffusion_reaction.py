"""Gray-Scott diffusion-reaction system in 2D."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 80))
    steps: int = int(payload.get("steps", 2000))
    Du: float = float(payload.get("Du", 0.16))    # diffusion rate of U
    Dv: float = float(payload.get("Dv", 0.08))    # diffusion rate of V
    f: float = float(payload.get("f", 0.035))      # feed rate
    k: float = float(payload.get("k", 0.065))      # kill rate
    dt: float = 1.0

    U = np.ones((grid_size, grid_size))
    V = np.zeros((grid_size, grid_size))
    # Seed centre
    c = grid_size // 2
    r = grid_size // 8
    U[c - r:c + r, c - r:c + r] = 0.5
    V[c - r:c + r, c - r:c + r] = 0.25
    rng = np.random.default_rng()
    U += 0.05 * rng.random((grid_size, grid_size))
    V += 0.05 * rng.random((grid_size, grid_size))

    def laplacian(Z):
        return (
            np.roll(Z, 1, 0) + np.roll(Z, -1, 0) +
            np.roll(Z, 1, 1) + np.roll(Z, -1, 1) - 4 * Z
        )

    report_every = max(1, steps // 100)
    for step in range(steps):
        uvv = U * V * V
        U += dt * (Du * laplacian(U) - uvv + f * (1 - U))
        V += dt * (Dv * laplacian(V) + uvv - (f + k) * V)
        U = np.clip(U, 0, 1)
        V = np.clip(V, 0, 1)

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "grid_size": grid_size,
        "steps": steps,
        "f": f,
        "k": k,
        "mean_U": float(U.mean()),
        "mean_V": float(V.mean()),
        "pattern_variance_V": float(V.var()),
        "final_U_grid": U.tolist(),
        "final_V_grid": V.tolist(),
    }
