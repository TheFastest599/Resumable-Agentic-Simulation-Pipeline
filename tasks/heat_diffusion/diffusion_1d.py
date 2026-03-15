"""1D heat diffusion (explicit finite differences)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n: int = int(payload.get("n_points", 100))
    steps: int = int(payload.get("steps", 1000))
    alpha: float = float(payload.get("diffusion_coeff", 0.1))
    dt: float = 0.1
    dx: float = 1.0

    if alpha * dt / dx ** 2 > 0.5:
        alpha = 0.5 * dx ** 2 / dt

    T = np.zeros(n)
    T[n // 2] = 100.0

    report_every = max(1, steps // 100)
    for step in range(steps):
        T_new = T.copy()
        T_new[1:-1] = T[1:-1] + alpha * dt / dx ** 2 * (T[2:] - 2 * T[1:-1] + T[:-2])
        T_new[0] = T_new[-1] = 0.0
        T = T_new
        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "n_points": n,
        "steps": steps,
        "diffusion_coeff": alpha,
        "max_temp": float(T.max()),
        "mean_temp": float(T.mean()),
        "final_profile": T.tolist(),
    }
