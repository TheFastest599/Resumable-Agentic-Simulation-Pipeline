"""Eigenvalue and eigenvector decomposition of a random symmetric matrix."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    size: int = int(payload.get("size", 200))

    progress_cb(0.1)
    rng = np.random.default_rng()
    A = rng.standard_normal((size, size))
    A = A @ A.T  # symmetric positive semi-definite
    progress_cb(0.3)

    eigenvalues, _ = np.linalg.eigh(A)
    progress_cb(0.9)

    eigenvalues = eigenvalues[::-1]  # descending
    progress_cb(1.0)
    return {
        "size": size,
        "largest_eigenvalue": float(eigenvalues[0]),
        "smallest_eigenvalue": float(eigenvalues[-1]),
        "top_5_eigenvalues": eigenvalues[:5].tolist(),
        "spectral_gap": float(eigenvalues[0] - eigenvalues[1]) if size > 1 else 0.0,
        "trace": float(eigenvalues.sum()),
    }
