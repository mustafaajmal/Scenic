#!/usr/bin/env python
"""MINIMUM path A: evaluate a fixed Scenic policy on curriculum scenarios.

Scenic samples each scene (craft ICs + asteroid shape). Basilisk simulates.
``record`` statements produce time series on ``sim.result.records``; we dump
those to CSV and score a **low** safe-landing gate for the writeup.

Example (from Scenic repo, use asteroid-rl-demo venv)::

    ../asteroid-rl-demo/.venv/Scripts/python.exe \\
      examples/basilisk/run_scenic_policy_eval.py --episodes 5 --seed 0
"""

from __future__ import annotations

import argparse
import csv
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

CURRICULUM = {
    "sphere": Path(__file__).with_name("curriculum") / "sphere.scenic",
    "ellipsoid": Path(__file__).with_name("curriculum") / "ellipsoid.scenic",
    "bumpy": Path(__file__).with_name("curriculum") / "bumpy.scenic",
}

CURRICULUM_DIVERT = {
    "sphere": Path(__file__).with_name("curriculum_divert") / "sphere.scenic",
    "ellipsoid": Path(__file__).with_name("curriculum_divert") / "ellipsoid.scenic",
    "bumpy": Path(__file__).with_name("curriculum_divert") / "bumpy.scenic",
}

# Low / writeup-friendly gates (PRIMARY = reach).
CONTACT_ALT_MAX = 8.0
CONTACT_ALT_MIN = 0.3
REACH_SPEED = 3.5  # primary "safe" for MINIMUM
SOFT_SPEED = 2.8  # stricter secondary


def _contact_ok(alt: float) -> bool:
    return CONTACT_ALT_MIN <= float(alt) <= CONTACT_ALT_MAX


def _reach_ok(alt: float, speed: float) -> bool:
    return _contact_ok(alt) and float(speed) <= REACH_SPEED


def _soft_ok(alt: float, speed: float) -> bool:
    return _contact_ok(alt) and float(speed) <= SOFT_SPEED


def _series_pairs(records: dict, key: str) -> list[tuple[float, float]]:
    """Return [(time, value), ...] from Scenic ``sim.result.records``."""
    if not records or key not in records:
        return []
    out: list[tuple[float, float]] = []
    for item in records[key]:
        try:
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                out.append((float(item[0]), float(item[-1])))
            else:
                out.append((float(len(out)), float(item)))
        except Exception:
            continue
    return out


def _series_values(records: dict, key: str) -> list[float]:
    return [v for _, v in _series_pairs(records, key)]


def dump_records_csv(records: dict, path: Path) -> None:
    """Write Scenic record time series to one CSV (easy for writeup plots)."""
    keys = ["altitude_m", "speed_mps", "throttle", "z_m"]
    series = {k: _series_pairs(records, k) for k in keys}
    n = max((len(series[k]) for k in keys), default=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["step", "time_s", "altitude_m", "speed_mps", "throttle", "z_m"])
        for i in range(n):
            t = series["altitude_m"][i][0] if i < len(series["altitude_m"]) else float(i)
            row = [i, t]
            for k in keys:
                row.append(series[k][i][1] if i < len(series[k]) else "")
            w.writerow(row)


