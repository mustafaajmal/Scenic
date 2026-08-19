#!/usr/bin/env python
"""Run the three coexisting lander modes (legacy soft-brake, acquire, divert).

Modes
-----
soft_brake  — already facing body, inbound soft land (MODE A)
acquire     — miss attitude → slew look-at-body → soft land (MODE B)
divert      — miss traj/attitude → velocity-target divert → land (MODE C)

Attitude uses rate-limited slew by default (RW stand-in). Pass
``--instant-attitude`` for the old MRP teleport.

Example::

    ../asteroid-rl-demo/.venv/bin/python examples/basilisk/run_lander_modes.py \\
      --mode divert --episodes 4 --seed 0 --viz --open-viz
"""

from __future__ import annotations

import argparse
import json
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

SCENARIOS = {
    "soft_brake": Path(__file__).with_name("soft_brake_inbound.scenic"),
    "acquire": Path(__file__).with_name("acquire_and_land.scenic"),
    "divert": Path(__file__).with_name("divert_and_land.scenic"),
}

CONTACT_ALT_MIN, CONTACT_ALT_MAX = 0.3, 8.0
REACH_SPEED = 3.5


def _series(records: dict, key: str) -> list[float]:
    out = []
    for item in records.get(key, []) or []:
        try:
            out.append(float(item[-1] if isinstance(item, (tuple, list)) else item))
        except Exception:
            continue
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode",
        choices=list(SCENARIOS),
        default="divert",
        help="Which lander scenario to run",
    )
    p.add_argument("--all-modes", action="store_true", help="Run A/B/C sequentially")
    p.add_argument("--episodes", type=int, default=4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Sim steps at 0.25s. Default 360 (~90s); divert/all-modes default 720 (~180s).",
    )
    p.add_argument("--viz", action="store_true")
    p.add_argument("--open-viz", action="store_true")
    p.add_argument(
        "--instant-attitude",
        action="store_true",
        help="Use legacy MRP teleport instead of rate-limited slew",
    )
    args = p.parse_args()
    if args.max_steps is None:
        args.max_steps = (
            720 if (args.all_modes or args.mode == "divert") else 360
        )

    import scenic

    modes = list(SCENARIOS) if args.all_modes else [args.mode]
    summary = {}
    last_bin = None

    for mode in modes:
        scen_path = SCENARIOS[mode]
        out = ROOT / "outputs" / "lander_modes" / mode
        out.mkdir(parents=True, exist_ok=True)
        print(f"\n=== MODE {mode} ({scen_path.name}) ===")
        n_ok = 0
        rows = []
        for i in range(int(args.episodes)):
            s = int(args.seed) + i
            random.seed(s)
            np.random.seed(s)
            params = {
                "enable_viz": False,
                "timestep": 0.25,
                "attitude_mode": "instant" if args.instant_attitude else "slew",
            }
            viz_bin = ""
            if args.viz and i == 0:
                viz_bin = str((out / f"ep{i:02d}_seed{s}_UnityViz.bin").resolve())
                params.update(
                    {
                        "enable_viz": True,
                        "viz_mode": "file",
                        "viz_save_file": viz_bin,
                    }
                )
            scenario = scenic.scenarioFromFile(str(scen_path), params=params)
            scene, _ = scenario.generate(maxIterations=150)
            craft = scene.egoObject
            print(
                f"  [ep{i} seed={s}] pos=({craft.position.x:.1f},{craft.position.y:.1f},"
                f"{craft.position.z:.1f}) "
                f"att≈({craft.yaw:.2f},{craft.pitch:.2f},{craft.roll:.2f})"
            )
            sim = scenario.getSimulator().simulate(
                scene, maxSteps=int(args.max_steps), timestep=0.25, verbosity=0
            )
            if sim is None:
                print("    REJECTED")
                continue
            records = getattr(sim.result, "records", {}) or {}
            alts = _series(records, "altitude_m")
            spds = _series(records, "speed_mps")
            reach = False
            for a, sp in zip(alts, spds):
                if CONTACT_ALT_MIN <= a <= CONTACT_ALT_MAX and sp <= REACH_SPEED:
                    reach = True
                    break
            n_ok += int(reach)
            phase = ""
            try:
                phase = str(
                    getattr(getattr(sim, "backend", None), "_last_guidance", {}).get(
                        "phase", ""
                    )
                )
            except Exception:
                pass
            print(
                f"    min_alt={min(alts) if alts else float('nan'):.2f} "
                f"spd={spds[-1] if spds else float('nan'):.2f} "
                f"reach={reach} last_phase={phase}"
            )
            rows.append({"seed": s, "reach": reach, "phase": phase})
            if viz_bin:
                last_bin = viz_bin
        summary[mode] = {
            "reach_rate": n_ok / max(len(rows), 1),
            "episodes": len(rows),
            "rows": rows,
        }
        print(f"  → reach {n_ok}/{len(rows)}")

    out_json = ROOT / "outputs" / "lander_modes" / "summary.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out_json}")
    if args.open_viz and last_bin:
        from asteroid_rl.environment.gym_env import _find_vizard_app
        from asteroid_rl.sensing.camera import launch_vizard_load_file

        launch_vizard_load_file(
            last_bin, find_app_fn=_find_vizard_app, popen_fn=subprocess.Popen
        )


if __name__ == "__main__":
    main()
