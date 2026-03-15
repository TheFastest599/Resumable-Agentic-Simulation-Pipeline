"""Quantum particle in a 1D potential well (time-independent Schrödinger, finite differences)."""
import math
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    n_points: int = int(payload.get("n_points", 500))
    well_depth: float = float(payload.get("well_depth", 50.0))  # eV
    well_width: float = float(payload.get("well_width", 0.5))   # nm
    hbar: float = 1.0546e-34  # J·s
    m_e: float = 9.109e-31    # kg
    eV: float = 1.602e-19     # J

    L: float = well_width * 3  # domain size in nm
    x = np.linspace(0, L, n_points)
    dx = x[1] - x[0]

    progress_cb(0.2)

    # Potential: infinite square well with finite depth inside
    V = np.zeros(n_points)
    mask = (x > (L - well_width) / 2) & (x < (L + well_width) / 2)
    V[~mask] = well_depth * eV  # walls

    # Build Hamiltonian (tridiagonal) in natural units scaled for numerics
    scale = hbar ** 2 / (2 * m_e * (dx * 1e-9) ** 2)
    diag = scale * 2 * np.ones(n_points) + V
    off = -scale * np.ones(n_points - 1)
    H = np.diag(diag) + np.diag(off, 1) + np.diag(off, -1)

    progress_cb(0.5)
    eigenvalues, eigenvectors = np.linalg.eigh(H)
    progress_cb(0.9)

    # Convert to eV, take bound states (E < well_depth)
    E_eV = eigenvalues / eV
    bound_mask = E_eV < well_depth
    bound_energies = E_eV[bound_mask][:5].tolist()

    progress_cb(1.0)
    return {
        "n_points": n_points,
        "well_width_nm": well_width,
        "well_depth_eV": well_depth,
        "n_bound_states": int(bound_mask.sum()),
        "ground_state_energy_eV": float(bound_energies[0]) if bound_energies else None,
        "bound_state_energies_eV": bound_energies,
        "ground_state_wavefunction": eigenvectors[:, 0].tolist(),
    }
