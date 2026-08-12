#!/usr/bin/env python
"""Print a short trajectory so you can *see* Basilisk+Scenic moving the craft.

Run from Scenic root with asteroid-rl on PYTHONPATH::

    ..\\asteroid-rl-demo\\.venv\\Scripts\\python.exe examples\\basilisk\\verify_trajectory.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT.parent / "asteroid-rl-demo"
os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))
if DEMO.is_dir() and str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))

import scenic


def main() -> None:
    path = Path(__file__).with_name("soft_brake.scenic")
    scenario = scenic.scenarioFromFile(str(path))
    scene, _ = scenario.generate(maxIterations=5)
    sim = scenario.getSimulator().simulate(
        scene, maxSteps=20, timestep=0.25, verbosity=0
    )
    if sim is None:
        raise SystemExit("simulation rejected")

    print("termination:", sim.result.terminationType)
    print("steps:", len(sim.result.trajectory) - 1)
    print("t_step  z(m)     (expect z to fall under gravity+partial brake)")
    for i, state in enumerate(sim.result.trajectory):
        # state is typically a tuple of object positions
        pos = state[0] if isinstance(state, (tuple, list)) else state
        z = float(pos.z) if hasattr(pos, "z") else float(pos[2])
        print(f"{i:6d}  {z:8.3f}")

    z0 = float(sim.result.trajectory[0][0].z)
    z1 = float(sim.result.trajectory[-1][0].z)
    dz = z1 - z0
    print(f"delta_z = {dz:.3f} m")
    if dz >= -0.5:
        raise SystemExit("FAIL: craft barely moved downward — interface likely broken")
    print("OK: altitude decreased — Scenic actions are driving Basilisk.")


if __name__ == "__main__":
    main()
