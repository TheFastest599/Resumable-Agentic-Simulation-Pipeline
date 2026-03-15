"""Random walk simulation (1D, 2D, or 3D)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    steps: int = int(payload.get("steps", 1_000_000))
    particles: int = int(payload.get("particles", 10))
    dimensions: int = int(payload.get("dimensions", 2))
    batch = max(1, steps // 100)

    rng = np.random.default_rng()
    positions = np.zeros((particles, dimensions))
    completed = 0

    while completed < steps:
        n = min(batch, steps - completed)
        moves = rng.choice([-1, 1], size=(particles, n, dimensions))
        positions += moves.sum(axis=1)
        completed += n
        progress_cb(completed / steps)

    distances = np.sqrt(np.sum(positions ** 2, axis=1))
    return {
        "steps": steps,
        "particles": particles,
        "dimensions": dimensions,
        "final_positions": positions.tolist(),
        "mean_displacement": float(distances.mean()),
        "max_displacement": float(distances.max()),
    }
