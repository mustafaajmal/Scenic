#!/usr/bin/env python
"""Demo: Scenic miss-point ICs → reorient toward asteroid → soft land.

Uses ``acquire_and_land.scenic``: random attitude/pose, then PointAtTarget +
mesh-radar altitude throttle. Optional Vizard save + open.
"""

from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT.parent / "asteroid-rl-demo"
os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))
if DEMO.is_dir() and str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))

SCENARIO = Path(__file__).with_name("acquire_and_land.scenic")
OUT = ROOT / "outputs" / "acquire_and_land"
OUT.mkdir(parents=True, exist_ok=True)

CONTACT_ALT_MIN, CONTACT_ALT_MAX = 0.3, 8.0
REACH_SPEED = 3.5


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=200)
    p.add_argument("--viz", action="store_true")
    p.add_argument("--open-viz", action="store_true")
    args = p.parse_args()

    import scenic

    print("Acquire-and-land: miss-point starts → look-at-body → soft brake\n")
    bins: list[str] = []
    n_ok = 0
    for i in range(int(args.episodes)):
        s = int(args.seed) + i
        random.seed(s)
        np.random.seed(s)
        viz_bin = ""
        params = {"enable_viz": False, "timestep": 0.25}
        if args.viz and i == 0:
            viz_bin = str((OUT / f"ep{i:02d}_seed{s}_UnityViz.bin").resolve())
            params = {
                "enable_viz": True,
                "viz_mode": "file",
                "viz_save_file": viz_bin,
            }
        scenario = scenic.scenarioFromFile(str(SCENARIO), params=params)
        scene, _ = scenario.generate(maxIterations=120)
        craft = scene.egoObject
        print(
            f"[ep{i} seed={s}] start=({craft.position.x:.1f}, "
            f"{craft.position.y:.1f}, {craft.position.z:.1f}) "
            f"yaw/pitch/roll≈({craft.yaw:.2f}, {craft.pitch:.2f}, {craft.roll:.2f})"
        )
        sim = scenario.getSimulator().simulate(
            scene, maxSteps=int(args.max_steps), timestep=0.25, verbosity=0
        )
        if sim is None:
            print("  REJECTED")
            continue
        records = getattr(sim.result, "records", {}) or {}
        alts = [float(x[-1]) if isinstance(x, (tuple, list)) else float(x) for x in records.get("altitude_m", [])]
        spds = [float(x[-1]) if isinstance(x, (tuple, list)) else float(x) for x in records.get("speed_mps", [])]
        reach = False
        for a, sp in zip(alts, spds):
            if CONTACT_ALT_MIN <= a <= CONTACT_ALT_MAX and sp <= REACH_SPEED:
                reach = True
                break
        min_alt = min(alts) if alts else float("nan")
        final_spd = spds[-1] if spds else float("nan")
        n_ok += int(reach)
        print(f"  min_alt={min_alt:.2f} final_spd={final_spd:.2f} reach={reach}")
        if viz_bin:
            bins.append(viz_bin)

    print(f"\nreach rate = {n_ok}/{args.episodes}")
    if bins:
        print("Vizard:", bins[0])
    if args.open_viz and bins:
        from asteroid_rl.environment.gym_env import _find_vizard_app
        from asteroid_rl.sensing.camera import launch_vizard_load_file

        launch_vizard_load_file(
            bins[-1],
            find_app_fn=_find_vizard_app,
            popen_fn=subprocess.Popen,
        )


if __name__ == "__main__":
    main()
