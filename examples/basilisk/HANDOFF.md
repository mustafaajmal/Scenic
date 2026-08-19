# HANDOFF — gap closed (2026-08-19)

## You do **not** need to do more for the MINIMUM / remaining gap

The last engineering hole is filled: Gym resets that use a Scenic scenario now
call `build_procedural_sim`, so MuJoCo loads the **same procedural rock** Scenic
sampled (not stock Itokawa).

## What to show
1. `examples/basilisk/RESULTS.md` — tables A (Scenic-native) and B (Gym train)
2. `examples/basilisk/ARCHITECTURE.md` — I/O, GT, controls, reward

## Optional (nice, not blocking)
- Longer PPO train (`--timesteps 50000`) for stronger transfer numbers
- More eval episodes for tighter confidence intervals
- Vizard recordings of bumpy vs sphere for slides

## Commands
```bash
cd asteroid-rl-demo
export SCENIC_ROOT=../Scenic PYTHONPATH=../Scenic/src:.
.venv/Scripts/python.exe -m asteroid_rl.cli.train_scenic_curriculum \
  --timesteps 5000 --eval-episodes 4 --seed 2 \
  --out-dir outputs/scenic_curriculum_v3
```
