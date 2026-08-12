"""World model for the Basilisk asteroid-landing simulator.

Scenarios should begin with::

    model scenic.simulators.basilisk.model

Supports stock Itokawa (``Asteroid``) or Mars-style procedural rocks
(``ProceduralAsteroid`` + bump/crater/ridge terrain).
"""

from scenic.simulators.basilisk.actions import *
from scenic.simulators.basilisk.simulator import BasiliskSimulator

param gravity_mode = 'constant'
param max_thrust = 275.0
param use_flat_surface = False
param flat_surface_z = -30.0
param enable_viz = False
param viz_mode = 'auto'
param viz_save_file = ''
param timestep = 0.25
param asteroid_rl_root = ''

simulator BasiliskSimulator(
    asteroid_rl_root=globalParameters.asteroid_rl_root,
    gravity_mode=globalParameters.gravity_mode,
    max_thrust=globalParameters.max_thrust,
    use_flat_surface=globalParameters.use_flat_surface,
    flat_surface_z=globalParameters.flat_surface_z,
    enable_viz=globalParameters.enable_viz,
    viz_mode=globalParameters.viz_mode,
    viz_save_file=globalParameters.viz_save_file,
    default_timestep=globalParameters.timestep,
)

workspace = Workspace(BoxRegion(dimensions=(800, 800, 800), position=(0, 0, 0)))

class BasiliskObject:
    """Base class for entities known to the Basilisk interface."""
    basiliskKind: None
    requireVisible: False
    basiliskHandle: None

class Asteroid(BasiliskObject):
    """Stock Itokawa mesh already in the default MuJoCo XML (fixed shape)."""
    basiliskKind: 'asteroid'
    width: 40
    length: 40
    height: 40
    allowCollisions: True

class AsteroidBump(BasiliskObject):
    """Gaussian hill on a ``ProceduralAsteroid`` (like Mars ``Hill``)."""
    basiliskKind: 'asteroid_bump'
    allowCollisions: False
    requireVisible: False
    position: new Point in BoxRegion(dimensions=(140, 140, 140), position=(0, 0, -150))
    bumpHeight: Range(5.0, 20.0)
    spread: Range(7.0, 24.0)
    width: 1
    length: 1
    height: 1
    regionContainedIn: everywhere

class AsteroidCrater(BasiliskObject):
    """Bowl + rim crater folded into the procedural mesh."""
    basiliskKind: 'asteroid_crater'
    allowCollisions: False
    requireVisible: False
    position: new Point in BoxRegion(dimensions=(140, 140, 140), position=(0, 0, -150))
    craterDepth: Range(3.0, 14.0)
    craterRadius: Range(4.0, 16.0)
    rimHeight: Range(1.0, 5.0)
    width: 1
    length: 1
    height: 1
    regionContainedIn: everywhere

class AsteroidRidge(BasiliskObject):
    """Elongated ridge folded into the procedural mesh."""
    basiliskKind: 'asteroid_ridge'
    allowCollisions: False
    requireVisible: False
    position: new Point in BoxRegion(dimensions=(140, 140, 140), position=(0, 0, -150))
    ridgeHeight: Range(4.0, 16.0)
    ridgeLength: Range(12.0, 40.0)
    ridgeWidth: Range(3.0, 10.0)
    # Tangent-ish direction sampled in Scenic (normalized in the mesh builder).
    ridgeDir: (Range(-1, 1), Range(-1, 1), Range(-1, 1))
    width: 1
    length: 1
    height: 1
    regionContainedIn: everywhere

class ProceduralAsteroid(BasiliskObject):
    """Dynamically generated asteroid; rebuilt each Scenic ``generate()``.

    Analogous to Webots/MuJoCo ``Ground`` with a ``terrain`` list: each sample
    draws new size/pose/terrain and a ``detailSeed`` so fine noise also changes.
    """
    basiliskKind: 'procedural_asteroid'
    allowCollisions: True
    radiusX: Range(35, 65)
    radiusY: Range(30, 55)
    radiusZ: Range(28, 50)
    width: 2 * self.radiusX
    length: 2 * self.radiusY
    height: 2 * self.radiusZ
    subdivisions: 3
    # Sampled every generate() — drives multi-octave surface noise + albedo.
    detailSeed: Range(0, 1e9)
    noiseAmp: Range(1.2, 3.5)
    terrain: ()

class Spacecraft(BasiliskObject):
    """Landing craft mapped to the MuJoCo ``hub`` body (+z thruster)."""
    basiliskKind: 'spacecraft'
    width: 2
    length: 2
    height: 2
    throttle[dynamic]: 0.0
    altitude[dynamic]: 0.0
    allowCollisions: True

landingPadRegion = RectangularRegion(0 @ 0, 0, 40, 40)
