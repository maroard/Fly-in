from dataclasses import dataclass

from src.domain import Connection, Drone, Zone


BlockingResource = Zone | Connection


@dataclass(frozen=True)
class MoveIntent:
    drone: Drone
    destination: Zone


@dataclass(frozen=True)
class RejectedIntent:
    """Describe a rejected movement and the resource that blocked it."""

    intent: MoveIntent
    blocked_by: BlockingResource
