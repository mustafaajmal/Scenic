"""Curriculum stage 2: bumpy rock with craters/ridges (hard)."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param curriculum_stage = 'bumpy'

asteroid = new ProceduralAsteroid at (Range(-25, 25), Range(-25, 25), -150 + Range(-15, 15)),
    with radiusX Range(38, 65),
    with radiusY Range(30, 55),
    with radiusZ Range(28, 50),
    with subdivisions 3,
    with detailSeed Range(0, 1e9),
    with noiseAmp Range(1.5, 3.5),
    with terrain (
        [new AsteroidBump for _ in range(20)]
        + [new AsteroidCrater for _ in range(16)]
        + [new AsteroidRidge for _ in range(8)]
    )

behavior ScriptedSoftBrake():
    while True:
        if ego.altitude < 22:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(1.0)
        elif ego.altitude < 55 and ego.speed > 1.3:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.75)
        elif ego.speed > 2.5:
            take SetPointingDirectionAction((0, 0, -1)), SetThrottleAction(0.45)
        else:
            take CoastAction()
        wait

ego = new Spacecraft at (Range(-18, 18), Range(-18, 18), Range(12, 55)),
    with velocity (Range(-0.35, 0.35), Range(-0.35, 0.35), Range(-2.4, -1.0)),
    facing toward asteroid,
    with behavior ScriptedSoftBrake

require distance from ego to asteroid > 120
require distance from ego to asteroid < 260

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.altitude < 4
terminate after 60 seconds
