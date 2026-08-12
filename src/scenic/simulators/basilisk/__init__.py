"""Basilisk simulator interface for Scenic.

This package connects Scenic scenarios to a Basilisk + MuJoCo landing
simulation (via the ``asteroid_rl`` demo package).

Typical usage::

    model scenic.simulators.basilisk.model

    ego = new Spacecraft at (0, 0, 120), with velocity (0, 0, -1.5)

    behavior Brake():
        take SetThrottleAction(0.8)
        wait

    ego = new Spacecraft at (0, 0, 120), with behavior Brake

Requires ``asteroid-rl-demo`` on ``PYTHONPATH`` (or ``ASTEROID_RL_ROOT`` /
sibling directory) and a Basilisk install with MuJoCo support.
"""

try:
    import Basilisk  # noqa: F401
except ImportError as _exc:  # pragma: no cover - optional dependency
    Basilisk = None
    _import_error = _exc
else:
    _import_error = None

if Basilisk is not None:
    from .simulator import BasiliskSimulator, BasiliskSimulation
else:  # pragma: no cover

    def BasiliskSimulator(*_args, **_kwargs):
        raise ImportError(
            "Basilisk is required for scenic.simulators.basilisk "
            f"(import failed: {_import_error})"
        )
