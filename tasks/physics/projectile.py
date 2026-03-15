"""Projectile motion with air drag (Euler integration)."""
import math
from typing import Callable


def run(payload: dict, progress_cb: Callable[[float], None]) -> dict:
    v0: float = float(payload.get("initial_velocity", 50.0))
    angle_deg: float = float(payload.get("angle_deg", 45.0))
    drag_coeff: float = float(payload.get("drag_coeff", 0.01))
    mass: float = float(payload.get("mass", 1.0))
    g: float = 9.81
    dt: float = float(payload.get("dt", 0.01))
    max_steps: int = int(payload.get("max_steps", 10_000))

    angle = math.radians(angle_deg)
    vx = v0 * math.cos(angle)
    vy = v0 * math.sin(angle)
    x, y = 0.0, 0.0
    max_height = 0.0
    step = 0

    while y >= 0 and step < max_steps:
        v = math.sqrt(vx ** 2 + vy ** 2)
        vx += (-drag_coeff * v * vx / mass) * dt
        vy += (-g - drag_coeff * v * vy / mass) * dt
        x += vx * dt
        y += vy * dt
        if y > max_height:
            max_height = y
        step += 1
        if step % (max_steps // 100 or 1) == 0:
            progress_cb(step / max_steps)

    progress_cb(1.0)
    return {
        "initial_velocity": v0,
        "angle_deg": angle_deg,
        "drag_coeff": drag_coeff,
        "range_m": float(x),
        "max_height_m": float(max_height),
        "flight_time_s": float(step * dt),
    }
