"""Lotka-Volterra predator-prey model (RK4)."""
from typing import Callable

import numpy as np


def _rk4_step(state, alpha, beta, delta, gamma, dt):
    def deriv(s):
        x, y = s
        return np.array([alpha * x - beta * x * y, delta * x * y - gamma * y])
    k1 = deriv(state)
    k2 = deriv(state + 0.5 * dt * k1)
    k3 = deriv(state + 0.5 * dt * k2)
    k4 = deriv(state + dt * k3)
    return state + (dt / 6) * (k1 + 2 * k2 + 2 * k3 + k4)


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    x0: float = float(payload.get("prey_initial", 40.0))
    y0: float = float(payload.get("predator_initial", 9.0))
    alpha: float = float(payload.get("alpha", 0.1))
    beta: float = float(payload.get("beta", 0.02))
    delta: float = float(payload.get("delta", 0.01))
    gamma: float = float(payload.get("gamma", 0.1))
    steps: int = int(payload.get("steps", 10_000))
    dt: float = float(payload.get("dt", 0.01))

    state = np.array([x0, y0])
    prey_hist = [x0]
    pred_hist = [y0]

    report_every = max(1, steps // 100)
    for i in range(steps):
        state = _rk4_step(state, alpha, beta, delta, gamma, dt)
        state = np.maximum(state, 0.0)
        prey_hist.append(float(state[0]))
        pred_hist.append(float(state[1]))
        if i % report_every == 0:
            progress_cb((i + 1) / steps)

    progress_cb(1.0)
    ds = max(1, steps // 500)
    return {
        "steps": steps,
        "prey_mean": float(np.mean(prey_hist)),
        "predator_mean": float(np.mean(pred_hist)),
        "prey_max": float(max(prey_hist)),
        "predator_max": float(max(pred_hist)),
        "final_prey": float(state[0]),
        "final_predator": float(state[1]),
        "prey_history": prey_hist[::ds],
        "predator_history": pred_hist[::ds],
    }
