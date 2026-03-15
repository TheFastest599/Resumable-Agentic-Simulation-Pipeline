"""Monte Carlo European option pricing (Black-Scholes)."""
import math
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    S: float = float(payload.get("S", 100.0))
    K: float = float(payload.get("K", 105.0))
    T: float = float(payload.get("T", 1.0))
    r: float = float(payload.get("r", 0.05))
    sigma: float = float(payload.get("sigma", 0.2))
    n_sim: int = int(payload.get("simulations", 100_000))
    n_steps: int = int(payload.get("steps", 252))

    dt = T / n_steps
    batch = max(1, n_sim // 100)
    rng = np.random.default_rng()

    payoffs = []
    completed = 0
    while completed < n_sim:
        n = min(batch, n_sim - completed)
        z = rng.standard_normal((n, n_steps))
        log_returns = (r - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z
        final_prices = S * np.exp(np.cumsum(log_returns, axis=1)[:, -1])
        payoffs.append(np.maximum(final_prices - K, 0.0))
        completed += n
        progress_cb(completed / n_sim)

    all_payoffs = np.concatenate(payoffs)
    discount = math.exp(-r * T)
    price = float(discount * all_payoffs.mean())
    variance = float(all_payoffs.var())
    return {
        "S": S, "K": K, "T": T, "r": r, "sigma": sigma,
        "simulations": n_sim,
        "price": price,
        "variance": variance,
        "std_error": float(math.sqrt(variance / n_sim)),
    }
