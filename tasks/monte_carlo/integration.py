"""Monte Carlo numerical integration of f(x) over [a, b]."""
import math
from typing import Callable

import numpy as np

_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "exp": math.exp,
    "x2": lambda x: x ** 2,
    "x3": lambda x: x ** 3,
    "sqrt": lambda x: math.sqrt(abs(x)),
}


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    samples: int = int(payload.get("samples", 1_000_000))
    a: float = float(payload.get("a", 0.0))
    b: float = float(payload.get("b", math.pi))
    fn_name: str = payload.get("function", "sin")

    fn = _FUNCTIONS.get(fn_name)
    if fn is None:
        raise ValueError(f"Unknown function '{fn_name}'. Choose from: {list(_FUNCTIONS)}")

    batch = max(1, samples // 100)
    rng = np.random.default_rng()
    total = 0.0
    completed = 0

    while completed < samples:
        n = min(batch, samples - completed)
        xs = rng.uniform(a, b, n)
        total += float(np.vectorize(fn)(xs).sum())
        completed += n
        progress_cb(completed / samples)

    return {
        "function": fn_name,
        "a": a,
        "b": b,
        "samples": samples,
        "integral": (b - a) * total / samples,
    }
