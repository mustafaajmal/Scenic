# Basilisk Scenic interface

Scenic world model and simulator for **Basilisk + MuJoCo** asteroid landing,
backed by the sister [asteroid-rl-demo](https://github.com/mustafaajmal/asteroid-rl-demo)
package (`asteroid_rl.env.build_sim`).

## Setup

1. Install Scenic (editable) from this repo.
2. Install Basilisk with MuJoCo extras and `asteroid-rl-demo` requirements.
3. Put `asteroid-rl-demo` on `PYTHONPATH`, or set `ASTEROID_RL_ROOT`, or keep
   it as a **sibling** of this `Scenic` checkout:

```text
Research/
  Scenic/
  asteroid-rl-demo/
```

## Probabilistic scenes → Vizard

Scenic defines a **distribution**; each `generate()` draws one scene. Rendering
is in **Vizard/Basilisk**, not Scenic's built-in visualizer:

```powershell
..\asteroid-rl-demo\.venv\Scripts\python.exe examples\basilisk\run_random_approach.py --samples 3 --open-last
```

You'll see different spacecraft XYZ each sample and a `.bin` per sample under
`outputs/viz/random_approach/`. Stock `Asteroid` still uses the fixed Itokawa
MuJoCo mesh (welded body — no free joint); Scenic uses it for `facing toward` /
distance constraints.

### Procedural asteroid (Mars-rover pattern)

Like the [Webots Mars hills example](https://docs.scenic-lang.org/en/latest/tutorials/fundamentals.html#a-worked-example),
each sample can rebuild **shape, size, and placement**:

```scenic
asteroid = new ProceduralAsteroid at (…),
    with radiusX Range(40, 70),
    with terrain [new AsteroidBump for _ in range(35)]
```

```powershell
..\asteroid-rl-demo\.venv\Scripts\python.exe examples\basilisk\run_dynamic_asteroid.py --samples 3 --open-last
```

Each sample writes a fresh OBJ+XML under a temp dir and a Vizard `.bin` under
`outputs/viz/dynamic_asteroid/`.

On **Windows**, live ZeroMQ often crashes; the safe path is **save-file**:

```powershell
cd C:\Users\Mustafa Ajmal\Desktop\Research\Scenic
$env:ASTEROID_RL_ROOT = "C:\Users\Mustafa Ajmal\Desktop\Research\asteroid-rl-demo"
$env:PYTHONPATH = $env:ASTEROID_RL_ROOT
..\asteroid-rl-demo\.venv\Scripts\python.exe examples\basilisk\run_with_viz.py --file --open
```

That records `outputs/viz/scenic_soft_brake_UnityViz.bin` and tries to launch
`Vizard.exe -loadFile ...`. You can also open the `.bin` from Vizard manually.

On **macOS**, omit `--file` for liveStream (`param enable_viz = True` in
`soft_brake_viz.scenic`).

Or set in a scenario:

```scenic
param enable_viz = True
param viz_mode = 'auto'   # or 'file' / 'live'
```

Or compile/simulate from Python:

```python
import scenic
scenario = scenic.scenarioFromFile("examples/basilisk/soft_brake.scenic")
scene, _ = scenario.generate()
scenario.getSimulator().simulate(scene, maxSteps=40, timestep=0.25)
```

## Layout

| File | Role |
|------|------|
| `scenic.simulators.basilisk.model` | `Spacecraft`, `Asteroid`, `ProceduralAsteroid`, `AsteroidBump` |
| `asteroid_mesh.py` | Icosphere + Gaussian bumps → OBJ + MuJoCo XML |
| `simulator.py` | `BasiliskSimulator` / `BasiliskSimulation` |
| `backend.py` | Stock `build_sim` + `build_procedural` |
| `actions.py` | `SetThrottleAction`, `SetPointingDirectionAction`, … |
| `dynamic_asteroid.scenic` | Mars-style procedural rock demo |

Thruster geometry matches asteroid_rl: body **+z** thrust, body **−z** boresight.
Pointing at the pad then firing brakes *away* from the pad along the LOS.
