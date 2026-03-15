"""Brownian motion / stochastic process simulation in 1D, 2D, or 3D."""
import math
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n_particles: int = int(payload.get("n_particles", 100))
    steps: int = int(payload.get("steps", 1000))
    dt: float = float(payload.get("dt", 0.01))
    D: float = float(payload.get("diffusion_coeff", 1.0))
    dimensions: int = int(payload.get("dimensions", 2))

    rng = np.random.default_rng()
    sigma = math.sqrt(2 * D * dt)

    pos = np.zeros((n_particles, dimensions))
    msd_hist = []  # mean square displacement

    batch_report = max(1, steps // 100)
    for step in range(steps):
        pos += rng.normal(0, sigma, (n_particles, dimensions))
        if step % batch_report == 0:
            msd = float(np.mean(np.sum(pos ** 2, axis=1)))
            msd_hist.append(msd)
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    msd_final = float(np.mean(np.sum(pos ** 2, axis=1)))
    # Theoretical MSD = 2*D*t*dimensions
    theoretical_msd = 2 * D * steps * dt * dimensions
    return {
        "n_particles": n_particles,
        "steps": steps,
        "dt": dt,
        "dimensions": dimensions,
        "diffusion_coeff": D,
        "final_msd": msd_final,
        "theoretical_msd": theoretical_msd,
        "msd_ratio": round(msd_final / theoretical_msd, 4) if theoretical_msd else None,
        "msd_history": msd_hist,
    }
