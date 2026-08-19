# Architecture: Scenic ↔ Basilisk ↔ RL (asteroid landing)

**Date:** 2026-08-19  
**Audience:** PI / collaborators  
**Repos:** `Scenic` (`basilisk-simulator`), `asteroid-rl-demo` (`master`)

## Motivation (case study)

Show Scenic’s value in the **space / Basilisk** domain: generate irregular
asteroid approach scenarios (sphere → ellipsoid → bumpy), run a fixed lander
policy, and measure which scenarios succeed. That gives designers a systematic
map of when autonomy works — without needing a camera/VLM yet.

## System diagram

```
┌─────────────────────────────┐
│ Scenic (.scenic)            │
│  • sample craft pose/vel    │
│  • sample rock shape/terrain│
│  • behaviors / Actions      │
│  • record altitude, speed…  │
└──────────────┬──────────────┘
               │ generate() / simulate()
               ▼
┌─────────────────────────────┐
│ scenic.simulators.basilisk  │
│  • build_procedural mesh    │
│  • SetThrottleAction → N    │
│  • surface_altitude (radar) │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ asteroid_rl Gym / Basilisk  │
│  • MuJoCo free-joint hub    │
│  • gravity + scalar thruster│
│  • reward + safe_landing    │
└─────────────────────────────┘
```

## Ground truth (what the simulator knows)

| Quantity | Representation | Units / notes |
|----------|----------------|---------------|
| Position | Inertial Cartesian `(x, y, z)` — **not** lat/lon | meters |
| Velocity | Inertial `(vx, vy, vz)` | m/s |
| Attitude | MRP `σ_BN` (Basilisk) ↔ Scenic yaw/pitch/roll | — |
| Angular rate | `ω_BN_B` → inertial `angularVelocity` | rad/s |
| Landing site | Fixed inertial point near surface | meters |
| Relative state (policy-friendly) | `r - site`, altitude, closing rates | meters / m/s |

There is **no latitude/longitude** frame in this demo. Everything is Cartesian
inertial (MuJoCo / Basilisk world).

## Controls that go out

| Control | Interface | Meaning |
|---------|-----------|---------|
| Throttle ∈ [0, 1] | Gym action / `SetThrottleAction` | Scalar force on hub **+z** body axis |
| Peak force | `max_thrust` (default 275 N Phase-1) | `force = throttle * max_thrust` |
| Pointing | `SetPointingDirectionAction` / `auto_point` | Aims body **−z** (boresight); thruster fires +z |

Phase-1 MINIMUM uses **1-D throttle** (+ optional scripted pointing). No multi-thruster
allocation yet.

## Observations (what the policy sees)

| Mode | Contents | Site distance? |
|------|----------|----------------|
| `truth` | alt, vz, **site distance**, speed, prev throttle | yes (privileged) |
| `sensors` | altimeter(=alt), vz, speed, closing rate, prev throttle | **no** |
| Avoid for now | camera / VLM | — |

**Altitude / “radar”:** for procedural rocks, altitude is a **mesh raycast** from
craft toward asteroid COM (distance to first triangle hit). That is the
straight-down-to-real-surface quantity the PI asked for — not a spherical shell
and not pad-Z. Stock Itokawa in Gym still uses the heightmap column query.

## Reward (end of episode + shaping)

Always computed on **truth**, never on noisy agent obs:

- Progress toward site + altitude progress  
- Speed / impact / fuel penalties  
- Terminal: `success_bonus` on `safe_landing`, penalties on crash / timeout / escape  

`safe_landing` (Gym defaults): altitude in `[0.5, 5]` m, speed ≤ `success_speed`,
lateral ≤ `success_lateral` (optional upright gate).

Scenic eval harness uses a slightly looser band so curriculum stages can show
**some** successes and **some** failures (interesting distinction).

## MINIMUM experiment (implemented)

1. **Fixed policy vs Scenic scenarios**  
   `Scenic/examples/basilisk/run_scenic_policy_eval.py`  
   Curriculum: `curriculum/sphere.scenic` → `ellipsoid.scenic` → `bumpy.scenic`  
   Scripted soft-brake reads **mesh-radar altitude**; CSV/JSON safe-landing rates.

2. **Gym + Scenic ICs**  
   `LandingEnvConfig.scenic_scenario_path` +  
   `python -m asteroid_rl.cli.evaluate_scenic --scenario … --policy scripted`  
   Each reset calls real `scenic.generate()` for craft pose/velocity.

3. **Train on Scenic starts** (optional)  
   Set `scenic_scenario_path` in training config the same way — poses come from
   Scenic; terrain for Gym reward still flat/Itokawa until procedural heightmaps
   are injected into `SurfaceMap` (next increment).

## What is intentionally deferred

- Camera / VLM landing-site selection  
- Full PPO train curriculum on procedural meshes inside Gym  
- Multi-thruster / reaction wheels  
- True Basilisk `simpleNav` radar module (raycast is the stand-in)

## Commands

```bash
# A) Scenic curriculum eval (MINIMUM)
cd Scenic
export ASTEROID_RL_ROOT=../asteroid-rl-demo PYTHONPATH=$ASTEROID_RL_ROOT
../asteroid-rl-demo/.venv/Scripts/python.exe \
  examples/basilisk/run_scenic_policy_eval.py --episodes 3 --seed 0

# B) Gym eval with Scenic resets
cd asteroid-rl-demo
.venv/Scripts/python.exe -m asteroid_rl.cli.evaluate_scenic \
  --scenario ../Scenic/examples/basilisk/curriculum/sphere.scenic \
  --episodes 5 --policy scripted
```
