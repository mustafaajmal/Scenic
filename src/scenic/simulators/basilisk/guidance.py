"""Lander GNC for Scenic↔Basilisk: soft-brake, acquire, and divert phases.

Attitude: optional rate-limited slew (reaction-wheel *stand-in*). Instant
``setAttitude`` remains available via ``attitude_mode='instant'``.

Translation: one body-+z thruster. Near the surface the throttle schedule
**settles** (cuts thrust when slow) so the craft does not boost away after
a soft contact.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np

from Basilisk.utilities import RigidBodyKinematics as rbk

BORESIGHT_B = np.array([0.0, 0.0, -1.0], dtype=np.float64)

# Soft-land / contact gates (meters, m/s).
CONTACT_ALT_M = 0.35
SETTLE_ALT_MAX_M = 8.0
SETTLE_SPEED_MPS = 3.5
HOVER_THROTTLE = 200.0 / 275.0  # ≈ cancels Phase-1 constant weight


def unit(v: np.ndarray) -> np.ndarray:
    x = np.asarray(v, dtype=np.float64).reshape(3)
    n = float(np.linalg.norm(x))
    if n < 1e-12:
        return np.array([0.0, 0.0, -1.0], dtype=np.float64)
    return x / n


def boresight_inertial(sigma_BN: Sequence[float]) -> np.ndarray:
    """Body −z expressed in the inertial frame."""
    c_bn = np.asarray(rbk.MRP2C(list(sigma_BN)), dtype=np.float64)
    return unit(c_bn.T @ BORESIGHT_B)


def pointing_error_rad(sigma_BN: Sequence[float], desired_dir_N: Sequence[float]) -> float:
    a = boresight_inertial(sigma_BN)
    b = unit(np.asarray(desired_dir_N, dtype=np.float64))
    return float(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0)))


def slew_direction(
    current_dir_N: Sequence[float],
    desired_dir_N: Sequence[float],
    max_angle_rad: float,
) -> np.ndarray:
    """Move ``current`` toward ``desired`` by at most ``max_angle_rad`` (RW stand-in)."""
    a = unit(np.asarray(current_dir_N, dtype=np.float64))
    b = unit(np.asarray(desired_dir_N, dtype=np.float64))
    max_angle = max(0.0, float(max_angle_rad))
    cos_a = float(np.clip(np.dot(a, b), -1.0, 1.0))
    angle = float(np.arccos(cos_a))
    if angle < 1e-8 or max_angle <= 0.0:
        return b if max_angle > 0 else a
    if angle <= max_angle:
        return b
    axis = np.cross(a, b)
    if float(np.linalg.norm(axis)) < 1e-10:
        helper = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        if abs(float(np.dot(helper, a))) > 0.9:
            helper = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        axis = np.cross(a, helper)
    axis = unit(axis)
    k = max_angle
    return unit(
        a * np.cos(k)
        + np.cross(axis, a) * np.sin(k)
        + axis * np.dot(axis, a) * (1.0 - np.cos(k))
    )


def soft_brake_throttle(altitude: float, speed: float) -> float:
    """Altitude/speed throttle with an explicit **settle** near the surface.

    Below ``SETTLE_ALT_MAX_M`` with low speed → cut thrust (do not boost away).
    Full throttle only while still closing too fast.
    """
    alt = float(altitude)
    spd = float(speed)

    # Soft-landed / settling: kill thrust so we don't shoot off.
    if alt <= CONTACT_ALT_M:
        return 0.0
    if alt <= SETTLE_ALT_MAX_M and spd <= SETTLE_SPEED_MPS:
        # Already in the safe band — coast / light hold only if still descending fast.
        if spd <= 1.2:
            return 0.0
        return min(0.45, HOVER_THROTTLE)

    # Closing too fast near the ground: brake, but taper with speed.
    if alt < 15.0:
        if spd > 3.0:
            return 1.0
        if spd > 2.0:
            return 0.85
        if spd > 1.2:
            return max(HOVER_THROTTLE, 0.55)
        return 0.25  # nearly settled

    if alt < 30.0:
        if spd > 2.5:
            return 0.9
        if spd > 1.5:
            return 0.7
        return 0.35

    if alt < 55.0 and spd > 1.5:
        return 0.75
    if spd > 2.5:
        return 0.55
    if alt < 90.0 and spd > 1.0:
        return 0.35
    return 0.15


def compute_guidance(
    *,
    position_N: Sequence[float],
    velocity_N: Sequence[float],
    altitude_m: float,
    target_N: Sequence[float],
    mode: str,
    sigma_BN: Optional[Sequence[float]] = None,
    acquired: bool = False,
    landed: bool = False,
    in_contact: bool = False,
) -> Dict[str, object]:
    """Return throttle, desired boresight (−z) direction, and phase name.

    Modes:
      ``soft_brake`` — inbound soft land (legacy).
      ``acquire`` — slew look-at-target, then soft-brake.
      ``divert`` — velocity-target divert, then terminal soft land.
    """
    mode = str(mode).strip().lower()
    r = np.asarray(position_N, dtype=np.float64).reshape(3)
    v = np.asarray(velocity_N, dtype=np.float64).reshape(3)
    target = np.asarray(target_N, dtype=np.float64).reshape(3)
    rel = r - target
    range_m = float(np.linalg.norm(rel))
    lateral = float(np.linalg.norm(rel[:2]))
    speed = float(np.linalg.norm(v))
    altitude = float(altitude_m)
    los = unit(target - r)
    r_hat = unit(rel) if range_m > 1e-9 else np.array([0.0, 0.0, 1.0])
    climbing = float(np.dot(r_hat, v)) > 0.25

    # Contact / already landed: freeze thrust.
    if landed or in_contact or altitude <= CONTACT_ALT_M:
        point = los
        return {
            "throttle": 0.0,
            "point_dir": point,
            "phase": "landed" if (landed or speed <= SETTLE_SPEED_MPS) else "contact",
            "acquired": True,
            "landed": True,
            "pointing_error_rad": (
                pointing_error_rad(sigma_BN, point) if sigma_BN is not None else 0.0
            ),
        }

    def _pack(throttle: float, point: np.ndarray, phase: str, acq: bool = True):
        return {
            "throttle": float(np.clip(throttle, 0.0, 1.0)),
            "point_dir": point,
            "phase": phase,
            "acquired": acq,
            "landed": False,
            "pointing_error_rad": (
                pointing_error_rad(sigma_BN, point) if sigma_BN is not None else 0.0
            ),
        }

    if mode == "soft_brake":
        return _pack(soft_brake_throttle(altitude, speed), los, "soft_brake")

    if mode == "acquire":
        err = pointing_error_rad(sigma_BN, los) if sigma_BN is not None else 0.0
        aligned = err < np.deg2rad(12.0)
        now_acquired = bool(acquired or aligned)
        if not now_acquired:
            return _pack(0.0, los, "acquire", acq=False)
        return _pack(soft_brake_throttle(altitude, speed), los, "soft_brake")

    # --- divert ---
    if altitude < 70.0 and lateral < 25.0 and not climbing:
        throttle = soft_brake_throttle(altitude, speed)
        # Do not re-raise to 1.0 inside the settle band (that caused shoot-offs).
        if altitude > SETTLE_ALT_MAX_M and speed > 2.0:
            throttle = max(throttle, 0.7)
        return _pack(throttle, los, "terminal")

    if altitude < 85.0 and lateral > 18.0:
        # Near surface with lateral miss: divert, but cut thrust if almost settled.
        if altitude <= SETTLE_ALT_MAX_M and speed <= SETTLE_SPEED_MPS:
            return _pack(0.0, los, "settle")
        lat_hat = unit(np.array([rel[0], rel[1], 0.0], dtype=np.float64))
        v_lat = np.array([v[0], v[1], 0.0], dtype=np.float64)
        a_cmd = -0.65 * lat_hat - 0.85 * v_lat
        if float(v[2]) < -1.2:
            a_cmd = a_cmd + np.array([0.0, 0.0, 0.7])
        a_hat = unit(a_cmd)
        point = -a_hat
        throttle = 0.55 if speed < 1.8 else 0.75
        if altitude < 20.0:
            throttle = min(throttle, 0.6)
        return _pack(throttle, point, "lateral_divert")

    if range_m > 180.0:
        v_close = 1.7
    elif range_m > 90.0:
        v_close = 1.2
    elif range_m > 40.0:
        v_close = 0.75
    else:
        v_close = 0.4
    v_des = -v_close * r_hat
    v_err = v_des - v
    if speed > 5.0 or climbing:
        brake_w = 0.65 if speed > 6.5 else 0.4
        v_err = (1.0 - brake_w) * v_err + brake_w * (-v)
    err_n = float(np.linalg.norm(v_err))
    if err_n < 1e-9:
        v_err = -unit(v) if speed > 1e-9 else los
        err_n = 1.0
    a_hat = v_err / err_n
    point = -a_hat
    if speed > 5.5 or climbing:
        throttle = 0.9
    elif err_n > 2.5:
        throttle = 0.75
    elif err_n > 1.2:
        throttle = 0.55
    else:
        throttle = 0.4
    if climbing and altitude > 50.0:
        throttle = max(throttle, 0.7)
    return _pack(throttle, point, "divert")
