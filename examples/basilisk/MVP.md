# MINIMUM MVP — Scenic ↔ Basilisk for asteroid landing

## Goal (one sentence)

**Use Scenic to generate asteroid-landing scenarios, run them in Basilisk, and
evaluate or train a lander policy** — showing Scenic’s value as a scenario layer
for autonomy (not camera/VLM yet).

## What “done” means

| Path | Deliverable | Pass criteria |
|------|-------------|---------------|
| **A** | Fixed policy vs curriculum | Summary rates + per-episode `record` CSVs |
| **B** | Train on Scenic scenarios | PPO zip + transfer table sphere→ellipsoid→bumpy |

Either A **or** B satisfies the PI MINIMUM; shipping **both** is best for the writeup.

## Architecture (writeup figure)

```
Scenic .scenic files          Basilisk / MuJoCo              Policy
─────────────────────         ─────────────────              ──────
sample craft pose/vel   →     dynamics + thruster      →     scripted OR PPO
sample rock (sphere /         mesh-raycast altitude          throttle ∈ [0,1]
  ellipsoid / bumpy)
record altitude, speed  →     sim.result.records       →     CSV + safe gate
```

Curriculum stages (same folder):

- `curriculum/sphere.scenic` — fixed smooth sphere (easy)
- `curriculum/ellipsoid.scenic` — random ellipsoid (medium)
- `curriculum/bumpy.scenic` — noisy rock + bumps/craters/ridges (hard)

## Safe-landing gate (low / writeup-friendly)

Scored **anytime** during the episode (not only the last step):

| Gate | Meaning | Threshold |
|------|---------|-----------|
| **reach / safe (PRIMARY)** | Near surface + not too fast | `0.3 ≤ alt ≤ 8` m and `speed ≤ 3.5` m/s |
| soft | Stricter | same alt band and `speed ≤ 2.8` m/s |
| contact | Reached band only | alt in band (any speed) |

Gym path B uses the same speed/alt numbers for `safe_landing`.

## How records work

In each `.scenic` file:

```scenic
record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m
```

After `simulate()`, dynamic Scenic props are cleared. Read:

```python
records = sim.result.records   # dict: name → [(time, value), ...]
```

Path A dumps each episode to  
`outputs/scenic_policy_eval/records/<stage>_ep##_seed#.csv`.

### One-liner: MINIMUM + Vizard

```bash
cd ~/Desktop/Research/Scenic
DEMO="../asteroid-rl-demo"
source "$DEMO/.venv/Scripts/activate"
export ASTEROID_RL_ROOT="$DEMO" SCENIC_ROOT="$PWD"
export PYTHONPATH="$PWD/src:$DEMO"

python examples/basilisk/run_mvp.py --mode both \
  --episodes 5 --seed 0 \
  --timesteps-per-stage 4000 --eval-episodes 4 \
  --viz --open-viz
```

Or separately:

```bash
# A only — fixed scripted policy
python examples/basilisk/run_mvp.py --mode eval --episodes 5 --seed 0

# B only — progressive PPO train on Scenic rocks
python examples/basilisk/run_mvp.py --mode train --timesteps-per-stage 4000 --seed 2
```

### Outputs

| Path | Location |
|------|----------|
| A summary | `Scenic/outputs/scenic_policy_eval/summary.{csv,json}` |
| A records | `Scenic/outputs/scenic_policy_eval/records/*.csv` |
| A viz (`--viz`) | `Scenic/outputs/scenic_policy_eval/viz/*_UnityViz.bin` |
| B model | `asteroid-rl-demo/outputs/scenic_curriculum_mvp/ppo_scenic_curriculum.zip` |
| B table | `asteroid-rl-demo/outputs/scenic_curriculum_mvp/summary.{csv,json}` |

## Writeup bullets (copy/paste)

1. **Interface:** Scenic scenarios drive Basilisk via `scenic.simulators.basilisk`;
   procedural asteroids rebuild the MuJoCo mesh each `generate()`.
2. **Scenario control:** craft pose/velocity and rock shape are Scenic distributions
   (curriculum stages), not ad-hoc Python random starts.
3. **Instrumentation:** `record` → `sim.result.records` → CSV time series for
   altitude/speed/throttle.
4. **MINIMUM A:** fixed soft-brake behavior evaluated across sphere/ellipsoid/bumpy;
   primary metric = reach rate (low threshold).
5. **MINIMUM B:** PPO trained progressively on Scenic stages, then evaluated for
   transfer; shows scenario-conditioned training enabled by Scenic.
6. **Out of scope this week:** camera, VLM, multi-thruster allocation.

## Common pitfalls (Windows / Git Bash)

- Activate **`asteroid-rl-demo/.venv`**, not a Scenic `venv/` (there isn’t one).
- Do **not** paste PowerShell `& "$env:USERPROFILE\..."` into Git Bash.
- Vizard replay:

```bash
"$USERPROFILE/OneDrive/Documents/Applications/Vizard/Vizard.exe" \
  -loadFile "/c/Users/Mustafa Ajmal/Desktop/Research/asteroid-rl-demo/outputs/viz/best_mesh/soft_landing_ppo_UnityViz.bin"
```
