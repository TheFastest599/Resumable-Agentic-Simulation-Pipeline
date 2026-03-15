"""Monte Carlo π estimation."""
import math
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    iterations: int = int(payload.get("iterations", 1_000_000))
    batch = max(1, iterations // 100)

    inside = 0
    completed = 0
    rng = np.random.default_rng()

    while completed < iterations:
        n = min(batch, iterations - completed)
        pts = rng.random((n, 2))
        inside += int(np.sum(pts[:, 0] ** 2 + pts[:, 1] ** 2 <= 1.0))
        completed += n
        progress_cb(completed / iterations)

    pi_estimate = 4 * inside / iterations
    return {
        "pi_estimate": pi_estimate,
        "error": abs(pi_estimate - math.pi),
        "iterations": iterations,
    }
