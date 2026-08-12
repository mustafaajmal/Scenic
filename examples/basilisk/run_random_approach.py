#!/usr/bin/env python
"""Sample several probabilistic Scenic scenes and record each in Vizard.

Shows that Scenic's distribution → different Basilisk/Vizard placements each run.

Usage::

    ..\\asteroid-rl-demo\\.venv\\Scripts\\python.exe examples\\basilisk\\run_random_approach.py
    ..\\asteroid-rl-demo\\.venv\\Scripts\\python.exe examples\\basilisk\\run_random_approach.py --samples 3 --open-last
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT.parent / "asteroid-rl-demo"
os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))
if DEMO.is_dir() and str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))

VIZ_DIR = ROOT / "outputs" / "viz" / "random_approach"
VIZ_DIR.mkdir(parents=True, exist_ok=True)


def _find_vizard():
    from asteroid_rl.env import _find_vizard_app

    return _find_vizard_app()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--timestep", type=float, default=0.25)
    parser.add_argument(
        "--scenario",
        type=str,
        default=str(Path(__file__).with_name("random_approach.scenic")),
    )
    parser.add_argument(
        "--open-last",
        action="store_true",
        help="Launch Vizard on the last recorded .bin",
    )
    args = parser.parse_args()

    import scenic

    scenario = scenic.scenarioFromFile(
        args.scenario,
        params={
            "enable_viz": True,
            "viz_mode": "file",
        },
    )

    bins = []
    print("Scenic samples a NEW scene each iteration; Basilisk/Vizard renders it.\n")
    for i in range(int(args.samples)):
        bin_path = VIZ_DIR / f"sample_{i:02d}_UnityViz.bin"
        # Recompile with a fresh save path so each recording is distinct.
        scenario_i = scenic.scenarioFromFile(
            args.scenario,
            params={
                "enable_viz": True,
                "viz_mode": "file",
                "viz_save_file": str(bin_path.resolve()),
            },
        )
        scene, _ = scenario_i.generate(maxIterations=50)
        craft = scene.egoObject
        # Find asteroid object if present
        asteroid = None
        for obj in scene.objects:
            if getattr(obj, "basiliskKind", None) == "asteroid":
                asteroid = obj
                break

        print(f"=== sample {i} ===")
        print(
            f"  spacecraft pos = ({craft.position.x:.2f}, {craft.position.y:.2f}, {craft.position.z:.2f})"
        )
        if hasattr(craft, "velocity") and craft.velocity is not None:
            print(
                f"  spacecraft vel = ({craft.velocity.x:.2f}, {craft.velocity.y:.2f}, {craft.velocity.z:.2f})"
            )
        if asteroid is not None:
            print(
                f"  asteroid    pos = ({asteroid.position.x:.2f}, {asteroid.position.y:.2f}, {asteroid.position.z:.2f})"
            )

        sim = scenario_i.getSimulator().simulate(
            scene,
            maxSteps=int(args.steps),
            timestep=float(args.timestep),
            verbosity=0,
        )
        if sim is None:
            print("  REJECTED by simulator")
            continue
        handles = getattr(getattr(sim, "backend", None), "handles", None)
        recorded = getattr(handles, "viz_bin_path", None) if handles else None
        recorded = recorded or str(bin_path.resolve())
        bins.append(recorded)
        print(f"  Vizard .bin   = {recorded}")
        print(f"  termination   = {sim.result.terminationType}")
        print()

    if not bins:
        raise SystemExit("No successful samples")

    print("Open any sample in Vizard, e.g.:")
    print(f'  Vizard.exe -loadFile "{bins[-1]}"')
    if args.open_last:
        app = _find_vizard()
        if app:
            subprocess.Popen([app, "-loadFile", bins[-1]])
            print("Launched Vizard on last sample.")
        else:
            print("Vizard.exe not found — open the .bin manually.")


if __name__ == "__main__":
    main()
