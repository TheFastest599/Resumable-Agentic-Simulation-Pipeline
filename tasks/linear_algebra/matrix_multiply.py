"""Large matrix multiplication benchmark."""
import time
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    size: int = int(payload.get("size", 512))

    progress_cb(0.1)
    rng = np.random.default_rng()
    A = rng.random((size, size))
    B = rng.random((size, size))

    progress_cb(0.3)
    start = time.perf_counter()
    C = A @ B
    elapsed_ms = (time.perf_counter() - start) * 1000

    progress_cb(0.9)
    checksum = float(C.sum())
    progress_cb(1.0)
    return {
        "size": size,
        "elapsed_ms": round(elapsed_ms, 3),
        "checksum": checksum,
    }
