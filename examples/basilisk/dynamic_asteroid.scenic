"""Mars-rover-style procedural asteroid: shape + placement vary each sample.

Mirrors ``examples/webots/mars/narrowGoal.scenic``::

    ground = new MarsGround on (0,0,0), with terrain [new MarsHill for _ in range(60)]

Each ``generate()`` re-samples pose, size, bumps, craters, ridges, and
``detailSeed`` (fine noise). Basilisk rebuilds MuJoCo mesh + albedo for Vizard.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param enable_viz = True
param viz_mode = 'file'

# Terrain list is sampled fresh every Scenic generate() — like Mars hills.
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

behavior SoftBrakeTowardAsteroid():
    while True:
        take PointAtTargetAction(asteroid.position), SetThrottleAction(0.6)
        wait

ego = new Spacecraft at (Range(-70, 70), Range(-70, 70), Range(55, 130)),
    with velocity (Range(-0.8, 0.8), Range(-0.8, 0.8), Range(-1.6, -0.5)),
    facing toward asteroid,
    with behavior SoftBrakeTowardAsteroid

require distance from ego to asteroid > 90
require distance from ego to asteroid < 320

terminate after 25 seconds
