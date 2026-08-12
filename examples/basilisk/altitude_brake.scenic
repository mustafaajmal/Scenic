"""Closed-loop soft brake using live ``ego.altitude`` (MuJoCo-style dynamic props).

Demonstrates that Basilisk feeds position/altitude back into Scenic each step
so behaviors can react — not just open-loop ``take`` sequences.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = True
param flat_surface_z = -30.0
param timestep = 0.25
param enable_viz = False

behavior AltitudeBrake():
    """Brake hard when high; ease off near the pad; coast if very close."""
    while True:
        if ego.altitude > 60:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.85)
        elif ego.altitude > 25:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.55)
        elif ego.altitude > 8:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.25)
        else:
            take CoastAction()
        wait

ego = new Spacecraft at (Range(-8, 8), Range(-8, 8), Range(70, 110)),
    with velocity (Range(-0.3, 0.3), Range(-0.3, 0.3), Range(-1.8, -0.8)),
    with behavior AltitudeBrake

require ego.position.z > -20
terminate when ego.altitude < 5
terminate after 45 seconds
