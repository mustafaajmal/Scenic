"""Asteroid approach / soft-brake demo for the Basilisk Scenic interface."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = True
param flat_surface_z = -30.0

behavior SoftBrake():
    """Point roughly nadir and fire a moderate throttle."""
    while True:
        take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.7)
        wait

ego = new Spacecraft at (0, 0, 80),
    with velocity (0, 0, -1.2),
    with behavior SoftBrake

require ego.position.z > -25
terminate after 40 seconds
