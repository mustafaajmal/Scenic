"""MODE B: miss-pointed attitude → acquire (slew look-at-body) → soft land.

Still assumes a roughly inbound approach. Does *not* correct large trajectory
misses — use ``divert_and_land.scenic`` for that.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param attitude_mode = 'slew'
param slew_rate_deg_s = 30.0
param lander_mode = 'acquire'

asteroid = new ProceduralAsteroid at (Range(-20, 20), Range(-20, 20), -150 + Range(-12, 12)),
    with radiusX Range(40, 58),
    with radiusY Range(35, 52),
    with radiusZ Range(30, 48),
    with subdivisions 3,
    with detailSeed Range(0, 1e9),
    with noiseAmp Range(0.8, 2.5),
    with terrain (
        [new AsteroidBump for _ in range(12)]
        + [new AsteroidCrater for _ in range(10)]
    )

behavior AcquireThenLand():
    while True:
        take LanderGuidanceAction('acquire')
        wait

ego = new Spacecraft at (Range(-22, 22), Range(-22, 22), Range(30, 80)),
    with velocity (Range(-0.35, 0.35), Range(-0.35, 0.35), Range(-2.3, -1.0)),
    facing (Range(0, 360) deg, Range(-75, 75) deg, Range(-180, 180) deg),
    with behavior AcquireThenLand

require distance from ego to asteroid > 120
require distance from ego to asteroid < 240

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.landed or ego.inContact or ego.altitude < 0.35
terminate after 90 seconds
