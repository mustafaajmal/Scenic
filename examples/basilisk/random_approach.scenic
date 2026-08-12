"""Probabilistic spacecraft approach — Scenic samples, Basilisk/Vizard renders.

Scenic fundamentals: ``Range`` / random facing define a *distribution* over
scenes. Each ``generate()`` draws one concrete scene; Basilisk simulates it and
Vizard displays it (not Scenic's built-in cube visualizer).

Note: the Itokawa mesh in ``sat_ast_landing.xml`` is a welded MuJoCo body, so
its rendered pose is fixed. The Scenic ``Asteroid`` object still anchors
geometry (``facing toward``, distance requires). What you *see* changing in
Vizard is the spacecraft's sampled position/velocity/attitude.
"""

model scenic.simulators.basilisk.model

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = True
param flat_surface_z = -30.0
param enable_viz = True
param viz_mode = 'file'

# Fixed asteroid landmark matching MuJoCo XML COM (rendered mesh stays here).
asteroid = new Asteroid at (0, 0, -150)

behavior SoftBrakeTowardAsteroid():
    while True:
        take PointAtTargetAction(asteroid.position), SetThrottleAction(0.65)
        wait

# Probabilistic spacecraft — this is what varies every sample in Vizard.
ego = new Spacecraft at (Range(-40, 40), Range(-40, 40), Range(50, 120)),
    with velocity (Range(-1.0, 1.0), Range(-1.0, 1.0), Range(-2.0, -0.5)),
    facing toward asteroid,
    with behavior SoftBrakeTowardAsteroid

require distance from ego to asteroid > 90
require distance from ego to asteroid < 300

terminate after 30 seconds
