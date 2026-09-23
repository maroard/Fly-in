from dataclasses import dataclass

from src.domain import Drone, Zone


@dataclass(frozen=True)
class MoveIntent:
    drone: Drone
    destination: Zone
