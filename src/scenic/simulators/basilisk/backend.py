"""Basilisk + MuJoCo backend for the Scenic Basilisk simulator.

Uses ``asteroid_rl.env.build_sim`` when the asteroid landing demo is available
(sibling checkout or ``ASTEROID_RL_ROOT``). Keeps SysModel Python refs so GC
does not tear down Basilisk modules mid-run.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

import numpy as np

_SISTER_DEMO = (
    Path(__file__).resolve().parents[4].parent / "asteroid-rl-demo"
)


def _ensure_asteroid_rl_on_path(root: Optional[str | Path] = None) -> Path:
    """Locate asteroid-rl-demo and put it on ``sys.path``."""
    candidates = []
    env = os.environ.get("ASTEROID_RL_ROOT")
    if env:
        candidates.append(Path(env))
    if root is not None:
        candidates.append(Path(root))
    candidates.append(_SISTER_DEMO)
    # Editable install already importable.
    try:
        import asteroid_rl  # noqa: F401

        return Path(asteroid_rl.__file__).resolve().parent.parent
    except ImportError:
        pass
    for cand in candidates:
        if cand is None:
            continue
        pkg = cand / "asteroid_rl"
        if pkg.is_dir():
            path = str(cand.resolve())
            if path not in sys.path:
                sys.path.insert(0, path)
            return cand.resolve()
    raise ImportError(
        "asteroid_rl not found. Set ASTEROID_RL_ROOT to the asteroid-rl-demo "
        f"repo, or place it next to Scenic (expected {_SISTER_DEMO})."
    )


@dataclass
class BasiliskBackendConfig:
    """Construction options for the Basilisk landing backend."""

    asteroid_rl_root: Optional[str] = None
    gravity_mode: str = "constant"  # or "central"
    max_thrust: float = 275.0
    use_flat_surface: bool = False
    flat_surface_z: float = -30.0
    enable_viz: bool = False
    control_dt: float = 0.25


class BasiliskBackend:
    """Thin stateful wrapper around ``asteroid_rl.env.SimHandles``."""

    def __init__(self, config: Optional[BasiliskBackendConfig] = None):
        self.config = config or BasiliskBackendConfig()
        self._demo_root = _ensure_asteroid_rl_on_path(self.config.asteroid_rl_root)
        self.handles: Any = None
        self._hub: Any = None
        self._landing_site: Optional[np.ndarray] = None
        self._pending_throttle: float = 0.0
        self._pending_point_dir: Optional[np.ndarray] = None

    @property
    def demo_root(self) -> Path:
        return self._demo_root

    def build(
        self,
        position_N: Sequence[float],
        velocity_N: Sequence[float],
        sigma_BN: Optional[Sequence[float]] = None,
    ) -> None:
        """Create (or rebuild) the Basilisk/MuJoCo sim at the given IC."""
        from asteroid_rl.env import (
            LandingEnvConfig,
            SPACECRAFT_BODY_NAME,
            build_sim,
        )
        from Basilisk.architecture import messaging

        cfg = LandingEnvConfig()
        cfg.gravity_mode = str(self.config.gravity_mode)
        cfg.max_thrust = float(self.config.max_thrust)
        cfg.use_flat_surface = bool(self.config.use_flat_surface)
        cfg.flat_surface_z = float(self.config.flat_surface_z)
        cfg.enable_viz = bool(self.config.enable_viz)
        cfg.control_dt = float(self.config.control_dt)
        cfg.reuse_sim = True
        if cfg.gravity_mode == "central":
            cfg.apply_orbital_defaults()
            # Keep caller thrust/flat overrides after orbital defaults.
            cfg.max_thrust = max(float(self.config.max_thrust), float(cfg.max_thrust))
            cfg.use_flat_surface = bool(self.config.use_flat_surface)
            cfg.flat_surface_z = float(self.config.flat_surface_z)

        pos = np.asarray(position_N, dtype=np.float64).reshape(3)
        vel = np.asarray(velocity_N, dtype=np.float64).reshape(3)
        self.handles = build_sim(cfg, initial_position_N=pos, initial_velocity_N=vel)
        self._hub = self.handles.scene.getBody(SPACECRAFT_BODY_NAME)
        self._landing_site = cfg.target_array()
        if sigma_BN is not None:
            self.set_attitude_mrp(sigma_BN)
        self.handles.thrust_msg.write(messaging.SingleActuatorMsgPayload(input=0.0))
        self._pending_throttle = 0.0
        self._pending_point_dir = None

    def soft_reset(
        self,
        position_N: Sequence[float],
        velocity_N: Sequence[float],
        sigma_BN: Optional[Sequence[float]] = None,
    ) -> None:
        """Reset kinematics without rebuilding the sim."""
        from Basilisk.architecture import messaging

        if self.handles is None or self._hub is None:
            self.build(position_N, velocity_N, sigma_BN)
            return
        self._hub.setPosition(list(np.asarray(position_N, dtype=float).reshape(3)))
        self._hub.setVelocity(list(np.asarray(velocity_N, dtype=float).reshape(3)))
        if sigma_BN is not None:
            self.set_attitude_mrp(sigma_BN)
        else:
            self._hub.setAttitudeRate([0.0, 0.0, 0.0])
        self.handles.thrust_msg.write(messaging.SingleActuatorMsgPayload(input=0.0))
        self._pending_throttle = 0.0
        self._pending_point_dir = None
        # Prime recorder with one integrator tick.
        self.advance(0.02)

    def set_attitude_mrp(self, sigma_BN: Sequence[float]) -> None:
        if self._hub is None:
            return
        sigma = list(np.asarray(sigma_BN, dtype=float).reshape(3))
        self._hub.setAttitude(sigma)
        self._hub.setAttitudeRate([0.0, 0.0, 0.0])

    def set_throttle(self, throttle: float) -> None:
        self._pending_throttle = float(np.clip(throttle, 0.0, 1.0))

    def set_pointing_direction(self, direction_N: Sequence[float]) -> None:
        d = np.asarray(direction_N, dtype=np.float64).reshape(3)
        n = float(np.linalg.norm(d))
        if n < 1e-12:
            return
        self._pending_point_dir = d / n

    def point_at_target(self, target_N: Sequence[float]) -> None:
        if self.handles is None:
            return
        r, _ = self.read_state()
        self.set_pointing_direction(
            np.asarray(target_N, dtype=np.float64).reshape(3) - r
        )

    def flush_controls(self) -> None:
        """Apply pending pointing + throttle to Basilisk messages."""
        from Basilisk.architecture import messaging
        from asteroid_rl.pointing import apply_pointing_direction

        if self.handles is None or self._hub is None:
            return
        if self._pending_point_dir is not None:
            apply_pointing_direction(self._hub, self._pending_point_dir)
        thrust_N = self._pending_throttle * float(self.handles.config.max_thrust)
        self.handles.thrust_msg.write(
            messaging.SingleActuatorMsgPayload(input=float(thrust_N))
        )

    def advance(self, dt: float) -> None:
        """Advance Basilisk by ``dt`` seconds."""
        from Basilisk.utilities import macros

        if self.handles is None:
            return
        dt = float(dt)
        if dt <= 0.0:
            return
        self.handles.absolute_sim_time_sec += dt
        self.handles.scSim.ConfigureStopTime(
            macros.sec2nano(self.handles.absolute_sim_time_sec)
        )
        self.handles.scSim.ExecuteSimulation()

    def read_state(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return ``(r_BN_N, v_BN_N)``."""
        if self.handles is None:
            return np.zeros(3), np.zeros(3)
        rec = self.handles.state_recorder
        r = np.array(rec.r_BN_N[-1], dtype=np.float64)
        v = np.array(rec.v_BN_N[-1], dtype=np.float64)
        return r, v

    def read_mrp(self) -> np.ndarray:
        if self.handles is None:
            return np.zeros(3)
        rec = self.handles.state_recorder
        return np.array(rec.sigma_BN[-1], dtype=np.float64)

    def landing_site(self) -> np.ndarray:
        if self._landing_site is not None:
            return np.asarray(self._landing_site, dtype=np.float64).reshape(3)
        return np.array([0.0, 0.0, -30.0], dtype=np.float64)

    def destroy(self) -> None:
        self.handles = None
        self._hub = None
