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

## Run

```bash
export PYTHONPATH=/path/to/asteroid-rl-demo:$PYTHONPATH
python examples/basilisk/run_soft_brake.py
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
| `scenic.simulators.basilisk.model` | World model (`Spacecraft`, `Asteroid`, actions) |
| `simulator.py` | `BasiliskSimulator` / `BasiliskSimulation` |
| `backend.py` | `build_sim` / thruster / pointing bridge |
| `actions.py` | `SetThrottleAction`, `SetPointingDirectionAction`, … |

Thruster geometry matches asteroid_rl: body **+z** thrust, body **−z** boresight.
Pointing at the pad then firing brakes *away* from the pad along the LOS.
