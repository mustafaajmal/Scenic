"""Actions for Basilisk spacecraft agents in Scenic."""

from __future__ import annotations

from typing import Sequence

from scenic.core.dynamics.actions import Action


class SetThrottleAction(Action):
    """Set thruster throttle in ``[0, 1]`` (body +z force)."""

    def __init__(self, throttle: float):
        self.throttle = float(throttle)

    def canBeTakenBy(self, agent):
        return hasattr(agent, "basiliskKind") and agent.basiliskKind == "spacecraft"

    def applyTo(self, agent, simulation):
        simulation.backend.set_throttle(self.throttle)
        agent.throttle = self.throttle


class SetPointingDirectionAction(Action):
    """Point body −z (boresight) along an inertial direction, then may fire +z.

    Attitude application respects ``param attitude_mode`` (``slew`` or ``instant``).
    """

    def __init__(self, direction):
        self.direction = direction

    def canBeTakenBy(self, agent):
        return hasattr(agent, "basiliskKind") and agent.basiliskKind == "spacecraft"

    def applyTo(self, agent, simulation):
        d = self.direction
        if hasattr(d, "x"):
            coords = (d.x, d.y, d.z)
        else:
            coords = tuple(d)
        simulation.backend.set_pointing_direction(coords)


class PointAtTargetAction(Action):
    """Point body −z at an inertial target position (slew or instant)."""

    def __init__(self, target):
        self.target = target

    def canBeTakenBy(self, agent):
        return hasattr(agent, "basiliskKind") and agent.basiliskKind == "spacecraft"

    def applyTo(self, agent, simulation):
        t = self.target
        if hasattr(t, "x"):
            coords = (t.x, t.y, t.z)
        else:
            coords = tuple(t)
        simulation.backend.point_at_target(coords)


class CoastAction(Action):
    """Zero throttle (coast under gravity)."""

    def canBeTakenBy(self, agent):
        return hasattr(agent, "basiliskKind") and agent.basiliskKind == "spacecraft"

    def applyTo(self, agent, simulation):
        simulation.backend.set_throttle(0.0)
        agent.throttle = 0.0


class LanderGuidanceAction(Action):
    """One control tick of lander GNC.

    Modes (must match ``scenic.simulators.basilisk.guidance.compute_guidance``):

    * ``soft_brake`` — inbound soft land (legacy Path A style).
    * ``acquire`` — slew to look at body, then soft-brake (no divert).
    * ``divert`` — velocity-target divert if miss/outbound, then terminal soft land.
    """

    def __init__(self, mode: str = "divert"):
        self.mode = str(mode)

    def canBeTakenBy(self, agent):
        return hasattr(agent, "basiliskKind") and agent.basiliskKind == "spacecraft"

    def applyTo(self, agent, simulation):
        cmd = simulation.backend.apply_lander_guidance(self.mode)
        agent.throttle = float(cmd.get("throttle", 0.0) or 0.0)
        if hasattr(agent, "guidancePhase"):
            agent.guidancePhase = str(cmd.get("phase", ""))
