"""Tests for the Basilisk Scenic simulator interface."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEMO = ROOT.parent / "asteroid-rl-demo"
if DEMO.is_dir():
    os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))
    if str(DEMO) not in sys.path:
        sys.path.insert(0, str(DEMO))

pytest.importorskip("numpy")

basilisk = pytest.importorskip("Basilisk")
asteroid_rl = pytest.importorskip("asteroid_rl")


def test_import_basilisk_simulator():
    from scenic.simulators.basilisk import BasiliskSimulator

    assert BasiliskSimulator is not None


def test_mrp_orientation_roundtrip():
    import numpy as np
    from scenic.core.vectors import Orientation
    from scenic.simulators.basilisk.utils import (
        mrp_to_scenic_orientation,
        scenic_orientation_to_mrp,
    )

    ori = Orientation.fromEuler(0.1, -0.2, 0.05)
    sigma = scenic_orientation_to_mrp(ori)
    back = mrp_to_scenic_orientation(sigma)
    # Quaternions are unique up to sign; compare rotation matrices.
    m1 = ori.getRotation().as_matrix()
    m2 = back.getRotation().as_matrix()
    assert np.allclose(m1, m2, atol=1e-5)


def test_soft_brake_scenario_runs():
    import scenic

    path = ROOT / "examples" / "basilisk" / "soft_brake.scenic"
    scenario = scenic.scenarioFromFile(str(path))
    scene, _ = scenario.generate(maxIterations=5)
    sim = scenario.getSimulator().simulate(
        scene, maxSteps=8, timestep=0.25, verbosity=0
    )
    assert sim is not None
    assert len(sim.result.trajectory) >= 2
    # Craft should still be somewhere near the approach corridor.
    final_objs = sim.result.trajectory[-1]
    # trajectory entries are typically tuples of positions / states
    assert final_objs is not None


def test_procedural_mesh_varies():
    import numpy as np
    from scenic.simulators.basilisk.asteroid_mesh import (
        BumpSpec,
        CraterSpec,
        RidgeSpec,
        generate_asteroid_mesh,
    )

    a = generate_asteroid_mesh(
        radii=(50, 40, 35),
        bumps=[BumpSpec(center=(40, 0, 0), height=8.0, spread=15.0)],
        craters=[CraterSpec(center=(0, 35, 0), depth=6.0, radius=8.0, rim_height=2.0)],
        ridges=[
            RidgeSpec(
                center=(0, 0, 30),
                direction=(1, 0.2, 0),
                height=7.0,
                length=25.0,
                width=5.0,
            )
        ],
        subdivisions=2,
        noise_amp=2.0,
        noise_seed=1,
    )
    b = generate_asteroid_mesh(
        radii=(60, 55, 45),
        bumps=[BumpSpec(center=(0, 50, 0), height=12.0, spread=20.0)],
        subdivisions=2,
        noise_amp=2.5,
        noise_seed=99,
    )
    assert len(a.vertices) >= 12
    assert not np.allclose(a.extents, b.extents)


def test_dynamic_asteroid_scenario_runs():
    import scenic

    path = ROOT / "examples" / "basilisk" / "dynamic_asteroid.scenic"
    scenario = scenic.scenarioFromFile(str(path))
    scene, _ = scenario.generate(maxIterations=20)
    sim = scenario.getSimulator().simulate(
        scene, maxSteps=6, timestep=0.25, verbosity=0
    )
    assert sim is not None
    meta = getattr(sim.backend, "procedural_meta", {}) or {}
    assert meta.get("mode") == "procedural"
    assert meta.get("n_vertices", 0) > 0


def test_altitude_brake_closed_loop():
    import scenic

    path = ROOT / "examples" / "basilisk" / "altitude_brake.scenic"
    scenario = scenic.scenarioFromFile(str(path), params={"enable_viz": False})
    scene, _ = scenario.generate(maxIterations=30)
    sim = scenario.getSimulator().simulate(
        scene, maxSteps=12, timestep=0.25, verbosity=0
    )
    assert sim is not None
    assert len(sim.result.trajectory) >= 2
    craft = next(
        o for o in sim.objects if getattr(o, "basiliskKind", None) == "spacecraft"
    )
    assert craft.altitude is not None
    assert float(craft.altitude) < 200.0


def test_inline_compile_scenic_and_angular_props():
    from scenic import scenarioFromString
    from scenic.simulators.basilisk import getBasiliskSimulator

    code = """
model scenic.simulators.basilisk.model
param use_flat_surface = True
param flat_surface_z = -30.0
param enable_viz = False
param timestep = 0.25
behavior B():
    while True:
        take SetThrottleAction(0.4)
        wait
ego = new Spacecraft at (0, 0, 70), with velocity (0, 0, -1.0), with behavior B
terminate after 2 seconds
"""
    scenario = scenarioFromString(code)
    scene, _ = scenario.generate(maxIterations=5)
    sim = getBasiliskSimulator().simulate(scene, maxSteps=4, timestep=0.25, verbosity=0)
    assert sim is not None
    craft = next(
        o for o in sim.objects if getattr(o, "basiliskKind", None) == "spacecraft"
    )
    # angularVelocity is wired (may be ~0 without torques, but must be a Vector)
    assert hasattr(craft.angularVelocity, "x")
    assert float(craft.speed) >= 0.0


def test_env_shim_import():
    from asteroid_rl.env import build_sim, LandingEnvConfig

    assert build_sim is not None
    assert LandingEnvConfig is not None
