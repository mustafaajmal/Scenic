"""Curriculum divert (MODE C): miss traj/attitude — sphere."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param attitude_mode = 'slew'
param slew_rate_deg_s = 28.0
param curriculum_stage = 'sphere_divert'
param lander_mode = 'divert'

asteroid = new ProceduralAsteroid at (0, 0, -150),
    with radiusX 45, with radiusY 45, with radiusZ 45,
    with subdivisions 2, with detailSeed 1, with noiseAmp 0.0, with terrain ()

behavior DivertLand():
    while True:
        take LanderGuidanceAction('divert')
        wait

ego = new Spacecraft at (Range(-30, 30), Range(-30, 30), Range(35, 95)),
    with velocity (Range(-1.6, 1.6), Range(-1.6, 1.6), Range(-1.0, 0.8)),
    facing (Range(0, 360) deg, Range(-75, 75) deg, Range(-180, 180) deg),
    with behavior DivertLand

require distance from ego to asteroid > 145
require distance from ego to asteroid < 250

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.landed or ego.inContact or ego.altitude < 0.35
terminate after 180 seconds
