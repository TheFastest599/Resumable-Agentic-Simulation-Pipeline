"""Wright-Fisher model: allele frequency drift over generations."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    pop_size: int = int(payload.get("population_size", 1000))
    generations: int = int(payload.get("generations", 500))
    p0: float = float(payload.get("initial_allele_freq", 0.5))
    mutation_rate: float = float(payload.get("mutation_rate", 0.001))
    n_replicates: int = int(payload.get("n_replicates", 20))

    rng = np.random.default_rng()
    freqs = np.full(n_replicates, p0)
    history = [freqs.tolist()]

    report_every = max(1, generations // 100)
    fixed = 0
    lost = 0

    for gen in range(generations):
        # Mutation
        freqs = freqs * (1 - mutation_rate) + (1 - freqs) * mutation_rate
        # Drift: binomial sampling
        counts = rng.binomial(pop_size, freqs)
        freqs = counts / pop_size

        if gen % report_every == 0:
            history.append(freqs.tolist())
            progress_cb((gen + 1) / generations)

    progress_cb(1.0)
    fixed = int((freqs > 0.99).sum())
    lost = int((freqs < 0.01).sum())
    return {
        "population_size": pop_size,
        "generations": generations,
        "n_replicates": n_replicates,
        "initial_allele_freq": p0,
        "final_mean_freq": float(freqs.mean()),
        "final_std_freq": float(freqs.std()),
        "fixed_count": fixed,
        "lost_count": lost,
        "history_sample": history[::max(1, len(history) // 50)],
    }
