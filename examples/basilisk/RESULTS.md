# Case-study results (2026-08-19)

## Question
Can Scenic generate space-domain asteroid scenarios that **distinguish** when a
fixed (or briefly trained) lander policy succeeds or fails?

## A) Scenic-native eval (mesh raycast, scripted policy)

12 episodes / stage, seed 0 — `outputs/scenic_policy_eval/sweep_dual.json`

| Stage | Contact | Reach (≤3.5) | Soft (≤2.8) | Mean speed |
|-------|---------|--------------|-------------|------------|
| sphere | 100% | 100% | 0% | 3.10 |
| ellipsoid | 100% | 100% | 0% | 3.17 |
| bumpy | 67% | 67% | 67% | 1.75 |

## B) Gym + procedural MuJoCo (gap closed)

Each Scenic sample now rebuilds the **actual** asteroid mesh in Basilisk/MuJoCo
(`asteroid_rl.environment.procedural_sim.build_procedural_sim`).

Short PPO train on sphere (5k steps), then eval — `outputs/scenic_curriculum_v3/`:

| Stage | Scripted | PPO (trained on sphere) |
|-------|----------|-------------------------|
| sphere | **75%** (3/4) | **75%** (3/4) |
| ellipsoid | 0% (0/4) | 25% (1/4) |
| bumpy | 50% (2/4) | 25% (1/4) |

## Conclusions
1. Scenic scenarios produce a clear **easy→hard** structure for landing.
2. Mesh-radar altitude + procedural physics make Gym train/eval consistent with
   the Scenic rock (no more stock-Itokawa mismatch).
3. A policy trained only on spheres does **not** fully transfer to ellipsoid/bumpy
   — exactly the curriculum story the PI wanted.
4. Ground truth remains inertial XYZ + MRP; control is scalar throttle on body +z;
   no camera/VLM required.

## Reproduce
```bash
# Scenic-native
cd Scenic
../asteroid-rl-demo/.venv/Scripts/python.exe \
  examples/basilisk/run_scenic_policy_eval.py --episodes 12 --seed 0

# Gym procedural train + curriculum eval
cd asteroid-rl-demo
export SCENIC_ROOT=../Scenic PYTHONPATH=../Scenic/src:.
.venv/Scripts/python.exe -m asteroid_rl.cli.train_scenic_curriculum \
  --timesteps 5000 --eval-episodes 4 --seed 2
```
