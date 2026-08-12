"""World model for the Basilisk asteroid-landing simulator.

Scenarios should begin with::

    model scenic.simulators.basilisk.model

Requires the ``asteroid-rl-demo`` package on ``PYTHONPATH`` (or sibling
checkout / ``ASTEROID_RL_ROOT``) plus a working Basilisk + MuJoCo install.
"""

from scenic.simulators.basilisk.actions import *
from scenic.simulators.basilisk.simulator import BasiliskSimulator

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = False
param flat_surface_z = -30.0
param enable_viz = False

simulator BasiliskSimulator(
    gravity_mode=globalParameters.gravity_mode,
    max_thrust=globalParameters.max_thrust,
    use_flat_surface=globalParameters.use_flat_surface,
    flat_surface_z=globalParameters.flat_surface_z,
    enable_viz=globalParameters.enable_viz,
)

# Large workspace so approach starts and the asteroid COM marker fit.
workspace = Workspace(BoxRegion(dimensions=(800, 800, 800), position=(0, 0, 0)))

class BasiliskObject:
    """Base class for entities known to the Basilisk interface."""
    basiliskKind: None
    requireVisible: False
    basiliskHandle: None

class Asteroid(BasiliskObject):
    """Itokawa (or flat pad) body already present in the MuJoCo scene.

    Scenic uses this for spatial reasoning; the mesh itself is not re-spawned.
    """
    basiliskKind: 'asteroid'
    width: 40
    length: 40
    height: 40
    allowCollisions: True

class Spacecraft(BasiliskObject):
    """Landing craft mapped to the MuJoCo ``hub`` body (+z thruster).

    Properties:
        throttle (float; dynamic): last commanded throttle in ``[0, 1]``.
        altitude (float; dynamic): approximate altitude above the landing pad.
        velocity (Vector): inertial velocity (read back each step).
    """
    basiliskKind: 'spacecraft'
    width: 2
    length: 2
    height: 2
    throttle[dynamic]: 0.0
    altitude[dynamic]: 0.0
    allowCollisions: True

# Convenience region (XY) above the default pad under (0, 0).
landingPadRegion = RectangularRegion(0 @ 0, 0, 40, 40)
