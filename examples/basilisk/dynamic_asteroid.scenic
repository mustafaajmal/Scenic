"""Showcase procedural rock with full divert lander (MODE C).

For MODE A / B see ``soft_brake_inbound.scenic`` and ``acquire_and_land.scenic``.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = True
param viz_mode = 'file'
param timestep = 0.25
param attitude_mode = 'slew'
param slew_rate_deg_s = 28.0

asteroid = new ProceduralAsteroid at (Range(-40, 40), Range(-40, 40), -150 + Range(-25, 25)),
    with radiusX Range(35, 75),
    with radiusY Range(28, 65),
    with radiusZ Range(25, 55),
    with subdivisions 3,
    with detailSeed Range(0, 1e9),
    with noiseAmp Range(1.5, 3.8),
    with terrain (
        [new AsteroidBump for _ in range(28)]
        + [new AsteroidCrater for _ in range(22)]
        + [new AsteroidRidge for _ in range(12)]
    )

behavior DivertAcquireLand():
    while True:
        take LanderGuidanceAction('divert')
        wait

ego = new Spacecraft at (Range(-70, 70), Range(-70, 70), Range(55, 130)),
    with velocity (Range(-1.5, 1.5), Range(-1.5, 1.5), Range(-1.4, 0.6)),
    facing (Range(0, 360) deg, Range(-75, 75) deg, Range(-180, 180) deg),
    with behavior DivertAcquireLand

require distance from ego to asteroid > 90
require distance from ego to asteroid < 320

terminate after 90 seconds
