"""Financial portfolio risk simulation (Monte Carlo VaR / CVaR)."""
import math
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n_assets: int = int(payload.get("n_assets", 5))
    n_scenarios: int = int(payload.get("n_scenarios", 100_000))
    horizon_days: int = int(payload.get("horizon_days", 10))
    confidence: float = float(payload.get("confidence", 0.95))
    portfolio_value: float = float(payload.get("portfolio_value", 1_000_000.0))

    rng = np.random.default_rng()

    # Random portfolio weights (equal-weight by default)
    weights = np.array(payload.get("weights", [1.0 / n_assets] * n_assets))
    weights = weights[:n_assets] / weights[:n_assets].sum()

    # Random annual volatilities and correlation matrix
    vols = np.array(payload.get("volatilities", [0.2] * n_assets))[:n_assets]
    daily_vols = vols / math.sqrt(252)

    # Cholesky of random correlation matrix
    corr_flat = payload.get("correlations", None)
    if corr_flat:
        corr = np.array(corr_flat).reshape(n_assets, n_assets)
    else:
        A = rng.standard_normal((n_assets, n_assets))
        corr = np.corrcoef(A)
        np.fill_diagonal(corr, 1.0)
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1.0)
    L = np.linalg.cholesky(corr + 1e-6 * np.eye(n_assets))

    batch = max(1, n_scenarios // 100)
    pnl_all = []
    completed = 0

    while completed < n_scenarios:
        n = min(batch, n_scenarios - completed)
        # Correlated normal returns over horizon
        Z = rng.standard_normal((n, n_assets, horizon_days))
        corr_Z = np.tensordot(Z, L.T, axes=[[1], [1]])  # (n, days, assets)
        daily_returns = corr_Z * daily_vols  # (n, days, assets)
        total_returns = daily_returns.sum(axis=1)  # (n, assets)
        portfolio_returns = total_returns @ weights
        pnl_all.append(portfolio_returns * portfolio_value)
        completed += n
        progress_cb(completed / n_scenarios)

    pnl = np.concatenate(pnl_all)
    var = float(np.percentile(pnl, (1 - confidence) * 100))
    cvar = float(pnl[pnl <= var].mean())

    return {
        "n_assets": n_assets,
        "n_scenarios": n_scenarios,
        "horizon_days": horizon_days,
        "confidence": confidence,
        "portfolio_value": portfolio_value,
        "VaR": round(var, 2),
        "CVaR": round(cvar, 2),
        "VaR_pct": round(var / portfolio_value * 100, 4),
        "CVaR_pct": round(cvar / portfolio_value * 100, 4),
        "mean_pnl": round(float(pnl.mean()), 2),
        "std_pnl": round(float(pnl.std()), 2),
    }
