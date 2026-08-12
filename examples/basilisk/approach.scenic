"""Near-pad divert-style start with coast then brake."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = True
param flat_surface_z = -30.0

behavior ApproachThenBrake():
    take CoastAction()
    wait
    take CoastAction()
    wait
    while True:
        take PointAtTargetAction((0, 0, -30)), SetThrottleAction(0.85)
        wait

ego = new Spacecraft at (Range(-15, 15), Range(-15, 15), Range(40, 90)),
    with velocity (Range(-0.5, 0.5), Range(-0.5, 0.5), Range(-1.5, -0.5)),
    with behavior ApproachThenBrake

terminate after 50 seconds
