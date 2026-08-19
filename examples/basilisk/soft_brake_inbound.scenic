"""MODE A (legacy): already facing the body, inbound soft-brake only.

No divert — assumes velocity is mostly toward the asteroid. Attitude can use
``slew`` (default) or ``instant`` via params.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param attitude_mode = 'slew'
param slew_rate_deg_s = 40.0
param lander_mode = 'soft_brake'

asteroid = new ProceduralAsteroid at (0, 0, -150),
    with radiusX 48,
    with radiusY 48,
    with radiusZ 48,
    with subdivisions 2,
    with detailSeed 7,
    with noiseAmp 0.0,
    with terrain ()

behavior SoftBrakeInbound():
    while True:
        take LanderGuidanceAction('soft_brake')
        wait

ego = new Spacecraft at (Range(-8, 8), Range(-8, 8), Range(35, 70)),
    with velocity (Range(-0.15, 0.15), Range(-0.15, 0.15), Range(-2.2, -1.2)),
    facing toward asteroid,
    with behavior SoftBrakeInbound

require distance from ego to asteroid > 150
require distance from ego to asteroid < 230

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.landed or ego.inContact or ego.altitude < 0.35
terminate after 75 seconds