def run_stage(
    stage: str,
    episodes: int,
    seed: int,
    max_steps: int,
    records_dir: Path | None,
    viz_dir: Path | None = None,
    viz_every: bool = False,
    curriculum: dict | None = None,
) -> list[dict]:
    import scenic

    table = curriculum or CURRICULUM
    path = table[stage]
    rows = []
    for i in range(episodes):
        s = int(seed) + i
        random.seed(s)
        np.random.seed(s)
        # Record Vizard .bin for first episode of each stage (or all if viz_every).
        do_viz = viz_dir is not None and (viz_every or i == 0)
        viz_bin = ""
        params = {"enable_viz": False, "timestep": 0.25}
        if do_viz:
            viz_dir.mkdir(parents=True, exist_ok=True)
            viz_bin = str(viz_dir / f"{stage}_ep{i:02d}_seed{s}_UnityViz.bin")
            params = {
                "enable_viz": True,
                "viz_mode": "file",
                "viz_save_file": viz_bin,
                "timestep": 0.25,
            }
        scenario = scenic.scenarioFromFile(str(path), params=params)
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
        if do_viz:
            print(f"  recording Vizard: {viz_bin}")
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
                    "reach_ok": False,
                    "soft_ok": False,
                    "contact_ok": False,
                }
            )
            continue

        # After simulate(), dynamic props are cleared — use records dict.
        records = getattr(sim.result, "records", {}) or {}
        if records_dir is not None:
            dump_records_csv(records, records_dir / f"{stage}_ep{i:02d}_seed{s}.csv")

        alts = _series_values(records, "altitude_m")
        speeds = _series_values(records, "speed_mps")
        throttles = _series_values(records, "throttle")
        alt = float(alts[-1]) if alts else float("nan")
        speed = float(speeds[-1]) if speeds else float("nan")
        min_alt = float(min(alts)) if alts else float("nan")
        max_speed = float(max(speeds)) if speeds else float("nan")
        throttle = float(throttles[-1]) if throttles else 0.0

        # Score anytime in the episode (not only the last step).
        contact = reach = soft = False
        for a, sp in zip(alts, speeds):
            if _contact_ok(a):
                contact = True
            if _reach_ok(a, sp):
                reach = True
            if _soft_ok(a, sp):
                soft = True

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
            "contact_ok": bool(contact),
            "reach_ok": bool(reach),
            "soft_ok": bool(soft),
            "safe_landing": bool(reach),  # PRIMARY MINIMUM metric
            "termination": "safe_landing" if reach else "fail",
            "n_steps": len(getattr(sim.result, "trajectory", []) or []),
            "records_csv": (
                str(records_dir / f"{stage}_ep{i:02d}_seed{s}.csv")
                if records_dir is not None
                else ""
            ),
            "viz_bin": viz_bin if do_viz else "",
        }
        rows.append(row)
        print(
            f"  [{stage} ep{i}] min_alt={min_alt:.2f} final_alt={alt:.2f} "
            f"spd={speed:.2f} reach={reach} soft={soft} seed={s}"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate fixed Scenic scripted policy on curriculum stages"
    )
    parser.add_argument("--episodes", type=int, default=5, help="Episodes per stage")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Sim steps (timestep 0.25s). Default 240 (~60s); with --divert default 720 (~180s).",
    )
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
    parser.add_argument(
        "--no-records",
        action="store_true",
        help="Skip dumping per-episode Scenic record CSVs",
    )
    parser.add_argument(
        "--viz",
        action="store_true",
        help="Record one Vizard .bin per stage (first episode; Windows save-file mode)",
    )
    parser.add_argument(
        "--viz-all",
        action="store_true",
        help="With --viz, record every episode (slower)",
    )
    parser.add_argument(
        "--open-viz",
        action="store_true",
        help="After eval, open the last recorded .bin in Vizard",
    )
    parser.add_argument(
        "--divert",
        action="store_true",
        help="Use curriculum_divert (MODE C miss traj/attitude) instead of inbound soft-brake",
    )
    args = parser.parse_args()
    if args.max_steps is None:
        args.max_steps = 720 if args.divert else 240

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    records_dir = None if args.no_records else out.parent / "records"
    viz_dir = (out.parent / "viz") if (args.viz or args.viz_all) else None
    curriculum = CURRICULUM_DIVERT if args.divert else CURRICULUM

    label = "divert GNC" if args.divert else "inbound soft-brake"
    print(f"MINIMUM Scenic policy eval ({label} vs curriculum)\n")
    print(
        f"Gates — contact: {CONTACT_ALT_MIN}<=alt<={CONTACT_ALT_MAX} m; "
        f"reach (PRIMARY safe): speed<={REACH_SPEED}; "
        f"soft: speed<={SOFT_SPEED}\n"
    )

    all_rows: list[dict] = []
    summary = {}
    for stage in args.stages:
        print(f"=== stage: {stage} ===")
        rows = run_stage(
            stage,
            args.episodes,
            args.seed,
            args.max_steps,
            records_dir,
            viz_dir=viz_dir,
            viz_every=bool(args.viz_all),
            curriculum=curriculum,
        )
        all_rows.extend(rows)
        n = max(len(rows), 1)
        summary[stage] = {
            "episodes": len(rows),
            "contact_rate": sum(1 for r in rows if r.get("contact_ok")) / n,
            "reach_rate": sum(1 for r in rows if r.get("reach_ok")) / n,
            "soft_rate": sum(1 for r in rows if r.get("soft_ok")) / n,
            "safe_rate": sum(1 for r in rows if r.get("safe_landing")) / n,
            "mean_final_speed": float(
                np.nanmean([r.get("final_speed_mps", np.nan) for r in rows])
            ),
            "mean_min_alt": float(
                np.nanmean([r.get("min_altitude_m", np.nan) for r in rows])
            ),
        }
        print(
            f"  → safe(reach)={100 * summary[stage]['safe_rate']:.0f}%  "
            f"contact={100 * summary[stage]['contact_rate']:.0f}%  "
            f"soft={100 * summary[stage]['soft_rate']:.0f}%  "
            f"mean_spd={summary[stage]['mean_final_speed']:.2f}\n"
        )

    if not all_rows:
        raise SystemExit("No episodes completed")

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)

    summary_json = out.with_suffix(".json")
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {summary_json}")
    if records_dir is not None:
        print(f"Record series: {records_dir}")
    if viz_dir is not None:
        print(f"Vizard bins: {viz_dir}")
        bins = [r.get("viz_bin") for r in all_rows if r.get("viz_bin")]
        for b in bins:
            print(f"  {b}")
        if args.open_viz and bins:
            last = bins[-1]
            try:
                from asteroid_rl.environment.gym_env import _find_vizard_app
                from asteroid_rl.sensing.camera import launch_vizard_load_file

                launch_vizard_load_file(
                    last,
                    find_app_fn=_find_vizard_app,
                    popen_fn=subprocess.Popen,
                )
            except Exception as exc:
                print(f"Could not auto-open Vizard ({exc}). Replay with:")
                print(f'  "$USERPROFILE/OneDrive/Documents/Applications/Vizard/Vizard.exe" -loadFile "{last}"')
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
