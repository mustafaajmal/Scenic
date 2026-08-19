# Lander modes (Scenic ↔ Basilisk)

Three **coexisting** scenarios — pick the story you need:

| Mode | File | Start | Behavior |
|------|------|-------|----------|
| **A soft_brake** | `soft_brake_inbound.scenic` | Facing body, inbound | Soft-brake only |
| **B acquire** | `acquire_and_land.scenic` | Random attitude, mostly inbound | Slew look-at-body → soft-brake |
| **C divert** | `divert_and_land.scenic` | Miss traj **and/or** attitude | Velocity-target divert → terminal soft land |

Curriculum:

- `curriculum/` — MODE A on sphere → ellipsoid → bumpy  
- `curriculum_divert/` — MODE C on the same rock stages  

## Attitude

- Default: ``param attitude_mode = 'slew'`` — rate-limited boresight motion (**RW stand-in**; not a full Basilisk reaction-wheel plant yet).
- Legacy teleport: ``attitude_mode = 'instant'`` or ``run_lander_modes.py --instant-attitude``.

## Soft land / hard surface

- **Settle throttle:** near the surface with low speed, thrust is cut so the craft does not boost away after a soft contact.
- **Hard surface:** procedural XML uses a **convex-hull collision mesh** with overdamped contacts (`solref` dampratio &gt; 1).
- **Stick on land:** at contact the hub velocity is zeroed and the pose is **frozen** (no further dynamics integration), so gravity cannot bounce it.
- Scenarios terminate on ``ego.landed or ego.inContact or ego.altitude < 0.35``.

## Run

```bash
cd Scenic
export ASTEROID_RL_ROOT=../asteroid-rl-demo
export PYTHONPATH=$PWD/src:$ASTEROID_RL_ROOT

# Full lander-like divert (recommended demo)
../asteroid-rl-demo/.venv/bin/python examples/basilisk/run_lander_modes.py \
  --mode divert --episodes 4 --seed 0 --viz --open-viz

# Legacy inbound soft-brake
../asteroid-rl-demo/.venv/bin/python examples/basilisk/run_lander_modes.py --mode soft_brake --episodes 4

# Miss-point acquire only
../asteroid-rl-demo/.venv/bin/python examples/basilisk/run_lander_modes.py --mode acquire --episodes 4

# All three
../asteroid-rl-demo/.venv/bin/python examples/basilisk/run_lander_modes.py --all-modes --episodes 3 --seed 1
```

Path A curriculum eval (unchanged entrypoint, MODE A behaviors):

```bash
../asteroid-rl-demo/.venv/bin/python examples/basilisk/run_scenic_policy_eval.py --episodes 5 --seed 0
```
