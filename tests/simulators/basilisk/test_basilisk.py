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
