"""Collect the fleet state and completed simulation turns."""

from dataclasses import dataclass, field

from src.domain.drone import Drone
from src.simulation.turn import Turn


@dataclass
class SimulationState:
    """Collect mutable drone states and the recorded simulation turns.

    Attributes:
        drones: Fleet states updated as simulation turns execute.
        turns: Completed turns recorded in execution order.
    """

    drones: list[Drone]
    turns: list[Turn] = field(default_factory=list)
