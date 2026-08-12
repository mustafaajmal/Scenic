#!/usr/bin/env python
"""Sample procedural asteroids and record each in Vizard.

Shows per-sample variation in asteroid pose, size, mesh, and craft start.
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

VIZ_DIR = ROOT / "outputs" / "viz" / "dynamic_asteroid"
VIZ_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--samples",
        type=int,
        default=3,
        help="How many independent Scenic generate()+simulate runs (default: 3).",
    )
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Base random seed for Scenic/NumPy. Sample i uses seed+i.",
    )
    parser.add_argument("--open-last", action="store_true")
    parser.add_argument(
        "--scenario",
        default=str(Path(__file__).with_name("dynamic_asteroid.scenic")),
    )
    args = parser.parse_args()

    import random

    import numpy as np
    import scenic

    bins = []
    print("Each sample rebuilds a NEW asteroid mesh + placement for Vizard.\n")
    if args.seed is not None:
        print(f"Base seed = {args.seed} (sample i uses seed+i)\n")
    for i in range(int(args.samples)):
        if args.seed is not None:
            s = int(args.seed) + i
            random.seed(s)
            np.random.seed(s)
            print(f"--- sample {i} seed={s} ---")
        bin_path = VIZ_DIR / f"sample_{i:02d}_UnityViz.bin"
        scenario = scenic.scenarioFromFile(
            args.scenario,
            params={
                "enable_viz": True,
                "viz_mode": "file",
                "viz_save_file": str(bin_path.resolve()),
            },
        )
        scene, _ = scenario.generate(maxIterations=80)
        craft = scene.egoObject
        asteroid = next(
            (
                o
                for o in scene.objects
                if getattr(o, "basiliskKind", None) == "procedural_asteroid"
            ),
            None,
        )
        n_bumps = sum(
            1
            for o in scene.objects
            if getattr(o, "basiliskKind", None) == "asteroid_bump"
        )
        n_craters = sum(
            1
            for o in scene.objects
            if getattr(o, "basiliskKind", None) == "asteroid_crater"
        )
        n_ridges = sum(
            1
            for o in scene.objects
            if getattr(o, "basiliskKind", None) == "asteroid_ridge"
        )
        print(f"=== sample {i} ===")
        print(
            f"  craft     = ({craft.position.x:.1f}, {craft.position.y:.1f}, {craft.position.z:.1f})"
        )
        if asteroid is not None:
            print(
                f"  asteroid  = ({asteroid.position.x:.1f}, {asteroid.position.y:.1f}, {asteroid.position.z:.1f})"
            )
            print(
                f"  radii     = ({float(asteroid.radiusX):.1f}, {float(asteroid.radiusY):.1f}, {float(asteroid.radiusZ):.1f})"
            )
            print(
                f"  features  = bumps={n_bumps} craters={n_craters} ridges={n_ridges}"
            )
            print(
                f"  detailSeed= {int(float(getattr(asteroid, 'detailSeed', 0)))}"
            )

        sim = scenario.getSimulator().simulate(
            scene, maxSteps=int(args.steps), timestep=0.25, verbosity=0
        )
        if sim is None:
            print("  REJECTED")
            continue
        meta = getattr(getattr(sim, "backend", None), "procedural_meta", {})
        print(f"  mesh verts= {meta.get('n_vertices')}")
        print(f"  extents   = {meta.get('extents')}")
        print(f"  texture   = {meta.get('texture_path')}")
        print(f"  obj       = {meta.get('obj_path')}")
        recorded = getattr(
            getattr(getattr(sim, "backend", None), "handles", None),
            "viz_bin_path",
            None,
        ) or str(bin_path.resolve())
        bins.append(recorded)
        print(f"  Vizard    = {recorded}\n")

    if not bins:
        raise SystemExit("no successful samples")
    print("Open with: Vizard.exe -loadFile \"" + bins[-1] + "\"")
    if args.open_last:
        from asteroid_rl.env import _find_vizard_app

        app = _find_vizard_app()
        if app:
            subprocess.Popen([app, "-loadFile", bins[-1]])


if __name__ == "__main__":
    main()
