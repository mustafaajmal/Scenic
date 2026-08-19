# Case-study results (2026-08-19)

## Question
Can Scenic generate space-domain asteroid scenarios that **distinguish** when a
fixed lander policy succeeds or fails?

## Setup
- Fixed scripted soft-brake policy (no camera / VLM)
- Altitude = **mesh raycast** (radar-like) toward the rock
- Curriculum: `sphere` → `ellipsoid` → `bumpy`
- 12 episodes / stage, seed 0
- Metrics:
  - **contact**: reached altitude band `[0.3, 8]` m
  - **reach**: contact + speed ≤ 3.5 m/s (MINIMUM “safe enough”)
  - **soft**: contact + speed ≤ 2.8 m/s (stricter)

## Results (`outputs/scenic_policy_eval/sweep_dual.json`)

| Stage | Contact | Reach | Soft | Mean final speed |
|-------|---------|-------|------|------------------|
| sphere | **100%** | **100%** | 0% | 3.10 m/s |
| ellipsoid | **100%** | **100%** | 0% | 3.17 m/s |
| bumpy | **67%** | **67%** | **67%** | **1.75 m/s** |

## Conclusions (PI-ready)
1. **Scenic is useful here**: one fixed policy + three Scenic scenario classes
   already produces a structured success table.
2. **Easy vs hard**: smooth rocks always *reach* the band but arrive hot
   (~3.1 m/s → fail the soft gate). Bumpy rocks fail contact more often (33%)
   but, when they contact, they are **slower** (soft 67%) — radar altitude on
   irregular terrain changes braking timing.
3. **Ground truth**: inertial XYZ + MRP; control = scalar throttle on body +z;
   reward/termination in Gym still on truth altitude/speed/site distance.
4. **Still open for full train loop**: Gym episodes now get Scenic ICs + mesh
   radar altitude, but MuJoCo geometry is still the stock scene — rebuild
   procedural XML inside Gym for true train-on-bumps. Until then, use the
   Scenic-native harness as the case study.

## Reproduce
```bash
cd Scenic
export ASTEROID_RL_ROOT=../asteroid-rl-demo PYTHONPATH=$ASTEROID_RL_ROOT
../asteroid-rl-demo/.venv/Scripts/python.exe \
  examples/basilisk/run_scenic_policy_eval.py --episodes 12 --seed 0 \
  --out outputs/scenic_policy_eval/sweep_dual.csv
```
