"""Curriculum divert (MODE C): miss traj/attitude — bumpy."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param attitude_mode = 'slew'
param slew_rate_deg_s = 28.0
param curriculum_stage = 'bumpy_divert'
param lander_mode = 'divert'

asteroid = new ProceduralAsteroid at (Range(-25, 25), Range(-25, 25), -150 + Range(-15, 15)),
    with radiusX Range(38, 65), with radiusY Range(30, 55), with radiusZ Range(28, 50),
    with subdivisions 3, with detailSeed Range(0, 1e9), with noiseAmp Range(1.5, 3.5),
    with terrain (
        [new AsteroidBump for _ in range(20)]
        + [new AsteroidCrater for _ in range(16)]
        + [new AsteroidRidge for _ in range(8)]
    )

behavior DivertLand():
    while True:
        take LanderGuidanceAction('divert')
        wait

ego = new Spacecraft at (Range(-40, 40), Range(-40, 40), Range(25, 110)),
    with velocity (Range(-1.8, 1.8), Range(-1.8, 1.8), Range(-1.2, 1.0)),
    facing (Range(0, 360) deg, Range(-80, 80) deg, Range(-180, 180) deg),
    with behavior DivertLand

require distance from ego to asteroid > 125
require distance from ego to asteroid < 270

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.landed or ego.inContact or ego.altitude < 0.35
terminate after 120 seconds
