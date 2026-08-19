# HANDOFF — toward end-state case study (2026-08-19)

## Status vs PI MINIMUM / end result

| Goal | Status |
|------|--------|
| Eval fixed policy on Scenic scenarios | **Done** (Scenic-native harness) |
| Irregular terrain (sphere→ellipsoid→bumpy) | **Done** |
| Radar-like altitude to real surface | **Done** (mesh raycast) |
| Architecture I/O writeup | **Done** (`ARCHITECTURE.md`) |
| Interesting easy/hard distinction | **Done** — see `RESULTS.md` |
| Train policy on Scenic scenarios | **Partial** — CLI exists; Gym physics still stock mesh |
| Avoid camera/VLM | **Done** |

## What to show the PI
Open **`examples/basilisk/RESULTS.md`**. Headline table: sphere/ellipsoid
100% reach but never soft; bumpy 67% reach but all soft when contacting.

## Commands
```bash
# Primary case study
python examples/basilisk/run_scenic_policy_eval.py --episodes 12 --seed 0

# Gym Scenic resets (altitude fixed; physics still stock)
python -m asteroid_rl.cli.train_scenic_curriculum --timesteps 8000
```

## Next engineering step (biggest remaining gap)
Rebuild MuJoCo/Basilisk scene from Scenic procedural OBJ **inside Gym reset**
(reuse `BasiliskBackend.build_procedural`) so train/eval share the same rock
geometry as the Scenic harness. Then PPO curriculum will be meaningful.

## Pushed branches
- Scenic `basilisk-simulator`
- asteroid-rl-demo `master`
