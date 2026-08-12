"""Scenic `Simulator` interface for Basilisk (via asteroid_rl MuJoCo scene).

The dynamics live in Basilisk + MuJoCo as built by ``asteroid_rl.env.build_sim``.
Scenic owns scenario sampling (initial pose, behaviors, requirements) and
orchestrates the control loop through this interface.

See also:
    - docs/new_simulator.rst
    - scenic.simulators.webots.simulator (external API pattern)
    - MuJoCo Scenic PR #433 (in-process physics pattern)
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from scenic.core.simulators import Simulation, SimulationCreationError, Simulator
from scenic.core.vectors import Vector
from scenic.simulators.basilisk.backend import BasiliskBackend, BasiliskBackendConfig
from scenic.simulators.basilisk.utils import (
    mrp_to_euler_zxy,
    scenic_orientation_to_mrp,
    vector3,
)


class BasiliskSimulator(Simulator):
    """Simulator factory for Basilisk asteroid-landing dynamics.

    Args:
        asteroid_rl_root: Optional path to the ``asteroid-rl-demo`` checkout.
            If omitted, uses ``ASTEROID_RL_ROOT`` or a sibling directory.
        gravity_mode: ``\"constant\"`` (Phase-1) or ``\"central\"`` (orbital).
        max_thrust: Peak thruster force in Newtons.
        use_flat_surface: Use flat pad altitude instead of Itokawa heightmap.
        flat_surface_z: World ``z`` of the flat pad when ``use_flat_surface``.
        enable_viz: Forwarded to asteroid_rl (Vizard).
        viz_mode: ``auto`` (save-file on Windows, live on macOS), ``live``, or ``file``.
        viz_save_file: Optional ``.bin`` path when recording for Vizard ``-loadFile``.
        default_timestep: Used when ``simulate(..., timestep=None)``.
    """

    def __init__(
        self,
        asteroid_rl_root: Optional[str] = None,
        gravity_mode: str = "constant",
        max_thrust: float = 275.0,
        use_flat_surface: bool = False,
        flat_surface_z: float = -30.0,
        enable_viz: bool = False,
        viz_mode: str = "auto",
        viz_save_file: str = "",
        default_timestep: float = 0.25,
    ):
        super().__init__()
        self.backend_config = BasiliskBackendConfig(
            asteroid_rl_root=asteroid_rl_root,
            gravity_mode=gravity_mode,
            max_thrust=max_thrust,
            use_flat_surface=use_flat_surface,
            flat_surface_z=flat_surface_z,
            enable_viz=enable_viz,
            viz_mode=viz_mode,
            viz_save_file=viz_save_file,
            control_dt=default_timestep,
        )
        self.default_timestep = float(default_timestep)

    def createSimulation(self, scene, **kwargs):
        if kwargs.get("timestep") is None:
            kwargs = dict(kwargs)
            kwargs["timestep"] = self.default_timestep
        return BasiliskSimulation(scene, backend_config=self.backend_config, **kwargs)


class BasiliskSimulation(Simulation):
    """One Basilisk episode driven by a Scenic scene."""

    def __init__(self, scene, *, backend_config: BasiliskBackendConfig, **kwargs):
        self.backend_config = backend_config
        self.backend = BasiliskBackend(backend_config)
        self._spacecraft = None
        super().__init__(scene, **kwargs)

    def setup(self):
        # Identify the spacecraft before object creation so we can build the sim.
        craft = None
        for obj in self.scene.objects:
            if getattr(obj, "basiliskKind", None) == "spacecraft":
                craft = obj
                break
        if craft is None:
            raise SimulationCreationError(
                "Basilisk scenes need at least one Spacecraft object "
                "(basiliskKind='spacecraft')."
            )

        pos = np.array(
            [float(craft.position.x), float(craft.position.y), float(craft.position.z)],
            dtype=np.float64,
        )
        if hasattr(craft, "velocity") and craft.velocity is not None:
            vel = np.array(
                [
                    float(craft.velocity.x),
                    float(craft.velocity.y),
                    float(craft.velocity.z),
                ],
                dtype=np.float64,
            )
        else:
            vel = np.array([0.0, 0.0, -1.5], dtype=np.float64)

        try:
            sigma = scenic_orientation_to_mrp(craft.orientation)
        except Exception:
            sigma = np.zeros(3, dtype=np.float64)

        try:
            self.backend.build(pos, vel, sigma)
        except Exception as exc:
            raise SimulationCreationError(f"Failed to build Basilisk sim: {exc}") from exc

        self._spacecraft = craft
        super().setup()

    def createObjectInSimulator(self, obj):
        kind = getattr(obj, "basiliskKind", None)
        if kind is None:
            return
        if kind == "asteroid":
            # Asteroid mesh already exists in MuJoCo; apply Scenic-sampled pose
            # so Vizard shows the probabilistic placement.
            pos = [
                float(obj.position.x),
                float(obj.position.y),
                float(obj.position.z),
            ]
            try:
                sigma = scenic_orientation_to_mrp(obj.orientation)
            except Exception:
                sigma = None
            self.backend.set_asteroid_pose(pos, sigma)
            obj.basiliskHandle = "asteroid"
            return
        if kind != "spacecraft":
            raise SimulationCreationError(f"Unknown basiliskKind: {kind!r}")

        # Soft-reset hub to this object's Scenic pose (supports multi-craft later
        # by rejecting >1 for now).
        if self._spacecraft is not None and obj is not self._spacecraft:
            raise SimulationCreationError(
                "Only one Spacecraft is supported in the Basilisk interface."
            )

        pos = [float(obj.position.x), float(obj.position.y), float(obj.position.z)]
        if hasattr(obj, "velocity") and obj.velocity is not None:
            vel = [float(obj.velocity.x), float(obj.velocity.y), float(obj.velocity.z)]
        else:
            vel = [0.0, 0.0, -1.5]
        try:
            sigma = scenic_orientation_to_mrp(obj.orientation)
        except Exception:
            sigma = [0.0, 0.0, 0.0]
        self.backend.soft_reset(pos, vel, sigma)
        obj.basiliskHandle = "hub"
        obj.throttle = float(getattr(obj, "throttle", 0.0) or 0.0)
        self._spacecraft = obj

    def executeActions(self, allActions):
        super().executeActions(allActions)
        self.backend.flush_controls()

    def step(self):
        self.backend.advance(self.timestep)

    def getProperties(self, obj, properties):
        kind = getattr(obj, "basiliskKind", None)
        if kind != "spacecraft":
            # Static / metadata objects keep Scenic values.
            vals = {
                "position": obj.position,
                "velocity": getattr(obj, "velocity", Vector(0, 0, 0)),
                "speed": float(getattr(obj, "speed", 0.0) or 0.0),
                "angularVelocity": Vector(0, 0, 0),
                "angularSpeed": 0.0,
                "yaw": obj.yaw,
                "pitch": obj.pitch,
                "roll": obj.roll,
            }
            for prop in properties:
                if prop not in vals:
                    vals[prop] = getattr(obj, prop, None)
            return vals

        r, v = self.backend.read_state()
        sigma = self.backend.read_mrp()
        yaw, pitch, roll = mrp_to_euler_zxy(sigma)
        speed = float(np.linalg.norm(v))
        vals = {
            "position": vector3(r),
            "velocity": vector3(v),
            "speed": speed,
            "angularVelocity": Vector(0, 0, 0),
            "angularSpeed": 0.0,
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
        }
        # Optional dynamic extras declared on the Scenic class.
        if "throttle" in properties:
            vals["throttle"] = float(getattr(obj, "throttle", 0.0) or 0.0)
        if "altitude" in properties:
            site = self.backend.landing_site()
            if self.backend.handles and self.backend.handles.config.use_flat_surface:
                vals["altitude"] = float(r[2] - site[2])
            else:
                vals["altitude"] = float(r[2] - site[2])
        for prop in properties:
            if prop not in vals:
                vals[prop] = getattr(obj, prop, None)
        return vals

    def destroy(self):
        self.backend.destroy()
        super().destroy()
