"""Singular Value Decomposition of a large random matrix."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    rows: int = int(payload.get("rows", 300))
    cols: int = int(payload.get("cols", 200))

    progress_cb(0.1)
    rng = np.random.default_rng()
    A = rng.standard_normal((rows, cols))
    progress_cb(0.3)

    _, S, _ = np.linalg.svd(A, full_matrices=False)
    progress_cb(0.9)

    rank = int((S > 1e-10).sum())
    explained = float((S[:5] ** 2).sum() / (S ** 2).sum()) if len(S) >= 5 else 1.0
    progress_cb(1.0)
    return {
        "rows": rows,
        "cols": cols,
        "rank": rank,
        "top_5_singular_values": S[:5].tolist(),
        "largest_singular_value": float(S[0]),
        "frobenius_norm": float(np.linalg.norm(A, "fro")),
        "top5_explained_variance_ratio": explained,
    }
