"""1D heat conduction with spatially varying thermal conductivity."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n: int = int(payload.get("n_points", 200))
    steps: int = int(payload.get("steps", 2000))
    dt: float = 0.01
    dx: float = 1.0
    profile: str = payload.get("conductivity_profile", "step")
    # Conductivity profiles
    x = np.linspace(0, n - 1, n)
    if profile == "step":
        kappa = np.where(x < n / 2, 1.0, 5.0)
    elif profile == "linear":
        kappa = 1.0 + 4.0 * x / (n - 1)
    elif profile == "gaussian":
        kappa = 1.0 + 9.0 * np.exp(-((x - n / 2) ** 2) / (2 * (n / 8) ** 2))
    else:
        kappa = np.ones(n)

    # Stability: dt <= dx^2 / (2 * max(kappa))
    max_kappa = float(kappa.max())
    if dt > dx ** 2 / (2 * max_kappa):
        dt = 0.9 * dx ** 2 / (2 * max_kappa)

    T = np.zeros(n)
    T[n // 2 - 5:n // 2 + 5] = 100.0

    report_every = max(1, steps // 100)
    for step in range(steps):
        flux = kappa[:-1] * (T[1:] - T[:-1]) / dx  # interface flux (n-1 values)
        T_new = T.copy()
        T_new[1:-1] += dt / dx * (flux[1:] - flux[:-1])
        T_new[0] = T_new[-1] = 0.0
        T = T_new
        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "n_points": n,
        "steps": steps,
        "conductivity_profile": profile,
        "max_conductivity": float(max_kappa),
        "max_temp": float(T.max()),
        "mean_temp": float(T.mean()),
        "final_profile": T.tolist(),
    }
