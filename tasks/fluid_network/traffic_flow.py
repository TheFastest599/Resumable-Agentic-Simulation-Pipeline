"""1D traffic flow simulation (Nagel-Schreckenberg cellular automaton)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    road_length: int = int(payload.get("road_length", 200))
    n_vehicles: int = int(payload.get("n_vehicles", 60))
    v_max: int = int(payload.get("v_max", 5))
    p_brake: float = float(payload.get("p_brake", 0.3))  # random braking probability
    steps: int = int(payload.get("steps", 500))

    rng = np.random.default_rng()

    # Place vehicles randomly on road
    positions = np.sort(rng.choice(road_length, size=n_vehicles, replace=False))
    velocities = rng.integers(0, v_max + 1, size=n_vehicles)

    mean_vel_hist = []
    flow_hist = []

    report_every = max(1, steps // 100)
    for step in range(steps):
        new_pos = positions.copy()
        new_vel = velocities.copy()

        for i in range(n_vehicles):
            # Distance to next vehicle (periodic boundary)
            next_i = (i + 1) % n_vehicles
            gap = (positions[next_i] - positions[i] - 1) % road_length

            # Accelerate
            v = min(velocities[i] + 1, v_max)
            # Brake (avoid collision)
            v = min(v, gap)
            # Random braking
            if v > 0 and rng.random() < p_brake:
                v -= 1
            new_vel[i] = max(v, 0)
            new_pos[i] = (positions[i] + new_vel[i]) % road_length

        positions = new_pos
        velocities = new_vel

        mean_vel_hist.append(float(velocities.mean()))
        flow_hist.append(float(velocities.sum() / road_length))

        if step % report_every == 0:
            progress_cb((step + 1) / steps)

    progress_cb(1.0)
    return {
        "road_length": road_length,
        "n_vehicles": n_vehicles,
        "v_max": v_max,
        "steps": steps,
        "density": n_vehicles / road_length,
        "mean_velocity": float(np.mean(mean_vel_hist)),
        "mean_flow": float(np.mean(flow_hist)),
        "final_mean_velocity": mean_vel_hist[-1],
        "velocity_history": mean_vel_hist[::max(1, steps // 200)],
    }
