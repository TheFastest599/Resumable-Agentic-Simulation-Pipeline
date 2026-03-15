"""SIR / SEIR epidemic model (ODE, RK4 integration)."""
from typing import Callable

import numpy as np


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    model: str = payload.get("model", "SIR")  # "SIR" or "SEIR"
    N: int = int(payload.get("population", 10_000))
    I0: int = int(payload.get("initial_infected", 10))
    E0: int = int(payload.get("initial_exposed", 0))
    beta: float = float(payload.get("beta", 0.3))    # transmission rate
    gamma: float = float(payload.get("gamma", 0.05)) # recovery rate
    sigma: float = float(payload.get("sigma", 0.1))  # incubation rate (SEIR only)
    steps: int = int(payload.get("steps", 365))
    dt: float = 1.0

    def sir_deriv(S, I, R):
        dS = -beta * S * I / N
        dI = beta * S * I / N - gamma * I
        dR = gamma * I
        return dS, dI, dR

    def seir_deriv(S, E, I, R):
        dS = -beta * S * I / N
        dE = beta * S * I / N - sigma * E
        dI = sigma * E - gamma * I
        dR = gamma * I
        return dS, dE, dI, dR

    report_every = max(1, steps // 100)

    if model == "SEIR":
        S, E, I, R = float(N - I0 - E0), float(E0), float(I0), 0.0
        S_h, E_h, I_h, R_h = [S], [E], [I], [R]
        for step in range(steps):
            k1 = seir_deriv(S, E, I, R)
            k2 = seir_deriv(*(s + 0.5 * dt * k for s, k in zip([S, E, I, R], k1)))
            k3 = seir_deriv(*(s + 0.5 * dt * k for s, k in zip([S, E, I, R], k2)))
            k4 = seir_deriv(*(s + dt * k for s, k in zip([S, E, I, R], k3)))
            S += (dt / 6) * (k1[0] + 2*k2[0] + 2*k3[0] + k4[0])
            E += (dt / 6) * (k1[1] + 2*k2[1] + 2*k3[1] + k4[1])
            I += (dt / 6) * (k1[2] + 2*k2[2] + 2*k3[2] + k4[2])
            R += (dt / 6) * (k1[3] + 2*k2[3] + 2*k3[3] + k4[3])
            S, E, I, R = max(S, 0), max(E, 0), max(I, 0), max(R, 0)
            S_h.append(S); E_h.append(E); I_h.append(I); R_h.append(R)
            if step % report_every == 0:
                progress_cb((step + 1) / steps)
        ds = max(1, steps // 200)
        return {
            "model": "SEIR", "population": N, "steps": steps,
            "peak_infected": round(max(I_h), 1),
            "total_recovered": round(R, 1),
            "attack_rate": round(R / N, 4),
            "S_history": S_h[::ds], "E_history": E_h[::ds],
            "I_history": I_h[::ds], "R_history": R_h[::ds],
        }
    else:
        S, I, R = float(N - I0), float(I0), 0.0
        S_h, I_h, R_h = [S], [I], [R]
        for step in range(steps):
            k1 = sir_deriv(S, I, R)
            k2 = sir_deriv(*(s + 0.5 * dt * k for s, k in zip([S, I, R], k1)))
            k3 = sir_deriv(*(s + 0.5 * dt * k for s, k in zip([S, I, R], k2)))
            k4 = sir_deriv(*(s + dt * k for s, k in zip([S, I, R], k3)))
            S += (dt / 6) * (k1[0] + 2*k2[0] + 2*k3[0] + k4[0])
            I += (dt / 6) * (k1[1] + 2*k2[1] + 2*k3[1] + k4[1])
            R += (dt / 6) * (k1[2] + 2*k2[2] + 2*k3[2] + k4[2])
            S, I, R = max(S, 0), max(I, 0), max(R, 0)
            S_h.append(S); I_h.append(I); R_h.append(R)
            if step % report_every == 0:
                progress_cb((step + 1) / steps)
        ds = max(1, steps // 200)
        return {
            "model": "SIR", "population": N, "steps": steps,
            "peak_infected": round(max(I_h), 1),
            "total_recovered": round(R, 1),
            "attack_rate": round(R / N, 4),
            "S_history": S_h[::ds],
            "I_history": I_h[::ds],
            "R_history": R_h[::ds],
        }
