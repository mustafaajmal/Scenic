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
        attitude_mode: str = "slew",
        slew_rate_deg_s: float = 25.0,
    ):
        super().__init__()
        root = asteroid_rl_root if asteroid_rl_root else None
        self.backend_config = BasiliskBackendConfig(
            asteroid_rl_root=root,
            gravity_mode=gravity_mode,
            max_thrust=max_thrust,
            use_flat_surface=use_flat_surface,
            flat_surface_z=flat_surface_z,
            enable_viz=enable_viz,
            viz_mode=viz_mode,
            viz_save_file=viz_save_file,
            control_dt=default_timestep,
            attitude_mode=attitude_mode,
            slew_rate_deg_s=slew_rate_deg_s,
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
        craft = None
        asteroid = None
        bumps = []
        craters = []
        ridges = []
        for obj in self.scene.objects:
            kind = getattr(obj, "basiliskKind", None)
            if kind == "spacecraft" and craft is None:
                craft = obj
            elif kind == "procedural_asteroid":
                asteroid = obj
            elif kind == "asteroid_bump":
                bumps.append(obj)
            elif kind == "asteroid_crater":
                craters.append(obj)
            elif kind == "asteroid_ridge":
                ridges.append(obj)

        if asteroid is not None:
            for b in getattr(asteroid, "terrain", ()) or ():
                kind = getattr(b, "basiliskKind", None)
                if kind == "asteroid_bump" and b not in bumps:
                    bumps.append(b)
                elif kind == "asteroid_crater" and b not in craters:
                    craters.append(b)
                elif kind == "asteroid_ridge" and b not in ridges:
                    ridges.append(b)

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
            if asteroid is not None:
                ast_pos = np.array(
                    [
                        float(asteroid.position.x),
                        float(asteroid.position.y),
                        float(asteroid.position.z),
                    ],
                    dtype=np.float64,
                )
                radii = (
                    float(getattr(asteroid, "radiusX", getattr(asteroid, "width", 50.0) / 2)),
                    float(getattr(asteroid, "radiusY", getattr(asteroid, "length", 40.0) / 2)),
                    float(getattr(asteroid, "radiusZ", getattr(asteroid, "height", 35.0) / 2)),
                )

                def _rel(obj):
                    return (
                        float(obj.position.x) - float(ast_pos[0]),
                        float(obj.position.y) - float(ast_pos[1]),
                        float(obj.position.z) - float(ast_pos[2]),
                    )

                bump_specs = [
                    (
                        _rel(b),
                        float(getattr(b, "bumpHeight", getattr(b, "height", 2.0))),
                        float(getattr(b, "spread", 8.0)),
                    )
                    for b in bumps
                ]
                crater_specs = [
                    (
                        _rel(c),
                        float(getattr(c, "craterDepth", 5.0)),
                        float(getattr(c, "craterRadius", 8.0)),
                        float(getattr(c, "rimHeight", 2.0)),
                    )
                    for c in craters
                ]
                ridge_specs = []
                for r in ridges:
                    d = getattr(r, "ridgeDir", (1.0, 0.0, 0.0))
                    if hasattr(d, "x"):
                        direction = (float(d.x), float(d.y), float(d.z))
                    else:
                        direction = (float(d[0]), float(d[1]), float(d[2]))
                    ridge_specs.append(
                        (
                            _rel(r),
                            direction,
                            float(getattr(r, "ridgeHeight", 6.0)),
                            float(getattr(r, "ridgeLength", 20.0)),
                            float(getattr(r, "ridgeWidth", 5.0)),
                        )
                    )
                self.backend.build_procedural(
                    craft_position_N=pos,
                    craft_velocity_N=vel,
                    craft_sigma_BN=sigma,
                    asteroid_position_N=ast_pos,
                    radii=radii,
                    bumps=bump_specs,
                    craters=crater_specs,
                    ridges=ridge_specs,
                    subdivisions=int(getattr(asteroid, "subdivisions", 3)),
                    detail_seed=int(float(getattr(asteroid, "detailSeed", 0)) % 1_000_000_007),
                    noise_amp=float(getattr(asteroid, "noiseAmp", 2.0)),
                )
            else:
                self.backend.build(pos, vel, sigma)
        except Exception as exc:
            raise SimulationCreationError(f"Failed to build Basilisk sim: {exc}") from exc

        self._spacecraft = craft
        super().setup()

    def createObjectInSimulator(self, obj):
        kind = getattr(obj, "basiliskKind", None)
        if kind is None:
            return
        if kind in ("asteroid_bump", "asteroid_crater", "asteroid_ridge"):
            # Terrain features only contribute to mesh generation in setup().
            return
        if kind in ("asteroid", "procedural_asteroid"):
            # Procedural asteroids are baked into XML at build time.
            # Stock asteroids remain metadata / welded mesh.
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
        omega_N = self.backend.read_omega_N()
        ang_speed = float(np.linalg.norm(omega_N))
        vals = {
            "position": vector3(r),
            "velocity": vector3(v),
            "speed": speed,
            "angularVelocity": vector3(omega_N),
            "angularSpeed": ang_speed,
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
        }
        # Optional dynamic extras declared on the Scenic class.
        if "throttle" in properties:
            vals["throttle"] = float(getattr(obj, "throttle", 0.0) or 0.0)
        if "altitude" in properties:
            vals["altitude"] = float(self.backend.surface_altitude(r))
        if "landed" in properties:
            vals["landed"] = bool(getattr(self.backend, "_landed", False))
        if "inContact" in properties:
            vals["inContact"] = bool(getattr(self.backend, "_in_contact", False))
        if "guidancePhase" in properties:
            vals["guidancePhase"] = str(
                getattr(self.backend, "_last_guidance", {}).get("phase", "")
            )
        for prop in properties:
            if prop not in vals:
                vals[prop] = getattr(obj, prop, None)
        return vals

    def destroy(self):
        self.backend.destroy()
        super().destroy()
