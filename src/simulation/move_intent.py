"""Describe candidate movements and capacity-based rejections."""

from dataclasses import dataclass

from src.domain import Connection, Drone, Zone


BlockingResource = Zone | Connection


@dataclass(frozen=True)
class MoveIntent:
    """Describe a drone movement requested for the current turn.

    Attributes:
        drone: Drone requesting the movement.
        destination: Adjacent zone the drone intends to enter.
    """

    drone: Drone
    destination: Zone


@dataclass(frozen=True)
class RejectedIntent:
    """Describe a rejected movement and the resource that blocked it.

    Attributes:
        intent: Movement removed from the accepted intents.
        blocked_by: Zone or connection whose capacity caused rejection.
    """

    intent: MoveIntent
    blocked_by: BlockingResource
