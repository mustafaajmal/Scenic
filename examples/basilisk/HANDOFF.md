# HANDOFF — MINIMUM Scenic policy experiment (2026-08-19)

## How far from MINIMUM were we?

~70% before this pass. RL train/eval and Scenic procedural rocks existed, but:

- Scenic altitude was **pad-Z**, not real surface  
- `scenic_reset` did **not** call Scenic  
- No curriculum eval harness tying a fixed policy to Scenic scenarios  

## MINIMUM (now implemented)

> Evaluate a fixed policy against Scenic-generated scenarios (curriculum).

| Piece | Status |
|-------|--------|
| Mesh “radar” altitude (raycast craft→rock) | Done |
| Curriculum sphere → ellipsoid → bumpy | Done |
| Fixed scripted policy + safe-landing rates | Done |
| Scenic `record` time series | Done |
| Gym `scenic_scenario_path` real `generate()` | Done |
| Architecture I/O writeup | `ARCHITECTURE.md` |
| Train on Scenic ICs | Hook ready (`scenic_scenario_path`); full procedural-Gym train still next |

### Smoke result (seed=11, 5 eps/stage)

| Stage | Safe rate |
|-------|-----------|
| sphere | 5/5 (100%) |
| ellipsoid | 4/5 (80%) |
| bumpy | 5/5 (100%) |

Interesting distinction already appears (ellipsoid miss). Bumpy still “easy” with the loose speed gate — tighten later for clearer hardness ordering.

## Commands

```bash
cd "/c/Users/Mustafa Ajmal/Desktop/Research/Scenic"
export ASTEROID_RL_ROOT="/c/Users/Mustafa Ajmal/Desktop/Research/asteroid-rl-demo"
export PYTHONPATH="$ASTEROID_RL_ROOT:$PWD/src"

../asteroid-rl-demo/.venv/Scripts/python.exe \
  examples/basilisk/run_scenic_policy_eval.py --episodes 5 --seed 11

# Gym path with Scenic resets
cd ../asteroid-rl-demo
.venv/Scripts/python.exe -m asteroid_rl.cli.evaluate_scenic \
  --scenario ../Scenic/examples/basilisk/curriculum/sphere.scenic \
  --episodes 5 --policy scripted
```

## Read next

1. `examples/basilisk/ARCHITECTURE.md` — GT, controls, reward, obs  
2. This file — MINIMUM status  
3. Open: bake procedural heightmap into Gym `SurfaceMap` for train-on-bumps; optional PPO zip eval  

## Key new files

- `asteroid_mesh.py` — `raycast_surface_distance`, `world_surface_altitude`, `bake_heightmap_npz`  
- `curriculum/{sphere,ellipsoid,bumpy}.scenic`  
- `run_scenic_policy_eval.py`  
- `asteroid_rl/cli/evaluate_scenic.py`  
- `asteroid_rl/dynamics/scenic_reset.py` — `sample_scenic_scenario_start`  
