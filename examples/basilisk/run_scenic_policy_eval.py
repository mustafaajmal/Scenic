#!/usr/bin/env python
"""MINIMUM harness: evaluate a fixed scripted policy across Scenic curriculum stages.

Reports safe-landing rate per stage (sphere → ellipsoid → bumpy). Uses mesh
raycast altitude (radar-like) via the Basilisk Scenic interface.

Example::

    python examples/basilisk/run_scenic_policy_eval.py --episodes 4 --seed 0
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT.parent / "asteroid-rl-demo"
os.environ.setdefault("ASTEROID_RL_ROOT", str(DEMO))
if DEMO.is_dir() and str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))

CURRICULUM = {
    "sphere": Path(__file__).with_name("curriculum") / "sphere.scenic",
    "ellipsoid": Path(__file__).with_name("curriculum") / "ellipsoid.scenic",
    "bumpy": Path(__file__).with_name("curriculum") / "bumpy.scenic",
}

# Low-threshold "interesting" safe landing (PI: not uniformly perfect).
SUCCESS_ALT_MAX = 8.0
SUCCESS_ALT_MIN = 0.3
SUCCESS_SPEED = 3.5  # scripted soft-brake is coarse; still separates stages


def _safe_landing(final_alt: float, final_speed: float) -> bool:
    return (
        SUCCESS_ALT_MIN <= float(final_alt) <= SUCCESS_ALT_MAX
        and float(final_speed) <= SUCCESS_SPEED
    )


def _series_values(records: dict, key: str) -> list[float]:
    if not records or key not in records:
        return []
    series = records[key]
    out = []
    for item in series:
        try:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                out.append(float(item[-1]))
            else:
                out.append(float(item))
        except Exception:
            continue
    return out


def _last_record(records: dict, key: str, default: float = float("nan")) -> float:
    vals = _series_values(records, key)
    return float(vals[-1]) if vals else default


def run_stage(stage: str, episodes: int, seed: int, max_steps: int) -> list[dict]:
    import scenic

    path = CURRICULUM[stage]
    rows = []
    for i in range(episodes):
        s = int(seed) + i
        random.seed(s)
        np.random.seed(s)
        scenario = scenic.scenarioFromFile(
            str(path),
            params={"enable_viz": False, "timestep": 0.25},
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
        sim = scenario.getSimulator().simulate(
            scene, maxSteps=int(max_steps), timestep=0.25, verbosity=0
        )
        if sim is None:
            rows.append(
                {
                    "stage": stage,
                    "episode": i,
                    "seed": s,
                    "termination": "rejected",
                    "safe_landing": False,
                }
            )
            continue
        # After simulate(), dynamic object props are cleared; use Scenic records.
        records = getattr(sim.result, "records", {}) or {}
        alts = _series_values(records, "altitude_m")
        speeds = _series_values(records, "speed_mps")
        throttles = _series_values(records, "throttle")
        alt = float(alts[-1]) if alts else float("nan")
        speed = float(speeds[-1]) if speeds else float("nan")
        min_alt = float(min(alts)) if alts else float("nan")
        max_speed = float(max(speeds)) if speeds else float("nan")
        throttle = float(throttles[-1]) if throttles else 0.0
        # Prefer "reached soft band" anytime in the episode (not only last step).
        safe = False
        for a, sp in zip(alts, speeds):
            if _safe_landing(a, sp):
                safe = True
                break
        row = {
            "stage": stage,
            "episode": i,
            "seed": s,
            "craft_start_z": float(craft.position.z),
            "asteroid_radii": (
                None
                if asteroid is None
                else (
                    float(asteroid.radiusX),
                    float(asteroid.radiusY),
                    float(asteroid.radiusZ),
                )
            ),
            "final_altitude_m": alt,
            "min_altitude_m": min_alt,
            "final_speed_mps": speed,
            "max_speed_mps": max_speed,
            "final_throttle": throttle,
            "safe_landing": bool(safe),
            "termination": "safe_landing" if safe else "fail",
            "n_steps": len(getattr(sim.result, "trajectory", []) or []),
            "surface_mode": "mesh_raycast",
        }
        rows.append(row)
        print(
            f"  [{stage} ep{i}] final_alt={alt:.2f} min_alt={min_alt:.2f} "
            f"speed={speed:.2f} safe={safe} seed={s}"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=3, help="Episodes per stage")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=160)
    parser.add_argument(
        "--stages",
        nargs="+",
        default=["sphere", "ellipsoid", "bumpy"],
        choices=list(CURRICULUM.keys()),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(ROOT / "outputs" / "scenic_policy_eval" / "summary.csv"),
    )
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    print("MINIMUM Scenic policy eval (scripted soft-brake vs curriculum)\n")
    print(
        f"Safe landing: {SUCCESS_ALT_MIN}<=alt<={SUCCESS_ALT_MAX} m, "
        f"speed<={SUCCESS_SPEED} m/s\n"
    )

    all_rows: list[dict] = []
    summary = {}
    for stage in args.stages:
        print(f"=== stage: {stage} ===")
        rows = run_stage(stage, args.episodes, args.seed, args.max_steps)
        all_rows.extend(rows)
        ok = sum(1 for r in rows if r.get("safe_landing"))
        summary[stage] = {
            "episodes": len(rows),
            "safe_landings": ok,
            "safe_rate": ok / max(len(rows), 1),
        }
        print(
            f"  → {ok}/{len(rows)} safe "
            f"({100.0 * summary[stage]['safe_rate']:.0f}%)\n"
        )

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    summary_json = out.with_suffix(".json")
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {summary_json}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
