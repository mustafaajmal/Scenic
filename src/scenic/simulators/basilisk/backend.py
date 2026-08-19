"""Basilisk + MuJoCo backend for the Scenic Basilisk simulator.

Supports:
  * Stock Itokawa scene via ``asteroid_rl.env.build_sim``
  * Procedural asteroid meshes (Mars-style Gaussian bumps) rebuilt into a
    fresh MuJoCo XML each Scenic sample — shape **and** placement vary.
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

import numpy as np

_SISTER_DEMO = Path(__file__).resolve().parents[4].parent / "asteroid-rl-demo"


def _ensure_asteroid_rl_on_path(root: Optional[str | Path] = None) -> Path:
    candidates = []
    env = os.environ.get("ASTEROID_RL_ROOT")
    if env:
        candidates.append(Path(env))
    if root is not None:
        candidates.append(Path(root))
    candidates.append(_SISTER_DEMO)
    try:
        import asteroid_rl  # noqa: F401

        return Path(asteroid_rl.__file__).resolve().parent.parent
    except ImportError:
        pass
    for cand in candidates:
        if cand is None:
            continue
        if (cand / "asteroid_rl").is_dir():
            path = str(cand.resolve())
            if path not in sys.path:
                sys.path.insert(0, path)
            return cand.resolve()
    raise ImportError(
        "asteroid_rl not found. Set ASTEROID_RL_ROOT or place asteroid-rl-demo "
        f"next to Scenic (expected {_SISTER_DEMO})."
    )


@dataclass
class BasiliskBackendConfig:
    asteroid_rl_root: Optional[str] = None
    gravity_mode: str = "constant"
    max_thrust: float = 275.0
    use_flat_surface: bool = False
    flat_surface_z: float = -30.0
    enable_viz: bool = False
    viz_mode: str = "auto"
    viz_save_file: str = ""
    control_dt: float = 0.25


class BasiliskBackend:
    """Stateful wrapper around Basilisk/MuJoCo ``SimHandles``."""

    def __init__(self, config: Optional[BasiliskBackendConfig] = None):
        self.config = config or BasiliskBackendConfig()
        self._demo_root = _ensure_asteroid_rl_on_path(self.config.asteroid_rl_root)
        self.handles: Any = None
        self._hub: Any = None
        self._asteroid_body: Any = None
        self._landing_site: Optional[np.ndarray] = None
        self._pending_throttle: float = 0.0
        self._pending_point_dir: Optional[np.ndarray] = None
        self._asset_dir: Optional[Path] = None
        self._procedural_mesh: Any = None
        self._asteroid_pos_N: Optional[np.ndarray] = None
        self.procedural_meta: dict = {}

    @property
    def demo_root(self) -> Path:
        return self._demo_root

    def _make_config(self):
        from asteroid_rl.environment.gym_env import LandingEnvConfig

        cfg = LandingEnvConfig()
        cfg.gravity_mode = str(self.config.gravity_mode)
        cfg.max_thrust = float(self.config.max_thrust)
        cfg.use_flat_surface = bool(self.config.use_flat_surface)
        cfg.flat_surface_z = float(self.config.flat_surface_z)
        cfg.enable_viz = bool(self.config.enable_viz)
        cfg.viz_mode = str(self.config.viz_mode)
        cfg.viz_save_file = str(self.config.viz_save_file or "")
        cfg.control_dt = float(self.config.control_dt)
        cfg.reuse_sim = True
        if cfg.gravity_mode == "central":
            cfg.apply_orbital_defaults()
            cfg.max_thrust = max(float(self.config.max_thrust), float(cfg.max_thrust))
            cfg.use_flat_surface = bool(self.config.use_flat_surface)
            cfg.flat_surface_z = float(self.config.flat_surface_z)
        return cfg

    def build(
        self,
        position_N: Sequence[float],
        velocity_N: Sequence[float],
        sigma_BN: Optional[Sequence[float]] = None,
    ) -> None:
        """Stock Itokawa scene via ``asteroid_rl.env.build_sim``."""
        from asteroid_rl.environment.gym_env import (
            ASTEROID_BODY_NAME,
            SPACECRAFT_BODY_NAME,
            build_sim,
        )
        from Basilisk.architecture import messaging

        cfg = self._make_config()
        pos = np.asarray(position_N, dtype=np.float64).reshape(3)
        vel = np.asarray(velocity_N, dtype=np.float64).reshape(3)
        self.handles = build_sim(cfg, initial_position_N=pos, initial_velocity_N=vel)
        self._hub = self.handles.scene.getBody(SPACECRAFT_BODY_NAME)
        try:
            self._asteroid_body = self.handles.scene.getBody(ASTEROID_BODY_NAME)
        except Exception:
            self._asteroid_body = None
        self._landing_site = cfg.target_array()
        if sigma_BN is not None:
            self.set_attitude_mrp(sigma_BN)
        self.handles.thrust_msg.write(messaging.SingleActuatorMsgPayload(input=0.0))
        self._pending_throttle = 0.0
        self._pending_point_dir = None
        self.procedural_meta = {"mode": "stock_itokawa"}
        self._procedural_mesh = None
        self._asteroid_pos_N = None

    def build_procedural(
        self,
        *,
        craft_position_N: Sequence[float],
        craft_velocity_N: Sequence[float],
        craft_sigma_BN: Optional[Sequence[float]] = None,
        asteroid_position_N: Sequence[float],
        radii: Sequence[float],
        bumps: Sequence[Tuple[Sequence[float], float, float]] = (),
        craters: Sequence = (),
        ridges: Sequence = (),
        subdivisions: int = 3,
        detail_seed: int = 0,
        noise_amp: float = 2.0,
    ) -> None:
        """Rebuild MuJoCo from a Scenic-generated asteroid mesh + placement."""
        from Basilisk.architecture import messaging
        from Basilisk.simulation import mujoco, svIntegrators
        from Basilisk.utilities import SimulationBaseClass, macros

        from asteroid_rl.dynamics import gravity as gravity_mod
        from asteroid_rl.environment.gym_env import (
            ASTEROID_BODY_NAME,
            SIM_DT,
            SIM_PROCESS_NAME,
            SIM_TASK_NAME,
            SPACECRAFT_BODY_NAME,
            THRUSTER_NAME,
            SimHandles,
            default_viz_bin_path,
            resolve_viz_mode,
            _setup_vizard,
        )
        from scenic.simulators.basilisk.asteroid_mesh import (
            BumpSpec,
            CraterSpec,
            RidgeSpec,
            generate_asteroid_mesh,
            write_albedo_texture,
            write_landing_xml,
            write_obj,
        )

        work = Path(tempfile.mkdtemp(prefix="scenic_basilisk_asteroid_"))
        self._asset_dir = work
        bump_specs = [
            BumpSpec(
                center=(float(c[0]), float(c[1]), float(c[2])),
                height=float(h),
                spread=float(s),
            )
            for c, h, s in bumps
        ]
        crater_specs = [
            CraterSpec(
                center=(float(c[0]), float(c[1]), float(c[2])),
                depth=float(depth),
                radius=float(radius),
                rim_height=float(rim),
            )
            for c, depth, radius, rim in craters
        ]
        ridge_specs = [
            RidgeSpec(
                center=(float(c[0]), float(c[1]), float(c[2])),
                direction=(float(d[0]), float(d[1]), float(d[2])),
                height=float(h),
                length=float(length),
                width=float(width),
            )
            for c, d, h, length, width in ridges
        ]
        mesh = generate_asteroid_mesh(
            radii=radii,
            bumps=bump_specs,
            craters=crater_specs,
            ridges=ridge_specs,
            subdivisions=int(subdivisions),
            noise_amp=float(noise_amp),
            noise_seed=int(detail_seed),
        )
        self._procedural_mesh = mesh
        ast = np.asarray(asteroid_position_N, dtype=np.float64).reshape(3)
        self._asteroid_pos_N = ast.copy()
        obj_path = write_obj(mesh, work / "procedural_asteroid.obj")
        tex_path = write_albedo_texture(mesh, work / "procedural_asteroid.jpg")
        xml_path = write_landing_xml(
            xml_path=work / "sat_ast_landing_dynamic.xml",
            mesh_filename=obj_path.name,
            asteroid_pos=asteroid_position_N,
        )

        cfg = self._make_config()
        ast = np.asarray(asteroid_position_N, dtype=np.float64).reshape(3)
        cfg.asteroid_com_N = (float(ast[0]), float(ast[1]), float(ast[2]))
        rz = float(radii[2]) if len(radii) > 2 else float(radii[0])
        cfg.use_flat_surface = True
        cfg.flat_surface_z = float(ast[2] + 0.85 * rz)
        self._landing_site = np.array(
            [ast[0], ast[1], cfg.flat_surface_z], dtype=np.float64
        )

        scSim = SimulationBaseClass.SimBaseClass()
        process = scSim.CreateNewProcess(SIM_PROCESS_NAME)
        task = scSim.CreateNewTask(SIM_TASK_NAME, macros.sec2nano(SIM_DT))
        process.addTask(task)

        scene = mujoco.MJScene.fromFile(str(xml_path), files=[str(obj_path)])
        scSim.AddModelToTask(SIM_TASK_NAME, scene)

        integ = svIntegrators.svIntegratorRKF45(scene)
        integ.setRelativeTolerance(1e-3)
        integ.setAbsoluteTolerance(1e-3)
        scene.setIntegrator(integ)

        if str(cfg.gravity_mode).lower() == "central":
            gravity = gravity_mod.CentralGravity(
                mu=float(cfg.gravity_mu),
                mass=float(cfg.gravity_mass_ref),
                com_N=cfg.asteroid_com_N,
            )
        else:
            gravity = gravity_mod.ConstantGravity(force_N=[0.0, 0.0, -200.0])
        scene.AddModelToDynamicsTask(gravity)
        gravity_site = scene.getBody(SPACECRAFT_BODY_NAME).getOrigin()
        gravity_actuator = scene.addForceActuator("hub_gravity", gravity_site)
        gravity_actuator.forceInMsg.subscribeTo(gravity.forceOutMsg)
        gravity.frameInMsg.subscribeTo(gravity_site.stateOutMsg)

        thrust_msg = messaging.SingleActuatorMsg()
        thrust_msg.write(messaging.SingleActuatorMsgPayload(input=0.0))
        scene.getSingleActuator(THRUSTER_NAME).actuatorInMsg.subscribeTo(thrust_msg)

        state_recorder = (
            scene.getBody(SPACECRAFT_BODY_NAME).getOrigin().stateOutMsg.recorder()
        )
        scSim.AddModelToTask(SIM_TASK_NAME, state_recorder)

        viz = thruster_viz_writer = camera_mod = viz_bin_path = None
        if bool(cfg.enable_viz or cfg.enable_camera):
            mode = resolve_viz_mode(cfg.viz_mode)
            if cfg.enable_camera:
                mode = "live"
            save_path = cfg.viz_save_file or default_viz_bin_path("scenic_procedural")
            tex_arg = str(tex_path) if tex_path.is_file() else ""
            viz, thruster_viz_writer, camera_mod, viz_bin_path = _setup_vizard(
                scSim,
                scene,
                thrust_msg,
                cfg.max_thrust,
                show_gui=bool(cfg.enable_viz),
                enable_camera=bool(cfg.enable_camera),
                camera_width=int(cfg.camera_width),
                camera_height=int(cfg.camera_height),
                camera_render_rate_sec=float(cfg.control_dt),
                viz_mode=mode,
                viz_save_file=save_path,
                viz_asteroid_model_path=str(obj_path),
                viz_asteroid_texture_path=tex_arg,
                viz_asteroid_scale=1.0,
            )

        scSim.InitializeSimulation()
        self.handles = SimHandles(
            scSim=scSim,
            scene=scene,
            thrust_msg=thrust_msg,
            state_recorder=state_recorder,
            gravity_model=gravity,
            gravity_actuator=gravity_actuator,
            thruster_viz_writer=thruster_viz_writer,
            viz=viz,
            viz_bin_path=viz_bin_path,
            camera_mod=camera_mod,
            config=cfg,
            absolute_sim_time_sec=0.0,
        )
        self._hub = scene.getBody(SPACECRAFT_BODY_NAME)
        try:
            self._asteroid_body = scene.getBody(ASTEROID_BODY_NAME)
        except Exception:
            self._asteroid_body = None

        pos = np.asarray(craft_position_N, dtype=np.float64).reshape(3)
        vel = np.asarray(craft_velocity_N, dtype=np.float64).reshape(3)
        self._hub.setPosition(pos.tolist())
        self._hub.setVelocity(vel.tolist())
        if craft_sigma_BN is not None:
            self.set_attitude_mrp(craft_sigma_BN)
        else:
            self._hub.setAttitudeRate([0.0, 0.0, 0.0])
        self.handles.thrust_msg.write(messaging.SingleActuatorMsgPayload(input=0.0))
        self._pending_throttle = 0.0
        self._pending_point_dir = None
        self.advance(SIM_DT)

        self.procedural_meta = {
            "mode": "procedural",
            "asset_dir": str(work),
            "obj_path": str(obj_path),
            "texture_path": str(tex_path) if tex_path.is_file() else "",
            "xml_path": str(xml_path),
            "asteroid_pos": [float(x) for x in ast],
            "radii": [float(x) for x in radii],
            "n_bumps": len(bump_specs),
            "n_craters": len(crater_specs),
            "n_ridges": len(ridge_specs),
            "detail_seed": int(detail_seed),
            "noise_amp": float(noise_amp),
            "n_vertices": int(len(mesh.vertices)),
            "extents": [float(x) for x in mesh.extents],
            "surface_altitude": "mesh_raycast",
        }

    def surface_altitude(self, craft_position_N: Sequence[float]) -> float:
        """Radar-like range from craft to the real surface (mesh or heightmap)."""
        from scenic.simulators.basilisk.asteroid_mesh import world_surface_altitude

        craft = np.asarray(craft_position_N, dtype=np.float64).reshape(3)
        site = self.landing_site()
        pad_fallback = float(craft[2] - site[2])
        if self._procedural_mesh is not None and self._asteroid_pos_N is not None:
            return world_surface_altitude(
                self._procedural_mesh,
                craft_world=craft,
                asteroid_world=self._asteroid_pos_N,
                fallback=pad_fallback,
            )
        # Stock Itokawa: heightmap column altitude (closest available to radar).
        try:
            from asteroid_rl.environment.surface import get_surface_map

            if self.handles and not bool(self.handles.config.use_flat_surface):
                return float(get_surface_map().altitude(craft))
        except Exception:
            pass
        return pad_fallback

    def soft_reset(
        self,
        position_N: Sequence[float],
        velocity_N: Sequence[float],
        sigma_BN: Optional[Sequence[float]] = None,
    ) -> None:
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
        self.advance(0.02)

    def set_asteroid_pose(
        self,
        position_N: Sequence[float],
        sigma_BN: Optional[Sequence[float]] = None,
    ) -> None:
        """No-op for welded bodies; procedural asteroids are placed at XML write time."""
        if self._asteroid_body is None or not hasattr(self._asteroid_body, "setPosition"):
            return
        try:
            self._asteroid_body.setPosition(
                list(np.asarray(position_N, dtype=float).reshape(3))
            )
        except Exception:
            return

    def set_attitude_mrp(self, sigma_BN: Sequence[float]) -> None:
        if self._hub is None:
            return
        self._hub.setAttitude(list(np.asarray(sigma_BN, dtype=float).reshape(3)))
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
        from Basilisk.architecture import messaging
        from asteroid_rl.dynamics.pointing import apply_pointing_direction

        if self.handles is None or self._hub is None:
            return
        if self._pending_point_dir is not None:
            apply_pointing_direction(self._hub, self._pending_point_dir)
        thrust_N = self._pending_throttle * float(self.handles.config.max_thrust)
        self.handles.thrust_msg.write(
            messaging.SingleActuatorMsgPayload(input=float(thrust_N))
        )

    def advance(self, dt: float) -> None:
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
        if self.handles is None:
            return np.zeros(3), np.zeros(3)
        rec = self.handles.state_recorder
        return (
            np.array(rec.r_BN_N[-1], dtype=np.float64),
            np.array(rec.v_BN_N[-1], dtype=np.float64),
        )

    def read_mrp(self) -> np.ndarray:
        if self.handles is None:
            return np.zeros(3)
        return np.array(self.handles.state_recorder.sigma_BN[-1], dtype=np.float64)

    def read_omega_B(self) -> np.ndarray:
        """Body-frame angular rate ``omega_BN_B`` (rad/s) from the state recorder."""
        if self.handles is None:
            return np.zeros(3)
        rec = self.handles.state_recorder
        if hasattr(rec, "omega_BN_B") and len(rec.times()) > 0:
            return np.array(rec.omega_BN_B[-1], dtype=np.float64).reshape(3)
        return np.zeros(3)

    def read_omega_N(self) -> np.ndarray:
        """Inertial-frame angular rate (rad/s) for Scenic ``angularVelocity``."""
        from Basilisk.utilities import RigidBodyKinematics as rbk

        omega_B = self.read_omega_B()
        sigma = self.read_mrp()
        c_bn = np.asarray(rbk.MRP2C(list(sigma)), dtype=np.float64)
        return c_bn.T @ omega_B

    def landing_site(self) -> np.ndarray:
        if self._landing_site is not None:
            return np.asarray(self._landing_site, dtype=np.float64).reshape(3)
        return np.array([0.0, 0.0, -30.0], dtype=np.float64)

    def destroy(self) -> None:
        self.handles = None
        self._hub = None
        self._asteroid_body = None
