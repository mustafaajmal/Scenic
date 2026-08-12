#!/usr/bin/env python
"""Run a Basilisk Scenic example programmatically.

Usage (from Scenic repo root, with asteroid-rl-demo on PYTHONPATH)::

    python examples/basilisk/run_soft_brake.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT.parent / "asteroid-rl-demo"
if DEMO.is_dir() and str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))
os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))

import scenic


def main() -> None:
    scenario_path = Path(__file__).with_name("soft_brake.scenic")
    scenario = scenic.scenarioFromFile(str(scenario_path))
    scene, _ = scenario.generate(maxIterations=10)
    simulator = scenario.getSimulator()
    sim = simulator.simulate(scene, maxSteps=40, timestep=0.25, verbosity=1)
    if sim is None:
        raise SystemExit("simulation rejected")
    print("termination:", sim.result.terminationType, sim.result.terminationReason)
    final = sim.result.trajectory[-1]
    print("final state sample:", final)


if __name__ == "__main__":
    main()
