#!/usr/bin/env python
"""One-command MINIMUM MVP for the Scenic ↔ Basilisk case-study writeup.

Goal
----
Use Scenic to define asteroid-landing *scenarios* (craft ICs + rock shape),
drive Basilisk dynamics, then either:

  A) evaluate a fixed policy on those scenarios, or
  B) train a policy on a Scenic curriculum (sphere → ellipsoid → bumpy).

Usage (Git Bash, from Scenic repo)::

    DEMO=../asteroid-rl-demo
    source "$DEMO/.venv/Scripts/activate"
    export ASTEROID_RL_ROOT="$DEMO"
    export SCENIC_ROOT="$PWD"
    export PYTHONPATH="$PWD/src:$DEMO"

    python examples/basilisk/run_mvp.py --mode both --episodes 5 --seed 0 \\
      --timesteps-per-stage 4000 --eval-episodes 4 --viz
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT.parent / "asteroid-rl-demo"
EVAL = Path(__file__).with_name("run_scenic_policy_eval.py")


def _ensure_paths() -> None:
    os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))
    os.environ.setdefault("SCENIC_ROOT", str(ROOT))
    scenic_src = str(ROOT / "src")
    demo = str(DEMO)
    parts = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    for p in (scenic_src, demo):
        if p not in parts:
            parts.insert(0, p)
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)
    if demo not in sys.path:
        sys.path.insert(0, demo)
    if scenic_src not in sys.path:
        sys.path.insert(0, scenic_src)


def run_eval(episodes: int, seed: int, max_steps: int, viz: bool, open_viz: bool) -> int:
    cmd = [
        sys.executable,
        str(EVAL),
        "--episodes",
        str(episodes),
        "--seed",
        str(seed),
        "--max-steps",
        str(max_steps),
    ]
    if viz:
        cmd.append("--viz")
    if open_viz:
        cmd.append("--open-viz")
    print("\n>>> PATH A: Scenic-native fixed-policy eval\n", " ".join(cmd), "\n")
    return subprocess.call(cmd, cwd=str(ROOT))


def run_train(timesteps_per_stage: int, eval_episodes: int, seed: int, viz: bool) -> int:
    if not DEMO.is_dir():
        print(f"Missing sibling repo: {DEMO}", file=sys.stderr)
        return 2
    out_dir = DEMO / "outputs" / "scenic_curriculum_mvp"
    cmd = [
        sys.executable,
        "-m",
        "asteroid_rl.cli.train_scenic_curriculum",
        "--timesteps-per-stage",
        str(timesteps_per_stage),
        "--eval-episodes",
        str(eval_episodes),
        "--seed",
        str(seed),
        "--out-dir",
        str(out_dir),
    ]
    print("\n>>> PATH B: Gym + Scenic progressive curriculum train\n", " ".join(cmd), "\n")
    rc = subprocess.call(cmd, cwd=str(DEMO), env=os.environ.copy())
    if rc != 0 or not viz:
        return rc

    model = out_dir / "ppo_scenic_curriculum.zip"
    if not model.is_file():
        print(f"No model for Vizard record pass: {model}", file=sys.stderr)
        return rc
    viz_cmd = [
        sys.executable,
        "-m",
        "asteroid_rl.cli.record_scenic_viz",
        "--skip-train",
        "--model",
        str(model),
        "--seed",
        str(seed),
        "--out-dir",
        str(out_dir / "viz_demos"),
    ]
    print("\n>>> PATH B viz: record curriculum .bin demos\n", " ".join(viz_cmd), "\n")
    return subprocess.call(viz_cmd, cwd=str(DEMO), env=os.environ.copy()) or rc


def main() -> None:
    p = argparse.ArgumentParser(description="Scenic↔Basilisk MINIMUM MVP runner")
    p.add_argument(
        "--mode",
        choices=("eval", "train", "both"),
        default="both",
        help="eval=fixed policy; train=PPO on Scenic curriculum; both=A then B",
    )
    p.add_argument("--episodes", type=int, default=5, help="Eval episodes/stage (path A)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=240)
    p.add_argument("--timesteps-per-stage", type=int, default=4000)
    p.add_argument("--eval-episodes", type=int, default=4, help="Gym eval eps/stage (path B)")
    p.add_argument(
        "--viz",
        action="store_true",
        help="Record Vizard .bin demos (path A: 1/stage; path B: after train)",
    )
    p.add_argument(
        "--open-viz",
        action="store_true",
        help="Open the last path-A .bin in Vizard when done",
    )
    args = p.parse_args()

    _ensure_paths()
    print(
        "MVP goal: Scenic scenarios → Basilisk sim → policy eval/train\n"
        "Curriculum: sphere → ellipsoid → bumpy\n"
        f"Python: {sys.executable}\n"
        f"Scenic: {ROOT}\n"
        f"Demo:   {DEMO}\n"
    )

    rc = 0
    if args.mode in ("eval", "both"):
        rc = run_eval(args.episodes, args.seed, args.max_steps, args.viz, args.open_viz) or rc
    if args.mode in ("train", "both"):
        rc = run_train(args.timesteps_per_stage, args.eval_episodes, args.seed, args.viz) or rc

    print("\n=== MVP outputs ===")
    print(f"  A) {ROOT / 'outputs' / 'scenic_policy_eval' / 'summary.json'}")
    print(f"     records: {ROOT / 'outputs' / 'scenic_policy_eval' / 'records'}")
    if args.viz:
        print(f"     viz:     {ROOT / 'outputs' / 'scenic_policy_eval' / 'viz'}")
    print(f"  B) {DEMO / 'outputs' / 'scenic_curriculum_mvp' / 'summary.json'}")
    if args.viz:
        print(f"     viz:     {DEMO / 'outputs' / 'scenic_curriculum_mvp' / 'viz_demos' / 'viz'}")
        print(
            "\nReplay (Git Bash):\n"
            '  "$USERPROFILE/OneDrive/Documents/Applications/Vizard/Vizard.exe" \\\n'
            '    -loadFile "C:/Users/Mustafa Ajmal/Desktop/Research/Scenic/outputs/scenic_policy_eval/viz/sphere_ep00_seed0_UnityViz.bin"'
        )
    print("See examples/basilisk/MVP.md for writeup bullets.")
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
