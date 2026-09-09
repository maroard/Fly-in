from dataclasses import dataclass, field

from src.domain.drone import Drone
from src.simulation.turn import Turn


@dataclass
class SimulationState:
    drones: list[Drone]
    turns: list[Turn] = field(default_factory=list)
