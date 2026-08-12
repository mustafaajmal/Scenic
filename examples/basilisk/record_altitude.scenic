"""Record live altitude / throttle / speed while soft-braking (no Vizard needed).

Mirrors MuJoCo ``record`` demos: Scenic time-series from dynamic properties.
Output CSV lands next to the working directory unless you override the path.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = True
param flat_surface_z = -30.0
param timestep = 0.25
param enable_viz = False

behavior SoftBrake():
    while True:
        take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.65)
        wait

ego = new Spacecraft at (0, 0, 90),
    with velocity (0, 0, -1.4),
    with behavior SoftBrake

record ego.altitude as altitude_m
record ego.throttle as throttle
record ego.speed as speed_mps
record ego.position.z as z_m

terminate when ego.altitude < 6
terminate after 30 seconds
