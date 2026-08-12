# Basilisk Scenic interface

Scenic world model and simulator for **Basilisk + MuJoCo** asteroid landing,
backed by the sister [asteroid-rl-demo](https://github.com/mustafaajmal/asteroid-rl-demo)
package (`asteroid_rl.environment.gym_env.build_sim`).

## Setup

1. Install Scenic (editable) from this repo.
2. Install Basilisk with MuJoCo extras and `asteroid-rl-demo` requirements.
3. Put `asteroid-rl-demo` on `PYTHONPATH`, or set `ASTEROID_RL_ROOT`, or keep
   it as a **sibling** of this `Scenic` checkout (or pass `param asteroid_rl_root`):

```text
Research/
  Scenic/
  asteroid-rl-demo/
```

## One-liner (like MuJoCo `scenic -S`)

```bash
export ASTEROID_RL_ROOT="/c/Users/Mustafa Ajmal/Desktop/Research/asteroid-rl-demo"
export PYTHONPATH="$ASTEROID_RL_ROOT"
python -m scenic -S examples/basilisk/soft_brake.scenic
```

Closed-loop altitude (uses live `ego.altitude`):

```bash
python -m scenic -S examples/basilisk/altitude_brake.scenic
```

Record time series (no Vizard):

```bash
python -m scenic -S examples/basilisk/record_altitude.scenic
```

Python API:

```python
import scenic
scenario = scenic.scenarioFromFile(
    "examples/basilisk/altitude_brake.scenic",
    params={"enable_viz": False, "timestep": 0.25},
)
scene, _ = scenario.generate()
sim = scenario.getSimulator().simulate(scene, maxSteps=40)
```

## Probabilistic scenes → Vizard

Scenic defines a **distribution**; each `generate()` draws one scene. Rendering
is in **Vizard/Basilisk**, not Scenic's built-in visualizer:

```bash
../asteroid-rl-demo/.venv/Scripts/python.exe examples/basilisk/run_random_approach.py --samples 3 --open-last
```

### Procedural asteroid (Mars-rover pattern)

```scenic
asteroid = new ProceduralAsteroid at (…),
    with terrain (
        [new AsteroidBump for _ in range(28)]
        + [new AsteroidCrater for _ in range(22)]
        + [new AsteroidRidge for _ in range(12)]
    )
```

```bash
../asteroid-rl-demo/.venv/Scripts/python.exe examples/basilisk/run_dynamic_asteroid.py --samples 3 --seed 42 --open-last
```

On **Windows**, prefer `viz_mode='file'` (live ZeroMQ is fragile).

## World-model params

| Param | Default | Meaning |
|-------|---------|---------|
| `timestep` | `0.25` | Scenic / control step (s) |
| `gravity_mode` | `constant` | or `central` |
| `max_thrust` | `275` | N |
| `use_flat_surface` | `False` | flat pad altitude |
| `flat_surface_z` | `-30` | pad z |
| `enable_viz` | `False` | attach Vizard |
| `viz_mode` | `auto` | `auto` / `live` / `file` |
| `viz_save_file` | `''` | `.bin` path |
| `asteroid_rl_root` | `''` | path to demo checkout |

## Layout

| File | Role |
|------|------|
| `model.scenic` | `Spacecraft`, `Asteroid`, `ProceduralAsteroid`, terrain kinds |
| `asteroid_mesh.py` | bumps / craters / ridges / noise → OBJ + albedo |
| `simulator.py` | live pose, velocity, **angular rate**, altitude |
| `backend.py` | stock + procedural Basilisk build |
| `actions.py` | throttle / pointing / coast |
| `altitude_brake.scenic` | closed-loop on `ego.altitude` |
| `record_altitude.scenic` | `record` time series |
| `dynamic_asteroid.scenic` | procedural rock demo |

Thruster geometry: body **+z** thrust, body **−z** boresight.
