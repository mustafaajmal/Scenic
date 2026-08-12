#!/usr/bin/env python
"""Run a Scenic Basilisk scenario with Vizard visualization.

Windows (default): records a ``.bin`` then prints how to open it in Vizard.
macOS: tries liveStream (Vizard should be running / will be launched).

Usage (from Scenic repo root)::

    ..\\asteroid-rl-demo\\.venv\\Scripts\\python.exe examples\\basilisk\\run_with_viz.py

Optional::

    python examples/basilisk/run_with_viz.py --live   # force ZeroMQ (fragile on Win)
    python examples/basilisk/run_with_viz.py --file   # force .bin recording
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

# Record under Scenic/outputs/viz so paths are easy to find.
VIZ_DIR = ROOT / "outputs" / "viz"
VIZ_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_BIN = VIZ_DIR / "scenic_soft_brake_UnityViz.bin"


def _find_vizard() -> str | None:
    from asteroid_rl.env import _find_vizard_app

    return _find_vizard_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scenic + Basilisk + Vizard")
    parser.add_argument(
        "--scenario",
        type=str,
        default=str(Path(__file__).with_name("soft_brake_viz.scenic")),
    )
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--timestep", type=float, default=0.25)
    parser.add_argument("--live", action="store_true", help="Force viz_mode=live")
    parser.add_argument("--file", action="store_true", help="Force viz_mode=file")
    parser.add_argument(
        "--bin",
        type=str,
        default=str(DEFAULT_BIN),
        help="Output .bin path for save-file mode",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="After recording, try to launch Vizard -loadFile on the .bin",
    )
    args = parser.parse_args()

    import scenic

    params = {"enable_viz": True}
    if args.live:
        params["viz_mode"] = "live"
    elif args.file:
        params["viz_mode"] = "file"
        params["viz_save_file"] = os.path.abspath(args.bin)
    else:
        # auto: still set save path so Windows recording lands somewhere known
        params["viz_save_file"] = os.path.abspath(args.bin)

    scenario = scenic.scenarioFromFile(args.scenario, params=params)
    scene, _ = scenario.generate(maxIterations=5)
    simulator = scenario.getSimulator()
    # Keep a handle on the Simulation to read viz_bin_path after run.
    sim = simulator.simulate(
        scene, maxSteps=int(args.steps), timestep=float(args.timestep), verbosity=1
    )
    if sim is None:
        raise SystemExit("simulation rejected")

    print("termination:", sim.result.terminationType, sim.result.terminationReason)
    bin_path = getattr(getattr(sim, "backend", None), "handles", None)
    viz_bin = None
    if bin_path is not None:
        viz_bin = getattr(bin_path, "viz_bin_path", None)
    if not viz_bin and Path(args.bin).is_file():
        viz_bin = os.path.abspath(args.bin)

    if viz_bin:
        print()
        print("Vizard recording:", viz_bin)
        print("Open in Vizard with:")
        print(f'  Vizard.exe -loadFile "{viz_bin}"')
        if args.open:
            app = _find_vizard()
            if not app:
                print("Vizard.exe not found; open the .bin manually.")
            else:
                print("Launching:", app)
                subprocess.Popen([app, "-loadFile", viz_bin])
    else:
        print()
        print(
            "No .bin path (live mode, or viz failed). "
            "On Windows prefer default/auto or --file."
        )


if __name__ == "__main__":
    main()
