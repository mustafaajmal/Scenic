"""Orientation helpers between Scenic Euler angles and Basilisk MRPs."""

from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
from scipy.spatial.transform import Rotation

from scenic.core.vectors import Orientation, Vector


def scenic_orientation_to_mrp(orientation: Orientation) -> np.ndarray:
    """Convert a Scenic `Orientation` to Basilisk MRP ``sigma_BN``.

    Scenic stores a SciPy rotation that maps body axes into the world frame.
    Basilisk ``MRP2C(sigma_BN)`` maps inertial vectors into the body frame, so
    ``C_BN = R.T``.
    """
    from Basilisk.utilities import RigidBodyKinematics as rbk

    R_NB = orientation.getRotation().as_matrix()
    C_BN = np.asarray(R_NB, dtype=np.float64).T
    return np.asarray(rbk.C2MRP(C_BN), dtype=np.float64).reshape(3)


def mrp_to_scenic_orientation(sigma_BN: Sequence[float]) -> Orientation:
    """Convert Basilisk MRP ``sigma_BN`` to a Scenic `Orientation`."""
    from Basilisk.utilities import RigidBodyKinematics as rbk

    C_BN = np.asarray(rbk.MRP2C(list(np.asarray(sigma_BN, dtype=float).reshape(3))))
    R_NB = C_BN.T
    return Orientation(Rotation.from_matrix(R_NB))


def mrp_to_euler_zxy(sigma_BN: Sequence[float]) -> Tuple[float, float, float]:
    """Return Scenic global intrinsic yaw, pitch, roll (radians)."""
    ori = mrp_to_scenic_orientation(sigma_BN)
    return float(ori.yaw), float(ori.pitch), float(ori.roll)


def vector3(value) -> Vector:
    """Coerce a sequence into a Scenic `Vector`."""
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size == 2:
        return Vector(float(arr[0]), float(arr[1]), 0.0)
    return Vector(float(arr[0]), float(arr[1]), float(arr[2]))
