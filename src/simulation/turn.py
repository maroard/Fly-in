"""Record the moving drones and destinations of each turn."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Movement:
    """Record one drone destination during a simulation turn.

    Attributes:
        drone_id: Identifier of the drone that moved.
        destination: Destination zone or restricted connection name.
    """

    drone_id: int
    destination: str


@dataclass
class Turn:
    """Collect the ordered movements recorded for one numbered turn.

    Attributes:
        number: One-based simulation turn number.
        movements: Recorded moves; stationary drones have no entry.
    """

    number: int
    movements: list[Movement] = field(default_factory=list)
