"""Fluid particle advection in a 2D divergence-free velocity field (RK4)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n_particles: int = int(payload.get("n_particles", 200))
    steps: int = int(payload.get("steps", 500))
    dt: float = float(payload.get("dt", 0.05))
    domain: float = float(payload.get("domain", 2 * np.pi))

    rng = np.random.default_rng()
    pos = rng.uniform(0, domain, (n_particles, 2))
    start = pos.copy()

    def velocity(p):
        return np.stack([np.sin(p[:, 1]), np.sin(p[:, 0])], axis=1)

    report_every = max(1, steps // 100)
    for step in range(steps):
        k1 = velocity(pos)
        k2 = velocity(pos + 0.5 * dt * k1)
        k3 = velocity(pos + 0.5 * dt * k2)
        k4 = velocity(pos + dt * k3)
        pos = (pos + (dt / 6) * (k1 + 2 * k2 + 2 * k3 + k4)) % domain

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    disp = np.linalg.norm(pos - start, axis=1)
    return {
        "n_particles": n_particles,
        "steps": steps,
        "dt": dt,
        "mean_displacement": float(disp.mean()),
        "max_displacement": float(disp.max()),
        "final_positions": pos.tolist(),
    }
