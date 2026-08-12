"""Same as soft_brake.scenic but with Vizard visualization enabled."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = True
param flat_surface_z = -30.0
param enable_viz = True
# Windows: auto → save-file .bin (open in Vizard after). macOS: liveStream.
param viz_mode = 'auto'

behavior SoftBrake():
    while True:
        take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.7)
        wait

ego = new Spacecraft at (0, 0, 80),
    with velocity (0, 0, -1.2),
    with behavior SoftBrake

require ego.position.z > -25
terminate after 40 seconds
