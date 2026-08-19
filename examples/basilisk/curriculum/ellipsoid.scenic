"""Curriculum stage 1: smooth ellipsoid (medium)."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param curriculum_stage = 'ellipsoid'

asteroid = new ProceduralAsteroid at (Range(-20, 20), Range(-20, 20), -150 + Range(-10, 10)),
    with radiusX Range(40, 60),
    with radiusY Range(30, 50),
    with radiusZ Range(28, 45),
    with subdivisions 2,
    with detailSeed Range(0, 1e6),
    with noiseAmp 0.3,
    with terrain ()

behavior ScriptedSoftBrake():
    while True:
        if ego.altitude < 20:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(1.0)
        elif ego.altitude < 50 and ego.speed > 1.5:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.7)
        elif ego.speed > 2.8:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.4)
        else:
            take CoastAction()
        wait

ego = new Spacecraft at (Range(-12, 12), Range(-12, 12), Range(15, 50)),
    with velocity (Range(-0.2, 0.2), Range(-0.2, 0.2), Range(-2.3, -1.1)),
    facing toward asteroid,
    with behavior ScriptedSoftBrake

require distance from ego to asteroid > 130
require distance from ego to asteroid < 240

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.altitude < 4
terminate after 60 seconds
