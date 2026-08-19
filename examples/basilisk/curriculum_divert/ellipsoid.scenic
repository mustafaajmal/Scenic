"""Curriculum divert (MODE C): miss traj/attitude — ellipsoid."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param attitude_mode = 'slew'
param slew_rate_deg_s = 28.0
param curriculum_stage = 'ellipsoid_divert'
param lander_mode = 'divert'

asteroid = new ProceduralAsteroid at (Range(-20, 20), Range(-20, 20), -150 + Range(-10, 10)),
    with radiusX Range(40, 60), with radiusY Range(30, 50), with radiusZ Range(28, 45),
    with subdivisions 2, with detailSeed Range(0, 1e6), with noiseAmp 0.3, with terrain ()

behavior DivertLand():
    while True:
        take LanderGuidanceAction('divert')
        wait

ego = new Spacecraft at (Range(-35, 35), Range(-35, 35), Range(30, 100)),
    with velocity (Range(-1.7, 1.7), Range(-1.7, 1.7), Range(-1.1, 0.9)),
    facing (Range(0, 360) deg, Range(-80, 80) deg, Range(-180, 180) deg),
    with behavior DivertLand

require distance from ego to asteroid > 135
require distance from ego to asteroid < 260

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.landed or ego.inContact or ego.altitude < 0.35
terminate after 120 seconds
