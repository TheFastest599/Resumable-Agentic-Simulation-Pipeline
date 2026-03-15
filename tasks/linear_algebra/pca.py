"""PCA / covariance analysis on a synthetic dataset."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n_samples: int = int(payload.get("n_samples", 5000))
    n_features: int = int(payload.get("n_features", 50))
    n_components: int = int(payload.get("n_components", 10))

    progress_cb(0.1)
    rng = np.random.default_rng()
    latent = rng.standard_normal((n_samples, n_components))
    mixing = rng.standard_normal((n_components, n_features))
    X = latent @ mixing + 0.1 * rng.standard_normal((n_samples, n_features))

    progress_cb(0.3)
    X -= X.mean(axis=0)
    cov = (X.T @ X) / (n_samples - 1)

    progress_cb(0.5)
    eigenvalues, _ = np.linalg.eigh(cov)
    eigenvalues = eigenvalues[::-1]

    progress_cb(0.85)
    total_var = float(eigenvalues.sum())
    explained_ratios = (eigenvalues[:n_components] / total_var).tolist()
    progress_cb(1.0)
    return {
        "n_samples": n_samples,
        "n_features": n_features,
        "n_components": n_components,
        "explained_variance_ratios": explained_ratios,
        "cumulative_explained_variance": float(sum(explained_ratios)),
        "top_eigenvalues": eigenvalues[:n_components].tolist(),
    }
