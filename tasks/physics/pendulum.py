"""Damped pendulum simulation (RK4 integration)."""
import math
from typing import Callable


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    length: float = float(payload.get("length", 1.0))
    mass: float = float(payload.get("mass", 1.0))
    damping: float = float(payload.get("damping", 0.1))
    theta0: float = float(payload.get("initial_angle_deg", 30.0))
    omega0: float = float(payload.get("initial_omega", 0.0))
    steps: int = int(payload.get("steps", 10_000))
    dt: float = float(payload.get("dt", 0.005))
    g: float = 9.81

    theta = math.radians(theta0)
    omega = float(omega0)
    energy_init = None
    energy_final = None

    def deriv(th, om):
        return om, -(g / length) * math.sin(th) - (damping / mass) * om

    theta_hist = [math.degrees(theta)]
    report_every = max(1, steps // 100)

    for i in range(steps):
        k1t, k1o = deriv(theta, omega)
        k2t, k2o = deriv(theta + 0.5 * dt * k1t, omega + 0.5 * dt * k1o)
        k3t, k3o = deriv(theta + 0.5 * dt * k2t, omega + 0.5 * dt * k2o)
        k4t, k4o = deriv(theta + dt * k3t, omega + dt * k3o)
        theta += (dt / 6) * (k1t + 2 * k2t + 2 * k3t + k4t)
        omega += (dt / 6) * (k1o + 2 * k2o + 2 * k3o + k4o)

        KE = 0.5 * mass * (length * omega) ** 2
        PE = mass * g * length * (1 - math.cos(theta))
        E = KE + PE
        if energy_init is None:
            energy_init = E
        energy_final = E

        theta_hist.append(math.degrees(theta))
        if i % report_every == 0:
            progress_cb((i + 1) / steps)

    progress_cb(1.0)
    ds = max(1, steps // 500)
    return {
        "steps": steps,
        "length_m": length,
        "damping": damping,
        "initial_angle_deg": theta0,
        "final_angle_deg": math.degrees(theta),
        "initial_energy": float(energy_init or 0.0),
        "final_energy": float(energy_final or 0.0),
        "energy_dissipated": float((energy_init or 0.0) - (energy_final or 0.0)),
        "theta_history_deg": theta_hist[::ds],
    }
