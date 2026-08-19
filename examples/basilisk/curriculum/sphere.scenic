"""Curriculum stage 0: smooth sphere (easy)."""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = False
param timestep = 0.25
param curriculum_stage = 'sphere'

asteroid = new ProceduralAsteroid at (0, 0, -150),
    with radiusX 45,
    with radiusY 45,
    with radiusZ 45,
    with subdivisions 2,
    with detailSeed 1,
    with noiseAmp 0.0,
    with terrain ()

behavior ScriptedSoftBrake():
    """Descend under gravity; brake only when closing too fast or near surface."""
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

ego = new Spacecraft at (Range(-8, 8), Range(-8, 8), Range(20, 45)),
    with velocity (Range(-0.15, 0.15), Range(-0.15, 0.15), Range(-2.2, -1.2)),
    facing toward asteroid,
    with behavior ScriptedSoftBrake

require distance from ego to asteroid > 140
require distance from ego to asteroid < 220

record ego.altitude as altitude_m
record ego.speed as speed_mps
record ego.throttle as throttle
record ego.position.z as z_m

terminate when ego.altitude < 4
terminate after 60 seconds
