# Basilisk ↔ Scenic integration handoff (2026-08-12)

Branch: **`basilisk-simulator`** (Scenic fork `mustafaajmal/Scenic`)  
Sister demo: **`asteroid-rl-demo` `master`** (Vizard overrides + `asteroid_rl.env` shim)

Planning PDF (`Scripts Planning Document`) was not found under Downloads on this
machine; work followed the Mars/MuJoCo Scenic patterns already in-repo plus the
asteroid landing stack in `WORK_DIARY.md`.

## Goal this session

Make the Basilisk Scenic interface feel as seamless as MuJoCo Scenic (PR #433 /
Webots-style): live dynamic properties, documented `scenic -S` path, closed-loop
behaviors, procedural rocks that actually show up in Vizard, and fewer import
gotchas after the asteroid_rl package reorg.

## What landed

### Scenic (`basilisk-simulator`)

| Area | Change |
|------|--------|
| Live state | `angularVelocity` / `angularSpeed` from hub `omega_BN_B` → inertial |
| Params | `param timestep`, `param asteroid_rl_root` wired through `model.scenic` |
| Closed-loop | `examples/basilisk/altitude_brake.scenic` reacts to `ego.altitude` |
| Record | `examples/basilisk/record_altitude.scenic` records altitude/throttle/speed |
| Procedural rock | bumps + craters + ridges + FBM noise + baked albedo JPG for Vizard |
| Vizard | uses **generated** OBJ at scale 1 (not stock Itokawa overlay) |
| API polish | `getBasiliskSimulator()` helper; README + `docs/simulators.rst` CLI snippets |
| Tests | altitude closed-loop, inline `scenarioFromString`, env shim, mesh/features |
| Seeded runs | `run_dynamic_asteroid.py --seed N` (sample `i` uses `seed+i`) |

### asteroid-rl-demo (`master`)

| Area | Change |
|------|--------|
| Vizard | `_setup_vizard(..., viz_asteroid_model_path/texture_path/scale)` |
| Compat | `asteroid_rl/env.py` re-exports `environment.gym_env` after reorg |

## How to run (Git Bash)

```bash
cd "/c/Users/Mustafa Ajmal/Desktop/Research/Scenic"
export ASTEROID_RL_ROOT="/c/Users/Mustafa Ajmal/Desktop/Research/asteroid-rl-demo"
export PYTHONPATH="$ASTEROID_RL_ROOT"

# One-liner (MuJoCo-style)
../asteroid-rl-demo/.venv/Scripts/python.exe -m scenic -S examples/basilisk/altitude_brake.scenic

# Procedural rock + Vizard save-files
../asteroid-rl-demo/.venv/Scripts/python.exe examples/basilisk/run_dynamic_asteroid.py --samples 3 --seed 42 --open-last
```

## Architecture (division of labor)

```
Scenic .scenic  →  sample pose / terrain / behaviors / Actions
       ↓
BasiliskSimulation.setup / step / getProperties
       ↓
asteroid_rl gym_env (build_sim | build_procedural) + Vizard
       ↓
Basilisk + MuJoCo physics
```

RL training still lives in **asteroid-rl-demo**, not inside Scenic. Next glue is
`scenic_reset` → real `scenario.generate()`.

## Not done / next

- [ ] Wire `asteroid_rl.dynamics.scenic_reset` to real Scenic `ProceduralAsteroid` / approach scenes.
- [ ] Surface-relative altitude (Itokawa heightmap / procedural radial shell) instead of pad `z` only.
- [ ] Optional `sensors.py` RGB observations (needs live Vizard; fragile on Windows).
- [ ] Upstream PR to BerkeleyLearnVerify/Scenic when ready.
- [ ] Planning PDF was missing locally — re-check against it for any checklist items not covered.

## Key files

- `src/scenic/simulators/basilisk/{model.scenic,simulator.py,backend.py,asteroid_mesh.py,actions.py}`
- `examples/basilisk/{altitude_brake,record_altitude,dynamic_asteroid}.scenic`
- `examples/basilisk/HANDOFF.md` (this file)
- `asteroid_rl/environment/gym_env.py` (`_setup_vizard` overrides)
- `asteroid_rl/env.py` (compat shim)
