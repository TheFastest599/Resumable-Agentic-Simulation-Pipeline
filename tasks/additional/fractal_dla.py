"""Diffusion-Limited Aggregation (DLA) fractal growth."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    grid_size: int = int(payload.get("grid_size", 200))
    n_particles: int = int(payload.get("n_particles", 2000))
    max_walk_steps: int = int(payload.get("max_walk_steps", 10_000))

    rng = np.random.default_rng()
    grid = np.zeros((grid_size, grid_size), dtype=bool)
    cx, cy = grid_size // 2, grid_size // 2
    grid[cx, cy] = True  # seed

    cluster_size = 1
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for p in range(n_particles):
        # Release particle from random point on a circle just outside cluster
        radius = int(np.sqrt(cluster_size) * 2) + 10
        angle = rng.uniform(0, 2 * np.pi)
        x = int(cx + radius * np.cos(angle)) % grid_size
        y = int(cy + radius * np.sin(angle)) % grid_size

        for _ in range(max_walk_steps):
            # Check neighbours
            stuck = False
            for dx, dy in steps:
                nx, ny = (x + dx) % grid_size, (y + dy) % grid_size
                if grid[nx, ny]:
                    grid[x, y] = True
                    cluster_size += 1
                    stuck = True
                    break
            if stuck:
                break
            # Random walk
            move = steps[rng.integers(4)]
            x = (x + move[0]) % grid_size
            y = (y + move[1]) % grid_size

        progress_cb((p + 1) / n_particles)

    # Compute fractal dimension estimate via box counting (coarse)
    scales = [2, 4, 8, 16, 32]
    counts = []
    for s in scales:
        boxes = 0
        for i in range(0, grid_size, s):
            for j in range(0, grid_size, s):
                if grid[i:i+s, j:j+s].any():
                    boxes += 1
        counts.append(boxes)

    # Log-log slope ≈ fractal dimension
    import math
    if len(scales) >= 2 and counts[-1] > 0 and counts[0] > 0:
        fd = (math.log(counts[0]) - math.log(counts[-1])) / (math.log(scales[-1]) - math.log(scales[0]))
    else:
        fd = 0.0

    return {
        "grid_size": grid_size,
        "n_particles": n_particles,
        "cluster_size": cluster_size,
        "estimated_fractal_dimension": round(fd, 3),
        "grid": grid.astype(int).tolist(),
    }
