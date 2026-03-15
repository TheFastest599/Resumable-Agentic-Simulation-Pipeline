"""Spring-mass system (Hooke's law with damping, RK4)."""
import math
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    mass: float = float(payload.get("mass", 1.0))
    k: float = float(payload.get("spring_constant", 10.0))
    damping: float = float(payload.get("damping", 0.5))
    x0: float = float(payload.get("initial_displacement", 1.0))
    v0: float = float(payload.get("initial_velocity", 0.0))
    steps: int = int(payload.get("steps", 5000))
    dt: float = float(payload.get("dt", 0.01))

    x, v = x0, v0
    x_hist = [x]
    v_hist = [v]

    def deriv(xi, vi):
        return vi, (-k * xi - damping * vi) / mass

    report_every = max(1, steps // 100)
    for i in range(steps):
        k1x, k1v = deriv(x, v)
        k2x, k2v = deriv(x + 0.5 * dt * k1x, v + 0.5 * dt * k1v)
        k3x, k3v = deriv(x + 0.5 * dt * k2x, v + 0.5 * dt * k2v)
        k4x, k4v = deriv(x + dt * k3x, v + dt * k3v)
        x += (dt / 6) * (k1x + 2 * k2x + 2 * k3x + k4x)
        v += (dt / 6) * (k1v + 2 * k2v + 2 * k3v + k4v)
        x_hist.append(x)
        v_hist.append(v)
        if i % report_every == 0:
            progress_cb((i + 1) / steps)

    progress_cb(1.0)
    x_arr = np.array(x_hist)
    ds = max(1, steps // 500)
    return {
        "steps": steps,
        "mass": mass,
        "spring_constant": k,
        "damping": damping,
        "natural_frequency_hz": round(math.sqrt(k / mass) / (2 * math.pi), 4),
        "max_displacement": float(x_arr.max()),
        "min_displacement": float(x_arr.min()),
        "final_displacement": float(x),
        "position_history": x_hist[::ds],
    }
